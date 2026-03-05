import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// For manual dev: if backend runs on another port (e.g. 8001), set VITE_BACKEND_PORT=8001
const backendPort = process.env.VITE_BACKEND_PORT || '8000'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/ws': {
        target: `ws://localhost:${backendPort}`,
        ws: true,
        changeOrigin: true,
      },
      '/api': {
        target: `http://localhost:${backendPort}`,
        changeOrigin: true,
      },
    },
  },
})
