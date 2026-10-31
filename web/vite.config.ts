import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// API_URL lets the dev server proxy to a locally run API (e.g. one started with APP_ENV=dev).
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': process.env.API_URL ?? 'http://127.0.0.1:8000',
    },
  },
})
