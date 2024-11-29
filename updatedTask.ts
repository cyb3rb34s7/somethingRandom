// metadata-history.service.ts
import { Injectable } from '@angular/core';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';

export type DynamicObject = { [key: string]: string | number };

export interface MetadataHistoryChange {
  field: string;
  oldVal: string | number | DynamicObject[];
  newVal: string | number | DynamicObject[];
}

@Injectable({
  providedIn: 'root'
})
export class MetadataHistoryService {
  constructor(private sanitizer: DomSanitizer) {}

  /**
   * Safely parse a value, handling different types
   */
  private parseValue(value: string): string | number | DynamicObject[] {
    if (typeof value === 'string') {
      try {
        const parsedValue = JSON.parse(value);
        
        if (Array.isArray(parsedValue) && 
            parsedValue.every(item => typeof item === 'object' && item !== null)) {
          return parsedValue as DynamicObject[];
        }
        
        if (typeof parsedValue === 'object' && parsedValue !== null) {
          return [parsedValue as DynamicObject];
        }
        
        if (typeof parsedValue === 'number' || typeof parsedValue === 'string') {
          return parsedValue;
        }
      } catch {
        return value;
      }
    }
    
    return value;
  }

  /**
   * Format value for UI display with modern table styling
   */
  formatValueForUI(value: string | number | DynamicObject[]): SafeHtml | string {
    const parsedValue = typeof value === 'string' 
      ? this.parseValue(value) 
      : value;

    // If parsed value is an array of objects
    if (Array.isArray(parsedValue) && parsedValue.length > 0) {
      // Get all unique keys from the objects
      const allKeys = Array.from(
        new Set(parsedValue.flatMap(obj => Object.keys(obj)))
      );

      // Generate HTML for the modern table
      const htmlContent = `
        <div style="
          border-radius: 8px;
          overflow: hidden;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1);
          border: 1px solid #e0e0e0;
        ">
          <table style="
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            font-family: 'Inter', 'Segoe UI', Roboto, sans-serif;
          ">
            <thead>
              <tr style="
                background-color: #f8f9fa;
                border-bottom: 2px solid #dee2e6;
              ">
                ${allKeys.map(key => `
                  <th style="
                    padding: 12px 15px;
                    text-align: left;
                    font-weight: 600;
                    color: #495057;
                    text-transform: uppercase;
                    font-size: 12px;
                    letter-spacing: 0.5px;
                    border-right: 1px solid #e9ecef;
                    &:last-child {
                      border-right: none;
                    }
                  ">${this.capitalizeFirstLetter(key)}</th>
                `).join('')}
              </tr>
            </thead>
            <tbody>
              ${parsedValue.map((obj, index) => `
                <tr style="
                  background-color: ${index % 2 === 0 ? '#ffffff' : '#f8f9fa'};
                  transition: background-color 0.2s;
                  border-bottom: 1px solid #e9ecef;
                  &:hover {
                    background-color: #f1f3f5;
                  }
                ">
                  ${allKeys.map((key, colIndex) => `
                    <td style="
                      padding: 12px 15px;
                      color: #343a40;
                      font-size: 14px;
                      border-right: 1px solid #e9ecef;
                      ${colIndex === allKeys.length - 1 ? 'border-right: none;' : ''}
                    ">${obj[key] || 'N/A'}</td>
                  `).join('')}
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      `;
      
      return this.sanitizer.bypassSecurityTrustHtml(htmlContent);
    }
    
    // For simple string or number values
    return parsedValue !== null && parsedValue !== undefined 
      ? String(parsedValue) 
      : 'N/A';
  }

  /**
   * Capitalize the first letter of a string
   */
  private capitalizeFirstLetter(str: string): string {
    return str.charAt(0).toUpperCase() + str.slice(1);
  }

  /**
   * Prepare expanded rows from changes array
   */
  prepareExpandedRows(changesStr: string): MetadataHistoryChange[] {
    try {
      const changes: MetadataHistoryChange[] = JSON.parse(changesStr);
      
      return changes.map(change => ({
        field: change.field,
        oldVal: this.parseValue(change.oldVal as string),
        newVal: this.parseValue(change.newVal as string)
      }));
    } catch (error) {
      console.error('Error parsing changes:', error);
      return [];
    }
  }
}

// metadata-history.component.ts
import { Component, Input, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { MetadataHistoryService, MetadataHistoryChange } from './metadata-history.service';

@Component({
  selector: 'app-metadata-history',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div style="
      max-width: 900px;
      margin: 0 auto;
      padding: 20px;
      background-color: #ffffff;
    ">
      <div *ngFor="let change of processedChanges" style="
        margin-bottom: 25px;
        background-color: #f8f9fa;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        overflow: hidden;
      ">
        <div style="
          font-weight: 600;
          font-size: 16px;
          color: #343a40;
          padding: 15px;
          background-color: #e9ecef;
          border-bottom: 1px solid #dee2e6;
        ">
          {{ change.field }}
        </div>
        <div style="
          display: flex;
          gap: 20px;
          padding: 15px;
        ">
          <div style="flex: 1;">
            <div style="
              color: #6c757d;
              font-size: 14px;
              margin-bottom: 10px;
              font-weight: 500;
            ">
              Old Value
            </div>
            <ng-container *ngIf="isComplexValue(change.oldVal); else stringValue">
              <div [innerHTML]="formatValue(change.oldVal)"></div>
            </ng-container>
            <ng-template #stringValue>
              <div style="
                background-color: #f1f3f5;
                padding: 10px 15px;
                border-radius: 6px;
                color: #343a40;
                font-size: 14px;
              ">
                {{ formatValue(change.oldVal) }}
              </div>
            </ng-template>
          </div>
          <div style="flex: 1;">
            <div style="
              color: #6c757d;
              font-size: 14px;
              margin-bottom: 10px;
              font-weight: 500;
            ">
              New Value
            </div>
            <ng-container *ngIf="isComplexValue(change.newVal); else stringNewValue">
              <div [innerHTML]="formatValue(change.newVal)"></div>
            </ng-container>
            <ng-template #stringNewValue>
              <div style="
                background-color: #f1f3f5;
                padding: 10px 15px;
                border-radius: 6px;
                color: #343a40;
                font-size: 14px;
              ">
                {{ formatValue(change.newVal) }}
              </div>
            </ng-template>
          </div>
        </div>
      </div>
    </div>
  `
})
export class MetadataHistoryComponent implements OnInit {
  @Input() changesStr = '';
  processedChanges: MetadataHistoryChange[] = [];

