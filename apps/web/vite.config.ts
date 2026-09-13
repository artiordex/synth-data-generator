/**
 * 파일명: vite.config.ts
 * 경로: apps/web/vite.config.ts
 * 목적: 웹 프론트엔드 빌드 도구 및 개발 프록시 설정을 정의함
 * 작성자: 개발팀
 * 작성일: 2026-09-09
 * 수정일: 2026-09-13
 */
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      '/docs': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      '/openapi.json': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      '/redoc': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      }
    }
  }
});
