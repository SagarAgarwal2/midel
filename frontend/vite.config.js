import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

const backendTarget = process.env.VITE_PROXY_TARGET || 'http://localhost:5001'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/upload': backendTarget,
      '/parse': backendTarget,
      '/ingest': backendTarget,
      '/signals': backendTarget,
      '/risk': backendTarget,
      '/impact': backendTarget,
      '/simulate': backendTarget,
      '/agent': backendTarget,
      '/alerts': backendTarget,
      '/decision': backendTarget,
      '/chat': backendTarget,
      '/summary': backendTarget,
      '/health': backendTarget,
    },
  },
})
