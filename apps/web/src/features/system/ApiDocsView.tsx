/**
 * 파일명: ApiDocsView.tsx
 * 경로: apps/web/src/features/system/ApiDocsView.tsx
 * 목적: 사내 데이터 생성기 API 대화형 Swagger 문서를 표시함
 * 작성자: 개발팀
 * 작성일: 2026-09-09
 * 수정일: 2026-09-09
 */
import React, { useState, useRef } from 'react';
import { RefreshCw } from 'lucide-react';

interface ApiDocsViewProps {
  isDarkMode?: boolean;
  onStepChange?: (step: number) => void;
}

export const ApiDocsView: React.FC<ApiDocsViewProps> = () => {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  return (
    <div className="space-y-4 animate-fade-in">
      {/* Embedded Swagger Container */}
      <div className="relative w-full rounded-2xl border border-subtle overflow-hidden bg-white shadow-sm transition-all h-[820px] min-h-[780px]">
        {isLoading && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-surface/80 backdrop-blur-xs z-10 gap-3">
            <RefreshCw className="w-7 h-7 text-accent animate-spin" />
            <p className="text-xs font-semibold text-fg-muted">
              사내 데이터 생성기 API 대화형 문서를 불러오는 중입니다...
            </p>
          </div>
        )}

        <iframe
          ref={iframeRef}
          src="/docs"
          title="사내 데이터 생성기 API Swagger UI"
          className="w-full h-full border-none"
          onLoad={() => {
            setIsLoading(false);
          }}
        />
      </div>
    </div>
  );
};
