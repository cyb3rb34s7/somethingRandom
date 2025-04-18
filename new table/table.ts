import { Component, Input, Output, EventEmitter, OnInit, ViewChild, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatTableModule, MatTableDataSource } from '@angular/material/table';
import { MatSortModule, MatSort } from '@angular/material/sort';
import { MatPaginatorModule, MatPaginator, PageEvent } from '@angular/material/paginator';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatButtonModule } from '@angular/material/button';
import { animate, state, style, transition, trigger } from '@angular/animations';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';

export interface TableColumn {
  header: string;
  field: string;
  isHtml?: boolean;
  sortable?: boolean;
  tooltip?: boolean;
  width?: string;
}

@Component({
  selector: 'app-dynamic-table',
  standalone: true,
  imports: [
    CommonModule,
    MatTableModule,
    MatSortModule,
    MatPaginatorModule,
    MatIconModule,
    MatTooltipModule,
    MatButtonModule
  ],
  templateUrl: './dynamic-table.component.html',
  styleUrls: ['./dynamic-table.component.scss'],
  animations: [
    trigger('detailExpand', [
      state('collapsed', style({ height: '0px', minHeight: '0', visibility: 'hidden' })),
      state('expanded', style({ height: '*', visibility: 'visible' })),
      transition('expanded <=> collapsed', animate('225ms cubic-bezier(0.4, 0.0, 0.2, 1)')),
    ]),
  ]
})
export class DynamicTableComponent implements OnInit, OnChanges {
  @Input() columns: TableColumn[] = [];
  @Input() expandedColumns: TableColumn[] = [];
  @Input() data: any[] = [];
  @Input() supportRowExpansion = false;
  @Input() pageSize = 10;
  @Input() pageSizeOptions: number[] = [5, 10, 25, 50, 100];
  @Input() showPaginator = true;
  @Input() totalRecords = 0;
  @Input() serverSidePagination = false;

  @Output() rowExpandToggle = new EventEmitter<any>();
  @Output() sortChange = new EventEmitter<{active: string, direction: string}>();
  @Output() pageChange = new EventEmitter<PageEvent>();

  @ViewChild(MatSort) sort!: MatSort;
  @ViewChild(MatPaginator) paginator!: MatPaginator;

  dataSource = new MatTableDataSource<any>([]);
  displayedColumns: string[] = [];
  expandedColumnsFields: string[] = [];
  expandedRow: any | null = null;
  expandedRowData: any[] = [];
  
  constructor(private sanitizer: DomSanitizer) {}

  ngOnInit() {
    this.updateDisplayedColumns();
    this.dataSource.data = this.data;
    this.expandedColumnsFields = this.expandedColumns.map(col => col.field);
  }

  ngAfterViewInit() {
    this.dataSource.sort = this.sort;
    if (!this.serverSidePagination && this.paginator) {
      this.dataSource.paginator = this.paginator;
    }
  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes['data'] || changes['columns'] || changes['supportRowExpansion']) {
      this.updateDisplayedColumns();
      if (changes['data']) {
        this.dataSource.data = this.data;
      }
      if (changes['expandedColumns']) {
        this.expandedColumnsFields = this.expandedColumns.map(col => col.field);
      }
    }
  }

  updateDisplayedColumns() {
    this.displayedColumns = [];
    if (this.supportRowExpansion) {
      this.displayedColumns.push('expand');
    }
    this.displayedColumns = [...this.displayedColumns, ...this.columns.map(col => col.field)];
  }

  toggleRowExpand(row: any) {
    if (this.expandedRow === row) {
      this.expandedRow = null;
      this.expandedRowData = [];
    } else {
      this.expandedRow = row;
      this.rowExpandToggle.emit(row);
    }
  }

  setExpandedRowData(data: any[]) {
    this.expandedRowData = data;
  }

  isExpanded = (row: any) => row === this.expandedRow;

  sanitizeHtml(html: string): SafeHtml {
    return this.sanitizer.bypassSecurityTrustHtml(html);
  }

  getFormattedCellValue(row: any, column: TableColumn): string | SafeHtml {
    const value = row[column.field];
    
    if (value === null || value === undefined) {
      return '--';
    }

    if (column.isHtml) {
      return this.sanitizeHtml(String(value));
    }
    
    return String(value);
  }

  onSortChange(event: any) {
    if (this.serverSidePagination) {
      this.sortChange.emit(event);
    }
  }

  onPageChange(event: PageEvent) {
    if (this.serverSidePagination) {
      this.pageChange.emit(event);
    }
  }
}