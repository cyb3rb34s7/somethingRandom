import { Component, ElementRef, EventEmitter, HostListener, Input, OnInit, Output, ViewChild, forwardRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ControlValueAccessor, FormsModule, NG_VALUE_ACCESSOR, ReactiveFormsModule } from '@angular/forms';

@Component({
  selector: 'app-datetime-picker',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule],
  templateUrl: './datetime-picker.component.html',
  styleUrls: ['./datetime-picker.component.scss'],
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => DatetimePickerComponent),
      multi: true
    }
  ]
})
export class DatetimePickerComponent implements OnInit, ControlValueAccessor {
  @Input() placeholder = 'Select date and time';
  @Input() label = '';
  @Input() isRequired = false;
  @Input() inputId = 'datetime-input';
  @Input() disabled = false;
  @Output() dateTimeChange = new EventEmitter<Date>();
  @ViewChild('inputField') inputField!: ElementRef;
  @ViewChild('pickerContainer') pickerContainer!: ElementRef;

  isOpen = false;
  selectedDate: Date = new Date();
  displayValue = '';
  currentMonth: Date = new Date();
  weekDays = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'];
  calendarDays: { date: Date, isCurrentMonth: boolean, isToday: boolean, isSelected: boolean }[] = [];
  hours = Array.from({ length: 24 }, (_, i) => i.toString().padStart(2, '0'));
  minutes = Array.from({ length: 60 }, (_, i) => i.toString().padStart(2, '0'));
  selectedHour = '00';
  selectedMinute = '00';
  today = new Date();

  private onChange: any = () => {};
  private onTouched: any = () => {};

  constructor(private elementRef: ElementRef) {}

  ngOnInit(): void {
    this.buildCalendar();
  }

  @HostListener('document:click', ['$event'])
  onClickOutside(event: Event) {
    if (!this.elementRef.nativeElement.contains(event.target)) {
      this.isOpen = false;
    }
  }

  togglePicker() {
    if (this.disabled) return;
    this.isOpen = !this.isOpen;
    if (this.isOpen) {
      // When opening, rebuild the calendar in case the date has changed
      this.buildCalendar();
      
      // Set time to current selection
      if (this.selectedDate) {
        this.selectedHour = this.selectedDate.getHours().toString().padStart(2, '0');
        this.selectedMinute = this.selectedDate.getMinutes().toString().padStart(2, '0');
      }
    }
  }

  buildCalendar() {
    this.calendarDays = [];
    
    // Get the first day of the month
    const firstDayOfMonth = new Date(this.currentMonth.getFullYear(), this.currentMonth.getMonth(), 1);
    
    // Get the last day of the month
    const lastDayOfMonth = new Date(this.currentMonth.getFullYear(), this.currentMonth.getMonth() + 1, 0);
    
    // Get the day of the week for the first day (0-6, 0 is Sunday)
    const firstDayOfWeek = firstDayOfMonth.getDay();
    
    // Get the day of the week for the last day (0-6, 0 is Sunday)
    const lastDayOfWeek = lastDayOfMonth.getDay();
    
    // Add days from previous month to fill the first week
    const prevMonthLastDay = new Date(this.currentMonth.getFullYear(), this.currentMonth.getMonth(), 0).getDate();
    
    for (let i = firstDayOfWeek - 1; i >= 0; i--) {
      const prevMonthDay = prevMonthLastDay - i;
      const date = new Date(this.currentMonth.getFullYear(), this.currentMonth.getMonth() - 1, prevMonthDay);
      this.calendarDays.push({ 
        date, 
        isCurrentMonth: false,
        isToday: this.isToday(date),
        isSelected: this.isSelectedDate(date)
      });
    }
    
    // Add days of current month
    for (let i = 1; i <= lastDayOfMonth.getDate(); i++) {
      const date = new Date(this.currentMonth.getFullYear(), this.currentMonth.getMonth(), i);
      this.calendarDays.push({ 
        date, 
        isCurrentMonth: true,
        isToday: this.isToday(date),
        isSelected: this.isSelectedDate(date)
      });
    }
    
    // Add days from next month to fill the last week
    const daysToAdd = 6 - lastDayOfWeek;
    for (let i = 1; i <= daysToAdd; i++) {
      const date = new Date(this.currentMonth.getFullYear(), this.currentMonth.getMonth() + 1, i);
      this.calendarDays.push({ 
        date, 
        isCurrentMonth: false,
        isToday: this.isToday(date),
        isSelected: this.isSelectedDate(date)
      });
    }

    // If we need to fill up another row to make it 6 rows total (for consistent height)
    if (this.calendarDays.length < 42) {
      const startDay = daysToAdd + 1;
      const endDay = 42 - this.calendarDays.length + startDay;
      for (let i = startDay; i < endDay; i++) {
        const date = new Date(this.currentMonth.getFullYear(), this.currentMonth.getMonth() + 1, i);
        this.calendarDays.push({ 
          date, 
          isCurrentMonth: false,
          isToday: this.isToday(date),
          isSelected: this.isSelectedDate(date)
        });
      }
    }
  }

