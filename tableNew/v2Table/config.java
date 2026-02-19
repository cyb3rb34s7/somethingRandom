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

        // THIS CONTROLS FULL EXPORT. Missing fields are strictly omitted from here.
        public static final String[] FULL_EXPORT_FIELDS = {
                        "contentId", "assetId", "type", "countryCode", "mainTitle", "mainTitleLanguage",
                        "shortTitle", "shortTitleLanguage", "runningTime", "adTag", "streamUri", "language",
                        "description", "tiName", "showTitle", "seasonTitle", "showId", "seasonId",
                        "seasonNo", "episodeNo", "vcCpId", "ingestionType",
                        
                        "releaseDate", "genres", "computedRatings",
                        
                        "computedActor", "computedDirector", "artist",
                        
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

                // --- ORIGINAL MAP DEFINITIONS ---
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
                
                // Computed arrays for full export
                FIELD_CONFIG.put("computedRatings", new FieldMetadata("Ratings", ASSET_DETAILS, FieldType.COMPUTED));
                FIELD_CONFIG.put("computedActor", new FieldMetadata("Actor", CAST_DETAILS, FieldType.COMPUTED));
                FIELD_CONFIG.put("computedDirector", new FieldMetadata("Director", CAST_DETAILS, FieldType.COMPUTED));
                FIELD_CONFIG.put("artist", new FieldMetadata("Artist", CAST_DETAILS, FieldType.SIMPLE)); 
                FIELD_CONFIG.put("computedExternalIds", new FieldMetadata("External Ids", EXTERNAL_IDS, FieldType.COMPUTED));
                
                // Asset Specs
                FIELD_CONFIG.put("deeplinkPayload", new FieldMetadata("Deeplink Payload", ASSET_SPECIFICATION, FieldType.SIMPLE));
                FIELD_CONFIG.put("chapterTime", new FieldMetadata("Chapter Time", ASSET_SPECIFICATION, FieldType.SIMPLE));
                FIELD_CONFIG.put("chapterDescription", new FieldMetadata("Chapter Description", ASSET_SPECIFICATION, FieldType.SIMPLE));
                FIELD_CONFIG.put("audioLang", new FieldMetadata("Audio Language", ASSET_SPECIFICATION, FieldType.SIMPLE));
                FIELD_CONFIG.put("subtitleLang", new FieldMetadata("Subtitle Language", ASSET_SPECIFICATION, FieldType.SIMPLE));
                FIELD_CONFIG.put("drm", new FieldMetadata("DRM", ASSET_SPECIFICATION, FieldType.SIMPLE));
                FIELD_CONFIG.put("quality", new FieldMetadata("Quality", ASSET_SPECIFICATION, FieldType.SIMPLE));
                FIELD_CONFIG.put("webVttUrl", new FieldMetadata("Scene Preview Url", ASSET_SPECIFICATION, FieldType.SIMPLE));
                FIELD_CONFIG.put("attributes", new FieldMetadata("Attributes", ASSET_SPECIFICATION, FieldType.SIMPLE));

                // Computed Licenses for full export
                FIELD_CONFIG.put("expiredLWs", new FieldMetadata("Expired LWs", LICENSE_DETAILS, FieldType.COMPUTED));
                FIELD_CONFIG.put("currentLWs", new FieldMetadata("Current LWs", LICENSE_DETAILS, FieldType.COMPUTED));
                FIELD_CONFIG.put("futureLWs", new FieldMetadata("Future LWs", LICENSE_DETAILS, FieldType.COMPUTED));
                FIELD_CONFIG.put("expiredEWs", new FieldMetadata("Expired EWs", LICENSE_DETAILS, FieldType.COMPUTED));
                FIELD_CONFIG.put("currentEWs", new FieldMetadata("Current EWs", LICENSE_DETAILS, FieldType.COMPUTED));
                FIELD_CONFIG.put("futureEWs", new FieldMetadata("Future EWs", LICENSE_DETAILS, FieldType.COMPUTED));
                FIELD_CONFIG.put("contentPartner", new FieldMetadata("Content Partner/Licensor", LICENSE_DETAILS, FieldType.SIMPLE));
                FIELD_CONFIG.put("contentTier", new FieldMetadata("Content Tier", LICENSE_DETAILS, FieldType.SIMPLE));

                // Sport & Geo
                FIELD_CONFIG.put("airType", new FieldMetadata("Air Type", SPORT_INFORMATION, FieldType.SIMPLE));
                FIELD_CONFIG.put("subType", new FieldMetadata("Sub Type", SPORT_INFORMATION, FieldType.SIMPLE));
                FIELD_CONFIG.put("matchInformation", new FieldMetadata("Match Information", SPORT_INFORMATION, FieldType.SIMPLE));
                FIELD_CONFIG.put("geoAccessType", new FieldMetadata("Access Type", GEO_RESTRICTION, FieldType.COMPUTED));
                FIELD_CONFIG.put("geoRestrictionType", new FieldMetadata("Type", GEO_RESTRICTION, FieldType.COMPUTED));
                FIELD_CONFIG.put("geoTeamRegion", new FieldMetadata("Value", GEO_RESTRICTION, FieldType.COMPUTED));

                // --- RESTORED FIELDS FOR SELECTIVE EXPORT ONLY ---
                
                // Status / Metadata
                FIELD_CONFIG.put("status", new FieldMetadata("Status", ASSET_BASIC_INFORMATION, FieldType.SIMPLE));
                FIELD_CONFIG.put("dbStatus", new FieldMetadata("DB Status", ASSET_BASIC_INFORMATION, FieldType.SIMPLE));
                FIELD_CONFIG.put("qcPassReason", new FieldMetadata("QC Pass Reason", ASSET_BASIC_INFORMATION, FieldType.SIMPLE));
                FIELD_CONFIG.put("regDate", new FieldMetadata("Registration Date", ASSET_BASIC_INFORMATION, FieldType.SIMPLE));
                FIELD_CONFIG.put("updateDate", new FieldMetadata("Update Date", ASSET_BASIC_INFORMATION, FieldType.SIMPLE));
                
                // Raw Windows
                FIELD_CONFIG.put("licenseWindow", new FieldMetadata("License Window", LICENSE_DETAILS, FieldType.SIMPLE));
                FIELD_CONFIG.put("availableStarting", new FieldMetadata("Available Starting", LICENSE_DETAILS, FieldType.SIMPLE));
                FIELD_CONFIG.put("expiryDate", new FieldMetadata("Expiry Date", LICENSE_DETAILS, FieldType.SIMPLE));
                FIELD_CONFIG.put("eventStarting", new FieldMetadata("Event Starting", LICENSE_DETAILS, FieldType.SIMPLE));
                FIELD_CONFIG.put("eventEnding", new FieldMetadata("Event Ending", LICENSE_DETAILS, FieldType.SIMPLE));

                // Raw Cast/Details
                FIELD_CONFIG.put("starring", new FieldMetadata("Starring", CAST_DETAILS, FieldType.SIMPLE));
                FIELD_CONFIG.put("ratings", new FieldMetadata("Ratings", ASSET_DETAILS, FieldType.SIMPLE)); // Raw JSON string
                
                // Raw External IDs
                FIELD_CONFIG.put("externalProgramId", new FieldMetadata("External Program ID", EXTERNAL_IDS, FieldType.SIMPLE));
                FIELD_CONFIG.put("externalIdProvider", new FieldMetadata("External ID Provider", EXTERNAL_IDS, FieldType.SIMPLE));
                
                // Specifications / Geo
                FIELD_CONFIG.put("liveOnDevice", new FieldMetadata("Live On Device", ASSET_SPECIFICATION, FieldType.SIMPLE));
                FIELD_CONFIG.put("onDeviceTrans", new FieldMetadata("On Device Trans", ASSET_SPECIFICATION, FieldType.SIMPLE));
                FIELD_CONFIG.put("geoRestrictionYn", new FieldMetadata("Geo Restriction Y/N", GEO_RESTRICTION, FieldType.SIMPLE));

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
                        if (metadata != null && group.equals(metadata.group))
                                count++;
                }
                return count;
        }
}
