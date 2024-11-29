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
   * @param value Stringified value
   * @returns Parsed value or original value
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
   * Format value for UI display with inline styles
   * @param value The value to be formatted
   * @returns Formatted value as SafeHtml or string
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

      // Generate HTML for the dynamic table with inline styles
      const htmlContent = `
        <div style="
          border: 1px solid #e0e0e0;
          border-radius: 8px;
          overflow: hidden;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
          max-width: 100%;
        ">
          <table style="
            width: 100%;
            border-collapse: collapse;
            font-family: Arial, sans-serif;
          ">
            <thead>
              <tr style="
                background-color: #f0f0f0;
                border-bottom: 1px solid #d0d0d0;
              ">
                ${allKeys.map(key => `
                  <th style="
                    padding: 10px;
                    text-align: left;
                    font-weight: bold;
                    color: #333;
                    text-transform: capitalize;
                  ">${this.capitalizeFirstLetter(key)}</th>
                `).join('')}
              </tr>
            </thead>
            <tbody>
              ${parsedValue.map(obj => `
                <tr style="
                  border-bottom: 1px solid #e0e0e0;
                  transition: background-color 0.2s;
                ">
                  ${allKeys.map(key => `
                    <td style="
                      padding: 10px;
                      color: #555;
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
   * @param str Input string
   * @returns Capitalized string
   */
  private capitalizeFirstLetter(str: string): string {
    return str.charAt(0).toUpperCase() + str.slice(1);
  }

  /**
   * Prepare expanded rows from changes array
   * @param changesStr Stringified changes array
   * @returns Processed changes with parsed values
   */
  prepareExpandedRows(changesStr: string): MetadataHistoryChange[] {
    try {
      // Parse the stringified changes array
      const changes: MetadataHistoryChange[] = JSON.parse(changesStr);
      
      // Process each change to parse its values
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
      max-width: 800px;
      margin: 0 auto;
      padding: 20px;
      background-color: #f9f9f9;
      border-radius: 10px;
    ">
      <div *ngFor="let change of processedChanges" style="margin-bottom: 20px;">
        <div style="
          font-weight: bold;
          font-size: 16px;
          color: #333;
          margin-bottom: 10px;
          border-bottom: 2px solid #e0e0e0;
          padding-bottom: 5px;
        ">
          {{ change.field }}
        </div>
        <div style="display: flex; gap: 20px;">
          <div style="flex: 1;">
            <div style="
              color: #666;
              font-size: 14px;
              margin-bottom: 5px;
            ">
              Old Value:
            </div>
            <ng-container *ngIf="isComplexValue(change.oldVal); else stringValue">
              <div [innerHTML]="formatValue(change.oldVal)"></div>
            </ng-container>
            <ng-template #stringValue>
              <div style="
                background-color: #f0f0f0;
                padding: 10px;
                border-radius: 5px;
                color: #333;
              ">
                {{ formatValue(change.oldVal) }}
              </div>
            </ng-template>
          </div>
          <div style="flex: 1;">
            <div style="
              color: #666;
              font-size: 14px;
              margin-bottom: 5px;
            ">
              New Value:
            </div>
            <ng-container *ngIf="isComplexValue(change.newVal); else stringNewValue">
              <div [innerHTML]="formatValue(change.newVal)"></div>
            </ng-container>
            <ng-template #stringNewValue>
              <div style="
                background-color: #f0f0f0;
                padding: 10px;
                border-radius: 5px;
                color: #333;
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