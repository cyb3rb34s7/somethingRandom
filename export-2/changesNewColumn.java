// ========================================
// CHANGE 1: Add dual-nature fields constant
// ========================================
public class AssetExportService {
    
    // Add this constant at the top of your class
    private static final Set<String> DUAL_NATURE_FIELDS = Set.of(
        "availableStarting", 
        "availableEnding",
        "expiryDate",
        "licenseId"
        // Add other dual-nature fields as needed
    );

    // ========================================
    // CHANGE 2: Update buildRowData method
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
            // FULL EXPORT: Use existing FieldMappingConfig logic
            String[] fieldsToProcess = context.getFieldsToProcess();
            
            for (String fieldName : fieldsToProcess) {
                ExportFieldMappingConfig.FieldMetadata metadata = 
                    ExportFieldMappingConfig.FIELD_CONFIG.get(fieldName);
                    
                if (metadata != null) {
                    String value = extractValueBasedOnType(asset, fieldName, metadata, arrayIndex, context);
                    rowData.put(fieldName, value);
                } else {
                    String value = getSimpleValueForUnknownField(asset, fieldName, arrayIndex);
                    rowData.put(fieldName, value);
                }
            }
        }

        return rowData;
    }

    // ========================================
    // CHANGE 3: Add new method for selective export field extraction
    // ========================================
    private String extractSimpleFieldForSelective(JsonNode asset, String fieldName, int arrayIndex) {
        if (arrayIndex > 0) {
            return ""; // Selective export only uses first row for simple fields
        }

        JsonNode value = asset.get(fieldName);
        if (value == null || value.isNull()) {
            // If simple field not found and it's a dual-nature field, try array fallback
            if (DUAL_NATURE_FIELDS.contains(fieldName)) {
                return tryArrayFallbackForSelective(asset, fieldName);
            }
            return "";
        }

        String stringValue = value.asText();
        
        // Apply date formatting if needed
        if (isDateField(fieldName) && stringValue.contains("T")) {
            return formatDateField(stringValue);
        }

        return stringValue;
    }

    // ========================================
    // CHANGE 4: Add array fallback for selective export
    // ========================================
    private String tryArrayFallbackForSelective(JsonNode asset, String fieldName) {
        // Try to find this field in known array structures
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
    // CHANGE 5: Update extractValueBasedOnType method signature and logic
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
    // CHANGE 6: Add dual-nature field handling for full export
    // ========================================
    private String extractDualNatureFieldForFull(JsonNode asset, String fieldName,
        ExportFieldMappingConfig.FieldMetadata metadata, int arrayIndex) {
        
        String result = "";
        
        // FULL EXPORT: Array fields first (as per your API contract), simple fallback
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
    // CHANGE 7: Add helper extraction methods
    // ========================================
    private String trySimpleExtraction(JsonNode asset, String fieldName, int arrayIndex) {
        if (arrayIndex > 0) {
            return ""; // Simple fields only appear in first row
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
    // CHANGE 8: Update createColumnHeaders method
    // ========================================
    private int createColumnHeaders(Sheet sheet, int rowIndex, ZipExportContext context) {
        Row row = sheet.createRow(rowIndex);

        if (context.isSelectiveExport()) {
            // SELECTIVE EXPORT: Use raw field names as column headers
            List<String> selectedColumns = context.getSelectedColumns();
            for (int i = 0; i < selectedColumns.size(); i++) {
                Cell cell = row.createCell(i);
                String fieldName = selectedColumns.get(i);
                
                // Format field name for display (convert camelCase to readable)
                String columnHeader = formatFieldNameForDisplay(fieldName);
                cell.setCellValue(columnHeader);
                cell.setCellStyle(context.getColumnHeaderStyle());
            }
        } else {
            // FULL EXPORT: Use existing FieldMappingConfig logic
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
    // CHANGE 9: Add helper method for formatting field names
    // ========================================
    private String formatFieldNameForDisplay(String fieldName) {
        if (fieldName == null || fieldName.isEmpty()) {
            return fieldName;
        }
        
        // Convert camelCase to readable format
        // e.g., "availableStarting" -> "Available Starting"
        return fieldName.replaceAll("([a-z])([A-Z])", "$1 $2")
                       .substring(0, 1).toUpperCase() + 
                       fieldName.replaceAll("([a-z])([A-Z])", "$1 $2").substring(1);
    }

    // ========================================
    // CHANGE 10: Update createExcelRow method
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
            // FULL EXPORT: Use configured fields order
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
    // CHANGE 11: Update addBottomBorderToRow method  
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
}