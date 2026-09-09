/**
 * 파일명: SectionHeader.tsx
 * 경로: apps/web/src/components/SectionHeader.tsx
 * 목적: 페이지 내 섹션 제목과 보조 정보를 표시함
 * 작성자: 개발팀
 * 작성일: 2026-09-09
 * 수정일: 2026-09-09
 */
import React from 'react';
import { LucideIcon } from 'lucide-react';

type SectionHeaderProps = {
  title: string;
  description?: string;
  Icon?: LucideIcon;
  action?: React.ReactNode;
  meta?: React.ReactNode;
  headingId?: string;
  className?: string;
};

export function SectionHeader({ title, description, Icon, action, meta, headingId, className = '' }: SectionHeaderProps) {
  // 섹션 제목과 선택적 작업 영역을 공통 배치함
  return (
    <div className={`flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between ${className}`}>
      <div className="min-w-0">
        <h2 id={headingId} className="ui-section-title">
          {Icon && <Icon className="h-4 w-4 shrink-0 text-accent" />}
          <span className="break-keep">{title}</span>
        </h2>
        {description && (
          <p className="ui-help-text mt-1">
            {description}
          </p>
        )}
      </div>
      {(action || meta) && (
        <div className="flex shrink-0 items-center gap-2 self-start">
          {meta}
          {action}
        </div>
      )}
    </div>
  );
}
