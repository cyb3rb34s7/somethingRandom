// src/app/components/react-wrapper/react-wrapper.component.ts
import { Component, OnInit, OnDestroy, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { loadRemoteModule } from '@angular-architects/module-federation';
import type { ComponentType } from 'react';
import type * as ReactDOM from 'react-dom/client';
import type * as React from 'react';

@Component({
  selector: 'app-react-wrapper',
  standalone: true,
  imports: [CommonModule],
  template: '<div #reactContainer></div>',
  styles: [':host { display: block; }']
})
export class ReactWrapperComponent implements OnInit, OnDestroy {
  private root?: ReactDOM.Root;
  private reactRoot?: HTMLElement;

  constructor(private elementRef: ElementRef<HTMLElement>) {}

  async ngOnInit(): Promise<void> {
    this.reactRoot = this.elementRef.nativeElement.querySelector('div') as HTMLElement;
    
    try {
      // Load React and ReactDOM
      const [React, { createRoot }, RemoteApp] = await Promise.all([
        import('react'),
        import('react-dom/client'),
        loadRemoteModule({
          remoteEntry: 'http://localhost:5173/remoteEntry.js', // Updated URL
          remoteName: 'react-app',
          exposedModule: './App'
        })
      ]);

      const AppComponent = RemoteApp.default as ComponentType<any>;
      
      // Create root and render
      this.root = createRoot(this.reactRoot);
      this.root.render(React.createElement(AppComponent));

    } catch (error) {
      console.error('Failed to load React application:', error);
    }
  }

  ngOnDestroy(): void {
    if (this.root) {
      this.root.unmount();
    }
  }
}