  isToday(date: Date): boolean {
    return date.getDate() === this.today.getDate() && 
           date.getMonth() === this.today.getMonth() && 
           date.getFullYear() === this.today.getFullYear();
  }

  isSelectedDate(date: Date): boolean {
    if (!this.selectedDate) return false;
    return date.getDate() === this.selectedDate.getDate() && 
           date.getMonth() === this.selectedDate.getMonth() && 
           date.getFullYear() === this.selectedDate.getFullYear();
  }

  selectDate(day: { date: Date }) {
    // Create a new date with hours and minutes from current selection
    this.selectedDate = new Date(
      day.date.getFullYear(),
      day.date.getMonth(),
      day.date.getDate(),
      parseInt(this.selectedHour),
      parseInt(this.selectedMinute)
    );
    
    // Update display value
    this.updateDisplayValue();
    
    // Rebuild calendar to update selection
    this.buildCalendar();
  }

  selectTime() {
    if (this.selectedDate) {
      this.selectedDate.setHours(parseInt(this.selectedHour));
      this.selectedDate.setMinutes(parseInt(this.selectedMinute));
      this.updateDisplayValue();
    }
  }

  updateDisplayValue() {
    if (this.selectedDate) {
      // Format date as MM/DD/YYYY HH:MM
      const month = (this.selectedDate.getMonth() + 1).toString().padStart(2, '0');
      const day = this.selectedDate.getDate().toString().padStart(2, '0');
      const year = this.selectedDate.getFullYear();
      const hours = this.selectedDate.getHours().toString().padStart(2, '0');
      const minutes = this.selectedDate.getMinutes().toString().padStart(2, '0');
      
      this.displayValue = `${month}/${day}/${year} ${hours}:${minutes}`;
      this.onChange(this.selectedDate);
      this.dateTimeChange.emit(this.selectedDate);
    } else {
      this.displayValue = '';
    }
  }

  prevMonth() {
    this.currentMonth = new Date(this.currentMonth.getFullYear(), this.currentMonth.getMonth() - 1, 1);
    this.buildCalendar();
  }

  nextMonth() {
    this.currentMonth = new Date(this.currentMonth.getFullYear(), this.currentMonth.getMonth() + 1, 1);
    this.buildCalendar();
  }

  goToToday() {
    this.currentMonth = new Date(this.today.getFullYear(), this.today.getMonth(), 1);
    this.buildCalendar();
  }

  // Clear selection
  clear() {
    this.selectedDate = new Date();
    this.displayValue = '';
    this.onChange(null);
    this.dateTimeChange.emit(null!);
    this.buildCalendar();
  }

  // Apply selection and close picker
  apply() {
    this.updateDisplayValue();
    this.isOpen = false;
  }

  // Control Value Accessor Methods
  writeValue(value: Date): void {
    if (value) {
      this.selectedDate = new Date(value);
      this.selectedHour = this.selectedDate.getHours().toString().padStart(2, '0');
      this.selectedMinute = this.selectedDate.getMinutes().toString().padStart(2, '0');
      this.updateDisplayValue();
      this.buildCalendar();
    } else {
      this.displayValue = '';
    }
  }

  registerOnChange(fn: any): void {
    this.onChange = fn;
  }

  registerOnTouched(fn: any): void {
    this.onTouched = fn;
  }

  setDisabledState(isDisabled: boolean): void {
    this.disabled = isDisabled;
  }
}