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
          eager: true
        },
        'react-dom': {
          singleton: true,
          eager: true
        }
      }
    })
  ],
  build: {
    modulePreload: false,
    target: 'esnext',
    minify: false,
    cssCodeSplit: false,
    rollupOptions: {
      output: {
        format: 'esm',
        entryFileNames: '[name].js',
        chunkFileNames: '[name].js'
      }
    }
  },
  preview: {
    port: 5173,
    strictPort: true,
    headers: {
      "Access-Control-Allow-Origin": "*",
      "Content-Type": "application/javascript"
    }
  },
  base: 'http://localhost:5173/'
});