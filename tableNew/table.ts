// custom-mat-table.component.ts
import { Component, Input, Output, EventEmitter, ViewChild, OnInit, OnChanges, SimpleChanges, AfterViewInit } from '@angular/core';
import { MatPaginator, PageEvent } from '@angular/material/paginator';
import { MatTableDataSource } from '@angular/material/table';
import { MatSort } from '@angular/material/sort';
import { animate, state, style, transition, trigger } from '@angular/animations';

@Component({
  selector: 'app-custom-mat-table',
  templateUrl: './custom-mat-table.component.html',
  styleUrls: ['./custom-mat-table.component.scss'],
  animations: [
    trigger('detailExpand', [
      state('collapsed', style({ height: '0px', minHeight: '0' })),
      state('expanded', style({ height: '*' })),
      transition('expanded <=> collapsed', animate('225ms cubic-bezier(0.4, 0.0, 0.2, 1)')),
    ]),
  ],
})
export class CustomMatTableComponent implements OnInit, OnChanges, AfterViewInit {
  @Input() tableData: any[] = [];
  @Input() isPaginated: boolean = false;
  @Input() supportRowExpansion: boolean = false;
  @Input() pageSizeOptions: number[] = [25, 50, 100, 250, 500];
  @Input() defaultPageSize: number = 25;
  @Input() totalRecords: number = 0;
  @Input() batchSize: number = 1000; // Size of each backend data batch
  
  @Output() loadMoreData = new EventEmitter<{limit: number, offset: number}>();
  
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;
  
  dataSource = new MatTableDataSource<any>([]);
  displayedColumns: string[] = [];
  expandedElement: any | null = null;
  
  // For pagination
  currentPageIndex = 0;
  currentPageSize = 25;
  
  constructor() {}
  
  ngOnInit() {
    this.currentPageSize = this.defaultPageSize;
    this.updateDataSource();
    this.setupDisplayColumns();
  }
  
  ngAfterViewInit() {
    this.dataSource.paginator = this.paginator;
    this.dataSource.sort = this.sort;
  }
  
  ngOnChanges(changes: SimpleChanges) {
    if (changes['tableData']) {
      this.updateDataSource();
      this.setupDisplayColumns();
    }
  }
  
  updateDataSource() {
    this.dataSource.data = this.tableData || [];
  }
  
  setupDisplayColumns() {
    if (this.tableData && this.tableData.length > 0) {
      this.displayedColumns = Object.keys(this.tableData[0]);
    }
  }
  
  onPageChange(event: PageEvent) {
    this.currentPageIndex = event.pageIndex;
    this.currentPageSize = event.pageSize;
    
    // Calculate the end index of the current page
    const startIndex = event.pageIndex * event.pageSize;
    const endIndex = startIndex + event.pageSize - 1;
    
    // Check if we need to load more data
    if (endIndex >= this.tableData.length && this.tableData.length < this.totalRecords) {
      // Calculate the next batch offset
      const nextOffset = Math.floor(this.tableData.length / this.batchSize) * this.batchSize;
      
      // Only request if we haven't loaded all data yet
      if (nextOffset < this.totalRecords) {
        this.loadMoreData.emit({
          limit: this.batchSize,
          offset: nextOffset
        });
      }
    }
  }
  
  toggleRowExpansion(element: any) {
    this.expandedElement = this.expandedElement === element ? null : element;
  }
  
  isExpandable(columnName: string): boolean {
    // Check if this is the expansion column
    const EMBEDDED_KEY = 'RENDER_EMBEDDED'; // Using your constant
    return columnName === EMBEDDED_KEY && this.supportRowExpansion;
  }
  
  getColumnDisplayName(columnName: string): string {
    // Format column name for display (remove underscores, capitalize, etc.)
    return columnName.replace(/_/g, ' ');
  }
  
  getNestedTableData(element: any): any[] {
    // Extract nested table data from the expanded element
    const EMBEDDED_KEY = 'RENDER_EMBEDDED'; // Using your constant
    return element[EMBEDDED_KEY] || [];
  }
  
  getNestedTableColumns(nestedData: any[]): string[] {
    // Extract column names from nested data
    if (nestedData && nestedData.length > 0) {
      return Object.keys(nestedData[0]).filter(key => key !== 'RENDER_EMBEDDED');
    }
    return [];
  }
}