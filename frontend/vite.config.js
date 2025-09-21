import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

// Production-grade Vite configuration
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  
  return {
    plugins: [
      react({
        // Use automatic JSX runtime for smaller bundles
        jsxRuntime: 'automatic',
        // Enable Fast Refresh in development
        fastRefresh: mode === 'development',
      })
    ],
    
    base: '/static/react/',
    
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
        '@components': path.resolve(__dirname, './src/components'),
        '@services': path.resolve(__dirname, './src/services'),
        '@hooks': path.resolve(__dirname, './src/hooks'),
        '@contexts': path.resolve(__dirname, './src/contexts'),
        '@styles': path.resolve(__dirname, './src/styles'),
        '@utils': path.resolve(__dirname, './src/utils'),
      },
    },
    
    define: {
      'process.env.NODE_ENV': JSON.stringify(mode),
      'process.env.REACT_APP_API_URL': JSON.stringify(env.REACT_APP_API_URL || '/api'),
      'process.env.REACT_APP_VERSION': JSON.stringify(process.env.npm_package_version),
    },
    
    build: {
      outDir: '../app/static/react',
      emptyOutDir: false,
      
      // Production optimizations
      minify: mode === 'production' ? 'terser' : false,
      sourcemap: mode === 'development' ? 'inline' : false,
      
      // Set reasonable chunk size warnings
      chunkSizeWarningLimit: 1000,
      
      // Terser options for better minification
      terserOptions: {
        compress: {
          drop_console: mode === 'production',
          drop_debugger: mode === 'production',
          pure_funcs: mode === 'production' ? ['console.log', 'console.info'] : [],
        },
        format: {
          comments: false,
        },
      },
      
      rollupOptions: {
        input: {
          'vibe-home': './src/main.jsx',
          'vibe-analyze': './src/analyze.jsx',
          'vibe-analyze-app': './src/analyze-app.jsx',
        },
        
        output: {
          entryFileNames: '[name].js',
          chunkFileNames: 'chunks/[name].js',
          assetFileNames: 'assets/[name][extname]',
          format: 'es',
          
          // Manual chunks for better caching
          manualChunks: {
            'vendor-react': ['react', 'react-dom'],
            'vendor-charts': ['chart.js'],
          },
        },
        
        // External dependencies (if needed)
        external: [],
      },
      
      // Enable CSS code splitting
      cssCodeSplit: true,
      
      // Asset handling
      assetsInlineLimit: 4096, // 4kb
      
      // Report compressed size
      reportCompressedSize: true,
    },
    
    // Development server configuration
    server: {
      port: 3000,
      proxy: {
        '/api': {
          target: env.VITE_API_URL || 'http://localhost:8000',
          changeOrigin: true,
          secure: false,
        },
      },
    },
    
    // Preview server configuration
    preview: {
      port: 5173,
    },
    
    // Optimize dependencies
    optimizeDeps: {
      include: ['react', 'react-dom', 'chart.js'],
      exclude: [],
    },
  };
});
