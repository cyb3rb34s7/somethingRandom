// metadata-history.service.ts
import { Injectable } from '@angular/core';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';

interface DynamicObject {
  [key: string]: any;
}

interface ChangeDiffResult {
  oldTableData: DynamicObject[];
  newTableData: DynamicObject[];
  changeTypes: { [key: string]: 'modified' | 'added' | 'deleted' };
}

@Injectable({
  providedIn: 'root'
})
export class MetadataHistoryService {
  constructor(private sanitizer: DomSanitizer) {}

  private parseValue(value: string): any {
    try {
      return JSON.parse(value);
    } catch {
      return value;
    }
  }

  private compareArrays(oldArr: DynamicObject[], newArr: DynamicObject[]): ChangeDiffResult {
    const oldTableData: DynamicObject[] = [];
    const newTableData: DynamicObject[] = [];
    const changeTypes: { [key: string]: 'modified' | 'added' | 'deleted' } = {};

    // Create a map of objects by a unique identifier (assuming 'id' exists)
    const oldMap = new Map(oldArr.map(item => [this.getItemIdentifier(item), item]));
    const newMap = new Map(newArr.map(item => [this.getItemIdentifier(item), item]));

    // Handle modifications and deletions
    oldArr.forEach(oldItem => {
      const id = this.getItemIdentifier(oldItem);
      const newItem = newMap.get(id);

      if (newItem) {
        // Item exists in both arrays - check for modifications
        if (!this.areObjectsEqual(oldItem, newItem)) {
          changeTypes[id] = 'modified';
        }
        oldTableData.push(oldItem);
        newTableData.push(newItem);
      } else {
        // Item was deleted
        changeTypes[id] = 'deleted';
        oldTableData.push(oldItem);
        newTableData.push({}); // Empty object for alignment
      }
    });

    // Handle additions
    newArr.forEach(newItem => {
      const id = this.getItemIdentifier(newItem);
      if (!oldMap.has(id)) {
        changeTypes[id] = 'added';
        oldTableData.push({}); // Empty object for alignment
        newTableData.push(newItem);
      }
    });

    return { oldTableData, newTableData, changeTypes };
  }

  private getItemIdentifier(item: DynamicObject): string {
    // Create a unique identifier based on the object's content
    // You might want to adjust this based on your specific data structure
    return item.id || JSON.stringify(item);
  }

  private areObjectsEqual(obj1: DynamicObject, obj2: DynamicObject): boolean {
    return JSON.stringify(obj1) === JSON.stringify(obj2);
  }

  formatValueForUI(oldValue: string | number | DynamicObject[], 
                  newValue: string | number | DynamicObject[]): { oldHtml: SafeHtml, newHtml: SafeHtml } {
    const parsedOldValue = typeof oldValue === 'string' ? this.parseValue(oldValue) : oldValue;
    const parsedNewValue = typeof newValue === 'string' ? this.parseValue(newValue) : newValue;

    if (Array.isArray(parsedOldValue) && Array.isArray(parsedNewValue)) {
      const { oldTableData, newTableData, changeTypes } = this.compareArrays(parsedOldValue, parsedNewValue);

      // Get all possible keys from both arrays
      const allKeys = Array.from(new Set([
        ...oldTableData.flatMap(obj => Object.keys(obj)),
        ...newTableData.flatMap(obj => Object.keys(obj))
      ]));

      // Generate tables with color-coded rows
      const oldHtml = this.generateTableHtml(oldTableData, allKeys, changeTypes, 'old');
      const newHtml = this.generateTableHtml(newTableData, allKeys, changeTypes, 'new');

      return {
        oldHtml: this.sanitizer.bypassSecurityTrustHtml(oldHtml),
        newHtml: this.sanitizer.bypassSecurityTrustHtml(newHtml)
      };
    }

    // Handle simple values
    if (parsedOldValue !== parsedNewValue) {
      return {
        oldHtml: this.sanitizer.bypassSecurityTrustHtml(
          `<div class="changed-value">${parsedOldValue ?? 'N/A'}</div>`
        ),
        newHtml: this.sanitizer.bypassSecurityTrustHtml(
          `<div class="changed-value">${parsedNewValue ?? 'N/A'}</div>`
        )
      };
    }

    const simpleValue = String(parsedOldValue ?? 'N/A');
    return {
      oldHtml: this.sanitizer.bypassSecurityTrustHtml(simpleValue),
      newHtml: this.sanitizer.bypassSecurityTrustHtml(simpleValue)
    };
  }

  private generateTableHtml(
    data: DynamicObject[], 
    columns: string[], 
    changeTypes: { [key: string]: string },
    tableType: 'old' | 'new'
  ): string {
    return `
      <div class="modern-table-container">
        <table class="modern-table">
          <thead>
            <tr>
              ${columns.map(key => `<th>${this.getColumnName(key)}</th>`).join('')}
            </tr>
          </thead>
          <tbody>
            ${data.map((row, index) => {
              const changeType = changeTypes[this.getItemIdentifier(row)];
              const rowClass = this.getRowClass(changeType, tableType);
              
              return `
                <tr class="${rowClass}">
                  ${columns.map(key => `
                    <td>
                      <div class="cell-content" title="${row[key] || 'N/A'}">
                        ${row[key] || 'N/A'}
                      </div>
                    </td>
                  `).join('')}
                </tr>
              `;
            }).join('')}
          </tbody>
        </table>
      </div>
    `;
  }

  private getRowClass(changeType: string | undefined, tableType: 'old' | 'new'): string {
    if (!changeType) return '';
    
    switch (changeType) {
      case 'modified':
        return 'modified-row';
      case 'deleted':
        return tableType === 'old' ? 'deleted-row' : '';
      case 'added':
        return tableType === 'new' ? 'added-row' : '';
      default:
        return '';
    }
  }

  private getColumnName(key: string): string {
    // Convert camelCase to Title Case
    return key
      .replace(/([A-Z])/g, ' $1')
      .replace(/^./, str => str.toUpperCase());
  }
}