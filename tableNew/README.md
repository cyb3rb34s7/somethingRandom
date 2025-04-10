# Implementation Guide: Custom Material Table with Lazy Loading and Row Expansion

This guide explains how to implement and use the custom Material Table component that supports lazy loading pagination and row expansion.

## Features

The custom table component provides:

1. **Lazy Loading Pagination**: Loads data in batches of 1000 records and fetches more when needed
2. **Row Expansion**: Supports expandable rows with nested tables
3. **Column Sorting**: All columns support sorting via MatSort
4. **Dynamic Columns**: Auto-generates columns based on the input data
5. **Customizable Page Sizes**: Configurable page size options (25, 50, 100, etc.)

## Installation

1. Add the custom table component to your Angular project:
   - CustomMatTableComponent (TS, HTML, SCSS)
   - Add the component to your module declarations

2. Make sure you have the required Angular Material dependencies:
   ```bash
   ng add @angular/material
   ```

## Usage

### 1. Basic Setup in Your Component

```typescript
import { Component, OnInit } from '@angular/core';
import { YourService } from '../services/your.service';
import { TABLE_CONSTANTS } from './constants';

@Component({
  selector: 'app-your-component',
  templateUrl: './your-component.html'
})
export class YourComponent implements OnInit {
  tableData: any[] = [];
  totalRecords: number = 0;
  
  constructor(private yourService: YourService) {}
  
  ngOnInit() {
    this.loadData({ limit: 1000, offset: 0 });
  }
  
  loadData(pagination: { limit: number, offset: number }) {
    this.yourService.getData(pagination).subscribe(response => {
      if (pagination.offset === 0) {
        this.yourData = response.data;
      } else {
        this.yourData = [...this.yourData, ...response.data];
      }
      
      this.totalRecords = response.totalCount;
      this.prepareTableData(this.yourData);
    });
  }
  
  prepareTableData(data: YourDataModel[]) {
    this.tableData = data.map(item => {
      const obj: any = {};
      
      // For expandable rows
      obj[TABLE_CONSTANTS.RENDER_EMBEDDED] = this.prepareExpandedRows(item.nestedData);
      
      // Regular columns
      obj['Column 1'] = item.property1;
      obj['Column 2'] = item.property2;
      // ...more columns
      
      return obj;
    });
  }
  
  prepareExpandedRows(nestedData: NestedDataModel[] | undefined): any[] {
    if (!nestedData || nestedData.length === 0) return [];
    
    return nestedData.map(item => {
      return {
        'Nested Column 1': item.nestedProperty1,
        'Nested Column 2': item.nestedProperty2,
        // ...more nested columns
      };
    });
  }
  
  onLoadMoreData(paginationParams: { limit: number, offset: number }) {
    this.loadData(paginationParams);
  }
}
```

### 2. Template Integration

```html
<app-custom-mat-table 
  [tableData]="tableData" 
  [isPaginated]="true"
  [supportRowExpansion]="true"
  [totalRecords]="totalRecords"
  [defaultPageSize]="25"
  [pageSizeOptions]="[25, 50, 100, 250, 500]"
  [batchSize]="1000"
  (loadMoreData)="onLoadMoreData($event)">
</app-custom-mat-table>
```

## Key Concepts

### Data Structure

The `tableData` array should contain objects with:
- Regular columns as key-value pairs
- A special `RENDER_EMBEDDED` property for nested data (if row expansion is supported)

### Lazy Loading Logic

1. The component tracks the current page and page size
2. When a user navigates to a page that might require more data:
   - The component checks if the end index of the current page exceeds loaded data
   - If needed, it emits a `loadMoreData` event with appropriate pagination parameters
   - Your component makes the API call and appends the new data

### Row Expansion

1. Each row can have a special `RENDER_EMBEDDED` property containing nested table data
2. When a user clicks the expansion icon, the nested table is shown
3. The nested table has its own columns defined by the keys in the nested data objects

## Customization Options

The component accepts several inputs to customize behavior:

- `tableData`: Your formatted table data
- `isPaginated`: Enable/disable pagination
- `supportRowExpansion`: Enable/disable expandable rows
- `pageSizeOptions`: Available page size options
- `defaultPageSize`: Initial page size
- `totalRecords`: Total number of records (for pagination)
- `batchSize`: Number of records to fetch in each API call

## Best Practices

1. **Performance**: Keep the batch size (1000) significantly larger than your largest page size (500) to minimize API calls
2. **Data Transformation**: Always transform your API data to the format expected by the table
3. **Column Names**: Use human-readable column names in your `prepareTableData` method
4. **Error Handling**: Add appropriate error handling to your data loading functions
5. **Loading States**: Show loading indicators when fetching additional data

By following this implementation guide, you can easily integrate the custom Material Table with lazy loading and row expansion into your Angular application.