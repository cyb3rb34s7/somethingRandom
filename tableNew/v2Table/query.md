# TVPCMS-1777: Asset Export Performance Optimization

## Table of Contents

1. [Current Architecture Overview](#1-current-architecture-overview)
2. [Identified Bottlenecks](#2-identified-bottlenecks)
3. [Proposed Fixes — Summary](#3-proposed-fixes--summary)
4. [Fix #1 In Detail — Splitting One-to-Many Collection Joins](#4-fix-1-in-detail--splitting-one-to-many-collection-joins)
5. [Functionality Preservation & Filter Handling](#5-functionality-preservation--filter-handling)
6. [Real-World Scenario & Time Estimates](#6-real-world-scenario--time-estimates)
7. [Tradeoffs](#7-tradeoffs)

---

## 1. Current Architecture Overview

### Endpoint

```
POST /cms/tvplus/asset/export
```

The caller (batch module) fetches all assets by making parallel threaded calls with paginated requests:

```
Thread 1 → offset=0,     limit=5000
Thread 2 → offset=5000,  limit=5000
Thread 3 → offset=10000, limit=5000
...continues until all assets fetched
```

### Call Flow

```
VodAssetController.getAssetsForExport()
    → VodAssetServiceImpl.getAssetsForExport()
        → Utils.getColumnMapping()                        // Map UI columns → DB columns
        → VodAssetExportMapper.getAssetsForExport()       // Single massive SQL query
        → Per-asset post-processing loop (×5000):
            → utils.getLicenseWindow()
            → utils.getStatus()
            → utils.checkExternalAsset()
            → utils.setExternalProviderData()
            → utils.checkLiveOnDevice()
            → Utils.retainOnlyFields()                    // Reflection-based field filtering
```

### SQL Query Structure

The MyBatis query in `VodAssetExportMapper.xml` executes as a two-layer nested structure:

```sql
-- OUTER QUERY (filteredAssetQueryRef)
SELECT DISTINCT [100+ columns including collection data]
FROM (
    -- INNER QUERY (contentTablePaginationQuery)
    SELECT *, ROW_NUMBER() OVER(ORDER BY feed_worker_priority, sort, content_id) RN
    FROM STD_VC_VOD_CONTENT SVVC_INTERNAL
      LEFT JOIN STD_VC_VOD_CONTENT      SVVC_SEASON    -- self-join for season
      LEFT JOIN STD_VC_VOD_CONTENT      SVVC_SHOW      -- self-join for show
      LEFT JOIN STD_VC_VOD_CP           SVC_INTERNAL   -- content partner name
    WHERE [filters on main table columns]
    AND   [1=1 for EXT/DRM/HISTORY filters — deferred to outer]
) SVVC
WHERE RN BETWEEN :offset AND :limit    -- pagination: 5000 rows

-- Outer joins for column data + filtering
LEFT JOIN STD_VC_VOD_CONTENT                SVVC_SEASON   -- DUPLICATE (already in inner)
LEFT JOIN STD_VC_VOD_CONTENT                SVVC_SHOW     -- DUPLICATE (already in inner)
LEFT JOIN STD_VC_VOD_CP                     SVC           -- DUPLICATE (already in inner)
LEFT JOIN STD_VC_VOD_DRM                    DRM           -- one-to-many
LEFT JOIN STD_VC_VOD_EXTERNALID             EXT           -- one-to-many
LEFT JOIN STD_VC_VOD_CONTENT_PARENTAL_RATINGS RATING      -- one-to-many
LEFT JOIN STD_VC_VOD_CAST                   CAST          -- one-to-many
LEFT JOIN STD_CMS_VOD_ASSET_LICENSE         LICENSE       -- one-to-many
LEFT JOIN STD_CMS_VOD_ASSET_EVENT           EVENT         -- one-to-many
LEFT JOIN STD_CMS_VOD_CONTENT_LAST_STATUS   LAST_STATUS   -- one-to-one
LEFT JOIN STD_VC_VOD_CONTENT_GEO_RESTRICTIONS GEO         -- one-to-many
LEFT JOIN STD_VC_CNTY_CD_LANG_MAP           MAP           -- one-to-one
LEFT JOIN STD_CMS_VOD_LANG_TEXT             CMS           -- one-to-one

WHERE [all filters applied AGAIN on outer result]
ORDER BY [feed_worker_priority, sort, content_id]         -- DUPLICATE of inner ORDER BY
```

MyBatis then uses a `resultMap` with `<collection>` elements to collapse the exploded rows back into Java objects with nested lists (cast, ratings, licenseWindowList, eventWindowList, geoRestrictions, externalProvider, etc.).

---

## 2. Identified Bottlenecks

### Bottleneck #1 (CRITICAL): Cartesian Product from Multiple One-to-Many JOINs

**File**: `VodAssetExportMapper.xml`, lines 1533-1621 (filteredAssetQueryRef)

**Problem**: The outer query LEFT JOINs 6 one-to-many tables simultaneously:

| Table | Collection Field | Typical Rows Per Asset |
|-------|-----------------|----------------------|
| `STD_VC_VOD_CAST` | cast | 1–5 |
| `STD_VC_VOD_CONTENT_PARENTAL_RATINGS` | parentalRatings | 1–3 |
| `STD_CMS_VOD_ASSET_LICENSE` | licenseWindowList | 1–3 |
| `STD_CMS_VOD_ASSET_EVENT` | eventWindowList | 0–10 |
| `STD_VC_VOD_CONTENT_GEO_RESTRICTIONS` | geoRestrictions | 0–3 |
| `STD_VC_VOD_EXTERNALID` | externalProvider | 0–2 |

When multiple one-to-many tables are joined in the same query, Oracle produces the **cartesian product** of all related rows for each asset.

**Example from actual sample data** — asset `TBPS_valid_Music_20251204_1437`:
- 2 cast × 1 rating × 3 license windows × 10 event windows × 1 external provider = **60 rows** for 1 asset

**At scale**: For 5000 assets, with modest averages (3 cast × 2 ratings × 2 license × 3 events × 1 geo × 1 ext = 36x multiplier), Oracle materializes approximately **180,000 rows**. With high cardinality assets (like the music asset above with 10 events), this can exceed **500,000 rows**.

The `SELECT DISTINCT` on line 303 then attempts to deduplicate all these rows — which requires Oracle to sort or hash 100+ column-wide rows. This is extremely memory and CPU intensive, often spilling to temporary tablespace on disk.

**Estimated cost**: 60-75% of total query time.

---

### Bottleneck #2 (HIGH): Duplicate JOINs — SEASON, SHOW, CP Joined Twice

**File**: `VodAssetExportMapper.xml`

The following tables are joined in the **inner** pagination subquery (lines 1001-1020):
- `STD_VC_VOD_CONTENT SVVC_SEASON` — for SEASON_TITLE filter support
- `STD_VC_VOD_CONTENT SVVC_SHOW` — for SHOW_TITLE filter support
- `STD_VC_VOD_CP SVC_INTERNAL` — for VC_CP_NM filter support

Then the **exact same tables** are joined again in the outer query (lines 1540-1557):
- `STD_VC_VOD_CONTENT SVVC_SEASON`
- `STD_VC_VOD_CONTENT SVVC_SHOW`
- `STD_VC_VOD_CP SVC`

This creates 6 self-joins to `STD_VC_VOD_CONTENT` when only 3 are needed. The inner query could carry these values forward (select SHOW_TITLE, SEASON_TITLE, VC_CP_NM in the inner query) so the outer query doesn't need to re-join.

**Estimated cost**: 10-15% of total query time.

---

### Bottleneck #3 (HIGH): Duplicate WHERE Filters Applied Twice

**File**: `VodAssetExportMapper.xml`, lines 1021-1525 (inner) and line 1621 (outer)

The `totalFilters` SQL fragment is included in both:
1. The inner pagination subquery — filters before ROW_NUMBER pagination
2. The outer query via `<include refid="totalFilters" />` at line 1621

All filter conditions (search, filter, dateRange types) are evaluated twice. Filters involving `LOWER()`, `TO_DATE()`, `TRUNC()` are computationally expensive. The inner query already filtered the data correctly before pagination. Re-applying the same filters on the already-filtered 5000 rows is redundant.

**Note**: Some filters (`EXT_ID`, `DRM`, `HISTORY`) are intentionally `1 = 1` in the inner query and only applied in the outer query. These specific filters are the exception and must be preserved. All other filters are purely duplicated.

**Estimated cost**: 5-10% of total query time.

---

### Bottleneck #4 (MEDIUM): Duplicate ORDER BY

**File**: `VodAssetExportMapper.xml`, lines 986-998 (inner) and lines 1626-1638 (outer)

The ORDER BY clause with the feed worker CASE priority expression and dynamic sort columns appears twice:
1. Inside `ROW_NUMBER() OVER(ORDER BY ...)` in the inner query
2. In the final `ORDER BY` of the outer SELECT

After pagination via `RN BETWEEN`, the 5000 rows are already in the correct order. Re-sorting with the same complex CASE expression is redundant. A simple `ORDER BY RN` (or no ORDER BY at all if the row order from RN is preserved) would suffice.

**Estimated cost**: 3-5% of total query time.

---

### Bottleneck #5 (MEDIUM): SELECT DISTINCT on Wide Rows

**File**: `VodAssetExportMapper.xml`, line 303

`SELECT DISTINCT` is necessary in the current design because the one-to-many JOINs produce duplicate rows. However, the deduplication must compare every column in the result set (100+ columns including long VARCHAR fields like `STREAM_URI`, `DEEPLINK_PAYLOAD`, image URLs). This is expensive.

This bottleneck disappears automatically when Bottleneck #1 is fixed (no more cartesian product = no more duplicates = no need for DISTINCT).

---

### Bottleneck #6 (MEDIUM): `${column}` String Interpolation Prevents SQL Caching

**File**: `VodAssetExportMapper.xml`, lines 443, 995, 1079, and others

MyBatis `${...}` syntax injects raw strings into the SQL, producing a unique SQL text for every different combination of requested columns, sort fields, and filter keys. Oracle must hard-parse each unique SQL string (no cursor sharing or execution plan caching).

Examples:
```xml
SVVC.${column}                    <!-- line 443 -->
SVVC_INTERNAL.${sort.field} ${sort.order}  <!-- line 995 -->
SVVC.${operation.key}             <!-- line 521 (via otherwise) -->
```

---

### Bottleneck #7 (LOW): Reflection-Based `retainOnlyFields`

**File**: `Utils.java`, lines 63-82

For each of the 5000 assets, this method uses Java reflection to:
1. Iterate ALL declared fields of `VodAssetDto` (~80+ fields)
2. For each field not in the retain list, look up the setter method via `getDeclaredMethod()`
3. Invoke the setter with `null`

That is approximately 80 × 5000 = **400,000 reflective operations** per request.

---

### Bottleneck #8 (LOW): `LOWER()` and `TO_DATE()`/`TRUNC()` on Every Row

**File**: `VodAssetExportMapper.xml`, throughout `totalFilters`

- `LOWER(column) LIKE LOWER(...)` prevents Oracle from using B-tree indexes on those columns.
- `TRUNC(TO_DATE(varchar_column, format))` converts VARCHAR date columns at runtime for every row, preventing index usage and adding CPU cost.

---

## 3. Proposed Fixes — Summary

| # | Fix | Targets Bottleneck | Impact | Complexity |
|---|-----|-------------------|--------|------------|
| **1** | **Split one-to-many collection JOINs into separate batch queries** | #1, #5 | Very High (~50-80% time reduction) | Medium |
| **2** | Remove duplicate SEASON/SHOW/CP joins by carrying values from inner query | #2 | Medium (~10-15%) | Low |
| **3** | Remove redundant outer `totalFilters` (keep only EXT/DRM/HISTORY handling) | #3 | Medium (~5-10%) | Low |
| **4** | Replace outer ORDER BY with `ORDER BY RN` | #4 | Low-Medium (~3-5%) | Trivial |
| **5** | Replace `retainOnlyFields` reflection with Set-based approach or skip unneeded columns entirely | #7 | Low | Low |
| **6** | Investigate Oracle function-based index equivalents using query hints | #8 | Low | Low |

**Fix #1 is the primary recommendation** and is detailed in the next section. Fixes #2-#4 can be applied independently or alongside Fix #1 for cumulative benefit.

---

## 4. Fix #1 In Detail — Splitting One-to-Many Collection Joins

### 4.1 The Core Idea

Instead of one query that JOINs all 6 one-to-many tables (creating a cartesian product), split into:

1. **One main query** — fetches 5000 assets with scalar/one-to-one fields only (no row explosion)
2. **Six batch queries** — each fetches flat collection data for those 5000 assets from one table
3. **Java assembly** — groups batch results by composite key and attaches them to the DTOs

### 4.2 Classifying Each Joined Table

Every table currently joined in the outer query falls into one of these categories:

#### Category A: Many-to-One / One-to-One (KEEP in main query)

These joins produce at most 1 row per asset. No explosion risk.

| Table | Alias | Purpose | Why Safe |
|-------|-------|---------|----------|
| `STD_VC_VOD_CONTENT` | SVVC_SEASON | Get SEASON_TITLE | One season per asset |
| `STD_VC_VOD_CONTENT` | SVVC_SHOW | Get SHOW_TITLE | One show per asset |
| `STD_VC_VOD_CP` | SVC | Get VC_CP_NM (TI Name) | One CP per (VC_CP_ID, CNTY_CD) |
| `STD_CMS_VOD_CONTENT_LAST_STATUS` | LAST_STATUS | HISTORY filter | One status per asset |
| `STD_VC_CNTY_CD_LANG_MAP` | MAP | Language mapping | One mapping per country |
| `STD_CMS_VOD_LANG_TEXT` | CMS | Language text | One text per language code |

**Action**: No change. These remain in the main query.

#### Category B: One-to-Many, NO filters reference them (REMOVE from main query, batch-fetch)

These tables are purely for collection data. No filter in `totalFilters` references them.

| Table | Alias | Collection Field | Avg Rows/Asset |
|-------|-------|-----------------|----------------|
| `STD_VC_VOD_CAST` | CAST | cast | 1-5 |
| `STD_VC_VOD_CONTENT_PARENTAL_RATINGS` | RATING | parentalRatings | 1-3 |
| `STD_CMS_VOD_ASSET_LICENSE` | LICENSE | licenseWindowList | 1-3 |
| `STD_CMS_VOD_ASSET_EVENT` | EVENT | eventWindowList | 0-10 |
| `STD_VC_VOD_CONTENT_GEO_RESTRICTIONS` | GEO | geoRestrictions | 0-3 |

**Action**: Remove LEFT JOINs from main query. Fetch via separate batch queries. **Zero filter risk** — no filter logic touches these tables.

#### Category C: One-to-Many, filters DO reference them (REPLACE join with EXISTS)

| Table | Alias | Filter Usage | Collection Data? |
|-------|-------|-------------|-----------------|
| `STD_VC_VOD_DRM` | DRM | `DRM` filter (Yes/No) | Only scalar IS_DRM flag |
| `STD_VC_VOD_EXTERNALID` | EXT | `EXTERNAL_PROGRAM_ID`, `EXT_ID`, `EXT_PROVIDER` search filters | Yes (externalProvider collection) |

**Action**: Replace LEFT JOINs with `EXISTS` subqueries for filtering. Fetch EXT collection data via batch query. Details below.

### 4.3 Changes to the Main Query

#### Current outer query structure (simplified):

```sql
SELECT DISTINCT
    SVVC.CONTENT_ID, ...,
    CASE WHEN DRM.PROGRAM_ID IS NOT NULL THEN 'Yes' ELSE 'No' END as IS_DRM,
    EXT.EXTERNAL_PROGRAM_ID as EXTERNAL_PROGRAM_ID_LIST,
    EXT.ID_TYPE, EXT.VC_CP_ID as EXT_VC_CP_ID, EXT.PROVIDER as EXT_PROVIDER_LIST,
    RATING."BODY" as RATING_BODY, RATING.CODE,
    CAST.CHARACTER_NAME, CAST."ROLE", CAST.NAME,
    LICENSE.AVAILABLE_STARTING as WINDOW_AVAILABLE_STARTING, ...,
    EVENT.EVENT_ID as WINDOW_EVENT_ID, ...,
    GEO.ACCESS_TYPE as GEO_ACCESS_TYPE, ...
FROM ( <paginated 5000 rows> ) SVVC
LEFT JOIN DRM ON (...)
LEFT JOIN EXT ON (...)
LEFT JOIN RATING ON (...)
LEFT JOIN CAST ON (...)
LEFT JOIN LICENSE ON (...)
LEFT JOIN EVENT ON (...)
LEFT JOIN GEO ON (...)
LEFT JOIN LAST_STATUS ON (...)
LEFT JOIN MAP ON (...)
LEFT JOIN CMS ON (...)
WHERE [totalFilters including DRM.PROGRAM_ID IS NOT NULL, EXT.EXTERNAL_PROGRAM_ID LIKE ...]
ORDER BY [complex ordering]
```

#### New outer query structure:

```sql
SELECT                              -- NO DISTINCT needed
    SVVC.CONTENT_ID, ...,
    -- DRM: EXISTS subquery replaces LEFT JOIN
    CASE
        WHEN EXISTS (
            SELECT 1 FROM ITVSTD_O.STD_VC_VOD_DRM DRM
            WHERE DRM.PROGRAM_ID = SVVC.CONTENT_ID
            AND DRM.PROVIDER_ID = SVVC.VC_CP_ID
            AND DRM.COUNTRY_CD = SVVC.CNTY_CD
        ) THEN 'Yes'
        ELSE 'No'
    END as IS_DRM
    -- NO EXT columns (fetched in batch)
    -- NO RATING columns (fetched in batch)
    -- NO CAST columns (fetched in batch)
    -- NO LICENSE columns (fetched in batch)
    -- NO EVENT columns (fetched in batch)
    -- NO GEO columns (fetched in batch)
FROM ( <paginated 5000 rows> ) SVVC
LEFT JOIN SVVC_SEASON ON (...)      -- KEEP: many-to-one
LEFT JOIN SVVC_SHOW ON (...)        -- KEEP: many-to-one
LEFT JOIN SVC ON (...)              -- KEEP: many-to-one
LEFT JOIN LAST_STATUS ON (...)      -- KEEP: one-to-one, used for HISTORY filter
LEFT JOIN MAP ON (...)              -- KEEP: one-to-one
LEFT JOIN CMS ON (...)              -- KEEP: one-to-one
-- NO DRM join
-- NO EXT join
-- NO RATING join
-- NO CAST join
-- NO LICENSE join
-- NO EVENT join
-- NO GEO join
WHERE
    SVVC.IS_DELETE = 'N'
    -- DRM filter: replaced with EXISTS
    -- EXT filter: replaced with EXISTS
    -- HISTORY filter: LAST_STATUS.LAST_QC_STATE = 2 (unchanged, join kept)
    -- All other filters: unchanged (they reference SVVC.* columns)
ORDER BY SVVC.RN                    -- simplified, order established by inner query
```

### 4.4 DRM Filter Conversion (EXISTS)

**Current** (uses LEFT JOIN + column check):
```xml
<!-- In exportSelectedColumns -->
<when test="column == 'DRM'">
    CASE WHEN DRM.PROGRAM_ID IS NOT NULL THEN 'Yes' ELSE 'No' END as IS_DRM
</when>

<!-- In totalFilters (DRM=Yes) -->
DRM.PROGRAM_ID IS NOT NULL

<!-- In totalFilters (DRM=No) -->
DRM.PROGRAM_ID IS NULL
```

**New** (uses EXISTS subquery):
```xml
<!-- In exportSelectedColumns -->
<when test="column == 'DRM'">
    CASE
        WHEN EXISTS (
            SELECT 1 FROM ITVSTD_O.STD_VC_VOD_DRM DRM
            WHERE DRM.PROGRAM_ID = SVVC.CONTENT_ID
            AND DRM.PROVIDER_ID = SVVC.VC_CP_ID
            AND DRM.COUNTRY_CD = SVVC.CNTY_CD
        ) THEN 'Yes'
        ELSE 'No'
    END as IS_DRM
</when>

<!-- In totalFilters (DRM=Yes) -->
EXISTS (
    SELECT 1 FROM ITVSTD_O.STD_VC_VOD_DRM DRM
    WHERE DRM.PROGRAM_ID = SVVC.CONTENT_ID
    AND DRM.PROVIDER_ID = SVVC.VC_CP_ID
    AND DRM.COUNTRY_CD = SVVC.CNTY_CD
)

<!-- In totalFilters (DRM=No) -->
NOT EXISTS (
    SELECT 1 FROM ITVSTD_O.STD_VC_VOD_DRM DRM
    WHERE DRM.PROGRAM_ID = SVVC.CONTENT_ID
    AND DRM.PROVIDER_ID = SVVC.VC_CP_ID
    AND DRM.COUNTRY_CD = SVVC.CNTY_CD
)
```

**Why this is functionally identical**: `EXISTS (SELECT 1 FROM DRM WHERE ...)` returns TRUE when at least one DRM row exists for that asset — exactly the same as `LEFT JOIN DRM ... WHERE DRM.PROGRAM_ID IS NOT NULL`. The difference is that `EXISTS` **stops at the first match** and does not produce additional joined rows.

### 4.5 EXT Filter Conversion (EXISTS)

**Current** (uses LEFT JOIN + column filter):
```xml
<!-- EXTERNAL_PROGRAM_ID search -->
LOWER(EXT.EXTERNAL_PROGRAM_ID) LIKE LOWER(q'[%${value}%]')

<!-- EXT_PROVIDER search -->
LOWER(EXT.PROVIDER) LIKE LOWER(q'[%${value}%]')
```

**New** (uses EXISTS):
```xml
<!-- EXTERNAL_PROGRAM_ID search -->
EXISTS (
    SELECT 1 FROM ITVSTD_O.STD_VC_VOD_EXTERNALID EXT
    WHERE EXT.PROGRAM_ID = SVVC.CONTENT_ID
    AND EXT.VC_CP_ID = SVVC.VC_CP_ID
    AND EXT.COUNTRY_CD = SVVC.CNTY_CD
    AND LOWER(EXT.EXTERNAL_PROGRAM_ID) LIKE LOWER(q'[%${value}%]')
)

<!-- EXT_PROVIDER search -->
EXISTS (
    SELECT 1 FROM ITVSTD_O.STD_VC_VOD_EXTERNALID EXT
    WHERE EXT.PROGRAM_ID = SVVC.CONTENT_ID
    AND EXT.VC_CP_ID = SVVC.VC_CP_ID
    AND EXT.COUNTRY_CD = SVVC.CNTY_CD
    AND LOWER(EXT.PROVIDER) LIKE LOWER(q'[%${value}%]')
)
```

**EXT collection data** (EXTERNAL_PROGRAM_ID_LIST, ID_TYPE, EXT_VC_CP_ID, EXT_PROVIDER_LIST) is fetched via a batch query instead.

### 4.6 Batch Collection Queries

Six new mapper methods, each executing a simple flat query:

```sql
-- Batch: Cast
SELECT CONTENT_ID, VC_CP_ID, CNTY_CD, CHARACTER_NAME, "ROLE", NAME
FROM ITVSTD_O.STD_VC_VOD_CAST
WHERE (CONTENT_ID, VC_CP_ID, CNTY_CD) IN
    (SELECT CONTENT_ID, VC_CP_ID, CNTY_CD FROM ( <same pagination subquery> ))

-- Batch: Parental Ratings
SELECT CONTENT_ID, VC_CP_ID, CNTY_CD, "BODY" AS RATING_BODY, CODE
FROM ITVSTD_O.STD_VC_VOD_CONTENT_PARENTAL_RATINGS
WHERE (CONTENT_ID, VC_CP_ID, CNTY_CD) IN
    (SELECT CONTENT_ID, VC_CP_ID, CNTY_CD FROM ( <same pagination subquery> ))

-- Batch: License Windows
SELECT PROGRAM_ID, PROVIDER_ID, COUNTRY_CD,
       AVAILABLE_STARTING, EXP_DATE, LICENSE_ID
FROM ITVSTD_O.STD_CMS_VOD_ASSET_LICENSE
WHERE (PROGRAM_ID, PROVIDER_ID, COUNTRY_CD) IN
    (SELECT CONTENT_ID, VC_CP_ID, CNTY_CD FROM ( <same pagination subquery> ))

-- Batch: Event Windows
SELECT PROGRAM_ID, PROVIDER_ID, COUNTRY_CD,
       EVENT_ID, EVENT_STARTING, EVENT_ENDING
FROM ITVSTD_O.STD_CMS_VOD_ASSET_EVENT
WHERE (PROGRAM_ID, PROVIDER_ID, COUNTRY_CD) IN
    (SELECT CONTENT_ID, VC_CP_ID, CNTY_CD FROM ( <same pagination subquery> ))

-- Batch: Geo Restrictions
SELECT CONTENT_ID, PROVIDER_ID, COUNTRY_CD,
       ACCESS_TYPE, RESTRICTION_TYPE, TEAM_REGION
FROM ITVSTD_O.STD_VC_VOD_CONTENT_GEO_RESTRICTIONS
WHERE (CONTENT_ID, PROVIDER_ID, COUNTRY_CD) IN
    (SELECT CONTENT_ID, VC_CP_ID, CNTY_CD FROM ( <same pagination subquery> ))

-- Batch: External Provider
SELECT PROGRAM_ID, VC_CP_ID, COUNTRY_CD,
       EXTERNAL_PROGRAM_ID, ID_TYPE, PROVIDER
FROM ITVSTD_O.STD_VC_VOD_EXTERNALID
WHERE (PROGRAM_ID, VC_CP_ID, COUNTRY_CD) IN
    (SELECT CONTENT_ID, VC_CP_ID, CNTY_CD FROM ( <same pagination subquery> ))
```

Each query returns flat rows from a single table — no joins, no cartesian product, no DISTINCT needed.

**Alternative approach**: Instead of repeating the pagination subquery, pass the 5000 composite keys from Java. For Oracle, this can be done via a temporary collection type or by chunking the IN clause (Oracle limit: 1000 elements per simple IN, but tuple IN `(col1, col2, col3) IN (...)` has no such limit in Oracle 12c+).

### 4.7 Java Assembly in Service Layer

```java
// Step 1: Main query — returns 5000 DTOs with scalar fields only
List<VodAssetDto> assets = vodAssetExportMapper.getAssetsForExport(filterBody, feedWorkerList, feedWorkerOrder);

if (assets == null || assets.isEmpty()) return assets;

// Step 2: Collect composite keys
List<AssetKeyDto> assetKeys = assets.stream()
    .map(a -> new AssetKeyDto(a.getContentId(), a.getVcCpId(), a.getCountryCode()))
    .toList();

// Step 3: Batch-fetch collections (parallelized)
CompletableFuture<List<AssetCastDto>> castFuture =
    CompletableFuture.supplyAsync(() -> vodAssetExportMapper.batchGetCast(assetKeys));
CompletableFuture<List<ParentalRatingsDto>> ratingsFuture =
    CompletableFuture.supplyAsync(() -> vodAssetExportMapper.batchGetRatings(assetKeys));
CompletableFuture<List<LicenseWindowDto>> licenseFuture =
    CompletableFuture.supplyAsync(() -> vodAssetExportMapper.batchGetLicenseWindows(assetKeys));
CompletableFuture<List<EventWindowDto>> eventFuture =
    CompletableFuture.supplyAsync(() -> vodAssetExportMapper.batchGetEventWindows(assetKeys));
CompletableFuture<List<GeoRestrictionsDto>> geoFuture =
    CompletableFuture.supplyAsync(() -> vodAssetExportMapper.batchGetGeoRestrictions(assetKeys));
CompletableFuture<List<ExternalProviderDto>> extFuture =
    CompletableFuture.supplyAsync(() -> vodAssetExportMapper.batchGetExternalProviders(assetKeys));

CompletableFuture.allOf(castFuture, ratingsFuture, licenseFuture, eventFuture, geoFuture, extFuture).join();

// Step 4: Build lookup maps (group by composite key)
Map<String, List<AssetCastDto>> castMap = castFuture.get().stream()
    .collect(Collectors.groupingBy(c -> c.getContentId() + "|" + c.getVcCpId() + "|" + c.getCntyCode()));
// ... same for ratings, license, event, geo, ext

// Step 5: Attach collections to DTOs
for (VodAssetDto asset : assets) {
    String key = asset.getCompositeKey();  // Already exists: contentId + "|" + vcCpId + "|" + countryCode
    asset.setCast(castMap.getOrDefault(key, List.of()));
    asset.setParentalRatings(ratingsMap.getOrDefault(key, List.of()));
    asset.setLicenseWindowList(licenseMap.getOrDefault(key, List.of()));
    asset.setEventWindowList(eventMap.getOrDefault(key, List.of()));
    asset.setGeoRestrictions(geoMap.getOrDefault(key, List.of()));
    asset.setExternalProvider(extMap.getOrDefault(key, List.of()));
}

// Step 6: Existing post-processing (unchanged)
for (VodAssetDto asset : assets) {
    String licenseWindow = utils.getLicenseWindow(asset.getAvailableStarting(), asset.getExpiryDate());
    String status = utils.getStatus(licenseWindow, asset.getStatus());
    // ... rest of existing logic unchanged
}
```

### 4.8 Conditional Batch Queries (Optimization)

The batch queries should only execute when the corresponding columns are requested. The `filterBody.columns` list tells us what the caller needs:

```java
// Only fetch cast if "cast" column is requested
if (fieldsToRetain.contains("cast")) {
    castFuture = CompletableFuture.supplyAsync(() -> vodAssetExportMapper.batchGetCast(assetKeys));
}

// Only fetch license windows if "licenseWindowList" column is requested
if (fieldsToRetain.contains("licenseWindowList")) {
    licenseFuture = CompletableFuture.supplyAsync(() -> vodAssetExportMapper.batchGetLicenseWindows(assetKeys));
}

// ... etc.
```

This means if the caller only needs scalar fields (contentId, mainTitle, etc.), no batch queries execute at all.

---

## 5. Functionality Preservation & Filter Handling

### 5.1 Current Request Body Capabilities

The endpoint accepts an `AssetFilterBodyDto` with three main sections:

#### A. `columns` — Which fields to return

```json
{
    "columns": ["contentId", "mainTitle", "type", "cast", "licenseWindowList", "drm", ...]
}
```

Mapped to DB columns via `AssetTableColumnMapping`. Controls which columns appear in `exportSelectedColumns` SQL fragment. If null/empty, defaults to `Constants.EXPORT_COLUMNS_LIST`.

**How preserved**: The main query still handles all scalar columns (mainTitle, type, genres, etc.) and computed columns (IS_DRM via EXISTS, SHOW_TITLE, SEASON_TITLE, INGESTION_TYPE, LANGUAGE, etc.). Collection columns (cast, parentalRatings, licenseWindowList, eventWindowList, geoRestrictions, externalProvider) are populated from batch queries. The final DTO has identical content.

#### B. `filters` — Three filter types

**Type: `search`** — Free-text search on specific columns

| Filter Key | Current Behavior | Tables Involved | Fix #1 Handling |
|-----------|-----------------|-----------------|-----------------|
| `CONTENT_ID` | `LOWER(SVVC.CONTENT_ID) LIKE ...` | Main table only | Unchanged |
| `MAIN_TITLE` | `LOWER(SVVC.MAIN_TITLE) LIKE ...` | Main table only | Unchanged |
| `SHOW_TITLE` | `LOWER(COALESCE(SVVC_SHOW.MAIN_TITLE, ...)) LIKE ...` | SHOW self-join | Unchanged (join kept) |
| `SEASON_TITLE` | `LOWER(COALESCE(SVVC_SEASON.MAIN_TITLE, ...)) LIKE ...` | SEASON self-join | Unchanged (join kept) |
| `SEASON_NO`, `EPISODE_NO` | `LOWER(SVVC.col) = LOWER(val)` | Main table only | Unchanged |
| `SERIES_DESCR` | `LOWER(SVVC.DESCR) LIKE ...` | Main table only | Unchanged |
| `STARRING` | `LOWER(SVVC.ARTIST/STARRING/DIRECTOR) LIKE ...` | Main table only | Unchanged |
| `MATCH_INFORMATION` | `LOWER(SVVC.MATCH_TEAM1/TEAM2) LIKE ...` | Main table only | Unchanged |
| `EXTERNAL_PROGRAM_ID` | `LOWER(EXT.EXTERNAL_PROGRAM_ID) LIKE ...` | EXT table | **Changed to EXISTS** (see Section 4.5) — same result |
| `EXT_ID` | Same as EXTERNAL_PROGRAM_ID | EXT table | **Changed to EXISTS** — same result |
| `EXT_PROVIDER` | `LOWER(EXT.PROVIDER) LIKE ...` | EXT table | **Changed to EXISTS** — same result |
| Any other key | `LOWER(SVVC.${key}) LIKE ...` | Main table only | Unchanged |

**Type: `filter`** — Exact match / multi-value selection

| Filter Key | Current Behavior | Tables Involved | Fix #1 Handling |
|-----------|-----------------|-----------------|-----------------|
| `TYPE` | `SVVC.TYPE IN (...)` | Main table | Unchanged |
| `CNTY_CD` | `SVVC.CNTY_CD IN (...)` | Main table | Unchanged |
| `VC_CP_NM` | `LOWER(SVC.VC_CP_NM) IN (...)` | CP table | Unchanged (join kept) |
| `AUDIO_LANG` | `LOWER(SVVC.AUDIO_CD) LIKE ...` | Main table | Unchanged |
| `SUBTITLE_LANG` | `LOWER(SVVC.SUBTITLE_CD) LIKE ...` | Main table | Unchanged |
| `GENRES` | `LOWER(SVVC.GENRES) LIKE ...` | Main table | Unchanged |
| `DRM` | `DRM.PROGRAM_ID IS [NOT] NULL` | DRM table | **Changed to EXISTS/NOT EXISTS** (see Section 4.4) — same result |
| `LICENSE_STATUS` | Date comparisons on `SVVC.AVAILABLE_STARTING/EXP_DATE` | Main table | Unchanged |
| `ASSET_CURRENT_STATUS` | Complex CASE on `SVVC.ASSET_CURRENT_STATUS + FEED_WORKER` | Main table | Unchanged |
| `DB_STATUS` | `SVVC.CMS_IS_PRD + FEED_WORKER` | Main table | Unchanged |
| `LIVE_ON_DEVICE` | Complex compound condition on SVVC columns | Main table | Unchanged |
| `ONDEVICE_TRANS_YN` | `SVVC.ONDEVICE_TRANS_YN IN (...)` | Main table | Unchanged |
| `HISTORY` | `LAST_STATUS.LAST_QC_STATE = 2` | LAST_STATUS table | Unchanged (join kept) |
| `INGESTION_TYPE` | `SVVC.FEED_WORKER IN (...) + DELTA_TYPE` | Main table | Unchanged |
| `ATTRIBUTES` | `LOWER(SVVC.ATTRIBUTES) LIKE ...` | Main table | Unchanged |
| Any other key | `SVVC."${key}" IN (...)` | Main table | Unchanged |

**Type: `dateRange`** — Date range filters

| Filter Key | Current Behavior | Fix #1 Handling |
|-----------|-----------------|-----------------|
| `LICENSE_STATUS_RANGE` | `TO_DATE(SVVC.AVAILABLE_STARTING) / TO_DATE(SVVC.EXP_DATE)` comparisons | Unchanged |
| `LICENSE_RANGE` | Same pattern | Unchanged |
| `EVENT_RANGE` | `TO_DATE(SVVC.EVENT_STARTING/ENDING)` comparisons | Unchanged |
| `ASSET_INGESTION_RANGE` | `TRUNC(SVVC.REG_DT)` comparisons | Unchanged |
| `ASSET_UPDATE_RANGE` | `TRUNC(SVVC.UPD_DT)` comparisons | Unchanged |

#### C. `sortBy` — Dynamic sorting

```json
{
    "sortBy": [{"field": "mainTitle", "order": "ASC"}]
}
```

All sort fields reference `SVVC.*` (main content table columns). No sort field references any one-to-many joined table. The inner query's `ROW_NUMBER() OVER(ORDER BY ...)` handles sorting before pagination.

**How preserved**: Completely unchanged. Sorting only depends on the main content table.

#### D. `pagination` — Offset and limit

```json
{
    "pagination": {"offset": 0, "limit": 5000}
}
```

Transformed in `VodAssetServiceImpl.java` lines 332-338 to ROW_NUMBER boundaries (`offset+1` to `offset+limit`). Applied in the inner query's `WHERE RN BETWEEN`.

**How preserved**: The inner pagination query is completely unchanged.

### 5.2 Complete Filter Safety Audit

**Filters that reference ONLY the main content table (SVVC)**: 23 filter keys — ALL UNCHANGED.

**Filters that reference joined tables**:

| Filter | Table | Current Inner Query | Current Outer Query | New Handling | Behavior Change? |
|--------|-------|--------------------|--------------------|-------------|-----------------|
| `EXTERNAL_PROGRAM_ID` search | EXT | `1 = 1` (skipped) | `EXT.EXTERNAL_PROGRAM_ID LIKE ...` | EXISTS subquery | **No** — same post-pagination filtering |
| `EXT_ID` search | EXT | `1 = 1` (skipped) | `EXT.EXTERNAL_PROGRAM_ID LIKE ...` | EXISTS subquery | **No** |
| `EXT_PROVIDER` search | EXT | `1 = 1` (skipped) | `EXT.PROVIDER LIKE ...` | EXISTS subquery | **No** |
| `DRM` filter | DRM | `1 = 1` (skipped) | `DRM.PROGRAM_ID IS [NOT] NULL` | EXISTS / NOT EXISTS | **No** — same post-pagination filtering |
| `HISTORY` filter | LAST_STATUS | `1 = 1` (skipped) | `LAST_STATUS.LAST_QC_STATE = 2` | Unchanged (join kept) | **No** |
| `VC_CP_NM` filter | SVC (CP) | Filtered on `SVC_INTERNAL.VC_CP_NM` | Filtered on `SVC.VC_CP_NM` | Unchanged (join kept) | **No** |
| `SHOW_TITLE` search | SHOW self-join | Filtered on `SVVC_SHOW.MAIN_TITLE` | Filtered on `SVVC_SHOW.MAIN_TITLE` | Unchanged (join kept) | **No** |
| `SEASON_TITLE` search | SEASON self-join | Filtered on `SVVC_SEASON.MAIN_TITLE` | Filtered on `SVVC_SEASON.MAIN_TITLE` | Unchanged (join kept) | **No** |

**Result**: Zero behavior changes across all filter types.

### 5.3 Post-Processing Logic Preservation

The Java post-processing in `VodAssetServiceImpl.java` lines 346-370 runs after the query returns. Here is each operation and its data dependency:

| Operation | Depends On | Source | Changed? |
|-----------|-----------|--------|----------|
| `getLicenseWindow()` | `availableStarting`, `expiryDate` | Main query scalar | No |
| `getStatus()` | `licenseWindow` (computed above), `status` | Main query scalar | No |
| `checkExternalAsset()` | `feedWorker`, `feedWorkerList` | Main query scalar + config | No |
| `checkExternalAssetForDbStatus()` | `dbStatus`, `feedWorker` | Main query scalar | No |
| `setExternalProviderData()` | `externalProvider` list | Now from batch query | No — same data |
| `setLicenseWindow()` | computed `licenseWindow` | Java computation | No |
| `setStatus()` | computed `status` | Java computation | No |
| `setDbStatus()` | computed `dbStatus` | Java computation | No |
| `checkLiveOnDevice()` | `status`, `dbStatus`, `type`, `licenseWindow` | All scalars | No |
| `retainOnlyFields()` | Final DTO with all fields populated | Runs last | No |

The only operation that uses collection data is `setExternalProviderData()`, which reads `asset.getExternalProvider()` to extract `externalProgramId` and `externalIdProvider` strings. In Fix #1, the `externalProvider` list is populated from the batch query **before** the post-processing loop runs, so this method receives the same data.

---

## 6. Real-World Scenario & Time Estimates

### Scenario: Export 50,000 assets with all columns

**Current approach**: 10 parallel threads, each requesting 5000 assets.

#### Current Performance (per thread)

| Phase | What Happens | Est. Time |
|-------|-------------|-----------|
| Inner pagination | ROW_NUMBER on content table + 3 joins, filter, pick 5000 | ~1.5s |
| Outer joins | 5000 rows × 6 one-to-many tables → cartesian explosion to ~180K rows | ~2.0s |
| SELECT DISTINCT | Deduplicate 180K rows of 100+ columns | ~3.0s |
| Outer WHERE | Re-apply all filters on 180K rows | ~1.5s |
| Outer ORDER BY | Re-sort the result | ~0.5s |
| Network transfer | Send ~180K rows to app server | ~0.5s |
| MyBatis mapping | Collapse rows into 5000 DTOs via resultMap | ~0.5s |
| Java post-processing | 5000 × (date parsing + status + reflection) | ~0.5s |
| **Total per thread** | | **~10s** |
| **Total wall-clock** | 10 threads parallel, limited by DB connections | **~10-15s** |

#### Optimized Performance (per thread, Fix #1 only)

| Phase | What Happens | Est. Time |
|-------|-------------|-----------|
| Inner pagination | Same as before (unchanged) | ~1.5s |
| Outer joins | Only many-to-one + EXISTS subqueries, returns exactly 5000 rows | ~0.5s |
| No DISTINCT | Not needed (no explosion) | 0s |
| Outer WHERE | Simpler filters, fewer rows | ~0.2s |
| ORDER BY RN | Trivial sort on integer | ~0.05s |
| Network transfer | Send 5000 rows (not 180K) | ~0.1s |
| 6 batch queries (parallel) | ~5K-15K flat rows each, simple WHERE IN, no joins | ~0.5s (max of 6) |
| Java assembly | HashMap grouping + setting collections | ~0.1s |
| Java post-processing | Same as before | ~0.5s |
| **Total per thread** | | **~3.5s** |
| **Total wall-clock** | 10 threads parallel | **~4-5s** |

**Estimated improvement: ~65% reduction in response time per page (10s → 3.5s).**

#### If Fixes #2-#4 are also applied

| Additional Fix | Saves | New Total |
|---------------|-------|-----------|
| Remove duplicate SEASON/SHOW/CP joins | ~0.3s | ~3.2s |
| Remove redundant outer totalFilters | ~0.2s | ~3.0s |
| Simplify ORDER BY to RN | ~0.1s | ~2.9s |
| **Combined** | | **~2.5-3.0s** |

---

## 7. Tradeoffs

### 7.1 More DB Round-Trips

| Aspect | Before | After |
|--------|--------|-------|
| SQL queries per request | 1 | 7 (1 main + 6 batch) |
| Network round-trip overhead | 0 | ~6 × 3ms = ~18ms |

**Why acceptable**: 18ms of network overhead is negligible compared to the ~6-7 seconds saved by eliminating the cartesian product. The bottleneck was never the number of DB calls — it was the volume of rows Oracle had to process.

### 7.2 Pagination Subquery May Execute Multiple Times

If batch queries use `WHERE (CONTENT_ID, ...) IN (SELECT ... FROM (<pagination subquery>))`, the pagination subquery executes 7 times total (1 main + 6 batch). Oracle's result cache may mitigate this, but it's a consideration.

**Mitigation**: Pass the 5000 composite keys from Java as parameters instead of re-executing the subquery. This requires handling Oracle's IN clause limitations for large lists (use temporary collections, or chunk into groups of 1000).

### 7.3 DB Connection Pool Usage

6 parallel batch queries per request × 10 parallel threads from batch module = potentially 60 simultaneous DB connections.

**Mitigation**: Configure HikariCP pool size accordingly, or limit the parallelism of batch queries (e.g., run 3 at a time using a Semaphore or custom executor with bounded thread pool).

### 7.4 Code Complexity

The service layer gains assembly logic (~30-40 lines) and 6 new mapper methods. This is additional code to maintain.

**Mitigation**: This is a well-known, well-documented pattern (batch fetching / collection splitting). The new mapper methods are trivially simple SELECT statements. The assembly logic is straightforward HashMap grouping.

### 7.5 What This Fix Does NOT Change

- Request/response contract (same JSON structure)
- Filter behavior (all filters preserved, same pre/post-pagination semantics)
- Sort order (same feed_worker priority + user sort)
- Pagination (same ROW_NUMBER BETWEEN logic)
- Business rules (status computation, license window, live-on-device)
- Error handling
- Logging
- Transaction boundaries
