import { Component, OnInit, OnDestroy, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import type { ComponentType } from 'react';
import type * as ReactDOM from 'react-dom/client';

@Component({
  selector: 'app-react-wrapper',
  standalone: true,
  imports: [CommonModule],
  template: '<div #reactContainer></div>',
  styles: [':host { display: block; width: 100%; height: 100%; }']
})
export class ReactWrapperComponent implements OnInit, OnDestroy {
  private root?: ReactDOM.Root;
  private reactRoot?: HTMLElement;

  constructor(private elementRef: ElementRef<HTMLElement>) {}

  async ngOnInit(): Promise<void> {
    this.reactRoot = this.elementRef.nativeElement.querySelector('div') as HTMLElement;
    
    try {
      // Use dynamic import with the full module specifier
      const [React, ReactDOM, RemoteApp] = await Promise.all([
        import('react'),
        import('react-dom/client'),
        // Changed this line to use dynamic import
        (window as any)['react_app'].get('./App').then((factory: any) => factory())
      ]);

      const AppComponent = RemoteApp.default as ComponentType<any>;
      
      if (this.reactRoot) {
        this.root = ReactDOM.createRoot(this.reactRoot);
        this.root.render(React.createElement(AppComponent));
      }
    } catch (error) {
      console.error('Failed to load React application:', error);
      console.error('Detailed error:', error instanceof Error ? error.stack : error);
    }
  }

  ngOnDestroy(): void {
    if (this.root) {
      this.root.unmount();
    }
  }
}