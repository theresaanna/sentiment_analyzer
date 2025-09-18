import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Build a single IIFE bundle that can be included from Flask templates
// Outputs to app/static/react/vibe-home.js
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: 'app/static/react',
    emptyOutDir: true,
    lib: {
      entry: 'frontend/src/main.jsx',
      name: 'VibeHome',
      formats: ['iife'],
      fileName: () => 'vibe-home.js',
    },
    rollupOptions: {
      // Bundle everything (including React) into the single output file
      external: [],
    },
  },
});
