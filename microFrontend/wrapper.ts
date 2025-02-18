// src/app/components/react-wrapper/react-wrapper.component.ts
import { Component, OnInit, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { loadRemoteModule } from '@angular-architects/module-federation';
import type { FC } from 'react';

@Component({
  selector: 'app-react-wrapper',
  standalone: true,
  imports: [CommonModule],
  template: '<div #reactContainer></div>'
})
export class ReactWrapperComponent implements OnInit {
  constructor(private elementRef: ElementRef) {}

  async ngOnInit() {
    try {
      const ReactApp = await loadRemoteModule({
        remoteEntry: 'http://localhost:5173/assets/remoteEntry.js',
        remoteName: 'react-app',
        exposedModule: './App'
      });

      const React = await import('react');
      const ReactDOM = await import('react-dom');

      const App = ReactApp.default as FC;
      
      ReactDOM.default.render(
        React.default.createElement(App),
        this.elementRef.nativeElement.querySelector('div')
      );
    } catch (error) {
      console.error('Error loading React app:', error);
    }
  }

  ngOnDestroy() {
    const container = this.elementRef.nativeElement.querySelector('div');
    if (container) {
      import('react-dom').then(ReactDOM => {
        ReactDOM.default.unmountComponentAtNode(container);
      });
    }
  }
}