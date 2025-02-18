import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import federation from '@originjs/vite-plugin-federation';

export default defineConfig({
  plugins: [
    react(),
    federation({
      name: 'react_app',
      filename: 'remoteEntry.js',
      exposes: {
        './App': './src/App'
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
  ],
  build: {
    target: 'esnext',
    modulePreload: false,
    minify: false,
    cssCodeSplit: false,
    rollupOptions: {
      output: {
        format: 'esm'
      }
    }
  },
  preview: {
    port: 5173,
    strictPort: true,
    headers: {
      "Access-Control-Allow-Origin": "*"
    }
  }
});