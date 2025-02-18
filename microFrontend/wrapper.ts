// src/app/components/react-wrapper/react-wrapper.component.ts
import { Component, OnInit, ElementRef } from '@angular/core';
import { loadRemoteModule } from '@angular-architects/module-federation';

@Component({
  selector: 'app-react-wrapper',
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

      ReactDOM.render(
        React.createElement(ReactApp.default),
        this.elementRef.nativeElement.querySelector('div')
      );
    } catch (error) {
      console.error('Error loading React app:', error);
    }
  }

  ngOnDestroy() {
    const container = this.elementRef.nativeElement.querySelector('div');
    if (container) {
      const ReactDOM = require('react-dom');
      ReactDOM.unmountComponentAtNode(container);
    }
  }
}