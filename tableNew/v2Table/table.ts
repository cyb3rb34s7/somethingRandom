// custom-mat-table.component.ts
import { Component, Input, Output, EventEmitter, ViewChild, OnInit, OnChanges, SimpleChanges, AfterViewInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatPaginator, MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';
import { MatSortModule, MatSort } from '@angular/material/sort';
import { MatIconModule } from '@angular/material/icon';
import { animate, state, style, transition, trigger } from '@angular/animations';

@Component({
  selector: 'app-custom-mat-table',
  standalone: true,
  imports: [
    CommonModule,
    MatTableModule,
    MatPaginatorModule,
    MatSortModule,
    MatIconModule
  ],
  templateUrl: './custom-mat-table.component.html',
  styleUrls: ['./custom-mat-table.component.scss'],
  animations: [
    trigger('detailExpand', [
      state('collapsed', style({ height: '0px', minHeight: '0', overflow: 'hidden' })),
      state('expanded', style({ height: '*' })),
      transition('expanded <=> collapsed', animate('225ms cubic-bezier(0.4, 0.0, 0.2, 1)')),
    ]),
  ]
})
export class CustomMatTableComponent implements OnInit, OnChanges, AfterViewInit {
  @Input() tableData: any[] = [];
  @Input() isPaginated: boolean = false;
  @Input() supportRowExpansion: boolean = false;
  @Input() pageSizeOptions: number[] = [25, 50, 100, 250, 500];
  @Input() defaultPageSize: number = 25;
  @Input() batchSize: number = 1000; // Size of each backend data batch
  @Input() totalRecords: number = 0; // Total records from API
  
  @Output() loadMoreData = new EventEmitter<{limit: number, offset: number}>();
  
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;
  
  dataSource = new MatTableDataSource<any>([]);
  displayedColumns: string[] = [];
  expandedElement: any = null;
  
  currentPageIndex = 0;
  currentPageSize = 25;
  
  ngOnInit() {
    this.currentPageSize = this.defaultPageSize;
    this.updateDataSource();
    this.setupDisplayColumns();
  }
  
  ngAfterViewInit() {
    this.dataSource.sort = this.sort;
    if (this.isPaginated) {
      this.dataSource.paginator = this.paginator;
    }
  }
  
  ngOnChanges(changes: SimpleChanges) {
    if (changes['tableData']) {
      this.updateDataSource();
      this.setupDisplayColumns();
    }
  }
  
  updateDataSource() {
    if (this.tableData && this.tableData.length > 0) {
      this.dataSource.data = this.tableData;
    }
  }
  
  setupDisplayColumns() {
    if (this.tableData && this.tableData.length > 0) {
      // Extract column names from the first data item
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
  
  toggleRow(row: any) {
    this.expandedElement = this.expandedElement === row ? null : row;
  }
  
  trackByFn(index: number, item: any) {
    return index;
  }
  
  getObjectKeys(obj: any): string[] {
    return Object.keys(obj);
  }
  
  isExpandableRow(row: any): boolean {
    const expandKey = 'RENDER_EMBEDDED';
    return this.supportRowExpansion && row[expandKey] && Array.isArray(row[expandKey]);
  }
  
  hasNestedData(row: any): boolean {
    const expandKey = 'RENDER_EMBEDDED';
    return this.supportRowExpansion && row[expandKey] && Array.isArray(row[expandKey]) && row[expandKey].length > 0;
  }
}