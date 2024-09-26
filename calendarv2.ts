import { Component, forwardRef, OnInit } from '@angular/core';
import { ControlValueAccessor, NG_VALUE_ACCESSOR, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { MatInputModule } from '@angular/material/input';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatNativeDateModule, DateAdapter, MAT_DATE_FORMATS, MAT_DATE_LOCALE } from '@angular/material/core';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';

@Component({
  selector: 'app-modern-date-time-picker',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    MatInputModule,
    MatDatepickerModule,
    MatNativeDateModule,
    MatFormFieldModule,
    MatSelectModule,
    MatIconModule,
    MatButtonModule
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
        <mat-label>Hour</mat-label>
        <mat-select [(ngModel)]="selectedHour" (ngModelChange)="updateDateTime()">
          <mat-option *ngFor="let hour of hours" [value]="hour">{{hour}}</mat-option>
        </mat-select>
      </mat-form-field>

      <mat-form-field appearance="outline">
        <mat-label>Minute</mat-label>
        <mat-select [(ngModel)]="selectedMinute" (ngModelChange)="updateDateTime()">
          <mat-option *ngFor="let minute of minutes" [value]="minute">{{minute}}</mat-option>
        </mat-select>
      </mat-form-field>

      <mat-form-field appearance="outline">
        <mat-label>Second</mat-label>
        <mat-select [(ngModel)]="selectedSecond" (ngModelChange)="updateDateTime()">
          <mat-option *ngFor="let second of seconds" [value]="second">{{second}}</mat-option>
        </mat-select>
      </mat-form-field>
    </div>
  `,
  styles: [`
    .modern-date-time-picker {
      display: flex;
      flex-wrap: wrap;
      gap: 16px;
      align-items: center;
    }
    mat-form-field {
      flex: 1 1 auto;
    }
  `],
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => ModernDateTimePickerComponent),
      multi: true
    },
    MatDatepickerModule,
    MatNativeDateModule,
    { provide: DateAdapter, useClass: DateAdapter },
    { provide: MAT_DATE_FORMATS, useValue: MAT_DATE_FORMATS },
    { provide: MAT_DATE_LOCALE, useValue: 'en-US' }
  ]
})
export class ModernDateTimePickerComponent implements ControlValueAccessor, OnInit {
  selectedDate: Date = new Date();
  selectedHour: string = '00';
  selectedMinute: string = '00';
  selectedSecond: string = '00';

  hours: string[] = Array.from({length: 24}, (_, i) => i.toString().padStart(2, '0'));
  minutes: string[] = Array.from({length: 60}, (_, i) => i.toString().padStart(2, '0'));
  seconds: string[] = Array.from({length: 60}, (_, i) => i.toString().padStart(2, '0'));

  private onChange: (value: string) => void = () => {};
  private onTouched: () => void = () => {};

  ngOnInit() {
    this.updateDateTime();
  }

  writeValue(value: string): void {
    if (value) {
      const date = new Date(value);
      this.selectedDate = date;
      this.selectedHour = date.getHours().toString().padStart(2, '0');
      this.selectedMinute = date.getMinutes().toString().padStart(2, '0');
      this.selectedSecond = date.getSeconds().toString().padStart(2, '0');
      this.updateDateTime();
    }
  }

  registerOnChange(fn: (value: string) => void): void {
    this.onChange = fn;
  }

  registerOnTouched(fn: () => void): void {
    this.onTouched = fn;
  }

  updateDateTime(): void {
    if (this.selectedDate) {
      const dateTime = new Date(
        this.selectedDate.getFullYear(),
        this.selectedDate.getMonth(),
        this.selectedDate.getDate(),
        parseInt(this.selectedHour),
        parseInt(this.selectedMinute),
        parseInt(this.selectedSecond)
      );

      const formattedDateTime = this.formatDateTime(dateTime);
      this.onChange(formattedDateTime);
      this.onTouched();
    }
  }

  formatDateTime(date: Date): string {
    return `${date.getFullYear()}-${(date.getMonth() + 1).toString().padStart(2, '0')}-${date.getDate().toString().padStart(2, '0')} ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}:${date.getSeconds().toString().padStart(2, '0')}`;
  }
}