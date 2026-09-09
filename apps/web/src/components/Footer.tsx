/**
 * 파일명: Footer.tsx
 * 경로: apps/web/src/components/Footer.tsx
 * 목적: 공통 푸터 UI를 표시함
 * 작성자: 개발팀
 * 작성일: 2026-09-09
 * 수정일: 2026-09-09
 */
import React from 'react';

interface FooterProps {
  isDarkMode: boolean;
  onOpenDoc: (view: 'changelog' | 'libraries' | 'dictionary' | 'history' | 'apidocs') => void;
}

export const Footer: React.FC<FooterProps> = ({ isDarkMode, onOpenDoc }) => {
  return (
    <footer className="mt-16 border-t border-subtle py-6 px-4 sm:px-8 bg-surface/50 transition-colors">
      <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-xs">
        <div className="flex flex-col sm:flex-row sm:items-center gap-1.5 sm:gap-3 text-center sm:text-left">
          <span className="font-bold text-fg">
            사내 데이터 생성기 v2.1.0
          </span>
          <span className="hidden sm:inline text-fg-muted/40">|</span>
          <span className="text-fg-muted">로컬 및 사내 인트라넷 전용 동작 환경</span>
        </div>

        {/* Text 'a' link style */}
        <div className="flex items-center gap-3 text-xs flex-wrap justify-center sm:justify-end">
          <button
            onClick={() => onOpenDoc('apidocs')}
            className="text-fg-muted hover:text-accent hover:underline transition-colors font-medium cursor-pointer"
            title="Swagger 대화형 API 문서 열기"
          >
            API 문서
          </button>
          <span className="text-fg-muted/40 select-none">|</span>
          <button
            onClick={() => onOpenDoc('changelog')}
            className="text-fg-muted hover:text-accent hover:underline transition-colors font-medium cursor-pointer"
          >
            개발이력
          </button>
          <span className="text-fg-muted/40 select-none">|</span>
          <button
            onClick={() => onOpenDoc('dictionary')}
            className="text-fg-muted hover:text-accent hover:underline transition-colors font-medium cursor-pointer"
          >
            용어사전
          </button>
          <span className="text-fg-muted/40 select-none">|</span>
          <button
            onClick={() => onOpenDoc('history')}
            className="text-fg-muted hover:text-accent hover:underline transition-colors font-medium cursor-pointer"
          >
            작업이력
          </button>
        </div>
      </div>
    </footer>
  );
};
