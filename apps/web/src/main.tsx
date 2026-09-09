/**
 * 파일명: main.tsx
 * 경로: apps/web/src/main.tsx
 * 목적: React 애플리케이션의 브라우저 진입점을 구성함
 * 작성자: 개발팀
 * 작성일: 2026-09-09
 * 수정일: 2026-09-09
 */
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './app/App';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
