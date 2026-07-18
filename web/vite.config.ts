import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Dev-server proxy: the FastAPI service (api/) runs on :8000; production puts both behind
// nginx/caddy with /api routed the same way, so the front end always calls relative /api paths.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
})
