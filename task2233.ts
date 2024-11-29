// metadata-history.model.ts
export type DynamicObject = { [key: string]: string | number };

export interface MetadataHistoryChange {
  field: string;
  oldVal: string | number | DynamicObject[];
  newVal: string | number | DynamicObject[];
}

// metadata-history.service.ts
import { Injectable } from '@angular/core';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';

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
    // If the value is a string representation of an object or array
    if (typeof value === 'string') {
      try {
        // Attempt to parse as JSON
        const parsedValue = JSON.parse(value);
        
        // Check if parsed value is an array of objects
        if (Array.isArray(parsedValue) && 
            parsedValue.every(item => typeof item === 'object' && item !== null)) {
          return parsedValue as DynamicObject[];
        }
        
        // If it's a single object, wrap in array
        if (typeof parsedValue === 'object' && parsedValue !== null) {
          return [parsedValue as DynamicObject];
        }
        
        // If it's a primitive, return as is
        if (typeof parsedValue === 'number' || typeof parsedValue === 'string') {
          return parsedValue;
        }
      } catch {
        // If JSON parsing fails, return the original string
        return value;
      }
    }
    
    // If it's already not a string, return as is
    return value;
  }

  /**
   * Format value for UI display
   * @param value The value to be formatted
   * @returns Formatted value as SafeHtml or string
   */
  formatValueForUI(value: string | number | DynamicObject[]): SafeHtml | string {
    // Ensure the value is properly parsed if it's a string
    const parsedValue = typeof value === 'string' 
      ? this.parseValue(value) 
      : value;

    // If parsed value is an array of objects
    if (Array.isArray(parsedValue) && parsedValue.length > 0) {
      // Get all unique keys from the objects
      const allKeys = Array.from(
        new Set(parsedValue.flatMap(obj => Object.keys(obj)))
      );

      // Generate HTML for the dynamic table
      const htmlContent = `
        <div class="grid grid-cols-${allKeys.length} border">
          ${allKeys.map(key => `<div class="border p-1 font-bold">${this.capitalizeFirstLetter(key)}</div>`).join('')}
          ${parsedValue.map(obj => 
            allKeys.map(key => `<div class="border p-1">${obj[key] || 'N/A'}</div>`).join('')
          ).join('')}
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
import { MetadataHistoryService } from './metadata-history.service';
import { MetadataHistoryChange } from './metadata-history.model';

@Component({
  selector: 'app-metadata-history',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="metadata-history-container">
      <div *ngFor="let change of processedChanges" class="mb-2">
        <div class="font-bold">{{ change.field }}</div>
        <div class="grid grid-cols-2 gap-2">
          <div>
            <span class="text-sm text-gray-500">Old Value:</span>
            <ng-container *ngIf="isComplexValue(change.oldVal); else stringValue">
              <div [innerHTML]="formatValue(change.oldVal)"></div>
            </ng-container>
            <ng-template #stringValue>
              {{ formatValue(change.oldVal) }}
            </ng-template>
          </div>
          <div>
            <span class="text-sm text-gray-500">New Value:</span>
            <ng-container *ngIf="isComplexValue(change.newVal); else stringNewValue">
              <div [innerHTML]="formatValue(change.newVal)"></div>
            </ng-container>
            <ng-template #stringNewValue>
              {{ formatValue(change.newVal) }}
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

// Example usage
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