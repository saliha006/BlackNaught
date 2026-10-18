/// <reference types="vitest/config" />
import { defineConfig } from 'vite';

// `npm run dev:live` talks to the real backend through the SSH tunnel
// (ssh -N -L 8000:localhost:8000 linux1@148.100.78.95); plain `npm run dev` uses fixtures.
const backend = 'http://localhost:8000';

export default defineConfig({
  server: {
    // fixtures/ lives at the repo root, outside the Vite root
    fs: { allow: ['..'] },
    proxy: {
      '/api': backend,
      '/stream': { target: backend, changeOrigin: true },
    },
  },
  worker: { format: 'es' },
  test: {
    environment: 'node',
  },
});
