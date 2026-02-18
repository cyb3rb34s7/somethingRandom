# Production Implementation Plan: Flat-File Asset Export Enhancement

This document provides the complete, production-ready implementation plan to transition the asset export engine from a multi-file zipped (1-N) relational format to a single-file flat (1:1) format.

## 1. Data Dictionary: New Excel Format & Mappings

Use this reference to cross-check the generated columns against the API JSON payload keys.

| Group Header | Column Header | API JSON Node Key | Strategy |
| --- | --- | --- | --- |
| **Asset Basic Information** | Program ID | `contentId` | SIMPLE |
|  | Asset ID | `assetId` | SIMPLE |
|  | Program Type | `type` | SIMPLE |
|  | Country | `countryCode` | SIMPLE |
|  | Main Title | `mainTitle` | SIMPLE |
|  | Main Title Language | `mainTitleLanguage` | SIMPLE |
|  | Short Title | `shortTitle` | SIMPLE |
|  | Short Title Language | `shortTitleLanguage` | SIMPLE |
|  | Duration (Sec) | `runningTime` | SIMPLE |
|  | Ad tags | `adTag` | SIMPLE |
|  | Stream URL | `streamUri` | SIMPLE |
|  | Description Language | `language` | SIMPLE |
|  | Synopsis | `description` | SIMPLE |
|  | Tech Integrator | `tiName` | SIMPLE |
|  | Show Title | `showTitle` | SIMPLE |
|  | Season Title | `seasonTitle` | SIMPLE |
|  | Show ID | `showId` | SIMPLE |
|  | Season ID | `seasonId` | SIMPLE |
|  | Season No | `seasonNo` | SIMPLE |
|  | Episode No | `episodeNo` | SIMPLE |
|  | Provider ID | `vcCpId` | SIMPLE |
|  | Ingestion Type | `ingestionType` | SIMPLE |
| **Asset Details** | Original Release Date | `releaseDate` | SIMPLE |
|  | Genre | `genres` | SIMPLE |
|  | Ratings | `parentalRatings` array | COMPUTED |
| **Cast Details** | Actor | `cast` array (role="actor") | COMPUTED |
|  | Director | `cast` array (role="director") | COMPUTED |
|  | Artist | `artist` | **SIMPLE** |
| **Asset Specifications** | Deeplink Payload | `deeplinkPayload` | SIMPLE |
|  | Chapter Time | `chapterTime` | SIMPLE |
|  | Chapter Description | `chapterDescription` | SIMPLE |
|  | Audio Language | `audioLang` | SIMPLE |
|  | Subtitle Language | `subtitleLang` | SIMPLE |
|  | DRM | `drm` | SIMPLE |
|  | Quality | `quality` | SIMPLE |
|  | Scene Preview Url | `webVttUrl` | SIMPLE |
|  | Attributes | `attributes` | SIMPLE |
| **External Ids** | External Ids | `externalProvider` array | COMPUTED |
| **License Details** | Expired LWs | `licenseWindowList` array | COMPUTED |
|  | Current LWs | `licenseWindowList` array | COMPUTED |
|  | Future LWs | `licenseWindowList` array | COMPUTED |
|  | Expired EWs | `eventWindowList` array | COMPUTED |
|  | Current EWs | `eventWindowList` array | COMPUTED |
|  | Future EWs | `eventWindowList` array | COMPUTED |
|  | Content Partner/Licensor | `contentPartner` | SIMPLE |
|  | Content Tier | `contentTier` | SIMPLE |
| **Sport Information** | Air Type | `airType` | SIMPLE |
|  | Sub Type | `subType` | SIMPLE |
|  | Match Information | `matchInformation` | SIMPLE |
| **Geo Restriction** | Access Type | `geoRestrictions` (accessType) | COMPUTED |
|  | Type | `geoRestrictions` (restrictionType) | COMPUTED |
|  | Value | `geoRestrictions` (teamRegion) | COMPUTED |

---

## 2. Architecture & Wiring Diagram

```text
[ Incoming Request ]
         |
         v
+---------------------------------------------------+
| AssetExportService.java                           |
| 1. Initialize SXSSFWorkbook(1000)                 |
| 2. Capture Instant.now()                          |
| 3. Create ExportStateContext (Stores isEval flag) |
+---------------------------------------------------+
         |
         | (While offset < total assets)
         v
+---------------------------------------------------+
| ThreadPoolTaskExecutor (2 Parallel Threads)       |
| -> Fetch Offset N    (5000 rows)                  |
| -> Fetch Offset N+5K (5000 rows)                  |
+---------------------------------------------------+
         | returns List<JsonNode> (10,000 rows)
         v
+---------------------------------------------------+
| AssetExportService (Main Thread Loop)             |
| -> For each JsonNode in 10k batch:                |
|    -> If SIMPLE type: extract node value          |
|    -> If COMPUTED type: pass to Formatter Utility |
+---------------------------------------------------+
         | passes JsonNode + Instant.now()
         v
+---------------------------------------------------+
| AssetExportDataFormatter.java                     |
| -> Evaluates Dates vs Instant.now()               |
| -> Filters arrays & executes String.join()        |
+---------------------------------------------------+
         | returns Map<String, String>
         v
+---------------------------------------------------+
| AssetExportService (Main Thread Writer)           |
| -> Writes flat row to POI Sheet                   |
| -> batchAssets.clear() (Memory Release)           |
+---------------------------------------------------+
         | (End Loop)
         v
[ Flush to ByteArrayOutputStream -> Return Dto ]

```

---

## 3. Implementation Steps

