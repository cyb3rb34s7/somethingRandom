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
    uniqueName: 'tvplus-cms',
    scriptType: 'module'
  },
  experiments: {
    topLevelAwait: true,
    outputModule: true
  },
  plugins: [
    new ModuleFederationPlugin({
      name: 'tvplus-cms',
      remotes: {
        'react-app': 'http://localhost:5173/assets/remoteEntry.js'
      },
      shared: {
        react: { 
          singleton: true,
          eager: true,
          requiredVersion: false,
          strictVersion: false
        },
        'react-dom': { 
          singleton: true,
          eager: true,
          requiredVersion: false,
          strictVersion: false
        }
      }
    })
  ]
};

export default config;