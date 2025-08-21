// ===============================
// CHANGE 1: Add constants to ExportFieldMappingConfig.java
// ===============================
public class ExportFieldMappingConfig {
    
    // Add these constants after your existing FIELD_CONFIG
    public static final Set<String> DUAL_NATURE_FIELDS = Set.of(
        "availableStarting", 
        "availableEnding",
        "expiryDate",
        "licenseId"
    );

    // Fields that appear in full export (ordered by groups)
    public static final String[] FULL_EXPORT_FIELDS = {
        // ASSET_BASIC_INFORMATION group
        "contentId", "assetId", "type", "countryCode", "mainTitle", "language", 
        "shortTitle", "runningTime", "adTag", "streamUri", "description",
        "tiName", "showTitle", "seasonTitle", "showId", "seasonId", 
        "seasonNo", "episodeNo", "vcCpId",
        
        // ASSET_DETAILS group  
        "releaseDate", "genres", "body", "ratings", "starring", "expiryDate",
        
        // CAST_DETAILS group
        "role", "name", "characterName",
        
        // ASSET_SPECIFICATION group
        "deeplinkPayload", "chapterTime", "chapterDescription", "audioLang", 
        "subtitleLang", "drm", "quality", "scenePreviewUrl",
        
        // EXTERNAL_IDS group
        "externalProgramId", "provider", "idType", "externalIdProvider", 
        "onDeviceTrans", "liveOnDevice",
        
        // LICENSE_DETAILS group
        "availableStarting", "availableEnding", "contentPartner", "contentTier",
        "status", "dbStatus", "regDate", "updateDate", "qcPassReason"
    };

    // Your existing FIELD_CONFIG and methods remain unchanged
}

// ===============================
// CHANGE 2: Update ZipExportContext.java setupFullExport method
// ===============================
public void setupFullExport() {
    this.isSelectiveExport = false;
    this.selectedColumns = new ArrayList<>();
    this.fieldsToProcess = ExportFieldMappingConfig.FULL_EXPORT_FIELDS;
}

// ===============================
// CHANGE 3: Update extractValueBasedOnType method in AssetExportService.java
// ===============================
private String extractValueBasedOnType(JsonNode asset, String fieldName,
    ExportFieldMappingConfig.FieldMetadata metadata, int arrayIndex, 
    ZipExportContext context) {
    
    // For dual-nature fields in selective export, try simple first
    if (context.isSelectiveExport() && 
        ExportFieldMappingConfig.DUAL_NATURE_FIELDS.contains(fieldName)) {
        JsonNode simpleValue = asset.get(fieldName);
        if (simpleValue != null && !simpleValue.isNull()) {
            return arrayIndex == 0 ? getSimpleValue(asset, fieldName) : "";
        }
    }
    
    // Use existing switch logic for everything else
    return switch (metadata.type) {
        case SIMPLE ->
            arrayIndex == 0 ? getSimpleValue(asset, fieldName) : "";
        case ARRAY -> {
            JsonNode parentArray = asset.get(metadata.sourceArray);
            if (parentArray != null && parentArray.isArray()) {
                yield getArrayValue(asset, metadata.sourceArray, metadata.sourceField,
                    arrayIndex);
            } else {
                yield arrayIndex == 0 ? getSimpleValue(asset, fieldName) : "";
            }
        }
        default -> "";
    };
}

// ===============================
// CHANGE 4: Update buildRowData method calls
// ===============================
// Find all calls to extractValueBasedOnType and add the context parameter:
// OLD: extractValueBasedOnType(asset, fieldName, metadata, arrayIndex)
// NEW: extractValueBasedOnType(asset, fieldName, metadata, arrayIndex, context)

private Map<String, String> buildRowData(JsonNode asset, int arrayIndex,
    ZipExportContext context) {
    Map<String, String> rowData = new HashMap<>();
    String[] fieldsToProcess = context.getFieldsToProcess();

    for (String fieldName : fieldsToProcess) {
        ExportFieldMappingConfig.FieldMetadata metadata = 
            ExportFieldMappingConfig.FIELD_CONFIG.get(fieldName);
            
        if (metadata != null) {
            // ADD CONTEXT PARAMETER HERE
            String value = extractValueBasedOnType(asset, fieldName, metadata, arrayIndex, context);
            rowData.put(fieldName, value);
        } else {
            String value = getSimpleValueForUnknownField(asset, fieldName, arrayIndex);
            rowData.put(fieldName, value);
        }
    }

    return rowData;
}

// ===============================
// CHANGE 5: Update createColumnHeaders for selective export
// ===============================
private int createColumnHeaders(Sheet sheet, int rowIndex, ZipExportContext context) {
    Row row = sheet.createRow(rowIndex);
    String[] fields = context.getFieldsToProcess();

    for (int i = 0; i < fields.length; i++) {
        Cell cell = row.createCell(i);
        
        ExportFieldMappingConfig.FieldMetadata metadata = 
            ExportFieldMappingConfig.FIELD_CONFIG.get(fields[i]);
            
        String columnName;
        if (metadata != null) {
            columnName = metadata.columnName;
        } else {
            // For unknown fields, format the field name
            columnName = fields[i].replaceAll("([a-z])([A-Z])", "$1 $2");
            columnName = columnName.substring(0, 1).toUpperCase() + columnName.substring(1);
        }
        
        cell.setCellValue(columnName);
        cell.setCellStyle(context.getColumnHeaderStyle());
    }

    return rowIndex + 1;
}

// ===============================
// CHANGE 6: Reorganize ExportFieldMappingConfig FIELD_CONFIG
// ===============================
// In ExportFieldMappingConfig.java, reorganize the static block to group fields by their groups:

static {
    // ASSET_BASIC_INFORMATION group - all together
    FIELD_CONFIG.put("contentId", new FieldMetadata("Program ID", ASSET_BASIC_INFORMATION, FieldType.SIMPLE, null, null));
    FIELD_CONFIG.put("assetId", new FieldMetadata("Asset ID", ASSET_BASIC_INFORMATION, FieldType.SIMPLE, null, null));
    FIELD_CONFIG.put("type", new FieldMetadata("Program Type", ASSET_BASIC_INFORMATION, FieldType.SIMPLE, null, null));
    // ... continue with all ASSET_BASIC_INFORMATION fields
    
    // ASSET_DETAILS group - all together  
    FIELD_CONFIG.put("releaseDate", new FieldMetadata("Original Release Date", ASSET_DETAILS, FieldType.SIMPLE, null, null));
    FIELD_CONFIG.put("genres", new FieldMetadata("Genre", ASSET_DETAILS, FieldType.SIMPLE, null, null));
    // ... continue with all ASSET_DETAILS fields
    
    // CAST_DETAILS group - all together
    FIELD_CONFIG.put("role", new FieldMetadata("Person Role", CAST_DETAILS, FieldType.ARRAY, "cast", "role"));
    // ... continue with all CAST_DETAILS fields
    
    // Continue for all other groups...
}