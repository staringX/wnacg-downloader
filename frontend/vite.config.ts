import { defineConfig } from 'vite'
import { fileURLToPath, URL } from 'node:url'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

const BACKEND = process.env.VITE_BACKEND_URL || 'http://localhost:8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    proxy: {
      // SSE 端点：禁用缓冲，保持长连接
      '/api/events': {
        target: BACKEND,
        changeOrigin: true,
        // 关闭代理超时，避免 SSE 长连接被断开
        timeout: 0,
        proxyTimeout: 0,
        configure: (proxy) => {
          proxy.on('proxyReq', (proxyReq) => {
            proxyReq.setHeader('Cache-Control', 'no-cache')
          })
        },
      },
      '/api': {
        target: BACKEND,
        changeOrigin: true,
      },
    },
  },
})
