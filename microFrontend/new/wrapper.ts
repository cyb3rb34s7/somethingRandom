import { Component, OnInit, OnDestroy, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { loadRemoteModule } from '@angular-architects/module-federation';
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
      const [React, { createRoot }, RemoteApp] = await Promise.all([
        import('react'),
        import('react-dom/client'),
        loadRemoteModule({
          type: 'module',
          remoteEntry: 'http://localhost:5173/assets/remoteEntry.js',
          exposedModule: './App'
        })
      ]);

      const AppComponent = RemoteApp.default as ComponentType<any>;
      if (this.reactRoot) {
        this.root = createRoot(this.reactRoot);
        this.root.render(React.createElement(AppComponent));
      }
    } catch (error) {
      console.error('Failed to load React application:', error);
      if (error instanceof Error) {
        console.error('Error details:', error.message);
        console.error('Stack:', error.stack);
      }
    }
  }

  ngOnDestroy(): void {
    if (this.root) {
      this.root.unmount();
    }
  }
}