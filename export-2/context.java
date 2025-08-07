// ========== ZIP Export Context (UPDATED) ==========

@Data
private static class ZipExportContext {
    private final ZipOutputStream zipStream;
    private Workbook currentExcel;
    private Sheet currentSheet;
    private int currentRow = 0;
    private int assetsInCurrentExcel = 0;
    private int completedExcelFiles = 0;
    private int totalAssetsProcessed = 0;
    
    // Style fields
    private CellStyle columnHeaderStyle;
    private CellStyle dataStyle;
    private CellStyle bottomBorderStyle;
    private Map<String, CellStyle> groupHeaderStyles;
    
    // *** NEW: Selective Export Fields ***
    private boolean isSelectiveExport = false;
    private List<String> selectedColumns = new ArrayList<>();
    private String[] fieldsToProcess;
    
    public ZipExportContext(ZipOutputStream zipStream) {
        this.zipStream = zipStream;
        this.groupHeaderStyles = new HashMap<>();
    }
    
    // *** NEW: Method to setup selective export ***
    public void setupSelectiveExport(List<String> selectedColumns) {
        this.isSelectiveExport = !selectedColumns.isEmpty();
        this.selectedColumns = new ArrayList<>(selectedColumns);
        
        if (this.isSelectiveExport) {
            this.fieldsToProcess = selectedColumns.toArray(new String[0]);
        } else {
            this.fieldsToProcess = FieldMappingConfig.getFieldsInOrder();
        }
    }
    
    // *** NEW: Method to setup full export (default) ***
    public void setupFullExport() {
        this.isSelectiveExport = false;
        this.selectedColumns = new ArrayList<>();
        this.fieldsToProcess = FieldMappingConfig.getFieldsInOrder();
    }
    
    // Existing methods remain unchanged
    public boolean hasAssetsInCurrentExcel() { 
        return assetsInCurrentExcel > 0; 
    }
    
    public void incrementAssetCount() { 
        this.assetsInCurrentExcel++; 
        this.totalAssetsProcessed++; 
    }
    
    public void resetCurrentExcelAssetCount() { 
        this.assetsInCurrentExcel = 0; 
    }
    
    public void incrementCompletedExcelFiles() { 
        this.completedExcelFiles++; 
    }
    
    public void clearCurrentExcel() { 
        this.currentExcel = null; 
        this.currentSheet = null;
        this.currentRow = 0;
        // Clear styles - they're workbook-specific
        this.columnHeaderStyle = null;
        this.dataStyle = null;
        this.bottomBorderStyle = null;
        this.groupHeaderStyles.clear();
    }
}
