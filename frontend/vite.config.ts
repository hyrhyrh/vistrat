/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/__tests__/setup.ts',
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      include: ['src/**/*.{ts,tsx}'],
      exclude: ['src/**/*.d.ts', 'src/__tests__/**']
    }
  },
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      '/api/stream-tasks': {
        target: 'http://localhost:16532',
        changeOrigin: true,
        ws: true,
        rewrite: (path) => path.replace(/^\/api\/stream-tasks/, '/stream-tasks')
      },
      '/api/flv': {
        target: 'http://localhost:16532',
        changeOrigin: true,
        // HTTP-FLV流代理，不重写路径
      },
      '/api': {
        target: 'http://localhost:16532',
        changeOrigin: true,
        ws: true
      },
      '/stream-tasks': {
        target: 'http://localhost:16532',
        changeOrigin: true,
        ws: true
      },
      '/uploads': {
        target: 'http://localhost:16532',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/uploads/, '/api/video/files')
      },
      '/ws': {
        target: 'ws://localhost:16532',
        ws: true,
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: 'dist'
  }
})