1. **Delete Legacy Files:** Delete `ZipExportContext.java`. It is being fully replaced.
2. **Create New Context:** Create `ExportStateContext.java` in the `model` package.
3. **Update Configuration:** Replace the existing `ExportFieldMappingConfig.java`. Ensure `ARRAY` is removed and replaced with `COMPUTED`.
4. **Create Formatter Utility:** Create `AssetExportDataFormatter.java` in the `util` package to isolate string manipulations and date evaluations.
5. **Refactor Main Service:** Gut `AssetExportService.java`. Remove all zip logic, class-level flags, and nested loops. Implement the sequential POI writing logic provided below.

---

## 4. Source Code Updates

### 4.1. `ExportStateContext.java`

*Path: `src/main/java/com/cms/backend/assets/model/ExportStateContext.java*`

```java
package com.cms.backend.assets.model;

import com.cms.backend.assets.configuration.ExportFieldMappingConfig;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import lombok.Data;
import org.apache.poi.ss.usermodel.CellStyle;
import org.apache.poi.ss.usermodel.Sheet;
import org.apache.poi.ss.usermodel.Workbook;

@Data
public class ExportStateContext {

    private Workbook currentExcel;
    private Sheet currentSheet;
    private int currentRow = 0;
    
    private CellStyle columnHeaderStyle;
    private CellStyle dataStyle;
    private CellStyle bottomBorderStyle;
    private Map<String, CellStyle> groupStyles = new HashMap<>();

    private boolean isSelectiveExport = false;
    private boolean isEvaluation = false; // Fixes concurrency bug
    private List<String> selectedColumns = new ArrayList<>();
    private String[] fieldsToProcess;

    public ExportStateContext() {}

    public void setupSelectiveExport(List<String> selectedColumns, boolean isEvaluation) {
        this.isEvaluation = isEvaluation;
        this.isSelectiveExport = !selectedColumns.isEmpty();
        this.selectedColumns = new ArrayList<>(selectedColumns);

        if (this.isSelectiveExport) {
            this.fieldsToProcess = selectedColumns.toArray(new String[0]);
        } else {
            this.fieldsToProcess = ExportFieldMappingConfig.getFieldsInOrder(isEvaluation);
        }
    }

    public void setupFullExport(boolean isEvaluation) {
        this.isEvaluation = isEvaluation;
        this.isSelectiveExport = false;
        this.selectedColumns = new ArrayList<>();
        this.fieldsToProcess = isEvaluation ? 
            ExportFieldMappingConfig.EVALUATION_FULL_EXPORT_FIELDS : 
            ExportFieldMappingConfig.FULL_EXPORT_FIELDS;
    }
}

```

### 4.2. `ExportFieldMappingConfig.java`

*Path: `src/main/java/com/cms/backend/assets/configuration/ExportFieldMappingConfig.java*`

