// React app webpack.config.js
const ModuleFederationPlugin = require('webpack/lib/container/ModuleFederationPlugin');

module.exports = {
  // ... other webpack configurations
  plugins: [
    new ModuleFederationPlugin({
      name: 'reactApp',
      filename: 'remoteEntry.js',
      exposes: {
        './ReactApp': './src/App',
      },
      shared: {
        react: { singleton: true },
        'react-dom': { singleton: true }
      }
    }),
  ],
}

npm install @angular-architects/module-federation



// Angular app webpack.config.js
const ModuleFederationPlugin = require('webpack/lib/container/ModuleFederationPlugin');

module.exports = {
  // ... other webpack configurations
  plugins: [
    new ModuleFederationPlugin({
      name: 'angularHost',
      remotes: {
        reactApp: 'reactApp@http://localhost:3000/remoteEntry.js' // Adjust port as needed
      },
      shared: {
        '@angular/core': { singleton: true },
        '@angular/common': { singleton: true }
      }
    }),
  ],
}



// react-wrapper.component.ts
import { Component, OnInit, ElementRef } from '@angular/core';
import { loadRemoteModule } from '@angular-architects/module-federation';
import * as React from 'react';
import * as ReactDOM from 'react-dom';

@Component({
  selector: 'app-react-wrapper',
  template: '<div #reactContainer></div>'
})
export class ReactWrapperComponent implements OnInit {
  constructor(private elementRef: ElementRef) {}

  async ngOnInit() {
    const { default: ReactApp } = await loadRemoteModule({
      remoteEntry: 'http://localhost:3000/remoteEntry.js',
      remoteName: 'reactApp',
      exposedModule: './ReactApp'
    });

    ReactDOM.render(
      React.createElement(ReactApp),
      this.elementRef.nativeElement.querySelector('#reactContainer')
    );
  }

  ngOnDestroy() {
    ReactDOM.unmountComponentAtNode(
      this.elementRef.nativeElement.querySelector('#reactContainer')
    );
  }
}


// app-routing.module.ts
const routes: Routes = [
  // ... other routes
  {
    path: 'react-app',
    component: ReactWrapperComponent
  }
];



