import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { MatCardModule } from '@angular/material/card';
import { PageEvent } from '@angular/material/paginator';
import { DynamicTableComponent, TableColumn } from '../shared/components/dynamic-table/dynamic-table.component';
import { MatIconModule } from '@angular/material/icon';

interface AssetResponse {
  assetId: string;
  cpName: string;
  techIntegrator: string;
  programTitle: string;
  type: string;
  lastUpdBy: string;
  lastTxnDt: string;
  currentStatus: string;
}

interface StatusChange {
  txnOccDt: string;
  oldStatus: string;
  newStatus: string;
  updBy: string;
}

interface AssetStatusHistoryResponse {
  assetId: string;
  cpName: string;
  techIntegrator: string;
  programTitle: string;
  type: string;
  lastUpdBy: string;
  lastTxnDt: string;
  statusChanges: StatusChange[];
}

@Component({
  selector: 'app-asset-status',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatIconModule,
    DynamicTableComponent
  ],
  templateUrl: './asset-status.component.html',
  styleUrls: ['./asset-status.component.scss']
})
export class AssetStatusComponent implements OnInit {
  assets: AssetResponse[] = [];
  columns: TableColumn[] = [
    { header: 'CP Name', field: 'cpName', sortable: true, tooltip: true },
    { header: 'Tech Integrator', field: 'techIntegrator', sortable: true, tooltip: true },
    { header: 'Asset ID', field: 'assetId', sortable: true, tooltip: true },
    { header: 'Program Title', field: 'programTitle', sortable: true, tooltip: true },
    { header: 'Type', field: 'type', sortable: true },
    { header: 'Status', field: 'statusDisplay', isHtml: true },
    { header: 'Last Updated By', field: 'lastUpdBy', sortable: true },
    { header: 'Last Change Time', field: 'lastTxnDt', sortable: true }
  ];

  expandedColumns: TableColumn[] = [
    { header: 'Change Date & Time', field: 'txnOccDt', sortable: false },
    { header: 'Old Status', field: 'oldStatusDisplay', isHtml: true },
    { header: 'New Status', field: 'newStatusDisplay', isHtml: true },
    { header: 'Updated By', field: 'updBy', sortable: false }
  ];

  totalAssets = 0;
  currentPage = 0;
  pageSize = 1000;
  tableReference: DynamicTableComponent | undefined;

  constructor(private http: HttpClient) {}

  ngOnInit() {
    this.loadAssets();
  }

  loadAssets(page: number = 0, size: number = 1000) {
    this.http.get<AssetResponse[]>(`/api/assets?page=${page}&size=${size}`).subscribe(
      (data) => {
        this.assets = data.map(asset => ({
          ...asset,
          statusDisplay: this.getStatusHtml(asset.currentStatus)
        }));
        this.totalAssets = 1000; // This would typically come from an API header or pagination metadata
        this.currentPage = page;
      },
      (error) => {
        console.error('Error loading assets', error);
      }
    );
  }

  onPageChange(event: PageEvent) {
    this.loadAssets(event.pageIndex, event.pageSize);
  }

  onRowExpand(row: AssetResponse) {
    if (this.tableReference) {
      this.http.get<AssetStatusHistoryResponse>(`/api/assets/${row.assetId}/history`).subscribe(
        (response) => {
          const formattedStatusChanges = response.statusChanges.map(change => ({
            ...change,
            oldStatusDisplay: this.getStatusHtml(change.oldStatus),
            newStatusDisplay: this.getStatusHtml(change.newStatus)
          }));
          this.tableReference?.setExpandedRowData(formattedStatusChanges);
        },
        (error) => {
          console.error('Error loading asset history', error);
          this.tableReference?.setExpandedRowData([]);
        }
      );
    }
  }

  onSortChange(event: any) {
    // Here you would implement server-side sorting if needed
    console.log('Sort changed', event);
  }

  getStatusHtml(status: string): string {
    let color = '';
    
    switch (status?.toLowerCase()) {
      case 'active':
      case 'passed':
      case 'completed':
        color = '#4CAF50'; // Green
        break;
      case 'pending':
      case 'in progress':
      case 'ready for qc':
        color = '#FFC107'; // Amber
        break;
      case 'failed':
      case 'error':
        color = '#F44336'; // Red
        break;
      default:
        color = '#9E9E9E'; // Grey
    }

    return `<div style="display: flex; align-items: center;">
              <span style="height: 12px; width: 12px; border-radius: 50%; background-color: ${color}; margin-right: 8px;"></span>
              <span>${status || '--'}</span>
            </div>`;
  }
}