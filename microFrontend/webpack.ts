import { Configuration as WebpackConfiguration } from 'webpack';
import { Configuration as WebpackDevServerConfiguration } from 'webpack-dev-server';
import { container } from 'webpack';

interface Configuration extends WebpackConfiguration {
  devServer?: WebpackDevServerConfiguration;
}

const { ModuleFederationPlugin } = container;

const config: Configuration = {
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
  resolve: {
    alias: {
      'react': require.resolve('react'),
      'react-dom': require.resolve('react-dom')
    }
  },
  plugins: [
    new ModuleFederationPlugin({
      name: 'tvplus-cms',
      remotes: {
        // Updated URL to match Vite's dev server output
        reactApp: "react-app@http://localhost:5173/remoteEntry.js"
      },
      shared: {
        react: { 
          singleton: true, 
          requiredVersion: false,
          eager: true
        },
        'react-dom': { 
          singleton: true, 
          requiredVersion: false,
          eager: true
        }
      }
    })
  ]
};

export default config;