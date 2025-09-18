import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Build a single IIFE bundle that can be included from Flask templates.
// Outputs to ../app/static/react/vibe-home.js relative to this frontend directory.
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: '../app/static/react',
    emptyOutDir: false, // do not wipe other static assets
    lib: {
      entry: './src/main.jsx',
      name: 'VibeHome',
      formats: ['iife'],
      fileName: () => 'vibe-home.js',
    },
    rollupOptions: {
      external: [],
    },
  },
});