```java
package com.cms.backend.assets.configuration;

import lombok.AllArgsConstructor;
import lombok.Generated;
import org.apache.poi.ss.usermodel.IndexedColors;
import java.util.*;

@Generated
public class ExportFieldMappingConfig {
    private static final String ASSET_BASIC_INFORMATION = "Asset Basic Information";
    private static final String ASSET_DETAILS = "Asset Details";
    private static final String CAST_DETAILS = "Cast Details";
    private static final String ASSET_SPECIFICATION = "Asset Specifications";
    private static final String EXTERNAL_IDS = "External Ids";
    private static final String LICENSE_DETAILS = "License Details";
    private static final String SPORT_INFORMATION = "Sport Information";
    private static final String GEO_RESTRICTION = "Geo Restriction";
    private static final String EVALUATION_DETAILS = "Evaluation Details";

    public static final String[] FULL_EXPORT_FIELDS = {
            "contentId", "assetId", "type", "countryCode", "mainTitle", "mainTitleLanguage",
            "shortTitle", "shortTitleLanguage", "runningTime", "adTag", "streamUri", "language",
            "description", "tiName", "showTitle", "seasonTitle", "showId", "seasonId", 
            "seasonNo", "episodeNo", "vcCpId", "ingestionType",
            
            "releaseDate", "genres", "computedRatings",
            
            "computedActor", "computedDirector", "artist", // Artist is strictly SIMPLE
            
            "deeplinkPayload", "chapterTime", "chapterDescription", "audioLang",
            "subtitleLang", "drm", "quality", "webVttUrl", "attributes",
            
            "computedExternalIds",
            
            "expiredLWs", "currentLWs", "futureLWs",
            "expiredEWs", "currentEWs", "futureEWs",
            "contentPartner", "contentTier",
            
            "airType", "subType", "matchInformation",
            
            "geoAccessType", "geoRestrictionType", "geoTeamRegion"
    };

    public static final String[] EVALUATION_FULL_EXPORT_FIELDS = {
            "programId", "cpId", "programType", "programTitle", "feedWorker", "tmsId",
            "coverageStatus", "comparisonStatus"
    };

    public enum FieldType {
        SIMPLE, 
        COMPUTED 
    }

    @AllArgsConstructor
    public static class FieldMetadata {
        public final String columnName;
        public final String group;
        public final FieldType type;
    }

    public static final Map<String, FieldMetadata> FIELD_CONFIG = new LinkedHashMap<>();
    public static final Map<String, FieldMetadata> EVALUATION_FIELD_CONFIG = new LinkedHashMap<>();
    public static final Map<String, IndexedColors> GROUP_COLORS = new HashMap<>();

    static {
        GROUP_COLORS.put(ASSET_BASIC_INFORMATION, IndexedColors.LIGHT_YELLOW);
        GROUP_COLORS.put(ASSET_DETAILS, IndexedColors.LIGHT_GREEN);
        GROUP_COLORS.put(CAST_DETAILS, IndexedColors.PALE_BLUE);
        GROUP_COLORS.put(ASSET_SPECIFICATION, IndexedColors.ROSE);
        GROUP_COLORS.put(EXTERNAL_IDS, IndexedColors.TAN);
        GROUP_COLORS.put(LICENSE_DETAILS, IndexedColors.LAVENDER);
        GROUP_COLORS.put(SPORT_INFORMATION, IndexedColors.LIGHT_ORANGE);
        GROUP_COLORS.put(GEO_RESTRICTION, IndexedColors.AQUA);
        GROUP_COLORS.put(EVALUATION_DETAILS, IndexedColors.LIGHT_GREEN);

        // Map definitions
        FIELD_CONFIG.put("contentId", new FieldMetadata("Program ID", ASSET_BASIC_INFORMATION, FieldType.SIMPLE));
        FIELD_CONFIG.put("assetId", new FieldMetadata("Asset ID", ASSET_BASIC_INFORMATION, FieldType.SIMPLE));
        FIELD_CONFIG.put("type", new FieldMetadata("Program Type", ASSET_BASIC_INFORMATION, FieldType.SIMPLE));
        FIELD_CONFIG.put("countryCode", new FieldMetadata("Country", ASSET_BASIC_INFORMATION, FieldType.SIMPLE));
        FIELD_CONFIG.put("mainTitle", new FieldMetadata("Main Title", ASSET_BASIC_INFORMATION, FieldType.SIMPLE));
        FIELD_CONFIG.put("mainTitleLanguage", new FieldMetadata("Main Title Language", ASSET_BASIC_INFORMATION, FieldType.SIMPLE));
        FIELD_CONFIG.put("shortTitle", new FieldMetadata("Short Title", ASSET_BASIC_INFORMATION, FieldType.SIMPLE));
        FIELD_CONFIG.put("shortTitleLanguage", new FieldMetadata("Short Title Language", ASSET_BASIC_INFORMATION, FieldType.SIMPLE));
        FIELD_CONFIG.put("runningTime", new FieldMetadata("Duration (Sec)", ASSET_BASIC_INFORMATION, FieldType.SIMPLE));
        FIELD_CONFIG.put("adTag", new FieldMetadata("Ad tags", ASSET_BASIC_INFORMATION, FieldType.SIMPLE));
        FIELD_CONFIG.put("streamUri", new FieldMetadata("Stream URL", ASSET_BASIC_INFORMATION, FieldType.SIMPLE));
        FIELD_CONFIG.put("language", new FieldMetadata("Description Language", ASSET_BASIC_INFORMATION, FieldType.SIMPLE));
        FIELD_CONFIG.put("description", new FieldMetadata("Synopsis", ASSET_BASIC_INFORMATION, FieldType.SIMPLE));
        FIELD_CONFIG.put("tiName", new FieldMetadata("Tech Integrator", ASSET_BASIC_INFORMATION, FieldType.SIMPLE));
        FIELD_CONFIG.put("showTitle", new FieldMetadata("Show Title", ASSET_BASIC_INFORMATION, FieldType.SIMPLE));
        FIELD_CONFIG.put("seasonTitle", new FieldMetadata("Season Title", ASSET_BASIC_INFORMATION, FieldType.SIMPLE));
        FIELD_CONFIG.put("showId", new FieldMetadata("Show ID", ASSET_BASIC_INFORMATION, FieldType.SIMPLE));
        FIELD_CONFIG.put("seasonId", new FieldMetadata("Season ID", ASSET_BASIC_INFORMATION, FieldType.SIMPLE));
        FIELD_CONFIG.put("seasonNo", new FieldMetadata("Season No", ASSET_BASIC_INFORMATION, FieldType.SIMPLE));
        FIELD_CONFIG.put("episodeNo", new FieldMetadata("Episode No", ASSET_BASIC_INFORMATION, FieldType.SIMPLE));
        FIELD_CONFIG.put("vcCpId", new FieldMetadata("Provider ID", ASSET_BASIC_INFORMATION, FieldType.SIMPLE));
        FIELD_CONFIG.put("ingestionType", new FieldMetadata("Ingestion Type", ASSET_BASIC_INFORMATION, FieldType.SIMPLE));

        FIELD_CONFIG.put("releaseDate", new FieldMetadata("Original Release Date", ASSET_DETAILS, FieldType.SIMPLE));
        FIELD_CONFIG.put("genres", new FieldMetadata("Genre", ASSET_DETAILS, FieldType.SIMPLE));
        FIELD_CONFIG.put("computedRatings", new FieldMetadata("Ratings", ASSET_DETAILS, FieldType.COMPUTED));

        FIELD_CONFIG.put("computedActor", new FieldMetadata("Actor", CAST_DETAILS, FieldType.COMPUTED));
        FIELD_CONFIG.put("computedDirector", new FieldMetadata("Director", CAST_DETAILS, FieldType.COMPUTED));
        FIELD_CONFIG.put("artist", new FieldMetadata("Artist", CAST_DETAILS, FieldType.SIMPLE)); // SIMPLE

        FIELD_CONFIG.put("deeplinkPayload", new FieldMetadata("Deeplink Payload", ASSET_SPECIFICATION, FieldType.SIMPLE));
        FIELD_CONFIG.put("chapterTime", new FieldMetadata("Chapter Time", ASSET_SPECIFICATION, FieldType.SIMPLE));
        FIELD_CONFIG.put("chapterDescription", new FieldMetadata("Chapter Description", ASSET_SPECIFICATION, FieldType.SIMPLE));
        FIELD_CONFIG.put("audioLang", new FieldMetadata("Audio Language", ASSET_SPECIFICATION, FieldType.SIMPLE));
        FIELD_CONFIG.put("subtitleLang", new FieldMetadata("Subtitle Language", ASSET_SPECIFICATION, FieldType.SIMPLE));
        FIELD_CONFIG.put("drm", new FieldMetadata("DRM", ASSET_SPECIFICATION, FieldType.SIMPLE));
        FIELD_CONFIG.put("quality", new FieldMetadata("Quality", ASSET_SPECIFICATION, FieldType.SIMPLE));
        FIELD_CONFIG.put("webVttUrl", new FieldMetadata("Scene Preview Url", ASSET_SPECIFICATION, FieldType.SIMPLE));
        FIELD_CONFIG.put("attributes", new FieldMetadata("Attributes", ASSET_SPECIFICATION, FieldType.SIMPLE));

        FIELD_CONFIG.put("computedExternalIds", new FieldMetadata("External Ids", EXTERNAL_IDS, FieldType.COMPUTED));

        FIELD_CONFIG.put("expiredLWs", new FieldMetadata("Expired LWs", LICENSE_DETAILS, FieldType.COMPUTED));
        FIELD_CONFIG.put("currentLWs", new FieldMetadata("Current LWs", LICENSE_DETAILS, FieldType.COMPUTED));
        FIELD_CONFIG.put("futureLWs", new FieldMetadata("Future LWs", LICENSE_DETAILS, FieldType.COMPUTED));
        FIELD_CONFIG.put("expiredEWs", new FieldMetadata("Expired EWs", LICENSE_DETAILS, FieldType.COMPUTED));
        FIELD_CONFIG.put("currentEWs", new FieldMetadata("Current EWs", LICENSE_DETAILS, FieldType.COMPUTED));
        FIELD_CONFIG.put("futureEWs", new FieldMetadata("Future EWs", LICENSE_DETAILS, FieldType.COMPUTED));
        FIELD_CONFIG.put("contentPartner", new FieldMetadata("Content Partner/Licensor", LICENSE_DETAILS, FieldType.SIMPLE));
        FIELD_CONFIG.put("contentTier", new FieldMetadata("Content Tier", LICENSE_DETAILS, FieldType.SIMPLE));

        FIELD_CONFIG.put("airType", new FieldMetadata("Air Type", SPORT_INFORMATION, FieldType.SIMPLE));
        FIELD_CONFIG.put("subType", new FieldMetadata("Sub Type", SPORT_INFORMATION, FieldType.SIMPLE));
        FIELD_CONFIG.put("matchInformation", new FieldMetadata("Match Information", SPORT_INFORMATION, FieldType.SIMPLE));

        FIELD_CONFIG.put("geoAccessType", new FieldMetadata("Access Type", GEO_RESTRICTION, FieldType.COMPUTED));
        FIELD_CONFIG.put("geoRestrictionType", new FieldMetadata("Type", GEO_RESTRICTION, FieldType.COMPUTED));
        FIELD_CONFIG.put("geoTeamRegion", new FieldMetadata("Value", GEO_RESTRICTION, FieldType.COMPUTED));

        // Evaluation
        EVALUATION_FIELD_CONFIG.put("programId", new FieldMetadata("Program ID", ASSET_BASIC_INFORMATION, FieldType.SIMPLE));
        EVALUATION_FIELD_CONFIG.put("cpId", new FieldMetadata("CP ID", ASSET_BASIC_INFORMATION, FieldType.SIMPLE));
        EVALUATION_FIELD_CONFIG.put("programType", new FieldMetadata("Program Type", ASSET_BASIC_INFORMATION, FieldType.SIMPLE));
        EVALUATION_FIELD_CONFIG.put("programTitle", new FieldMetadata("Program Title", ASSET_BASIC_INFORMATION, FieldType.SIMPLE));
        EVALUATION_FIELD_CONFIG.put("feedWorker", new FieldMetadata("Source", ASSET_BASIC_INFORMATION, FieldType.SIMPLE));
        EVALUATION_FIELD_CONFIG.put("tmsId", new FieldMetadata("TMS ID", ASSET_BASIC_INFORMATION, FieldType.SIMPLE));
        EVALUATION_FIELD_CONFIG.put("coverageStatus", new FieldMetadata("On Status", EVALUATION_DETAILS, FieldType.SIMPLE));
        EVALUATION_FIELD_CONFIG.put("comparisonStatus", new FieldMetadata("GVD - On", EVALUATION_DETAILS, FieldType.SIMPLE));
    }

    public static String[] getFieldsInOrder(boolean isEvaluation) {
        return (isEvaluation ? EVALUATION_FIELD_CONFIG : FIELD_CONFIG).keySet().toArray(new String[0]);
    }

    public static String[] getGroupsInOrder(boolean isEvaluation) {
        Set<String> groups = new LinkedHashSet<>();
        for (FieldMetadata metadata : (isEvaluation ? EVALUATION_FIELD_CONFIG : FIELD_CONFIG).values()) {
            groups.add(metadata.group);
        }
        return groups.toArray(new String[0]);
    }

    public static int countColumnsInGroup(String[] fields, String group, boolean isEvaluation) {
        int count = 0;
        for (String field : fields) {
            FieldMetadata metadata = (isEvaluation ? EVALUATION_FIELD_CONFIG : FIELD_CONFIG).get(field);
            if (metadata != null && group.equals(metadata.group)) count++;
        }
        return count;
    }
}

```

