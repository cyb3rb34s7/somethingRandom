// metadata-history.module.ts
import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MetadataHistoryComponent } from './metadata-history.component';

@NgModule({
  declarations: [MetadataHistoryComponent],
  imports: [
    CommonModule,
    MatTooltipModule
  ],
  exports: [MetadataHistoryComponent]
})
export class MetadataHistoryModule { }

// column-mapping.ts
export const columnMappings: { [key: string]: string } = {
  id: 'ID',
  type: 'Type',
  provider: 'Service Provider',
  name: 'Full Name',
  role: 'Character Role',
  characterName: 'Character',
};

// metadata-history.service.ts
import { Injectable } from '@angular/core';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { columnMappings } from './column-mapping';

@Injectable({
  providedIn: 'root'
})
export class MetadataHistoryService {
  constructor(private sanitizer: DomSanitizer) {}

  private getColumnName(key: string): string {
    return columnMappings[key] || key;
  }

  formatValueForUI(value: string | number | DynamicObject[]): SafeHtml | string {
    const parsedValue = typeof value === 'string' ? this.parseValue(value) : value;

    if (Array.isArray(parsedValue) && parsedValue.length > 0) {
      const allKeys = Array.from(
        new Set(parsedValue.flatMap(obj => Object.keys(obj)))
      );

      const htmlContent = `
        <div class="modern-table-container">
          <table class="modern-table">
            <thead>
              <tr>
                ${allKeys.map(key => `
                  <th>${this.getColumnName(key)}</th>
                `).join('')}
              </tr>
            </thead>
            <tbody>
              ${parsedValue.map(obj => `
                <tr>
                  ${allKeys.map(key => `
                    <td>
                      <div class="cell-content" [matTooltip]="${obj[key] || 'N/A'}">
                        ${obj[key] || 'N/A'}
                      </div>
                    </td>
                  `).join('')}
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      `;
      
      return this.sanitizer.bypassSecurityTrustHtml(htmlContent);
    }
    
    return parsedValue !== null && parsedValue !== undefined ? String(parsedValue) : 'N/A';
  }

  // ... rest of the service code remains the same ...
}

// metadata-history.component.ts
import { Component, Input, OnInit } from '@angular/core';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MetadataHistoryService } from './metadata-history.service';

@Component({
  selector: 'app-metadata-history',
  templateUrl: './metadata-history.component.html',
  styleUrls: ['./metadata-history.component.css']
})
export class MetadataHistoryComponent implements OnInit {
  @Input() changesStr = '';
  processedChanges: MetadataHistoryChange[] = [];

  constructor(private metadataHistoryService: MetadataHistoryService) {}

  ngOnInit() {
    this.processedChanges = this.metadataHistoryService.prepareExpandedRows(this.changesStr);
  }

  // Helper method to safely display cell content with tooltip
  formatCellContent(value: any): string {
    return value || 'N/A';
  }
}