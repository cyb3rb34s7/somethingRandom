Recommended Plan

Fix this by separating export into two responsibilities:

1. Find the correct assets


2. Fetch export data for those assets



Right now one query tries to do both, which causes the row explosion and pagination bugs.

Current Flow

Frontend export request
  -> cms-backend
    -> calls cms-assetmanagement /export/count
    -> calls cms-assetmanagement /export with limit=5000, offset=0
       -> one huge SQL:
          base VOD content
          + show self join
          + season self join
          + external IDs
          + cast
          + ratings
          + license windows
          + event windows
          + geo restrictions
          + service IDs
          + linear licenses
          + DISTINCT
          + ORDER BY

This means Oracle creates a large joined dataset first, then MyBatis groups it back into assets.

New Flow

Frontend export request
  -> cms-backend
    -> cms-assetmanagement /export/count
       -> lightweight count using only filters

    -> cms-assetmanagement /export with limit/offset
       Step 1: get page of matching asset keys
       Step 2: fetch base asset columns for those keys
       Step 3: fetch requested collection data separately
       Step 4: assemble VodAssetDto in Java

Step 1: Asset Key Query Create a query that returns only:

CONTENT_ID
VC_CP_ID
CNTY_CD
sort columns if needed

All filters must be applied here before pagination.

For simple filters, use STD_VC_VOD_CONTENT directly:

SVVC.TYPE IN (...)
SVVC.ASSET_CURRENT_STATUS IN (...)
SVVC.UPD_DT BETWEEN ...

For joined-data filters, use EXISTS.

Example external ID filter:

AND EXISTS (
  SELECT 1
  FROM STD_VC_VOD_EXTERNALID EXT
  WHERE EXT.PROGRAM_ID = SVVC.CONTENT_ID
    AND EXT.VC_CP_ID = SVVC.VC_CP_ID
    AND EXT.COUNTRY_CD = SVVC.CNTY_CD
    AND LOWER(EXT.EXTERNAL_PROGRAM_ID) LIKE LOWER('%abc%')
)

Same pattern for:

DRM
CHAPTERS_YN
SERVICE_ID
EXT_PROVIDER
HISTORY
SELECTED_SOURCE
LINEAR_LICENSE_STATUS

Then paginate after all filters:

ROW_NUMBER() OVER (ORDER BY ...)
WHERE RN BETWEEN :offset AND :limit

Step 2: Base Asset Query Fetch scalar data only for the returned keys.

This can include:

main asset columns
content partner name
language
show title
season title
linear scalar fields if selected

Self-joins to STD_VC_VOD_CONTENT for show/season title should happen only if:

showTitle or seasonTitle is selected
or showTitle/seasonTitle is used in filter/sort

No reason to always do both self-joins.

Step 3: Collection Queries Fetch one-to-many data separately, only if selected columns need them.

Examples:

cast selected -> fetch cast by page keys
licenseWindowList selected -> fetch license windows by page keys
eventWindowList selected -> fetch event windows by page keys
geoRestrictions selected -> fetch geo restrictions by page keys
serviceIds selected -> fetch service IDs by page keys
externalProvider selected -> fetch external IDs by page keys

Each query returns child rows only for the current page of asset keys.

Then Java groups them:

Map<AssetKey, VodAssetDto>
Map<AssetKey, List<Cast>>
Map<AssetKey, List<LicenseWindow>>
...

Attach collections to the base assets.

Step 4: Count Query Rewrite count to use the same filter logic as Step 1:

SELECT COUNT(*)
FROM matched_asset_keys_query

No export columns.
No cast join unless filtering by cast.
No license-window join unless filtering by license-window child data.
No collection hydration joins.

Pagination Fix Backend currently does:

currentOffset += batchAssets.size();

That is unsafe when filters are applied after pagination.

After this fix, filters happen before pagination, so use:

currentOffset += PAGE_SIZE * PARALLEL_CALLS

or simpler, avoid two parallel offsets initially and page sequentially:

offset 0
offset 5000
offset 10000

If keeping parallel calls:

batch 1: offset 0 and 5000
batch 2: offset 10000 and 15000

Do not advance by returned asset count.

Example Scenario Assume:

Total assets in VOD content: 100,000
Assets matching externalProgramId = "abc": 3,000
First matching asset appears around base row 20,000
Page size: 5,000

Current behavior:

Page 1 gets base rows 1-5000
Then applies external ID filter
Returns 0

Backend sees empty batch
Breaks export
Result: wrong export, or incomplete export

Or if page 1 returns 200:

Backend offset becomes 200
Next page gets base rows 201-5200
Huge overlap with previous page
Repeated work, possible duplicates, slow progress

New behavior:

Apply external ID filter first
Matching set = 3,000 assets
Paginate matching set rows 1-3000
Fetch details only for those 3,000
Export completes correctly

Before vs After Impact

Before:

Oracle scans VOD content
joins parent VOD content twice
joins many one-to-many child tables
creates multiplied rows
runs HASH UNIQUE
runs final ORDER BY
MyBatis groups after Oracle has already paid the cost

After:

Oracle finds matching asset keys first
uses EXISTS for joined filters
paginates correct filtered result
fetches only selected details
fetches child collections separately
no giant DISTINCT over multiplied rowset

Expected impact for your 3k asset / 40 sec case:

Current: ~40 sec
Reasonable target after restructuring: ~8-15 sec
Best case: ~5-10 sec

The exact number depends on external table scan cost and selected columns, but the biggest wasted work disappears: cast/license/service/external child tables no longer multiply the main asset rows.

Implementation Order

1. Add shared filter builder SQL for asset-key query.


2. Build getExportAssetKeys(filterBody) with correct pre-pagination filtering.


3. Build lightweight getExportAssetCount(filterBody) from the same filter logic.


4. Build getExportBaseAssets(assetKeys, columns).


5. Add collection queries per selected collection column.


6. Assemble collections in Java.


7. Fix backend offset increment.


8. Add tests for external ID filter pagination, service ID filter pagination, and selected-column exports.