### 4.3. `AssetExportDataFormatter.java`

*Path: `src/main/java/com/cms/backend/assets/util/AssetExportDataFormatter.java*`

```java
package com.cms.backend.assets.util;

import com.fasterxml.jackson.databind.JsonNode;
import com.cms.backend.common.util.CommonMethodUtil;
import java.time.Instant;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.List;

public class AssetExportDataFormatter {

    public static String extractComputedValue(JsonNode asset, String fieldName, Instant exportTime) {
        switch (fieldName) {
            case "computedRatings":
                return formatRatings(asset.get("parentalRatings"));
            case "computedActor":
                return formatCast(asset.get("cast"), "actor");
            case "computedDirector":
                return formatCast(asset.get("cast"), "director");
            case "computedExternalIds":
                return formatExternalIds(asset.get("externalProvider"));
            
            // License Windows
            case "expiredLWs":
                return categorizeWindows(asset.get("licenseWindowList"), exportTime, "EXPIRED", "availableStarting", "availableEnding");
            case "currentLWs":
                return categorizeWindows(asset.get("licenseWindowList"), exportTime, "CURRENT", "availableStarting", "availableEnding");
            case "futureLWs":
                return categorizeWindows(asset.get("licenseWindowList"), exportTime, "FUTURE", "availableStarting", "availableEnding");
            
            // Event Windows
            case "expiredEWs":
                return categorizeWindows(asset.get("eventWindowList"), exportTime, "EXPIRED", "eventStarting", "eventEnding");
            case "currentEWs":
                return categorizeWindows(asset.get("eventWindowList"), exportTime, "CURRENT", "eventStarting", "eventEnding");
            case "futureEWs":
                return categorizeWindows(asset.get("eventWindowList"), exportTime, "FUTURE", "eventStarting", "eventEnding");

            // Geo Restrictions
            case "geoAccessType":
                return extractSimpleJsonArray(asset.get("geoRestrictions"), "accessType");
            case "geoRestrictionType":
                return extractSimpleJsonArray(asset.get("geoRestrictions"), "restrictionType");
            case "geoTeamRegion":
                return extractSimpleJsonArray(asset.get("geoRestrictions"), "teamRegion");

            default:
                return "";
        }
    }

    private static String categorizeWindows(JsonNode windowList, Instant now, String targetStatus, String startKey, String endKey) {
        if (windowList == null || !windowList.isArray()) return "";

        List<String> validWindows = new ArrayList<>();
        
        for (JsonNode window : windowList) {
            String startStr = window.path(startKey).asText(null);
            String endStr = window.path(endKey).asText(null);

            if (startStr == null || startStr.isEmpty()) continue;

            try {
                Instant startDateTime = Instant.parse(startStr);
                Instant endDateTime = (endStr != null && !endStr.isEmpty()) ? Instant.parse(endStr) : Instant.MAX;

                String currentStatus;
                if (startDateTime.isAfter(now)) {
                    currentStatus = "FUTURE";
                } else if (endDateTime.isBefore(now)) {
                    currentStatus = "EXPIRED";
                } else {
                    currentStatus = "CURRENT";
                }

                if (currentStatus.equals(targetStatus)) {
                    String formattedStart = CommonMethodUtil.formatDateField(startStr);
                    String formattedEnd = (endStr != null && !endStr.isEmpty()) ? CommonMethodUtil.formatDateField(endStr) : "";
                    validWindows.add(formattedStart + ";" + formattedEnd);
                }
            } catch (DateTimeParseException e) {
                // Ignore invalid date mappings and continue parsing valid ones
            }
        }
        return String.join(", ", validWindows);
    }

    private static String formatCast(JsonNode castNode, String targetRole) {
        if (castNode == null || !castNode.isArray()) return "";
        List<String> results = new ArrayList<>();
        
        for (JsonNode member : castNode) {
            if (targetRole.equalsIgnoreCase(member.path("role").asText(""))) {
                String name = member.path("name").asText("");
                String character = member.path("characterName").asText("");
                
                if (!character.isEmpty()) {
                    results.add(name + " (" + character + ")");
                } else if (!name.isEmpty()) {
                    results.add(name);
                }
            }
        }
        return String.join(", ", results);
    }

    private static String formatRatings(JsonNode ratingsNode) {
        if (ratingsNode == null || !ratingsNode.isArray()) return "";
        List<String> results = new ArrayList<>();
        
        for (JsonNode rating : ratingsNode) {
            String body = rating.path("body").asText("");
            String value = rating.path("ratings").asText("");
            if (!body.isEmpty() || !value.isEmpty()) {
                 results.add(body + " (" + value + ")");
            }
        }
        return String.join(", ", results);
    }

    private static String formatExternalIds(JsonNode providerNode) {
        if (providerNode == null || !providerNode.isArray()) return "";
        List<String> results = new ArrayList<>();
        
        for (JsonNode provider : providerNode) {
            String prov = provider.path("provider").asText("");
            String extId = provider.path("externalProgramId").asText("");
            if (!prov.isEmpty() && !extId.isEmpty()) {
                results.add(prov + ": " + extId);
            }
        }
        return String.join(", ", results);
    }

    private static String extractSimpleJsonArray(JsonNode arrayNode, String key) {
        if (arrayNode == null || !arrayNode.isArray()) return "";
        List<String> results = new ArrayList<>();
        for (JsonNode node : arrayNode) {
            String val = node.path(key).asText("");
            if(!val.isEmpty()) results.add(val);
        }
        return String.join(", ", results);
    }
}

```

