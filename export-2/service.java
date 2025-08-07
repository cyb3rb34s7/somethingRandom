@Slf4j
@Service
public class ExcelExportService {
    
    private final ObjectMapper objectMapper = new ObjectMapper();
    private final HttpMethodHandler httpMethodHandler;
    private final RegionEndpointService regionEndpointService;
    private final TaskExecutor exportTaskExecutor;
    
    // Constants remain unchanged
    private static final int PARALLEL_CALLS = 5;
    private static final int PAGE_SIZE = 5000;
    private static final int ASSET_LIMIT_PER_EXCEL = 10000;
    private static final int BATCH_SIZE = PAGE_SIZE * PARALLEL_CALLS;
    
    public ExcelExportService(HttpMethodHandler httpMethodHandler, 
                             RegionEndpointService regionEndpointService,
                             TaskExecutor exportTaskExecutor) {
        this.httpMethodHandler = httpMethodHandler;
        this.regionEndpointService = regionEndpointService;
        this.exportTaskExecutor = exportTaskExecutor;
    }
    
    /**
     * *** UPDATED: Main export method with selective export support ***
     */
    public ExportHelperDto startExport(JsonNode filterBody) throws IOException {
        log.info("Starting export process");
        
        // *** NEW: Extract selected columns from filterBody ***
        List<String> selectedColumns = extractSelectedColumns(filterBody);
        boolean isSelectiveExport = !selectedColumns.isEmpty();
        
        log.info("Export type: {} (columns: {})", 
            isSelectiveExport ? "SELECTIVE" : "FULL", 
            isSelectiveExport ? selectedColumns : "ALL");
        
        // Get first page to determine dataset size
        List<JsonNode> firstPage = fetchAssetsFromAPI(filterBody, 0);
        
        String timestamp = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss"));
        
        if (firstPage.size() >= PAGE_SIZE) {
            // Large dataset - use ZIP
            log.info("Large dataset detected ({} assets in first page) - generating ZIP", firstPage.size());
            byte[] excelData = generateExcelZip(filterBody, selectedColumns);  // *** UPDATED: Pass selectedColumns ***
            
            return ExportHelperDto.builder()
                .excelData(excelData)
                .fileName("mediaasset_export_" + timestamp + ".zip")
                .fileType("ZIP")
                .build();
        } else {
            // Small dataset - use single Excel with first page data
            log.info("Small dataset detected ({} assets total) - generating single Excel", firstPage.size());
            byte[] excelData = createExcelFromAssets(firstPage, selectedColumns);  // *** UPDATED: Pass selectedColumns ***
            
            return ExportHelperDto.builder()
                .excelData(excelData)
                .fileName("mediaasset_export_" + timestamp + ".xlsx")
                .fileType("EXCEL")
                .build();
        }
    }
    
    /**
     * *** NEW: Extract selected columns from filterBody ***
     */
    private List<String> extractSelectedColumns(JsonNode filterBody) {
        List<String> selectedColumns = new ArrayList<>();
        
        JsonNode columnsNode = filterBody.get("columns");
        if (columnsNode != null && columnsNode.isArray() && columnsNode.size() > 0) {
            for (JsonNode columnNode : columnsNode) {
                String columnName = columnNode.asText();
                if (columnName != null && !columnName.trim().isEmpty()) {
                    selectedColumns.add(columnName.trim());
                }
            }
        }
        
        return selectedColumns;
    }
    
    /**
     * *** UPDATED: Generate ZIP file with selective export support ***
     */
    private byte[] generateExcelZip(JsonNode filterBody, List<String> selectedColumns) throws IOException {
        log.info("Starting ZIP-based Excel export process");
        
        try (ByteArrayOutputStream zipByteStream = new ByteArrayOutputStream();
             ZipOutputStream zipStream = new ZipOutputStream(zipByteStream)) {
            
            ZipExportContext context = new ZipExportContext(zipStream);
            
            // *** NEW: Setup export type ***
            if (selectedColumns.isEmpty()) {
                context.setupFullExport();
            } else {
                context.setupSelectiveExport(selectedColumns);
            }
            
            processAssetsInBatches(context, filterBody);
            finalizePendingExcel(context);
            
            zipStream.finish();
            
            log.info("ZIP export completed successfully. Created {} Excel files with {} total assets", 
                context.getCompletedExcelFiles(), context.getTotalAssetsProcessed());
            
            return zipByteStream.toByteArray();
            
        } catch (Exception e) {
            log.error("Failed to generate Excel ZIP: {}", e.getMessage(), e);
            throw new RuntimeException("Excel ZIP generation failed", e);
        }
    }
    
