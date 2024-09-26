import { Component, forwardRef, OnInit } from '@angular/core';
import { ControlValueAccessor, NG_VALUE_ACCESSOR, FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { MatInputModule } from '@angular/material/input';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatNativeDateModule } from '@angular/material/core';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';

@Component({
  selector: 'app-modern-date-time-picker',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatInputModule,
    MatDatepickerModule,
    MatNativeDateModule,
    MatFormFieldModule,
    MatSelectModule,
  ],
  template: `
    <div class="modern-date-time-picker">
      <mat-form-field appearance="outline">
        <mat-label>Date</mat-label>
        <input matInput [matDatepicker]="picker" [(ngModel)]="selectedDate" (ngModelChange)="updateDateTime()">
        <mat-datepicker-toggle matSuffix [for]="picker"></mat-datepicker-toggle>
        <mat-datepicker #picker></mat-datepicker>
      </mat-form-field>

      <mat-form-field appearance="outline">
        <mat-label>Time</mat-label>
        <input matInput type="time" [(ngModel)]="selectedTime" (ngModelChange)="updateDateTime()" step="1">
      </mat-form-field>
    </div>
  `,
  styles: [`
    .modern-date-time-picker {
      display: flex;
      gap: 16px;
      align-items: center;
    }
    mat-form-field {
      flex: 1;
    }
  `],
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => ModernDateTimePickerComponent),
      multi: true
    }
  ]
})
export class ModernDateTimePickerComponent implements ControlValueAccessor, OnInit {
  selectedDate: Date = new Date();
  selectedTime: string = '00:00:00';

  private onChange: (value: string) => void = () => {};
  private onTouched: () => void = () => {};

  ngOnInit() {
    this.updateDateTime();
  }

  writeValue(value: string): void {
    if (value) {
      const date = new Date(value);
      this.selectedDate = date;
      this.selectedTime = this.formatTime(date);
    }
  }

  registerOnChange(fn: (value: string) => void): void {
    this.onChange = fn;
  }

  registerOnTouched(fn: () => void): void {
    this.onTouched = fn;
  }

  updateDateTime(): void {
    if (this.selectedDate && this.selectedTime) {
      const [hours, minutes, seconds] = this.selectedTime.split(':').map(Number);
      const dateTime = new Date(this.selectedDate);
      dateTime.setHours(hours, minutes, seconds);

      const formattedDateTime = this.formatDateTime(dateTime);
      this.onChange(formattedDateTime);
      this.onTouched();
    }
  }

  private formatDateTime(date: Date): string {
    return `${date.getFullYear()}-${(date.getMonth() + 1).toString().padStart(2, '0')}-${date.getDate().toString().padStart(2, '0')} ${this.formatTime(date)}`;
  }

  private formatTime(date: Date): string {
    return `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}:${date.getSeconds().toString().padStart(2, '0')}`;
  }
}