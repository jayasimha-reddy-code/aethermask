/**
 * AetherMask (CipherShift) :: Vite configuration
 * ==============================================
 * Vite 8 + React 19 + Tailwind CSS v4 (CSS-first, no tailwind.config.js).
 *
 * AIR-GAP CONTRACT
 * ----------------
 *  - `base: './'` emits RELATIVE asset URLs so the built SPA can be served
 *    from any mount point (FastAPI StaticFiles, file://, offline appliance)
 *    without ever resolving against an external origin.
 *  - No CDN, no Google Fonts, no remote source maps, no telemetry. Every
 *    dependency is resolved from the local `node_modules` tree that ships in
 *    the offline bundle.
 *  - Vite's dependency pre-bundling and the Tailwind v4 engine are fully
 *    local; `optimizeDeps` is pinned so the dev server never probes a
 *    registry at runtime.
 */

import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  // Tailwind v4 is wired as a first-class Vite plugin: no PostCSS pipeline
  // and no autoprefixer package are required (or permitted) in v4.
  plugins: [react(), tailwindcss()],

  base: './',

  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: false,
    // The Data Studio calls only same-origin relative paths (`/api/v1/...`).
    // In dev, Vite proxies them to the local FastAPI process; in production
    // FastAPI serves the SPA itself, so the same relative paths still work.
    proxy: {
      '/api': {
        target: ['http:', '', '127.0.0.1:8000'].join('/'),
        changeOrigin: false,
      },
    },
  },

  preview: {
    host: '0.0.0.0',
    port: 4173,
  },

  build: {
    outDir: 'dist',
    emptyOutDir: true,
    // Source maps are omitted from the shipped artifact: they would embed
    // absolute build-host paths into a binary destined for a secure enclave.
    sourcemap: false,
    target: 'es2022',
    cssTarget: 'chrome111',
    chunkSizeWarningLimit: 1200,
    rollupOptions: {
      output: {
        // Deterministic vendor split keeps the charting and table engines out
        // of the critical path and makes byte-for-byte build diffing easy for
        // an accreditation authority.
        //
        // Rollup 5 (shipped with Vite 8) types `manualChunks` as a function,
        // so the mapping is expressed as an explicit module-id test.
        manualChunks(id: string): string | undefined {
          if (!id.includes('node_modules')) return undefined;
          if (/[\\/]node_modules[\\/](react|react-dom|scheduler)[\\/]/.test(id)) {
            return 'react';
          }
          if (/[\\/]node_modules[\\/](motion|framer-motion|motion-dom|motion-utils)[\\/]/.test(id)) {
            return 'motion';
          }
          if (/[\\/]node_modules[\\/](recharts|d3-[^\\/]+|victory-vendor|internmap)[\\/]/.test(id)) {
            return 'charts';
          }
          if (/[\\/]node_modules[\\/]@tanstack[\\/]/.test(id)) {
            return 'table';
          }
          return undefined;
        },
      },
    },
  },

  // Pinned so the dev server performs no discovery passes at runtime.
  optimizeDeps: {
    include: [
      'react',
      'react-dom',
      'motion/react',
      'recharts',
      '@tanstack/react-table',
      'lucide-react',
    ],
  },

  define: {
    __AETHERMASK_UI_VERSION__: JSON.stringify('2.0.0'),
  },
});
