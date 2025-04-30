// app.component.ts
import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { DatetimePickerComponent } from './datetime-picker/datetime-picker.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    DatetimePickerComponent
  ],
  template: `
    <div class="container">
      <h2>License Information</h2>
      
      <form [formGroup]="licenseForm">
        <div class="form-row">
          <div class="form-group">
            <label for="licenseNumber">License Number</label>
            <input id="licenseNumber" type="text" formControlName="licenseNumber">
          </div>
          
          <div class="form-group">
            <app-datetime-picker
              formControlName="expirationDate"
              label="License Expiration Date"
              placeholder="MM/DD/YYYY HH:MM"
              [isRequired]="true"
              (dateTimeChange)="onDateTimeChange($event)"
            ></app-datetime-picker>
          </div>
        </div>
        
        <div class="form-row">
          <div class="form-group">
            <label for="licenseType">License Type</label>
            <select id="licenseType" formControlName="licenseType">
              <option value="standard">Standard</option>
              <option value="professional">Professional</option>
              <option value="enterprise">Enterprise</option>
            </select>
          </div>
          
          <div class="form-group">
            <label for="status">Status</label>
            <select id="status" formControlName="status">
              <option value="active">Active</option>
              <option value="pending">Pending</option>
              <option value="expired">Expired</option>
            </select>
          </div>
        </div>
        
        <button type="submit" [disabled]="licenseForm.invalid">Save</button>
      </form>
      
      <div class="form-values" *ngIf="licenseForm.valid">
        <h3>Form Values:</h3>
        <pre>{{ licenseForm.value | json }}</pre>
      </div>
    </div>
  `,
  styles: [`
    .container {
      max-width: 800px;
      margin: 0 auto;
      padding: 20px;
    }
    
    h2 {
      margin-bottom: 20px;
    }
    
    .form-row {
      display: flex;
      gap: 20px;
      margin-bottom: 20px;
    }
    
    .form-group {
      flex: 1;
    }
    
    label {
      display: block;
      margin-bottom: 6px;
      font-weight: 500;
    }
    
    input, select {
      width: 100%;
      padding: 10px 12px;
      border: 1px solid #ddd;
      border-radius: 4px;
      font-size: 14px;
    }
    
    button {
      background-color: #2196f3;
      color: white;
      border: none;
      padding: 10px 16px;
      border-radius: 4px;
      cursor: pointer;
      font-size: 16px;
    }
    
    button:disabled {
      background-color: #bdbdbd;
      cursor: not-allowed;
    }
    
    .form-values {
      margin-top: 30px;
      padding: 20px;
      background-color: #f5f5f5;
      border-radius: 4px;
    }
    
    pre {
      white-space: pre-wrap;
    }
  `]
})
export class AppComponent {
  licenseForm: FormGroup;
  
  constructor(private fb: FormBuilder) {
    this.licenseForm = this.fb.group({
      licenseNumber: ['', Validators.required],
      expirationDate: [null, Validators.required],
      licenseType: ['standard', Validators.required],
      status: ['active', Validators.required]
    });
  }
  
  onDateTimeChange(date: Date) {
    console.log('Date changed:', date);
  }
}