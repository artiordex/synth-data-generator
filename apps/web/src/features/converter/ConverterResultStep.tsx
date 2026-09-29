/**
 * 파일명: ConverterResultStep.tsx
 * 경로: apps/web/src/features/converter/ConverterResultStep.tsx
 * 목적: 문서 변환 결과와 내려받기 동작을 표시함
 * 작성자: 개발팀
 * 작성일: 2026-09-29
 * 수정일: 2026-09-29
 */
import React from 'react';
import {
  AlertCircle,
  CheckCircle2,
  ChevronRight,
  Download,
  RefreshCw,
  Sliders,
} from 'lucide-react';
import type { ConvertResponse } from '../../services/api';
import { getDownloadUrl } from '../../services/api';
import { MarkdownPreviewStudio } from './MarkdownPreviewStudio';
import { DatasetComparisonStudio } from './DatasetComparisonStudio';
import type { DownloadCheckStatus } from './converterTypes';
import { chooseDocumentReviewTab, formatFileSize } from './converterTypes';

interface ConverterResultStepProps {
  result: ConvertResponse;
  selectedFile: File | null;
  csvEncoding: string;
  sourceSheetName?: string;
  downloadCheckStatus: DownloadCheckStatus;
  onRetryDownloadCheck: () => void;
  onReset: () => void;
  onReconfigure: () => void;
}

