// column-mapping.ts
export const columnMappings: { [key: string]: string } = {
  id: 'ID',
  type: 'Type',
  provider: 'Service Provider',
  name: 'Full Name',
  role: 'Character Role',
  characterName: 'Character',
  // Add more mappings as needed
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

  private getColumnWidth(key: string): string {
    // Define specific widths for different columns
    const columnWidths: { [key: string]: string } = {
      id: '15%',
      type: '20%',
      provider: '25%',
      name: '25%',
      role: '20%',
      characterName: '25%',
      // Add more width mappings as needed
    };
    return columnWidths[key] || '20%'; // Default width
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
                  <th style="width: ${this.getColumnWidth(key)}">
                    ${this.getColumnName(key)}
                  </th>
                `).join('')}
              </tr>
            </thead>
            <tbody>
              ${parsedValue.map(obj => `
                <tr>
                  ${allKeys.map(key => `
                    <td class="cell-with-tooltip" data-tooltip="${obj[key] || 'N/A'}">
                      ${obj[key] || 'N/A'}
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
import { CommonModule } from '@angular/common';
import { MetadataHistoryService } from './metadata-history.service';

@Component({
  selector: 'app-metadata-history',
  standalone: true,
  imports: [CommonModule],
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

  // ... rest of the component code remains the same ...
}