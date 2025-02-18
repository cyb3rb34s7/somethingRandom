import { Configuration } from 'webpack';
import { ModuleFederationPlugin } from 'webpack/lib/container/ModuleFederationPlugin';

export default {
  output: {
    publicPath: 'auto',
    uniqueName: 'tvplus-cms'
  },
  optimization: {
    runtimeChunk: false
  },
  experiments: {
    topLevelAwait: true
  },
  plugins: [
    new ModuleFederationPlugin({
      name: 'tvplus-cms',
      remotes: {
        reactApp: "react-app@http://localhost:5173/assets/remoteEntry.js"
      },
      shared: {
        '@angular/core': { singleton: true },
        '@angular/common': { singleton: true },
        'react': { singleton: true },
        'react-dom': { singleton: true }
      }
    })
  ]
} as Configuration;