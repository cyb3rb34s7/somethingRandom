The issue you're experiencing is common when working with Excel cell protection in Apache POI. Setting `cellStyle.setLocked(true)` alone doesn't actually protect the cells - you need to enable worksheet protection as well.

Here's why it's not working and the complete solution:

## Why `setLocked(true)` Isn't Working

By default, ALL cells in Excel are locked (`setLocked(true)`), but the worksheet protection is disabled. When worksheet protection is off, the locked property has no effect. You need to:

1. Set specific columns as locked (which you're doing)
2. Set other columns as unlocked 
3. **Enable worksheet protection**

## Complete Solution

import org.apache.poi.ss.usermodel.*;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;
import java.io.FileOutputStream;
import java.io.IOException;

public class ExcelColumnProtection {
    
    public void createProtectedExcel() throws IOException {
        Workbook workbook = new XSSFWorkbook();
        Sheet sheet = workbook.createSheet("Protected Sheet");
        
        // Create cell styles
        CellStyle lockedStyle = workbook.createCellStyle();
        CellStyle unlockedStyle = workbook.createCellStyle();
        
        // Set locked style (for non-editable columns)
        lockedStyle.setLocked(true);
        lockedStyle.setFillForegroundColor(IndexedColors.LIGHT_GREY.getIndex());
        lockedStyle.setFillPattern(FillPatternType.SOLID_FOREGROUND);
        
        // Set unlocked style (for editable columns)
        unlockedStyle.setLocked(false);
        
        // Create header row
        Row headerRow = sheet.createRow(0);
        String[] headers = {"ID (Locked)", "Name (Editable)", "Email (Editable)", "Status (Locked)"};
        
        for (int i = 0; i < headers.length; i++) {
            Cell cell = headerRow.createCell(i);
            cell.setCellValue(headers[i]);
            // Apply appropriate style based on column
            if (i == 0 || i == 3) { // Columns 0 and 3 are locked
                cell.setCellStyle(lockedStyle);
            } else {
                cell.setCellStyle(unlockedStyle);
            }
        }
        
        // Add sample data rows
        for (int rowNum = 1; rowNum <= 5; rowNum++) {
            Row row = sheet.createRow(rowNum);
            
            // ID column (locked)
            Cell idCell = row.createCell(0);
            idCell.setCellValue("ID" + rowNum);
            idCell.setCellStyle(lockedStyle);
            
            // Name column (editable)
            Cell nameCell = row.createCell(1);
            nameCell.setCellValue("User " + rowNum);
            nameCell.setCellStyle(unlockedStyle);
            
            // Email column (editable)
            Cell emailCell = row.createCell(2);
            emailCell.setCellValue("user" + rowNum + "@example.com");
            emailCell.setCellStyle(unlockedStyle);
            
            // Status column (locked)
            Cell statusCell = row.createCell(3);
            statusCell.setCellValue("Active");
            statusCell.setCellStyle(lockedStyle);
        }
        
        // CRITICAL STEP: Enable worksheet protection
        // This is what you were missing!
        sheet.protectSheet("your-password-here"); // You can use null for no password
        
        // Optional: Set specific protection options
        // sheet.protectSheet("password", true, true); // Enable protection with specific settings
        
        // Auto-size columns
        for (int i = 0; i < headers.length; i++) {
            sheet.autoSizeColumn(i);
        }
        
        // Write to file
        try (FileOutputStream fileOut = new FileOutputStream("protected_excel.xlsx")) {
            workbook.write(fileOut);
        }
        
        workbook.close();
    }
}

// Alternative approach for more granular control
public class AdvancedExcelProtection {
    
    public void createAdvancedProtectedExcel() throws IOException {
        Workbook workbook = new XSSFWorkbook();
        Sheet sheet = workbook.createSheet("Advanced Protection");
        
        // Create styles
        CellStyle lockedStyle = workbook.createCellStyle();
        CellStyle unlockedStyle = workbook.createCellStyle();
        
        lockedStyle.setLocked(true);
        unlockedStyle.setLocked(false);
        
        // Your data creation logic here...
        
        // Enable protection with specific options
        sheet.protectSheet(
            "password",     // Password (can be null)
            true,          // Select locked cells
            true,          // Select unlocked cells
            true,          // Format cells
            true,          // Format columns
            true,          // Format rows
            true,          // Insert columns
            true,          // Insert rows
            true,          // Insert hyperlinks
            true,          // Delete columns
            true,          // Delete rows
            true,          // Sort
            true,          // Use auto filter
            true,          // Use pivot table reports
            true           // Objects
        );
        
        workbook.close();
    }
}

// Spring Boot Controller example
@RestController
public class ExcelController {
    
    @GetMapping("/download-protected-excel")
    public ResponseEntity<byte[]> downloadProtectedExcel() throws IOException {
        Workbook workbook = new XSSFWorkbook();
        Sheet sheet = workbook.createSheet("Data");
        
        // Create styles
        CellStyle lockedStyle = workbook.createCellStyle();
        CellStyle unlockedStyle = workbook.createCellStyle();
        
        lockedStyle.setLocked(true);
        unlockedStyle.setLocked(false);
        
        // Add your data and apply styles...
        
        // IMPORTANT: Enable worksheet protection
        sheet.protectSheet(null); // No password protection
        
        // Convert to byte array
        ByteArrayOutputStream outputStream = new ByteArrayOutputStream();
        workbook.write(outputStream);
        workbook.close();
        
        byte[] excelContent = outputStream.toByteArray();
        
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_OCTET_STREAM);
        headers.setContentDispositionFormData("attachment", "protected-data.xlsx");
        
        return ResponseEntity.ok()
                .headers(headers)
                .body(excelContent);
    }
}

## Key Points:

1. **The Missing Step**: You must call `sheet.protectSheet()` after setting up your cell styles. Without this, the `setLocked(true)` has no effect.

2. **Two Types of Cells**: 
   - Locked cells (`setLocked(true)`) - cannot be edited when sheet is protected
   - Unlocked cells (`setLocked(false)`) - can be edited even when sheet is protected

3. **Password Protection**: You can protect with or without a password:
   ```java
   sheet.protectSheet("password");  // With password
   sheet.protectSheet(null);        // Without password
   ```

4. **Visual Indication**: Consider adding visual styling (like gray background) to locked columns so users can easily identify which fields are non-editable.

The key takeaway is that Excel's protection model requires both the cell-level lock setting AND worksheet-level protection to be enabled. Once you add `sheet.protectSheet()`, your locked columns will become non-editable in the downloaded Excel file.