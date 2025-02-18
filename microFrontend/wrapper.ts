// src/app/components/react-wrapper/react-wrapper.component.ts
import { Component, OnInit, OnDestroy, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { loadRemoteModule } from '@angular-architects/module-federation';
import type { ComponentType } from 'react';

declare global {
  interface Window {
    React: typeof import('react');
    ReactDOM: typeof import('react-dom');
  }
}

@Component({
  selector: 'app-react-wrapper',
  standalone: true,
  imports: [CommonModule],
  template: '<div #reactContainer></div>',
  styles: [':host { display: block; }']
})
export class ReactWrapperComponent implements OnInit, OnDestroy {
  private reactRoot?: HTMLElement;

  constructor(private elementRef: ElementRef<HTMLElement>) {}

  async ngOnInit(): Promise<void> {
    this.reactRoot = this.elementRef.nativeElement.querySelector('div') as HTMLElement;
    
    try {
      // Load React and ReactDOM
      const [React, ReactDOM, RemoteApp] = await Promise.all([
        import('react') as Promise<typeof import('react')>,
        import('react-dom') as Promise<typeof import('react-dom')>,
        loadRemoteModule({
          remoteEntry: 'http://localhost:5173/assets/remoteEntry.js',
          remoteName: 'react-app',
          exposedModule: './App'
        })
      ]);

      // Store React and ReactDOM on window to avoid multiple instances
      window.React = React;
      window.ReactDOM = ReactDOM;

      const AppComponent = RemoteApp.default as ComponentType<any>;
      
      ReactDOM.default.render(
        React.default.createElement(AppComponent),
        this.reactRoot
      );
    } catch (error) {
      console.error('Failed to load React application:', error);
    }
  }

  ngOnDestroy(): void {
    if (this.reactRoot) {
      window.ReactDOM?.unmountComponentAtNode(this.reactRoot);
    }
  }
}