/**
 * 파일명: aiGuidePreviewTypes.ts
 * 경로: apps/web/src/features/aiguide/aiGuidePreviewTypes.ts
 * 목적: AI 가이드 데이터 미리보기 타입을 제공함
 * 작성자: 개발팀
 * 작성일: 2026-09-29
 * 수정일: 2026-09-29
 */
/** AI 가이드 미리보기에 표시할 데이터 표본 구조임 */
export interface SamplePreviewData {
  format: string;
  sheetName?: string;
  headers: string[];
  rows: string[][];
  totalRows: number;
  totalCols: number;
  jsonSnippet?: string;
}