### 4.4. `AssetExportService.java`

*Path: `src/main/java/com/cms/backend/assets/service/AssetExportService.java*`

```java
package com.cms.backend.assets.service;

import com.cms.backend.assets.configuration.ExportFieldMappingConfig;
import com.cms.backend.assets.model.AssetFilterBodyDto;
import com.cms.backend.assets.model.ExportHelperDto;
import com.cms.backend.assets.model.PaginationDto;
import com.cms.backend.assets.model.ExportStateContext;
import com.cms.backend.assets.util.AssetExportDataFormatter;
import com.cms.backend.common.constants.Constants;
import com.cms.backend.common.exception.CustomException;
import com.cms.backend.common.model.ResponseDto;
import com.cms.backend.common.service.RegionEndpointService;
import com.cms.backend.common.util.CommonMethodUtil;
import com.cms.backend.common.util.HttpMethodHandler;
import com.cms.backend.evaluation.model.ComparisonAssetListResponseDto;
import com.cms.backend.evaluation.model.CountDto;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CompletionException;

import lombok.extern.slf4j.Slf4j;
import org.apache.poi.ss.usermodel.*;
import org.apache.poi.ss.util.CellRangeAddress;
import org.apache.poi.xssf.streaming.SXSSFWorkbook;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.http.HttpEntity;
import org.springframework.http.ResponseEntity;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;
import org.springframework.stereotype.Service;

@Slf4j
@Service
public class AssetExportService {

    private final RegionEndpointService regionEndpointService;
    private final HttpMethodHandler httpMethodHandler;
    private final ThreadPoolTaskExecutor exportTaskExecutor;

    private static final int PARALLEL_CALLS = 2;
    private static final int PAGE_SIZE = 5000;
    
    private final ObjectMapper objectMapper = new ObjectMapper();

    public AssetExportService(RegionEndpointService regionEndpointService,
                              HttpMethodHandler httpMethodHandler,
                              @Qualifier("exportTaskExecutor") ThreadPoolTaskExecutor exportTaskExecutor) {
        this.regionEndpointService = regionEndpointService;
        this.httpMethodHandler = httpMethodHandler;
        this.exportTaskExecutor = exportTaskExecutor;
    }

    public ExportHelperDto startExport(AssetFilterBodyDto filterBodyDto, boolean isEvaluation) throws IOException {
        String fileNamePrefix = isEvaluation ? "EvaluationAssets_" : "MediaAssets_";
        
        int totalAssetCount = getTotalAssetCount(filterBodyDto, isEvaluation);
        log.info("Asset Count Received from API: {}", totalAssetCount);

        Instant exportTime = Instant.now();
        
        byte[] excelData = createExcelFromAssetsSequential(filterBodyDto, totalAssetCount, exportTime, isEvaluation);
        
        String fileName = fileNamePrefix + LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMddHHmmss")) + ".xlsx";

        return ExportHelperDto.builder()
                .excelData(excelData)
                .fileName(fileName)
                .fileType("EXCEL")
                .build();
    }

    private byte[] createExcelFromAssetsSequential(AssetFilterBodyDto filterBody, int totalAssetCount, Instant exportTime, boolean isEvaluation) throws IOException {
        try (SXSSFWorkbook workbook = new SXSSFWorkbook(1000); 
             ByteArrayOutputStream outputStream = new ByteArrayOutputStream()) {
            
            workbook.setCompressTempFiles(true);
            
            ExportStateContext context = new ExportStateContext();
            if (filterBody.getColumns() != null && !filterBody.getColumns().isEmpty()) {
                context.setupSelectiveExport(filterBody.getColumns(), isEvaluation);
            } else {
                context.setupFullExport(isEvaluation);
            }
            
            Sheet sheet = workbook.createSheet(isEvaluation ? "EvaluationAssets" : "MediaAssets");
            sheet.setDefaultRowHeightInPoints(30.0f);
            
            initializeStyles(workbook, context);
            context.setCurrentExcel(workbook);
            context.setCurrentSheet(sheet);
            
            int currentRow = 0;
            currentRow = createGroupHeaders(sheet, currentRow, context);
            currentRow = createColumnHeaders(sheet, currentRow, context);
            context.setCurrentRow(currentRow);

            int currentOffset = 0;

            while (currentOffset < totalAssetCount) {
                List<JsonNode> batchAssets = fetchAssetBatch(filterBody, currentOffset, isEvaluation);
                if (batchAssets.isEmpty()) break;

                for (JsonNode asset : batchAssets) {
                    Map<String, String> rowData = buildRowData(asset, context, exportTime);
                    createExcelRow(sheet, rowData, context.getCurrentRow(), context);
                    context.setCurrentRow(context.getCurrentRow() + 1);
                }

                currentOffset += batchAssets.size();
                log.info("Processed {}/{} assets into excel sheet", currentOffset, totalAssetCount);
                
                // Memory clearance to prevent OOM
                batchAssets.clear();
            }

            workbook.write(outputStream);
            return outputStream.toByteArray();

        } catch (Exception e) {
            log.error("Error Creating Excel: {}", e.getMessage());
            throw new IOException("Failed to create Excel: ", e);
        }
    }

    private List<JsonNode> fetchAssetBatch(AssetFilterBodyDto filterBody, int startOffset, boolean isEvaluation) {
        try {
            List<CompletableFuture<List<JsonNode>>> batchFutures = new ArrayList<>();
            for (int i = 0; i < PARALLEL_CALLS; i++) {
                final int offset = startOffset + (i * PAGE_SIZE);
                batchFutures.add(CompletableFuture.supplyAsync(() -> {
                    try {
                        return fetchAssetsFromAPI(filterBody, offset, isEvaluation);
                    } catch (IOException e) {
                        throw new CompletionException(e);
                    }
                }, exportTaskExecutor));
            }

            return new ArrayList<>(batchFutures.stream()
                    .map(CompletableFuture::join)
                    .flatMap(List::stream)
                    .toList());

        } catch (CompletionException e) {
            log.error("Failed to fetch asset batch: {}", e.getMessage());
            throw new CustomException("Failed to fetch asset batch");
        }
    }

    public List<JsonNode> fetchAssetsFromAPI(AssetFilterBodyDto assetFilterBodyDto, int offset, boolean isEvaluation) throws IOException {
        AssetFilterBodyDto apiFilterBody = AssetFilterBodyDto.builder()
                .columns(assetFilterBodyDto.getColumns())
                .filters(assetFilterBodyDto.getFilters())
                .pagination(PaginationDto.builder().limit(PAGE_SIZE).offset(offset).build())
                .build();
                
        HttpEntity<AssetFilterBodyDto> httpEntity = new HttpEntity<>(apiFilterBody);
        String finalUrl = regionEndpointService.getOpenAPIEndpointNLB() + 
            (isEvaluation ? Constants.GET_EVALUATION_VIEW : Constants.EXPORT_ASSET_ENDPOINT);
            
        ResponseEntity<ResponseDto> responseEntity = httpMethodHandler.handleHttpExchange(
                finalUrl, Constants.METHOD_POST, httpEntity, ResponseDto.class);
                
        ResponseDto responseBody = Objects.requireNonNull(responseEntity.getBody());

        if (isEvaluation) {
            ComparisonAssetListResponseDto comparisonDto = objectMapper.convertValue(
                    responseBody.getRsp().getPayload().get("evaluation"), ComparisonAssetListResponseDto.class);
            return comparisonDto.getData();
        } else {
            return objectMapper.convertValue(
                    responseBody.getRsp().getPayload().get(Constants.ASSETS),
                    new TypeReference<>() {});
        }
    }

    private Map<String, String> buildRowData(JsonNode asset, ExportStateContext context, Instant exportTime) {
        Map<String, String> rowData = new HashMap<>();

        for (String fieldName : context.getFieldsToProcess()) {
            ExportFieldMappingConfig.FieldMetadata metadata = context.isEvaluation() ? 
                ExportFieldMappingConfig.EVALUATION_FIELD_CONFIG.get(fieldName) : 
                ExportFieldMappingConfig.FIELD_CONFIG.get(fieldName);

            if (metadata != null) {
                if (metadata.type == ExportFieldMappingConfig.FieldType.COMPUTED) {
                    rowData.put(fieldName, AssetExportDataFormatter.extractComputedValue(asset, fieldName, exportTime));
                } else {
                    rowData.put(fieldName, getSimpleValue(asset, fieldName));
                }
            } else {
                rowData.put(fieldName, "");
            }
        }
        return rowData;
    }

    private String getSimpleValue(JsonNode asset, String fieldName) {
        JsonNode value = asset.get(fieldName);
        if (value == null || value.isNull()) return "";
        
        String stringValue = value.asText();
        if (isDateField(fieldName) && stringValue.contains("T")) {
            return CommonMethodUtil.formatDateField(stringValue);
        }
        return stringValue;
    }

    private void createExcelRow(Sheet sheet, Map<String, String> rowData, int rowIndex, ExportStateContext context) {
        Row row = sheet.createRow(rowIndex);
        String[] fields = context.getFieldsToProcess();

        for (int i = 0; i < fields.length; i++) {
            Cell cell = row.createCell(i);
            cell.setCellStyle(context.getDataStyle());
            String value = rowData.get(fields[i]);
            cell.setCellValue(value != null ? value : "");
        }
    }

    private int createGroupHeaders(Sheet sheet, int rowIndex, ExportStateContext context) {
        if (context.isSelectiveExport()) return rowIndex;
        
        Row row = sheet.createRow(rowIndex);
        String[] groups = ExportFieldMappingConfig.getGroupsInOrder(context.isEvaluation());
        String[] fields = context.getFieldsToProcess();

        int colIndex = 0;
        for (String group : groups) {
            int groupStartCol = colIndex;
            int groupColCount = ExportFieldMappingConfig.countColumnsInGroup(fields, group, context.isEvaluation());

            if (groupColCount > 0) {
                Cell cell = row.createCell(groupStartCol);
                cell.setCellValue(group);
                cell.setCellStyle(context.getGroupStyles().get(group));

                if (groupColCount > 1) {
                    sheet.addMergedRegion(new CellRangeAddress(rowIndex, rowIndex, groupStartCol, groupStartCol + groupColCount - 1));
                }
                colIndex += groupColCount;
            }
        }
        return rowIndex + 1;
    }

    private int createColumnHeaders(Sheet sheet, int rowIndex, ExportStateContext context) {
        Row row = sheet.createRow(rowIndex);
        String[] fields = context.getFieldsToProcess();

        for (int i = 0; i < fields.length; i++) {
            Cell cell = row.createCell(i);
            ExportFieldMappingConfig.FieldMetadata metadata = context.isEvaluation() ? 
                ExportFieldMappingConfig.EVALUATION_FIELD_CONFIG.get(fields[i]) : 
                ExportFieldMappingConfig.FIELD_CONFIG.get(fields[i]);
                
            cell.setCellValue(metadata != null ? metadata.columnName : fields[i]);
            cell.setCellStyle(context.getColumnHeaderStyle());
        }
        return rowIndex + 1;
    }

    private void initializeStyles(Workbook workbook, ExportStateContext context) {
        context.setGroupStyles(createGroupHeaderStyle(workbook, context.isEvaluation()));
        context.setDataStyle(createDataStyle(workbook));
        context.setColumnHeaderStyle(createColumnHeaderStyle(workbook));
        context.setBottomBorderStyle(createBottomBorderStyle(workbook));
    }

    public Map<String, CellStyle> createGroupHeaderStyle(Workbook workbook, boolean isEvaluation) {
        Map<String, CellStyle> groupStyles = new HashMap<>();
        for (String group : ExportFieldMappingConfig.getGroupsInOrder(isEvaluation)) {
            CellStyle style = workbook.createCellStyle();
            Font font = workbook.createFont();
            font.setBold(true);
            font.setFontHeightInPoints((short) 12);
            style.setFont(font);
            IndexedColors color = ExportFieldMappingConfig.GROUP_COLORS.getOrDefault(group, IndexedColors.LIGHT_BLUE);
            style.setFillForegroundColor(color.getIndex());
            style.setFillPattern(FillPatternType.SOLID_FOREGROUND);
            style.setAlignment(HorizontalAlignment.CENTER);
            style.setVerticalAlignment(VerticalAlignment.CENTER);
            style.setBorderBottom(BorderStyle.THIN);
            style.setBorderTop(BorderStyle.THIN);
            style.setBorderLeft(BorderStyle.THIN);
            style.setBorderRight(BorderStyle.THIN);
            groupStyles.put(group, style);
        }
        return groupStyles;
    }

    public CellStyle createColumnHeaderStyle(Workbook workbook) {
        CellStyle style = workbook.createCellStyle();
        Font font = workbook.createFont();
        font.setBold(true);
        font.setFontHeightInPoints((short) 10);
        style.setFont(font);
        style.setFillForegroundColor(IndexedColors.GREY_25_PERCENT.getIndex());
        style.setFillPattern(FillPatternType.SOLID_FOREGROUND);
        style.setAlignment(HorizontalAlignment.CENTER);
        style.setVerticalAlignment(VerticalAlignment.CENTER);
        style.setBorderBottom(BorderStyle.THIN);
        style.setBorderTop(BorderStyle.THIN);
        style.setBorderLeft(BorderStyle.THIN);
        style.setBorderRight(BorderStyle.THIN);
        return style;
    }

    public CellStyle createDataStyle(Workbook workbook) {
        CellStyle style = workbook.createCellStyle();
        style.setAlignment(HorizontalAlignment.LEFT);
        style.setVerticalAlignment(VerticalAlignment.CENTER);
        style.setBorderBottom(BorderStyle.THIN);
        style.setBorderTop(BorderStyle.THIN);
        style.setBorderLeft(BorderStyle.THIN);
        style.setBorderRight(BorderStyle.THIN);
        return style;
    }

    public CellStyle createBottomBorderStyle(Workbook workbook) {
        CellStyle style = workbook.createCellStyle();
        style.setAlignment(HorizontalAlignment.LEFT);
        style.setVerticalAlignment(VerticalAlignment.CENTER);
        style.setBorderBottom(BorderStyle.THICK);
        style.setBorderTop(BorderStyle.THIN);
        style.setBorderLeft(BorderStyle.THIN);
        style.setBorderRight(BorderStyle.THIN);
        return style;
    }

    public int getTotalAssetCount(AssetFilterBodyDto assetFilterBodyDto, boolean isEvaluation) throws IOException {
        HttpEntity<AssetFilterBodyDto> httpEntity = new HttpEntity<>(assetFilterBodyDto);
        String finalUrl = regionEndpointService.getOpenAPIEndpointNLB() + 
            (isEvaluation ? Constants.GET_EVALUATION_COUNT : Constants.EXPORT_ASSET_COUNT_ENDPOINT);

        ResponseEntity<ResponseDto> responseEntity = httpMethodHandler.handleHttpExchange(
                finalUrl, Constants.METHOD_POST, httpEntity, ResponseDto.class);
        ResponseDto responseBody = Objects.requireNonNull(responseEntity.getBody());

        if (isEvaluation) {
            CountDto countDto = objectMapper.convertValue(
                responseBody.getRsp().getPayload().get("evaluation"), CountDto.class);
            return countDto.getTotalCount();
        } else {
            return objectMapper.convertValue(
                responseBody.getRsp().getPayload().get("assetCount"), Integer.class);
        }
    }

    private boolean isDateField(String fieldName) {
        return fieldName.equals("releaseDate") || fieldName.equals("expiryDate") ||
               fieldName.equals("regDate") || fieldName.equals("updateDate");
    }
}

```

---

## 5. Verification & Testing Checklist

1. [ ] Check that `ZipExportContext.java` is fully deleted from the codebase.
2. [ ] Validate that `artist` mapping pulls directly from the `artist` key rather than attempting to filter the `cast` array.
3. [ ] Confirm memory management by generating an export with > 50,000 assets. The JVM heap should stay stable due to `batchAssets.clear()` and the `SXSSFWorkbook` sliding window.
4. [ ] Initiate simultaneous requests (1 Media Export, 1 Evaluation Export) to verify that the `isEvaluation` concurrency bug is fixed.
5. [ ] Check the `License Details` generated columns for boundary conditions (e.g. Ensure a start date exactly matching `Instant.now()` categorizes properly as `CURRENT`).
