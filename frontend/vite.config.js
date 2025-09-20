import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Build bundles that can be included from Flask templates.
// Outputs to ../app/static/react/ relative to this frontend directory.
export default defineConfig({
  plugins: [react()],
  base: '/static/react/',
  build: {
    outDir: '../app/static/react',
    emptyOutDir: false, // do not wipe other static assets
    rollupOptions: {
      input: {
        'vibe-home': './src/main.jsx',
        'vibe-analyze': './src/analyze.jsx'
      },
      output: {
        entryFileNames: '[name].js',
        chunkFileNames: 'chunks/[name].js',
        format: 'es',
      },
    },
  },
});
