// timezone-format.directive.ts
import { Directive, ElementRef, Input, OnDestroy, OnInit } from '@angular/core';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import * as moment from 'moment';
import { StateStoreService } from './state-store.service';

@Directive({
  selector: '[appTimezoneFormat]'
})
export class TimezoneFormatDirective implements OnInit, OnDestroy {
  @Input('appTimezoneFormat') utcDate!: string;
  @Input() type: 'date' | 'time' = 'date';
  
  private destroy$ = new Subject<void>();
  private originalValue: string;

  constructor(
    private el: ElementRef,
    private stateStore: StateStoreService
  ) {}

  ngOnInit() {
    this.originalValue = this.utcDate;

    this.stateStore.timezone$.pipe(
      takeUntil(this.destroy$)
    ).subscribe(timezone => {
      const momentDate = moment.utc(this.originalValue);
      
      if (timezone === 'LOCAL') {
        momentDate.local();
      }

      const formattedValue = this.type === 'date' 
        ? momentDate.format('YYYY-MM-DD')
        : momentDate.format('HH:mm:ss');

      this.el.nativeElement.textContent = formattedValue;
    });
  }

  ngOnDestroy() {
    this.destroy$.next();
    this.destroy$.complete();
  }
}