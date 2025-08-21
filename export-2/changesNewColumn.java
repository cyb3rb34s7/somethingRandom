// ========================================
// STEP 1: Add constants at the top of AssetExportService class
// ========================================
public class AssetExportService {
    
    // Dual-nature fields that can appear as both simple and array
    private static final Set<String> DUAL_NATURE_FIELDS = Set.of(
        "availableStarting", 
        "availableEnding",
        "expiryDate",
        "licenseId"
    );

    // Fields that appear in full export (ordered by groups)
    private static final String[] FULL_EXPORT_FIELDS = {
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

    // ========================================
    // STEP 2: Update ZipExportContext setupFullExport method
    // ========================================
    // In ZipExportContext.java, replace the setupFullExport method:
    
    public void setupFullExport() {
        this.isSelectiveExport = false;
        this.selectedColumns = new ArrayList<>();
        // Use the hardcoded full export fields instead of config
        this.fieldsToProcess = AssetExportService.FULL_EXPORT_FIELDS;
    }

    // ========================================
    // STEP 3: Completely replace buildRowData method
    // ========================================
    private Map<String, String> buildRowData(JsonNode asset, int arrayIndex,
        ZipExportContext context) {
        Map<String, String> rowData = new HashMap<>();

        if (context.isSelectiveExport()) {
            // SELECTIVE EXPORT: Process user-selected columns as simple fields
            for (String fieldName : context.getSelectedColumns()) {
                String value = extractSimpleFieldForSelective(asset, fieldName, arrayIndex);
                rowData.put(fieldName, value);
            }
        } else {
            // FULL EXPORT: Use FULL_EXPORT_FIELDS with FieldMappingConfig
            String[] fieldsToProcess = context.getFieldsToProcess();
            
            for (String fieldName : fieldsToProcess) {
                ExportFieldMappingConfig.FieldMetadata metadata = 
                    ExportFieldMappingConfig.FIELD_CONFIG.get(fieldName);
                    
                if (metadata != null) {
                    String value = extractValueBasedOnType(asset, fieldName, metadata, arrayIndex, context);
                    rowData.put(fieldName, value);
                } else {
                    // For fields not in config, treat as simple
                    String value = getSimpleValueForUnknownField(asset, fieldName, arrayIndex);
                    rowData.put(fieldName, value);
                }
            }
        }

        return rowData;
    }

    // ========================================
    // STEP 4: Add selective export field extraction method
    // ========================================
    private String extractSimpleFieldForSelective(JsonNode asset, String fieldName, int arrayIndex) {
        if (arrayIndex > 0) {
            return ""; // Selective export only uses first row
        }

        JsonNode value = asset.get(fieldName);
        if (value == null || value.isNull()) {
            // If simple field not found and it's dual-nature, try array fallback
            if (DUAL_NATURE_FIELDS.contains(fieldName)) {
                return tryArrayFallbackForSelective(asset, fieldName);
            }
            return "";
        }

        String stringValue = value.asText();
        
        if (isDateField(fieldName) && stringValue.contains("T")) {
            return formatDateField(stringValue);
        }

        return stringValue;
    }

    // ========================================
    // STEP 5: Add array fallback for selective export
    // ========================================
    private String tryArrayFallbackForSelective(JsonNode asset, String fieldName) {
        ExportFieldMappingConfig.FieldMetadata metadata = 
            ExportFieldMappingConfig.FIELD_CONFIG.get(fieldName);
            
        if (metadata != null && metadata.type == ExportFieldMappingConfig.FieldType.ARRAY) {
            JsonNode parentArray = asset.get(metadata.sourceArray);
            if (parentArray != null && parentArray.isArray() && parentArray.size() > 0) {
                JsonNode firstItem = parentArray.get(0);
                JsonNode fieldValue = firstItem.get(metadata.sourceField);
                
                if (fieldValue != null && !fieldValue.isNull()) {
                    String stringValue = fieldValue.asText();
                    if (isDateField(fieldName) && stringValue.contains("T")) {
                        return formatDateField(stringValue);
                    }
                    return stringValue;
                }
            }
        }
        
        return "";
    }

    // ========================================
    // STEP 6: Update extractValueBasedOnType method signature and logic
    // ========================================
    private String extractValueBasedOnType(JsonNode asset, String fieldName,
        ExportFieldMappingConfig.FieldMetadata metadata, int arrayIndex, 
        ZipExportContext context) {
        
        // Check if this is a dual-nature field requiring special handling
        if (DUAL_NATURE_FIELDS.contains(fieldName)) {
            return extractDualNatureFieldForFull(asset, fieldName, metadata, arrayIndex);
        }
        
        // For non-dual-nature fields, use existing logic
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

    // ========================================
    // STEP 7: Add dual-nature field handling for full export
    // ========================================
    private String extractDualNatureFieldForFull(JsonNode asset, String fieldName,
        ExportFieldMappingConfig.FieldMetadata metadata, int arrayIndex) {
        
        String result = "";
        
        // FULL EXPORT: Array fields first, simple fallback
        if (metadata.type == ExportFieldMappingConfig.FieldType.ARRAY) {
            result = tryArrayExtraction(asset, metadata, arrayIndex);
            
            if (result.isEmpty()) {
                result = trySimpleExtraction(asset, fieldName, arrayIndex);
                if (!result.isEmpty()) {
                    log.debug("Used simple fallback for field '{}' in full export", fieldName);
                }
            }
        } else {
            // If configured as SIMPLE but it's a dual-nature field
            result = trySimpleExtraction(asset, fieldName, arrayIndex);
        }
        
        return result;
    }

    // ========================================
    // STEP 8: Add helper extraction methods
    // ========================================
    private String trySimpleExtraction(JsonNode asset, String fieldName, int arrayIndex) {
        if (arrayIndex > 0) {
            return "";
        }
        
        JsonNode value = asset.get(fieldName);
        if (value == null || value.isNull()) {
            return "";
        }
        
        String stringValue = value.asText();
        
        if (isDateField(fieldName) && stringValue.contains("T")) {
            return formatDateField(stringValue);
        }
        
        return stringValue;
    }

    private String tryArrayExtraction(JsonNode asset, ExportFieldMappingConfig.FieldMetadata metadata, int arrayIndex) {
        JsonNode parentArray = asset.get(metadata.sourceArray);
        if (parentArray == null || !parentArray.isArray() || arrayIndex >= parentArray.size()) {
            return "";
        }
        
        JsonNode item = parentArray.get(arrayIndex);
        if (item == null) {
            return "";
        }
        
        JsonNode fieldValue = item.get(metadata.sourceField);
        if (fieldValue == null || fieldValue.isNull()) {
            return "";
        }
        
        String stringValue = fieldValue.asText();
        
        if (isDateField(metadata.sourceField) && stringValue.contains("T")) {
            return formatDateField(stringValue);
        }
        
        return stringValue;
    }

    // ========================================
    // STEP 9: Update createColumnHeaders method
    // ========================================
    private int createColumnHeaders(Sheet sheet, int rowIndex, ZipExportContext context) {
        Row row = sheet.createRow(rowIndex);

        if (context.isSelectiveExport()) {
            // SELECTIVE EXPORT: Use formatted field names as headers
            List<String> selectedColumns = context.getSelectedColumns();
            for (int i = 0; i < selectedColumns.size(); i++) {
                Cell cell = row.createCell(i);
                String fieldName = selectedColumns.get(i);
                
                // Try to get display name from config, fallback to formatted name
                ExportFieldMappingConfig.FieldMetadata metadata = 
                    ExportFieldMappingConfig.FIELD_CONFIG.get(fieldName);
                String columnHeader = metadata != null ? metadata.columnName : 
                                    formatFieldNameForDisplay(fieldName);
                
                cell.setCellValue(columnHeader);
                cell.setCellStyle(context.getColumnHeaderStyle());
            }
        } else {
            // FULL EXPORT: Use FieldMappingConfig display names
            String[] fields = context.getFieldsToProcess();
            for (int i = 0; i < fields.length; i++) {
                Cell cell = row.createCell(i);
                ExportFieldMappingConfig.FieldMetadata metadata = 
                    ExportFieldMappingConfig.FIELD_CONFIG.get(fields[i]);
                String columnName = metadata != null ? metadata.columnName : fields[i];
                cell.setCellValue(columnName);
                cell.setCellStyle(context.getColumnHeaderStyle());
            }
        }

        return rowIndex + 1;
    }

    // ========================================
    // STEP 10: Add helper method for formatting field names
    // ========================================
    private String formatFieldNameForDisplay(String fieldName) {
        if (fieldName == null || fieldName.isEmpty()) {
            return fieldName;
        }
        
        // Convert camelCase to readable format
        String formatted = fieldName.replaceAll("([a-z])([A-Z])", "$1 $2");
        return formatted.substring(0, 1).toUpperCase() + formatted.substring(1);
    }

    // ========================================
    // STEP 11: Update createExcelRow method
    // ========================================
    private void createExcelRow(Sheet sheet, Map<String, String> rowData,
        int rowIndex, ZipExportContext context) {
        Row row = sheet.createRow(rowIndex);
        
        if (context.isSelectiveExport()) {
            // SELECTIVE EXPORT: Use selected columns order
            List<String> selectedColumns = context.getSelectedColumns();
            for (int i = 0; i < selectedColumns.size(); i++) {
                Cell cell = row.createCell(i);
                cell.setCellStyle(context.getDataStyle());
                String value = rowData.get(selectedColumns.get(i));
                cell.setCellValue(value != null ? value : "");
            }
        } else {
            // FULL EXPORT: Use full export fields order
            String[] fields = context.getFieldsToProcess();
            for (int i = 0; i < fields.length; i++) {
                Cell cell = row.createCell(i);
                cell.setCellStyle(context.getDataStyle());
                String value = rowData.get(fields[i]);
                cell.setCellValue(value != null ? value : "");
            }
        }
    }

    // ========================================
    // STEP 12: Update addBottomBorderToRow method
    // ========================================
    private void addBottomBorderToRow(Sheet sheet, int rowIndex, ZipExportContext context) {
        Row row = sheet.getRow(rowIndex);
        if (row != null) {
            int columnCount;
            if (context.isSelectiveExport()) {
                columnCount = context.getSelectedColumns().size();
            } else {
                columnCount = context.getFieldsToProcess().length;
            }
            
            for (int i = 0; i < columnCount; i++) {
                Cell cell = row.getCell(i);
                if (cell != null) {
                    cell.setCellStyle(context.getBottomBorderStyle());
                }
            }
        }
    }

    // ========================================
    // STEP 13: Update all calls to extractValueBasedOnType
    // ========================================
    // Find any other calls to extractValueBasedOnType in your code and add the context parameter
    // The signature is now: extractValueBasedOnType(asset, fieldName, metadata, arrayIndex, context)
}

// ========================================
// STEP 14: Reorganize your ExportFieldMappingConfig
// ========================================
// In ExportFieldMappingConfig.java, reorganize the FIELD_CONFIG entries to group fields by their groups:

// Group all ASSET_BASIC_INFORMATION fields together
// Group all ASSET_DETAILS fields together  
// Group all CAST_DETAILS fields together
// Group all ASSET_SPECIFICATION fields together
// Group all EXTERNAL_IDS fields together
// Group all LICENSE_DETAILS fields together

// This ensures group headers span the correct columns