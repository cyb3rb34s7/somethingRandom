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
  },
  experiments: {
    topLevelAwait: true,
  },
  plugins: [
    new ModuleFederationPlugin({
      name: 'tvplus-cms',
      filename: 'remoteEntry.js',
      remotes: {
        'react-app': `promise new Promise(resolve => {
          const script = document.createElement('script')
          script.src = 'http://localhost:5173/assets/remoteEntry.js'
          script.onload = () => {
            const module = window['react_app']
            resolve(module)
          }
          document.head.appendChild(script)
        })`
      },
      shared: {
        react: { 
          singleton: true,
          eager: true,
          requiredVersion: false
        },
        'react-dom': { 
          singleton: true,
          eager: true,
          requiredVersion: false
        }
      }
    })
  ]
};

export default config;