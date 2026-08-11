import { resolve } from 'node:path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Dev-server proxy: the FastAPI service (api/) runs on :8000; production puts both behind
// nginx/caddy with /api routed the same way, so the front end always calls relative /api paths.
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html'),
        // the Korea pages: unlisted (noindex, no nav link) but first-class build entries.
        // korea.html = the stable presenter view; korea-app.html = the interactive parity
        // track (graduates to the default Korea entry when it lands).
        korea: resolve(__dirname, 'korea.html'),
        koreaApp: resolve(__dirname, 'korea-app.html'),
      },
    },
  },
  server: {
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
})