/** 변환 결과와 검증 상태를 표시함 */
export const ConverterResultStep: React.FC<ConverterResultStepProps> = ({
  result,
  selectedFile,
  csvEncoding,
  sourceSheetName,
  downloadCheckStatus,
  onRetryDownloadCheck,
  onReset,
  onReconfigure,
}) => {
  const hasDocumentPreviewResult = Boolean(
    result.category === 'document' && (result.markdown_preview || result.html_preview)
  );
  const quality = result.document_structure?.quality;
  const hasQuality = Boolean(quality);
  const hasEmptyResult = Boolean(
    result.file_size <= 0 || (
      result.category === 'document' &&
      result.document_structure &&
      result.document_structure.text_length <= 0 &&
      !result.markdown_preview &&
      !result.html_preview
    )
  );
  const downloadReady = Boolean(result.download_url && !hasEmptyResult);
  // 결과 파일의 내려받기 가능 상태를 문구로 표현함
  const downloadStatusLabel = (() => {
    if (hasEmptyResult) return '결과가 비어 있어 다운로드 불가';
    if (!result.download_url) return '다운로드 파일 없음';
    return '다운로드 가능';
  })();
  const reviewPageText = quality?.ocr_review_pages?.length
    ? `${quality.ocr_review_pages.join(', ')}페이지`
    : '없음';
  const averageConfidenceText = quality?.average_confidence == null
    ? '미측정'
    : `${(quality.average_confidence * 100).toFixed(1)}%`;
  // OCR 품질 측정 상태를 검토 가능한 문구로 표현함
  const ocrStatusLabel = (() => {
    if (!hasQuality) return '품질 정보 없음';
    switch (quality?.ocr_status) {
      case 'completed':
        return 'OCR 완료';
      case 'review_required':
        return 'OCR 검토 필요';
      case 'failed':
        return 'OCR 실패';
      case 'not_required':
        return 'OCR 불필요';
      default:
        return 'OCR 상태 확인';
    }
  })();
  const documentReviewInitialTab = chooseDocumentReviewTab(
    result.source_format,
    result.target_format,
    Boolean(result.html_preview)
  );

  return (
    <div
      className={`bg-surface border border-subtle rounded-2xl shadow-sm ${
        hasDocumentPreviewResult
          ? 'overflow-visible p-3 sm:p-4 flex flex-col gap-3'
          : 'p-6 sm:p-8 space-y-6'
      }`}
    >
      {/* 상단 워크플로우 단계 전환 바 */}
      <div
        className={`${
          hasDocumentPreviewResult
            ? 'shrink-0 flex flex-wrap items-center justify-between gap-3 rounded-xl bg-surface-muted/60 border border-subtle text-xs px-3 py-1.5'
            : 'shrink-0 flex flex-wrap items-center justify-between gap-3 rounded-xl bg-surface-muted/60 border border-subtle text-xs p-3'
        }`}
      >
        <div className="flex items-center gap-2">
          <span className="text-2xs font-bold uppercase tracking-wider text-fg-muted">워크플로우 단계:</span>
          <div className="flex items-center gap-1.5 font-medium">
            <button
              type="button"
              onClick={onReset}
              className="px-2.5 py-1 rounded-lg text-fg-muted hover:text-fg hover:bg-surface border border-transparent hover:border-subtle transition-all flex items-center gap-1"
              title="파일 업로드 단계로 이동 (새 파일 선택)"
            >
              <span className="w-4 h-4 rounded-full bg-surface-muted flex items-center justify-center text-2xs font-mono">1</span>
              <span>파일 업로드</span>
            </button>
            <ChevronRight className="w-3.5 h-3.5 text-fg-muted/40" />
            <button
              type="button"
              onClick={onReconfigure}
              className="px-2.5 py-1 rounded-lg text-fg hover:text-accent hover:bg-surface border border-transparent hover:border-subtle transition-all flex items-center gap-1 font-bold"
              title="변환 설정 단계로 복귀하여 포맷 또는 옵션 변경"
            >
              <span className="w-4 h-4 rounded-full bg-surface-muted flex items-center justify-center text-2xs font-mono">2</span>
              <span>변환 설정 (포맷 변경)</span>
            </button>
            <ChevronRight className="w-3.5 h-3.5 text-fg-muted/40" />
            <span className="px-2.5 py-1 rounded-lg bg-accent/15 text-accent border border-accent/30 font-bold flex items-center gap-1">
              <span className="w-4 h-4 rounded-full bg-accent text-white flex items-center justify-center text-2xs font-mono">4</span>
              <span>결과 검토</span>
            </span>
          </div>
        </div>
        <button
          type="button"
          onClick={onReconfigure}
          className="text-xs font-semibold text-accent hover:underline flex items-center gap-1"
        >
          <Sliders className="w-3.5 h-3.5" />
          <span>포맷 변경 후 재변환</span>
        </button>
      </div>

      {downloadCheckStatus === 'checking' && (
        <div className="flex items-center gap-2 rounded-lg border border-accent/20 bg-accent-subtle/40 px-3 py-2 text-xs text-fg-muted" role="status" aria-live="polite">
          <RefreshCw className="h-3.5 w-3.5 animate-spin text-accent" />
          <span>서버에서 다운로드 파일 접근 상태를 확인하고 있습니다.</span>
        </div>
      )}
      {downloadCheckStatus === 'ready' && downloadReady && (
        <div className="flex items-center gap-2 rounded-lg border border-emerald-500/20 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-700 dark:text-emerald-300" role="status" aria-live="polite">
          <CheckCircle2 className="h-3.5 w-3.5 shrink-0" />
          <span>다운로드 파일 접근을 확인했습니다.</span>
        </div>
      )}
      {(downloadCheckStatus === 'missing' || downloadCheckStatus === 'failed') && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-amber-500/20 bg-amber-500/10 px-3 py-2 text-xs text-amber-800 dark:text-amber-200">
          <div className="flex items-center gap-2" role="alert">
            <AlertCircle className="h-3.5 w-3.5 shrink-0" />
            <span>
              {!result.download_url
                ? '다운로드 경로가 제공되지 않았습니다.'
                : downloadCheckStatus === 'missing'
                  ? '다운로드 파일에 접근하지 못했습니다. 잠시 후 다시 확인할 수 있습니다.'
                  : '다운로드 파일 확인 중 오류가 발생했습니다. 다시 확인해 주세요.'}
            </span>
          </div>
          {result.download_url && (
            <button
              type="button"
              className="ui-button-secondary text-xs"
              onClick={onRetryDownloadCheck}
            >
              <RefreshCw className="h-3.5 w-3.5" />
              파일 다시 확인
            </button>
          )}
        </div>
      )}

      {hasDocumentPreviewResult ? (
        <div className="shrink-0 flex flex-col gap-2 rounded-xl border border-subtle bg-surface-muted/55 px-3 py-2 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0 flex flex-wrap items-center gap-2">
            <span className="px-2 py-0.5 rounded-full text-2xs font-bold border border-emerald-500/20 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
              <CheckCircle2 className="w-3 h-3" />
              <span>변환 완료</span>
            </span>
            <span className="text-2xs font-semibold px-2 py-0.5 rounded-full bg-accent/10 text-accent font-mono shrink-0">
              {result.source_format} → {result.target_format}
            </span>
            <h3
              className="min-w-[180px] max-w-[42vw] truncate text-sm font-bold text-fg"
              title={result.file_name}
            >
              {result.file_name}
            </h3>
            <span className="text-2xs text-fg-muted font-mono truncate">
              {formatFileSize(result.file_size)}
              {result.document_structure?.pages_count != null && ` · ${result.document_structure.pages_count}페이지`}
              {result.document_structure?.block_count != null && ` · 블록 ${result.document_structure.block_count}`}
              {result.document_structure?.table_count != null && ` · 표 ${result.document_structure.table_count}`}
              {result.document_structure?.image_count != null && ` · 이미지 ${result.document_structure.image_count}`}
            </span>
          </div>

          <div className="flex shrink-0 flex-wrap items-center gap-1.5">
            <button
              type="button"
              onClick={onReconfigure}
              className="ui-button-secondary text-2xs px-2.5 py-1.5 flex items-center gap-1.5"
              title="현재 파일을 유지하고 다른 포맷(HTML, DOCX, MD 등)으로 설정을 변경하여 재변환합니다"
            >
              <Sliders className="w-3 h-3 text-accent" />
              <span>설정 변경</span>
            </button>

            <button
              type="button"
              onClick={onReset}
              className="ui-button-secondary text-2xs px-2.5 py-1.5"
              title="새로운 파일을 업로드합니다"
            >
              다른 파일
            </button>

            {downloadReady ? (
              <a
                href={getDownloadUrl(result.download_url)}
                className="ui-button-primary text-2xs px-2.5 py-1.5 shadow-md shadow-accent/20 flex items-center gap-1.5"
              >
                <Download className="w-3 h-3" />
                <span>다운로드</span>
              </a>
            ) : (
              <button
                type="button"
                disabled
                className="ui-button-secondary text-2xs px-2.5 py-1.5 flex items-center gap-1.5 opacity-60"
              >
                {downloadCheckStatus === 'checking' ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Download className="w-3 h-3" />}
                <span>{downloadStatusLabel}</span>
              </button>
            )}
          </div>
        </div>
      ) : (
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 border-b border-subtle pb-4 shrink-0">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold border border-emerald-500/20 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>변환 완료</span>
            </span>
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-accent/10 text-accent font-mono">
              {result.source_format} → {result.target_format}
            </span>
          </div>
          <h3 className="text-base sm:text-lg font-bold text-fg mt-1">
            {result.file_name}
          </h3>
          <p className="text-xs text-fg-muted mt-0.5">
            파일 크기: {formatFileSize(result.file_size)}
            {result.rows_count != null && ` · 총 ${result.rows_count.toLocaleString()}행`}
            {result.columns_count != null && ` · ${result.columns_count}개 컬럼`}
          </p>
          {result.document_structure && (
            <div className="mt-3 flex flex-wrap gap-1.5 text-2xs font-semibold text-fg-muted">
              <span className="rounded-md border border-subtle bg-surface-muted px-2 py-1">
                {result.document_structure.fidelity_level === 'high' ? '고충실도 파싱' : '최선형 파싱'}
              </span>
              <span className="rounded-md border border-subtle bg-surface-muted px-2 py-1">
                {result.document_structure.pages_count}페이지
              </span>
              <span className="rounded-md border border-subtle bg-surface-muted px-2 py-1">
                블록 {result.document_structure.block_count}
              </span>
              <span className="rounded-md border border-subtle bg-surface-muted px-2 py-1">
                표 {result.document_structure.table_count}
              </span>
              <span className="rounded-md border border-subtle bg-surface-muted px-2 py-1">
                이미지 {result.document_structure.image_count}
              </span>
              {result.document_structure.quality && !hasDocumentPreviewResult && (
                <div className="w-full pt-3" role="status">
                  <div className="flex flex-wrap items-center gap-2 p-3 rounded-xl bg-surface border border-subtle">
                    {/* 미리보기 텍스트 보존율 배지 */}
                    <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-muted border border-subtle">
                      <span className="text-2xs text-fg-muted font-bold">미리보기 텍스트 보존율:</span>
                      {result.document_structure.quality.text_coverage != null ? (
                        <span className={`text-xs font-mono font-bold ${
                          result.document_structure.quality.text_coverage >= 0.85
                            ? 'text-emerald-600 dark:text-emerald-400'
                            : 'text-amber-600 dark:text-amber-400'
                        }`}>
                          {(result.document_structure.quality.text_coverage * 100).toFixed(1)}%
                        </span>
                      ) : (
                        <span className="text-xs text-fg-muted">미측정</span>
                      )}
                    </div>

                    {/* 평균 신뢰도 배지 */}
                    <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-muted border border-subtle">
                      <span className="text-2xs text-fg-muted font-bold">평균 신뢰도:</span>
                      <span className={`text-xs font-mono font-bold ${
                        quality?.average_confidence != null && quality.average_confidence >= 0.85
                          ? 'text-emerald-600 dark:text-emerald-400'
                          : quality?.average_confidence != null
                          ? 'text-amber-600 dark:text-amber-400'
                          : 'text-fg-muted'
                      }`}>
                        {averageConfidenceText}
                      </span>
                    </div>

                    {/* 검토 페이지 배지 */}
                    <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-muted border border-subtle">
                      <span className="text-2xs text-fg-muted font-bold">검토 페이지:</span>
                      <span className={`text-xs font-semibold ${
                        quality?.ocr_review_pages?.length ? 'text-amber-600 dark:text-amber-400' : 'text-emerald-600 dark:text-emerald-400'
                      }`}>
                        {reviewPageText}
                      </span>
                    </div>

                    {/* 품질 검증 통과 안내 태그 */}
                    {quality?.text_coverage != null && quality.text_coverage >= 0.85 && (!quality.warnings || quality.warnings.length === 0) && (
                      <span className="text-2xs font-bold px-2 py-1 rounded-md bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                        품질 검증 통과
                      </span>
                    )}
                  </div>

                  {/* 경고 목록 */}
                  {result.document_structure.quality.warnings && result.document_structure.quality.warnings.length > 0 && (
                    <div className="mt-2 space-y-1">
                      {result.document_structure.quality.warnings.map((warning: string, index: number) => (
                        <p key={index} className="text-xs text-amber-600 dark:text-amber-400 flex items-center gap-1.5">
                          <span className="inline-block w-1.5 h-1.5 rounded-full bg-amber-500 shrink-0" />
                          <span>{warning}</span>
                        </p>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
          {result.document_structure && !hasDocumentPreviewResult && (
            <div className="mt-4 rounded-xl border border-subtle bg-surface-muted/50 p-4">
              <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <div className="text-xs font-bold text-fg">OCR 처리 품질</div>
                  <div className="mt-1 text-xs text-fg-muted">
                    {ocrStatusLabel} · {quality?.ocr_engine === 'local' ? '로컬 엔진' : '엔진 정보 없음'} · {downloadStatusLabel}
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs sm:grid-cols-4">
                  <div className="rounded-lg border border-subtle bg-surface px-3 py-2">
                    <div className="text-2xs font-bold text-fg-muted">페이지</div>
                    <div className="font-bold text-fg">{result.document_structure?.pages_count ?? 1}</div>
                  </div>
                  <div className="rounded-lg border border-subtle bg-surface px-3 py-2">
                    <div className="text-2xs font-bold text-fg-muted">진행률</div>
                    <div className="font-bold text-fg">
                      {quality?.page_progress?.length
                        ? `${Math.round(quality.page_progress.reduce((sum: number, page: any) => sum + page.progress, 0) / quality.page_progress.length)}%`
                        : hasQuality ? '100%' : '미확인'}
                    </div>
                  </div>
                  <div className="rounded-lg border border-subtle bg-surface px-3 py-2">
                    <div className="text-2xs font-bold text-fg-muted">평균 신뢰도</div>
                    <div className="font-bold text-fg">{averageConfidenceText}</div>
                  </div>
                  <div className="rounded-lg border border-subtle bg-surface px-3 py-2">
                    <div className="text-2xs font-bold text-fg-muted">저신뢰 영역</div>
                    <div className="font-bold text-fg">{quality?.low_confidence_regions?.length ?? 0}</div>
                  </div>
                </div>
              </div>

              {!hasQuality && (
                <div className="mt-3 rounded-lg border border-slate-500/20 bg-slate-500/10 p-3 text-xs text-fg-muted">
                  구형 변환 응답이라 OCR 품질 세부 정보가 포함되지 않았습니다. 결과 미리보기와 다운로드 파일을 직접 확인하세요.
                </div>
              )}

              {quality?.page_progress && quality.page_progress.length > 0 && (
                <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
                  {quality.page_progress.slice(0, 6).map((page: any) => (
                    <div key={page.page} className="rounded-lg border border-subtle bg-surface px-3 py-2 text-xs">
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-bold text-fg">{page.page}페이지</span>
                        <span className={page.status === 'review_required' ? 'text-amber-700 dark:text-amber-300' : 'text-emerald-700 dark:text-emerald-300'}>
                          {page.progress}%
                        </span>
                      </div>
                      <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-surface-muted">
                        <div
                          className={`h-full rounded-full ${page.status === 'review_required' ? 'bg-amber-500' : 'bg-emerald-500'}`}
                          style={{ width: `${page.progress}%` }}
                        />
                      </div>
                      <div className="mt-1 text-2xs text-fg-muted">{page.message}</div>
                    </div>
                  ))}
                </div>
              )}

              {quality?.low_confidence_regions && quality.low_confidence_regions.length > 0 && (
                <div className="mt-3 rounded-lg border border-amber-500/20 bg-amber-500/10 p-3 text-xs text-amber-800 dark:text-amber-200">
                  <div className="font-bold">검토가 필요한 영역</div>
                  <div className="mt-1 space-y-1">
                    {quality.low_confidence_regions.slice(0, 3).map((region: any, index: number) => (
                      <div key={`${region.label}-${index}`}>
                        {region.label}: {region.reason}
                        {region.confidence != null && ` (${(region.confidence * 100).toFixed(1)}%)`}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={onReconfigure}
            className="ui-button-secondary text-xs px-3.5 py-2.5 flex items-center gap-1.5"
            title="현재 파일을 유지하고 다른 포맷(HTML, DOCX, MD 등)으로 설정을 변경하여 재변환합니다"
          >
            <Sliders className="w-3.5 h-3.5 text-accent" />
            <span>변환 설정 다시 하기 (포맷 변경)</span>
          </button>

          <button
            type="button"
            onClick={onReset}
            className="ui-button-secondary text-xs px-4 py-2.5"
            title="새로운 파일을 업로드합니다"
          >
            다른 파일 변환
          </button>

          {result.field_mapping_url && (
            <a href={getDownloadUrl(result.field_mapping_url)} className="ui-button-secondary text-xs px-4 py-2.5">
              <Download className="w-4 h-4" />컬럼명 매핑 다운로드
            </a>
          )}
          {result.warnings && result.warnings.length > 0 && (
            <div className="ui-panel-muted text-sm">
              {result.warnings.map((warning, index) => <p key={index}>{warning}</p>)}
            </div>
          )}
          {downloadReady ? (
            <a
              href={getDownloadUrl(result.download_url)}
              className="ui-button-primary text-xs px-5 py-2.5 shadow-md shadow-accent/20 flex items-center gap-2"
            >
              <Download className="w-4 h-4" />
              <span>변환 파일 다운로드</span>
            </a>
          ) : (
            <button
              type="button"
              disabled
              className="ui-button-secondary text-xs px-5 py-2.5 flex items-center gap-2 opacity-60"
            >
              {downloadCheckStatus === 'checking' ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
              <span>{downloadStatusLabel}</span>
            </button>
          )}
        </div>
      </div>
      )}

      {/* A. 문서 변환 결과: 고충실도 HTML 및 마크다운 전체 연속 스크롤 & 원본 나란히 대조 뷰어 */}
      {result.category === 'document' && (result.markdown_preview || result.html_preview) && (
        <div className="h-[82vh] min-h-[720px]">
          <MarkdownPreviewStudio
            markdown={result.markdown_preview || ''}
            fileName={result.file_name}
            downloadUrl={downloadReady ? getDownloadUrl(result.download_url) : undefined}
            originalFile={selectedFile}
            originalUrl={result.original_file_url ? getDownloadUrl(result.original_file_url) : undefined}
            htmlPreview={result.html_preview}
            pagesCount={result.document_structure?.pages_count}
            initialRightTab={documentReviewInitialTab}
            targetFormat={result.target_format}
          />
        </div>
      )}

      {/* B. 정형 데이터셋 변환 결과: 원본 테이블과 변환 결과(SQL/Parquet/JSON/CSV) 양쪽 대조 & 전체 연속 스크롤 */}
      {result.category === 'dataset' && (
        <div className="space-y-3">
          <DatasetComparisonStudio
            originalFile={selectedFile}
            originalUrl={result.original_file_url ? getDownloadUrl(result.original_file_url) : undefined}
            originalFilename={result.original_filename || selectedFile?.name}
            sourceFormat={result.source_format || 'CSV'}
            sourceEncoding={csvEncoding}
            sourceSheetName={sourceSheetName}
            targetFormat={result.target_format}
            fileName={result.file_name}
            downloadUrl={downloadReady ? getDownloadUrl(result.download_url) : undefined}
            downloadReady={downloadReady}
            rowsCount={result.rows_count}
            structuredPreview={result.structured_preview}
            columnsCount={result.columns_count}
            columns={result.columns || []}
            preview={result.preview || []}
            markdownPreview={result.markdown_preview}
            htmlPreview={result.html_preview}
          />
        </div>
      )}

      {/* C. 문서 변환 결과 안내 (미리보기 텍스트가 없는 바이너리 문서 전용) */}
      {result.category === 'document' && !result.markdown_preview && !result.html_preview && (
        <div className="p-4 rounded-xl bg-accent-subtle/50 border border-accent/20 text-xs text-fg leading-relaxed flex items-start gap-3">
          <CheckCircle2 className="w-4 h-4 text-accent shrink-0 mt-0.5" />
          <div>
            <span className="font-bold">사내 문서 고해상도 변환이 완료되었습니다.</span>
            <p className="text-fg-muted mt-0.5">
              다운로드한 {result.target_format} 파일은 Acrobat Reader, 웹 브라우저, 한컴오피스 등에서 원본 서식 그대로 열람 및 인쇄하실 수 있습니다.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