    /**
     * *** UPDATED: Create single Excel with selective export support ***
     */
    private byte[] createExcelFromAssets(List<JsonNode> assets, List<String> selectedColumns) throws IOException {
        log.info("Creating single Excel file for {} assets", assets.size());
        
        try (Workbook workbook = new XSSFWorkbook()) {
            Sheet sheet = workbook.createSheet("Assets");
            
            // Use ZipExportContext for styles (zipStream = null)
            ZipExportContext context = new ZipExportContext(null);
            context.setCurrentExcel(workbook);
            context.setCurrentSheet(sheet);
            
            // *** NEW: Setup export type ***
            if (selectedColumns.isEmpty()) {
                context.setupFullExport();
            } else {
                context.setupSelectiveExport(selectedColumns);
            }
            
            // Initialize styles
            initializeStyles(context, workbook);
            
            // Create headers
            int currentRow = 0;
            currentRow = createGroupHeaders(sheet, currentRow, context);  // *** UPDATED: Will handle selective export ***
            currentRow = createColumnHeaders(sheet, currentRow, context);
            
            // Process all assets
            for (JsonNode asset : assets) {
                currentRow = processAsset(sheet, asset, currentRow, context);
            }
            
            try (ByteArrayOutputStream outputStream = new ByteArrayOutputStream()) {
                workbook.write(outputStream);
                return outputStream.toByteArray();
            }
        }
    }
    
    /**
     * *** UPDATED: Create group headers with selective export support ***
     */
    private int createGroupHeaders(Sheet sheet, int rowIndex, ZipExportContext context) {
        // *** NEW: Skip group headers for selective export ***
        if (context.isSelectiveExport()) {
            log.debug("Skipping group headers for selective export");
            return rowIndex; // No group headers, return same row index
        }
        
        // Existing group header logic for full export
        Row row = sheet.createRow(rowIndex);
        String[] groups = FieldMappingConfig.getGroupsInOrder();
        String[] fields = context.getFieldsToProcess();  // *** UPDATED: Use context fields ***
        
        int colIndex = 0;
        for (String group : groups) {
            CellStyle groupStyle = context.getGroupHeaderStyles().get(group);
            
            int groupStartCol = colIndex;
            int groupColCount = FieldMappingConfig.countColumnsInGroup(fields, group);
            
            if (groupColCount > 0) {
                Cell cell = row.createCell(groupStartCol);
                cell.setCellValue(group);
                cell.setCellStyle(groupStyle);
                
                if (groupColCount > 1) {
                    sheet.addMergedRegion(new CellRangeAddress(
                        rowIndex, rowIndex, groupStartCol, groupStartCol + groupColCount - 1));
                }
                
                colIndex += groupColCount;
            }
        }
        
        return rowIndex + 1;
    }
    
    /**
     * *** UPDATED: Create column headers using selected fields ***
     */
    private int createColumnHeaders(Sheet sheet, int rowIndex, ZipExportContext context) {
        Row row = sheet.createRow(rowIndex);
        String[] fields = context.getFieldsToProcess();  // *** UPDATED: Use context fields instead of FieldMappingConfig.getFieldsInOrder() ***
        
        for (int i = 0; i < fields.length; i++) {
            Cell cell = row.createCell(i);
            FieldMappingConfig.FieldMetadata metadata = FieldMappingConfig.FIELD_CONFIG.get(fields[i]);
            String columnName = metadata != null ? metadata.columnName : fields[i];
            cell.setCellValue(columnName);
            cell.setCellStyle(context.getColumnHeaderStyle());
        }
        
        return rowIndex + 1;
    }
    
    /**
     * *** UPDATED: Build row data using selected fields only ***
     */
    private Map<String, String> buildRowData(JsonNode asset, int arrayIndex, ZipExportContext context) {
        Map<String, String> rowData = new HashMap<>();
        
        // *** UPDATED: Use context.getFieldsToProcess() instead of FieldMappingConfig.FIELD_CONFIG.entrySet() ***
        String[] fieldsToProcess = context.getFieldsToProcess();
        
        for (String fieldName : fieldsToProcess) {
            FieldMappingConfig.FieldMetadata metadata = FieldMappingConfig.FIELD_CONFIG.get(fieldName);
            if (metadata != null) {
                String value = extractValueBasedOnType(asset, fieldName, metadata, arrayIndex);
                rowData.put(fieldName, value);
            }
        }
        
        return rowData;
    }
    
    /**
     * *** UPDATED: Create Excel row using selected fields ***
     */
    private void createExcelRow(Sheet sheet, Map<String, String> rowData, CellStyle dataStyle, int rowIndex, ZipExportContext context) {
        Row row = sheet.createRow(rowIndex);
        String[] fields = context.getFieldsToProcess();  // *** UPDATED: Use context fields ***
        
        for (int i = 0; i < fields.length; i++) {
            Cell cell = row.createCell(i);
            cell.setCellStyle(dataStyle);
            
            String value = rowData.get(fields[i]);
            cell.setCellValue(value != null ? value : "");
        }
    }
    
