// media-assets.component.ts
import { Component, OnInit } from '@angular/core';
import { MediaAssetsService } from '../services/media-assets.service';

// Constants
export const TABLE_CONSTANTS = {
  RENDER_EMBEDDED: 'RENDER_EMBEDDED' // Constant for expanded row data
};

// Models
export interface MediaAssetModel {
  programId: string;
  title: string;
  status: string;
  type: string;
  createdDate: string;
  changes?: ChangeModel[];
}

export interface ChangeModel {
  changeId: string;
  changeDate: string;
  changeType: string;
  changedBy: string;
  details: string;
}

@Component({
  selector: 'app-media-assets',
  templateUrl: './media-assets.component.html',
  styleUrls: ['./media-assets.component.scss']
})
export class MediaAssetsComponent implements OnInit {
  
  // Table data
  tableData: any[] = [];
  totalRecords: number = 0;
  mediaAssets: MediaAssetModel[] = [];
  
  constructor(private mediaAssetsService: MediaAssetsService) {}
  
  ngOnInit() {
    // Initial data load with pagination
    this.loadMediaAssets({ limit: 1000, offset: 0 });
  }
  
  loadMediaAssets(pagination: { limit: number, offset: number }) {
    this.mediaAssetsService.getMediaAssets(pagination).subscribe(response => {
      if (pagination.offset === 0) {
        // First load - replace data
        this.mediaAssets = response.data;
      } else {
        // Subsequent loads - append data
        this.mediaAssets = [...this.mediaAssets, ...response.data];
      }
      
      // Update total count from response
      this.totalRecords = response.totalCount;
      
      // Prepare table data
      this.prepareTableData(this.mediaAssets);
    });
  }
  
  // Prepare data for the table
  prepareTableData(mediaAssets: MediaAssetModel[]) {
    this.tableData = mediaAssets.map((asset: MediaAssetModel) => {
      const obj: any = {};
      
      // Add expandable row data if changes exist
      obj[TABLE_CONSTANTS.RENDER_EMBEDDED] = this.prepareExpandedRows(asset.changes);
      
      // Add regular columns
      obj['Program ID'] = asset.programId;
      obj['Title'] = asset.title;
      obj['Status'] = asset.status;
      obj['Type'] = asset.type;
      obj['Created Date'] = asset.createdDate;
      
      return obj;
    });
  }
  
  // Prepare nested table data for expanded rows
  prepareExpandedRows(changes: ChangeModel[] | undefined): any[] {
    if (!changes || changes.length === 0) {
      return [];
    }
    
    return changes.map((change: ChangeModel) => {
      return {
        'Change ID': change.changeId,
        'Change Date': change.changeDate,
        'Change Type': change.changeType,
        'Changed By': change.changedBy,
        'Details': change.details
      };
    });
  }
  
  // Called when shared table needs more data
  onLoadMoreData(paginationParams: { limit: number, offset: number }) {
    this.loadMediaAssets(paginationParams);
  }
}