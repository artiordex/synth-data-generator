/**
 * 파일명: converterTypes.ts
 * 경로: apps/web/src/features/converter/converterTypes.ts
 * 목적: 변환 화면의 파일 상태와 공통 유틸리티를 제공함
 * 작성자: 개발팀
 * 작성일: 2026-09-29
 * 수정일: 2026-09-29
 */
/** 변환 화면에서 사용하는 입력 파일 범주임 */
export type FileCategory = 'document' | 'dataset' | 'image';

export type DownloadCheckStatus = 'idle' | 'checking' | 'ready' | 'missing' | 'failed';

/** 파일 크기를 화면 표시용 문자열로 바꿈 */
export const formatFileSize = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} Bytes`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

/** 대상 형식에 맞는 기본 변환 미리보기 탭을 선택함 */
export const chooseDocumentReviewTab = (
  sourceFormat?: string,
  targetFormat?: string,
  hasHtmlPreview?: boolean
): 'html' | 'markdown' => {
  const target = targetFormat?.trim().toLowerCase() || '';
  if (['html', 'htm'].includes(target)) return 'html';
  return 'markdown';
};
