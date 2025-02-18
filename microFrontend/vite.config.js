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
      shared: ['react', 'react-dom']
    })
  ],
  build: {
    target: 'esnext',
    modulePreload: false,
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
  }
});