  constructor(
    private metadataHistoryService: MetadataHistoryService,
    private sanitizer: DomSanitizer
  ) {}

  ngOnInit() {
    this.processedChanges = this.metadataHistoryService.prepareExpandedRows(this.changesStr);
  }

  formatValue(value: string | number | DynamicObject[]): SafeHtml | string {
    return this.metadataHistoryService.formatValueForUI(value);
  }

  isComplexValue(value: string | number | DynamicObject[]): boolean {
    return Array.isArray(value) && value.length > 0;
  }
}

// Example usage component
@Component({
  selector: 'app-example',
  standalone: true,
  imports: [MetadataHistoryComponent],
  template: `
    <app-metadata-history 
      [changesStr]="exampleChangesStr">
    </app-metadata-history>
  `
})
export class ExampleComponent {
  exampleChangesStr = JSON.stringify([
    {
      field: 'External Provider',
      oldVal: [
        { id: '123', type: 'Service', provider: 'Old Provider' }
      ],
      newVal: [
        { id: '456', type: 'Platform', provider: 'New Provider' }
      ]
    },
    {
      field: 'Cast',
      oldVal: [
        { name: 'John Doe', role: 'Lead', characterName: 'Hero' },
        { name: 'Jane Smith', role: 'Support', characterName: 'Sidekick' }
      ],
      newVal: [
        { name: 'Mike Johnson', role: 'Guest', characterName: 'Antagonist' }
      ]
    },
    {
      field: 'Age',
      oldVal: 25,
      newVal: 26
    }
  ]);
}