    /**
     * *** UPDATED: Add bottom border using selected fields ***
     */
    private void addBottomBorderToRow(Sheet sheet, CellStyle borderStyle, int rowIndex, ZipExportContext context) {
        Row row = sheet.getRow(rowIndex);
        if (row != null) {
            String[] fields = context.getFieldsToProcess();  // *** UPDATED: Use context fields ***
            for (int i = 0; i < fields.length; i++) {
                Cell cell = row.getCell(i);
                if (cell != null) {
                    cell.setCellStyle(borderStyle);
                }
            }
        }
    }
    
    /**
     * *** UPDATED: Process asset with selective export support ***
     */
    private int processAsset(Sheet sheet, JsonNode asset, int currentRow, ZipExportContext context) {
        int maxRows = calculateMaxRows(asset);
        
        for (int arrayIndex = 0; arrayIndex < maxRows; arrayIndex++) {
            Map<String, String> rowData = buildRowData(asset, arrayIndex, context);  // *** UPDATED: Pass context ***
            createExcelRow(sheet, rowData, context.getDataStyle(), currentRow++, context);  // *** UPDATED: Pass context ***
        }
        
        addBottomBorderToRow(sheet, context.getBottomBorderStyle(), currentRow - 1, context);  // *** UPDATED: Pass context ***
        return currentRow;
    }
    
    // ========== ALL OTHER METHODS REMAIN UNCHANGED ==========
    
    /**
     * Process assets in batches continuously until all data is fetched
     */
    private void processAssetsInBatches(ZipExportContext context, JsonNode filterBody) throws IOException {
        boolean hasMore = true;
        int currentOffset = 0;
        
        while (hasMore) {
            List<JsonNode> batchAssets = fetchAssetBatch(filterBody, currentOffset);
            
            if (batchAssets.isEmpty()) {
                break;
            }
            
            processAssetBatch(context, batchAssets);
            
            currentOffset += BATCH_SIZE;
            hasMore = batchAssets.size() == BATCH_SIZE;
            
            log.info("Processed batch: {} assets. Total processed: {}", 
                batchAssets.size(), context.getTotalAssetsProcessed());
        }
    }
    
    /**
     * Fetch a batch of assets using parallel API calls
     */
    private List<JsonNode> fetchAssetBatch(JsonNode filterBody, int startOffset) {
        List<CompletableFuture<List<JsonNode>>> batchFutures = new ArrayList<>();
        
        for (int i = 0; i < PARALLEL_CALLS; i++) {
            final int offset = startOffset + (i * PAGE_SIZE);
            
            batchFutures.add(CompletableFuture.supplyAsync(() -> {
                try {
                    return fetchAssetsFromAPI(filterBody, offset);
                } catch (IOException e) {
                    throw new CompletionException(e);
                }
            }, exportTaskExecutor));
        }
        
        return batchFutures.stream()
            .map(CompletableFuture::join)
            .flatMap(List::stream)
            .collect(Collectors.toList());
    }
    
    /**
     * Process a batch of assets, creating Excel files based on asset count limit
     */
    private void processAssetBatch(ZipExportContext context, List<JsonNode> assets) throws IOException {
        for (JsonNode asset : assets) {
            if (context.getAssetsInCurrentExcel() >= ASSET_LIMIT_PER_EXCEL && 
                context.hasAssetsInCurrentExcel()) {
                
                finalizeCurrentExcel(context);
                startNewExcel(context);
            }
            
            if (context.getCurrentExcel() == null) {
                startNewExcel(context);
            }
            
            int newRowIndex = processAsset(context.getCurrentSheet(), asset, 
                context.getCurrentRow(), context);
            
            context.setCurrentRow(newRowIndex);
            context.incrementAssetCount();
        }
    }
    
    /**
     * Start building a new Excel file
     */
    private void startNewExcel(ZipExportContext context) {
        log.info("Starting Excel file #{}", context.getCompletedExcelFiles() + 1);
        
        Workbook workbook = new XSSFWorkbook();
        Sheet sheet = workbook.createSheet("Assets");
        
        context.setCurrentExcel(workbook);
        context.setCurrentSheet(sheet);
        
        initializeStyles(context, workbook);
        
        int currentRow = 0;
        currentRow = createGroupHeaders(sheet, currentRow, context);
        currentRow = createColumnHeaders(sheet, currentRow, context);
        
        context.setCurrentRow(currentRow);
        context.resetCurrentExcelAssetCount();
    }
    
    // All other methods (initializeStyles, finalizeCurrentExcel, addExcelToZip, 
    // generateExcelBytes, fetchAssetsFromAPI, calculateMaxRows, extractValueBasedOnType, 
    // getSimpleValue, getArrayValue, getCommaSeparatedValue, style creation methods) 
    // REMAIN EXACTLY THE SAME - NO CHANGES NEEDED
}
