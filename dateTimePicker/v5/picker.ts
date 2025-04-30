import { Component, ElementRef, EventEmitter, Input, OnInit, Output, ViewChild, forwardRef   setDisabledState(isDisabled: boolean): void {
    this.disabled = isDisabled;
  } from '@angular/core';
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
  @ViewChild('hoursContainer') hoursContainer!: ElementRef;
  @ViewChild('minutesContainer') minutesContainer!: ElementRef;
  @ViewChild('secondsContainer') secondsContainer!: ElementRef;

  isOpen = false;
  selectedDate: Date = new Date();
  displayValue = '';
  currentMonth: Date = new Date();
  weekDays = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'];
  calendarDays: { date: Date, isCurrentMonth: boolean, isToday: boolean, isSelected: boolean }[] = [];
  hours: string[] = [];
  minutes: string[] = [];
  seconds: string[] = [];
  selectedHour = '00';
  selectedMinute = '00';
  selectedSecond = '00';
  today = new Date();

  private onChange: any = () => {};
  private onTouched: any = () => {};

  constructor(private elementRef: ElementRef) {
    // Generate hours (00-23)
    this.hours = Array.from({ length: 24 }, (_, i) => i.toString().padStart(2, '0'));
    
    // Generate minutes (00-59)
    this.minutes = Array.from({ length: 60 }, (_, i) => i.toString().padStart(2, '0'));
    
    // Generate seconds (00-59)
    this.seconds = Array.from({ length: 60 }, (_, i) => i.toString().padStart(2, '0'));
  }

  ngOnInit(): void {
    this.buildCalendar();
  }

  // Close picker when clicking outside
  onClickOutside(event: Event) {
    if (this.isOpen && !this.elementRef.nativeElement.contains(event.target)) {
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
        this.selectedSecond = this.selectedDate.getSeconds().toString().padStart(2, '0');
        
        // Wait for view to initialize before scrolling
        setTimeout(() => {
          this.scrollToSelectedTime();
        }, 0);
      }
      
      // Add click outside listener
      document.addEventListener('click', this.onClickOutsideHandler);
    } else {
      // Remove click outside listener when closed
      document.removeEventListener('click', this.onClickOutsideHandler);
    }
  }

  // Handler for click outside
  private onClickOutsideHandler = (event: Event) => {
    this.onClickOutside(event);
  };

  buildCalendar() {
    this.calendarDays = [];
    
    // Get the first day of the month
    const firstDayOfMonth = new Date(this.currentMonth.getFullYear(), this.currentMonth.getMonth(), 1);
    
    // Get the last day of the month
    const lastDayOfMonth = new Date(this.currentMonth.getFullYear(), this.currentMonth.getMonth() + 1, 0);
    
    // Get the day of the week for the first day (0-6, 0 is Sunday)
    const firstDayOfWeek = firstDayOfMonth.getDay();
    
    // Add days from previous month to fill the first week
    const prevMonthLastDay = new Date(this.currentMonth.getFullYear(), this.currentMonth.getMonth(), 0).getDate();
    
    for (let i = 0; i < firstDayOfWeek; i++) {
      const prevMonthDay = prevMonthLastDay - firstDayOfWeek + i + 1;
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
    const daysToAdd = 42 - this.calendarDays.length; // Always show 6 weeks (42 days)
    for (let i = 1; i <= daysToAdd; i++) {
      const date = new Date(this.currentMonth.getFullYear(), this.currentMonth.getMonth() + 1, i);
      this.calendarDays.push({ 
        date, 
        isCurrentMonth: false,
        isToday: this.isToday(date),
        isSelected: this.isSelectedDate(date)
      });
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
    // Create a new date with hours, minutes, and seconds from current selection
    this.selectedDate = new Date(
      day.date.getFullYear(),
      day.date.getMonth(),
      day.date.getDate(),
      parseInt(this.selectedHour),
      parseInt(this.selectedMinute),
      parseInt(this.selectedSecond)
    );
    
    // Update display value
    this.updateDisplayValue();
    
    // Rebuild calendar to update selection
    this.buildCalendar();
  }

  selectHour(hour: string) {
    // Update the selected hour
    this.selectedHour = hour;
    
    if (this.selectedDate) {
      this.selectedDate.setHours(parseInt(hour));
      this.updateDisplayValue();
    }
    
    // Scroll to center the selected hour
    setTimeout(() => {
      this.scrollToSelected(this.hoursContainer.nativeElement, hour);
    }, 0);
  }

  selectMinute(minute: string) {
    // Update the selected minute
    this.selectedMinute = minute;
    
    if (this.selectedDate) {
      this.selectedDate.setMinutes(parseInt(minute));
      this.updateDisplayValue();
    }
    
    // Scroll to center the selected minute
    setTimeout(() => {
      this.scrollToSelected(this.minutesContainer.nativeElement, minute);
    }, 0);
  }
  
  selectSecond(second: string) {
    // Update the selected second
    this.selectedSecond = second;
    
    if (this.selectedDate) {
      this.selectedDate.setSeconds(parseInt(second));
      this.updateDisplayValue();
    }
    
    // Scroll to center the selected second
    setTimeout(() => {
      this.scrollToSelected(this.secondsContainer.nativeElement, second);
    }, 0);
  }
  
  // Helper method to scroll a time selector to center the selected value
  scrollToSelected(container: HTMLElement, value: string) {
    const items = container.querySelectorAll('.time-item');
    for (let i = 0; i < items.length; i++) {
      if (items[i].textContent?.trim() === value) {
        const containerHeight = container.clientHeight;
        const itemHeight = items[i].clientHeight;
        container.scrollTop = items[i].offsetTop - (containerHeight / 2) + (itemHeight / 2);
        break;
      }
    }
  }

  scrollToSelectedTime() {
    if (this.hoursContainer && this.minutesContainer && this.secondsContainer) {
      // Scroll each time selector to center the selected value
      this.scrollToSelected(this.hoursContainer.nativeElement, this.selectedHour);
      this.scrollToSelected(this.minutesContainer.nativeElement, this.selectedMinute);
      this.scrollToSelected(this.secondsContainer.nativeElement, this.selectedSecond);
    }
  }

  updateDisplayValue() {
    if (this.selectedDate) {
      // Format date as MM/DD/YYYY HH:MM:SS
      const month = (this.selectedDate.getMonth() + 1).toString().padStart(2, '0');
      const day = this.selectedDate.getDate().toString().padStart(2, '0');
      const year = this.selectedDate.getFullYear();
      const hours = this.selectedDate.getHours().toString().padStart(2, '0');
      const minutes = this.selectedDate.getMinutes().toString().padStart(2, '0');
      const seconds = this.selectedDate.getSeconds().toString().padStart(2, '0');
      
      this.displayValue = `${month}/${day}/${year} ${hours}:${minutes}:${seconds}`;
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
    // Update current month view to today's month
    this.currentMonth = new Date(this.today.getFullYear(), this.today.getMonth(), 1);
    
    // Set the selected date to today with current time
    const currentHour = this.selectedDate ? this.selectedDate.getHours() : 0;
    const currentMinute = this.selectedDate ? this.selectedDate.getMinutes() : 0;
    const currentSecond = this.selectedDate ? this.selectedDate.getSeconds() : 0;
    
    this.selectedDate = new Date(
      this.today.getFullYear(),
      this.today.getMonth(),
      this.today.getDate(),
      currentHour,
      currentMinute,
      currentSecond
    );
    
    // Update hours, minutes, seconds
    this.selectedHour = currentHour.toString().padStart(2, '0');
    this.selectedMinute = currentMinute.toString().padStart(2, '0');
    this.selectedSecond = currentSecond.toString().padStart(2, '0');
    
    // Update the display value
    this.updateDisplayValue();
    
    // Rebuild calendar to show the selection
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

  // Add wheel event handlers for smooth scrolling
  onHoursWheel(event: WheelEvent) {
    event.preventDefault();
    const direction = event.deltaY > 0 ? 1 : -1;
    const currentIndex = this.hours.findIndex(h => h === this.selectedHour);
    const newIndex = Math.max(0, Math.min(this.hours.length - 1, currentIndex + direction));
    this.selectHour(this.hours[newIndex]);
  }

  onMinutesWheel(event: WheelEvent) {
    event.preventDefault();
    const direction = event.deltaY > 0 ? 1 : -1;
    const currentIndex = this.minutes.findIndex(m => m === this.selectedMinute);
    const newIndex = Math.max(0, Math.min(this.minutes.length - 1, currentIndex + direction));
    this.selectMinute(this.minutes[newIndex]);
  }

  onSecondsWheel(event: WheelEvent) {
    event.preventDefault();
    const direction = event.deltaY > 0 ? 1 : -1;
    const currentIndex = this.seconds.findIndex(s => s === this.selectedSecond);
    const newIndex = Math.max(0, Math.min(this.seconds.length - 1, currentIndex + direction));
    this.selectSecond(this.seconds[newIndex]);
  }

  // Control Value Accessor Methods
  writeValue(value: Date): void {
    if (value) {
      this.selectedDate = new Date(value);
      this.selectedHour = this.selectedDate.getHours().toString().padStart(2, '0');
      this.selectedMinute = this.selectedDate.getMinutes().toString().padStart(2, '0');
      this.selectedSecond = this.selectedDate.getSeconds().toString().padStart(2, '0');
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

  // Apply selection and close picker
  apply() {
    this.updateDisplayValue();
    this.isOpen = false;
  }
}