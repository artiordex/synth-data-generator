/**
 * 파일명: DataConverterStudio.tsx
 * 경로: apps/web/src/features/converter/DataConverterStudio.tsx
 * 목적: 데이터·문서 변환 작업 화면을 제공함
 * 작성자: 개발팀
 * 작성일: 2026-09-09
 * 수정일: 2026-09-09
 */
import React, { useState, useEffect } from 'react';
import {
  ArrowRight,
  Download,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  FileText,
  Database,
  Table,
  FileCode,
  Layers,
  RotateCcw,
  Copy,
  Check,
  Code2,
  Globe,
  Eye,
  ExternalLink,
  Maximize2,
  Minimize2,
  ChevronRight,
  Sliders,
} from 'lucide-react';
import { UnifiedFileUploader } from '../shared/UnifiedFileUploader';
import { convertFile, ConvertResponse, getDownloadUrl, verifyDownloadUrl } from '../../services/api';
import { MarkdownPreviewStudio } from './MarkdownPreviewStudio';
import { DatasetComparisonStudio } from './DatasetComparisonStudio';

interface Props {
  isDarkMode: boolean;
  onStepChange?: (step: number) => void;
  activeStep?: number;
  onSelectStep?: (step: number) => void;
}

const SUPPORTED_CONVERTER_EXTENSIONS =
  '.csv,.xlsx,.xls,.tsv,.txt,.json,.jsonl,.xml,.parquet,.pq,.hwp,.hwpx,.doc,.docx,.pdf,.md,.png,.jpg,.jpeg,.tif,.tiff,.bmp,.webp,.heic';

const DOCUMENT_REVIEW_HTML_FIRST_FORMATS = new Set([
  'pdf',
  'hwp',
  'hwpx',
  'doc',
  'docx',
  'png',
  'jpg',
  'jpeg',
  'tif',
  'tiff',
  'bmp',
  'webp',
  'heic',
]);

const chooseDocumentReviewTab = (
  sourceFormat?: string,
  targetFormat?: string,
  hasHtmlPreview?: boolean
): 'html' | 'markdown' => {
  if (!hasHtmlPreview) return 'markdown';
  const source = sourceFormat?.trim().toLowerCase() || '';
  const target = targetFormat?.trim().toLowerCase() || '';
  if (['html', 'htm'].includes(target)) return 'html';
  if (DOCUMENT_REVIEW_HTML_FIRST_FORMATS.has(source)) return 'html';
  if (['md', 'markdown', 'txt'].includes(target)) return 'markdown';
  return 'html';
};

export const DataConverterStudio: React.FC<Props> = ({
  isDarkMode,
  onStepChange,
  activeStep,
  onSelectStep,
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileCategory, setFileCategory] = useState<'document' | 'dataset' | null>(null);
  const [targetFormat, setTargetFormat] = useState<string>('md');
  const [tableName, setTableName] = useState<string>('converted_data');
  const [isConverting, setIsConverting] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [result, setResult] = useState<ConvertResponse | null>(null);
  const [copied, setCopied] = useState<boolean>(false);
  const [copiedHtml, setCopiedHtml] = useState<boolean>(false);
  const [htmlPreviewTab, setHtmlPreviewTab] = useState<'visual' | 'code'>('visual');
  const [isHtmlFullScreen, setIsHtmlFullScreen] = useState<boolean>(false);
  const [downloadCheckStatus, setDownloadCheckStatus] = useState<'idle' | 'checking' | 'ready' | 'missing' | 'failed'>('idle');
  const hasDocumentPreviewResult = Boolean(
    result?.category === 'document' && (result.markdown_preview || result.html_preview)
  );

  useEffect(() => {
    onStepChange?.(result ? 4 : isConverting ? 3 : selectedFile ? 2 : 1);
  }, [isConverting, onStepChange, result, selectedFile]);

  // 상위 워크스페이스 헤더의 단계 선택에 따라 화면 전환 처리함
  useEffect(() => {
    if (activeStep === 1) {
      if (selectedFile || result) {
        handleReset();
      }
    } else if (activeStep === 2) {
      if (result) {
        setResult(null);
      }
    }
  }, [activeStep]);

  useEffect(() => {
    if (!result?.download_url || result.download_ready === false) {
      setDownloadCheckStatus(result ? 'missing' : 'idle');
      return;
    }
    let cancelled = false;
    setDownloadCheckStatus('checking');
    verifyDownloadUrl(result.download_url)
      .then((ok: boolean) => {
        if (!cancelled) setDownloadCheckStatus(ok ? 'ready' : 'missing');
      })
      .catch(() => {
        if (!cancelled) setDownloadCheckStatus('failed');
      });
    return () => {
      cancelled = true;
    };
  }, [result]);

  useEffect(() => {
    document.body.style.overflow = isHtmlFullScreen ? 'hidden' : '';
    document.documentElement.style.overflow = isHtmlFullScreen ? 'hidden' : '';
    return () => {
      document.body.style.overflow = '';
      document.documentElement.style.overflow = '';
    };
  }, [isHtmlFullScreen]);

  useEffect(() => {
    if (!isHtmlFullScreen) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setIsHtmlFullScreen(false);
    };
    window.addEventListener('keydown', closeOnEscape);
    return () => window.removeEventListener('keydown', closeOnEscape);
  }, [isHtmlFullScreen]);

  // 업로드 파일 선택 시 확장자를 분석하여 카테고리(문서/데이터셋) 및 기본 타깃 포맷을 자동 설정함
  const handleSelectFile = (file: File) => {
    setErrorMsg(null);
    setResult(null);
    setSelectedFile(file);

    const ext = file.name.split('.').pop()?.toLowerCase() || '';
    const cleanName = file.name
      .replace(/\.[^/.]+$/, '')
      .replace(/[^\p{L}\p{N}_]/gu, '_')
      .replace(/_+/g, '_')
      .replace(/^_|_$/g, '');
    setTableName(cleanName || 'converted_data');

    if (['hwp', 'hwpx', 'doc', 'docx', 'pdf', 'md', 'png', 'jpg', 'jpeg', 'tif', 'tiff', 'bmp', 'webp', 'heic'].includes(ext)) {
      setFileCategory('document');
      if (ext === 'md') {
        setTargetFormat('html');
      } else {
        setTargetFormat('md');
      }
    } else {
      setFileCategory('dataset');
      if (['csv', 'xlsx', 'xls', 'tsv'].includes(ext)) {
        setTargetFormat('parquet');
      } else {
        setTargetFormat('csv');
      }
    }
  };

  // 선택된 파일과 설정값을 백엔드 API로 전송하여 포맷 변환을 비동기 수행함
  const handleConvert = async () => {
    if (!selectedFile) return;
    setIsConverting(true);
    setErrorMsg(null);
    setResult(null);
    setDownloadCheckStatus('idle');

    try {
      const res = await convertFile({
        file: selectedFile,
        targetFormat,
        tableName: fileCategory === 'dataset' ? tableName : undefined,
      });
      setResult(res);
    } catch (err: any) {
      setErrorMsg(err.message || '파일 변환에 실패했습니다.');
    } finally {
      setIsConverting(false);
    }
  };

  // 작업 상태 및 미리보기 데이터를 초기화하여 새 변환 준비 상태로 복원함
  const handleReset = () => {
    setSelectedFile(null);
    setFileCategory(null);
    setResult(null);
    setErrorMsg(null);
    setCopied(false);
    setCopiedHtml(false);
    setHtmlPreviewTab('visual');
    setIsHtmlFullScreen(false);
    setDownloadCheckStatus('idle');
  };

  // 변환된 마크다운 텍스트를 클립보드에 복사하고 알림 상태를 2초간 유지함
  const handleCopyMarkdown = () => {
    if (result?.markdown_preview) {
      void navigator.clipboard.writeText(result.markdown_preview);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  // 변환된 HTML 소스코드를 클립보드에 복사하고 알림 상태를 2초간 유지함
  const handleCopyHtml = () => {
    if (result?.html_preview) {
      void navigator.clipboard.writeText(result.html_preview);
      setCopiedHtml(true);
      setTimeout(() => setCopiedHtml(false), 2000);
    }
  };

  // 바이트 단위 파일 크기를 읽기 쉬운 포맷(Bytes, KB, MB) 문자열로 변환함
  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} Bytes`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const fileExt = selectedFile?.name.split('.').pop()?.toLowerCase() || '';
  const showWordDocumentOption = fileCategory === 'document' && !['doc', 'docx'].includes(fileExt);
  const showHwpxDocumentOption = fileCategory === 'document' && fileExt !== 'hwpx';
  const showHwpDocumentOption = fileCategory === 'document' && ['pdf', 'hwpx'].includes(fileExt);
  const normalizedTargetFormat = result?.target_format?.trim().toLowerCase() || '';
  const previewMode: 'html' | 'markdown' | 'sql' | 'none' = result
    ? normalizedTargetFormat === 'sql' && result.markdown_preview
      ? 'sql'
      : ['html', 'htm'].includes(normalizedTargetFormat) && result.html_preview
        ? 'html'
        : ['md', 'markdown'].includes(normalizedTargetFormat) && result.markdown_preview
          ? 'markdown'
          : result.html_preview
            ? 'html'
            : result.markdown_preview
              ? 'markdown'
              : 'none'
    : 'none';
  const isRenderedHtmlFallback = previewMode === 'html' && !['html', 'htm'].includes(normalizedTargetFormat);
  const quality = result?.document_structure?.quality;
  const hasQuality = Boolean(quality);
  const requiresQualityReview = Boolean(
    result?.status === 'review_required' || quality?.requires_review
  );
  const hasEmptyResult = Boolean(
    result && (result.file_size <= 0 || (
      result.category === 'document' &&
      result.document_structure &&
      result.document_structure.text_length <= 0 &&
      !result.markdown_preview &&
      !result.html_preview
    ))
  );
  const apiDownloadReady = Boolean(result?.download_url && (result.download_ready ?? true) && !hasEmptyResult);
  const downloadReady = apiDownloadReady && downloadCheckStatus === 'ready';
  const downloadStatusLabel = (() => {
    if (hasEmptyResult) return '결과가 비어 있어 다운로드 차단';
    if (result?.download_ready === false) {
      return result.status === 'review_required'
        ? '품질 검토 완료 전 다운로드 차단'
        : '다운로드 준비 안 됨';
    }
    if (!result?.download_url) return '다운로드 파일 없음';
    switch (downloadCheckStatus) {
      case 'checking':
        return '다운로드 파일 확인 중';
      case 'ready':
        return '다운로드 가능';
      case 'missing':
        return '다운로드 파일을 찾을 수 없음';
      case 'failed':
        return '다운로드 확인 실패';
      default:
        return '다운로드 대기';
    }
  })();
  const reviewPageText = quality?.ocr_review_pages?.length
    ? `${quality.ocr_review_pages.join(', ')}페이지`
    : '없음';
  const averageConfidenceText = quality?.average_confidence == null
    ? '미측정'
    : `${(quality.average_confidence * 100).toFixed(1)}%`;
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
  const ocrStatusClass = !hasQuality
    ? 'border-slate-500/20 bg-slate-500/10 text-slate-700 dark:text-slate-300'
    : quality?.requires_review
    ? 'border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300'
    : 'border-emerald-500/20 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300';
  const documentReviewInitialTab = result
    ? chooseDocumentReviewTab(result.source_format, result.target_format, Boolean(result.html_preview))
    : 'markdown';

  return (
    <div className="space-y-6">
      {errorMsg && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-700 dark:text-rose-300 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-500 shrink-0" />
            <span>{errorMsg}</span>
          </div>
          <button onClick={() => setErrorMsg(null)} className="text-rose-500 hover:text-rose-700 font-bold">
            닫기
          </button>
        </div>
      )}

      {/* Step 1: Upload Zone if no file is selected */}
      {!selectedFile && (
        <UnifiedFileUploader
          title="변환할 데이터셋 또는 사내 문서 파일 업로드"
          subtitle="CSV, Excel, TSV, JSON, XML, Parquet 데이터셋 또는 HWP, HWPX, Word, PDF, 이미지 문서를 드래그하거나 선택하세요."
          accept={SUPPORTED_CONVERTER_EXTENSIONS}
          formatsHint="CSV · XLSX · TSV · JSON · XML · PARQUET · HWP · HWPX · DOCX · PDF · PNG · JPG · JPEG · TIFF · BMP · WEBP · HEIC (최대 100MB)"
          onFilesSelected={([file]) => {
            if (file) handleSelectFile(file);
          }}
          onError={msg => setErrorMsg(msg)}
        />
      )}

      {/* Step 2: File Configuration & Conversion Options */}
      {selectedFile && !result && (
        <div className="bg-surface border border-subtle rounded-2xl p-6 sm:p-8 space-y-6 shadow-sm">
          {/* Selected File Card */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-xl bg-surface-muted border border-subtle">
            <div className="flex items-center gap-3 min-w-0">
              <div className="w-10 h-10 rounded-xl bg-accent-subtle text-accent flex items-center justify-center shrink-0">
                {fileCategory === 'document' ? (
                  <FileText className="w-5 h-5" />
                ) : (
                  <Database className="w-5 h-5" />
                )}
              </div>
              <div className="min-w-0">
                <div className="text-sm font-bold text-fg truncate">
                  {selectedFile.name}
                </div>
                <div className="text-xs text-fg-muted flex items-center gap-2 mt-0.5">
                  <span>{formatFileSize(selectedFile.size)}</span>
                  <span>·</span>
                  <span className="font-semibold text-accent uppercase">
                    {fileExt} {fileCategory === 'document' ? '사내 문서' : '정형 데이터'}
                  </span>
                </div>
              </div>
            </div>

            <button
              onClick={handleReset}
              disabled={isConverting}
              className="ui-button-secondary text-xs shrink-0 self-start sm:self-auto"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>다른 파일 선택</span>
            </button>
          </div>

          {/* Target Format Selector */}
          <div className="space-y-3">
            <label className="block text-xs font-bold text-fg uppercase tracking-wider">
              변환 대상 포맷 선택
            </label>

            {/* If Document */}
            {fileCategory === 'document' && (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {/* Markdown */}
                <button
                  type="button"
                  onClick={() => setTargetFormat('md')}
                  className={`p-4 rounded-xl border text-left transition-all ${
                    targetFormat === 'md'
                      ? 'border-accent bg-accent-subtle/80 ring-2 ring-accent/30 shadow-sm'
                      : 'border-subtle hover:border-accent bg-surface'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold text-sm text-fg">마크다운 (.md)</span>
                    <span className="text-2xs font-bold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                      추천 · LLM/RAG
                    </span>
                  </div>
                  <p className="text-xs text-fg-muted">
                    제목(#), 본문 단락, 글머리 기호 및 표(|---|---|)를 완벽 보존하여 사내 위키·노션·AI 파이프라인에 즉시 활용
                  </p>
                </button>

                {/* HTML Web Document */}
                <button
                  type="button"
                  onClick={() => setTargetFormat('html')}
                  className={`p-4 rounded-xl border text-left transition-all ${
                    targetFormat === 'html'
                      ? 'border-accent bg-accent-subtle/80 ring-2 ring-accent/30 shadow-sm'
                      : 'border-subtle hover:border-accent bg-surface'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold text-sm text-fg">HTML 웹 문서 (.html)</span>
                    <span className="text-2xs font-bold px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-600 dark:text-indigo-400">
                      반응형 웹 · 브라우저 열람
                    </span>
                  </div>
                  <p className="text-xs text-fg-muted">
                    제목, 본문 문단, 표 스타일이 적용되어 웹 브라우저에서 바로 열람 가능한 단독 실행형 웹 문서
                  </p>
                </button>

                {/* PDF */}
                {fileExt !== 'pdf' && (
                  <button
                    type="button"
                    onClick={() => setTargetFormat('pdf')}
                    className={`p-4 rounded-xl border text-left transition-all ${
                      targetFormat === 'pdf'
                        ? 'border-accent bg-accent-subtle/80 ring-2 ring-accent/30 shadow-sm'
                        : 'border-subtle hover:border-accent bg-surface'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-bold text-sm text-fg">PDF 문서 (.pdf)</span>
                      <span className="text-2xs font-bold px-2 py-0.5 rounded bg-rose-500/10 text-rose-600 dark:text-rose-400">
                        인쇄 품질 1:1 보존
                      </span>
                    </div>
                    <p className="text-xs text-fg-muted">
                      한컴/MS Word 공식 엔진을 통한 표, 줄바꿈, 폰트 깨짐 없는 배포용 고해상도 PDF 변환
                    </p>
                  </button>
                )}

                {/* Word Document */}
                {showWordDocumentOption && (
                  <button
                    type="button"
                    onClick={() => setTargetFormat('docx')}
                    className={`p-4 rounded-xl border text-left transition-all ${
                      targetFormat === 'docx'
                        ? 'border-accent bg-accent-subtle/80 ring-2 ring-accent/30 shadow-sm'
                        : 'border-subtle hover:border-accent bg-surface'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-bold text-sm text-fg">Word 문서 (.docx)</span>
                      <span className="text-2xs font-bold px-2 py-0.5 rounded bg-blue-500/10 text-blue-600 dark:text-blue-400">
                        MS Word 편집
                      </span>
                    </div>
                    <p className="text-xs text-fg-muted">
                      PDF/HWP/HWPX 문서를 표와 문단 구조를 유지한 편집 가능한 MS Word 문서로 변환
                    </p>
                  </button>
                )}

                {/* HWPX */}
                {showHwpxDocumentOption && (
                  <button
                    type="button"
                    onClick={() => setTargetFormat('hwpx')}
                    className={`p-4 rounded-xl border text-left transition-all ${
                      targetFormat === 'hwpx'
                        ? 'border-accent bg-accent-subtle/80 ring-2 ring-accent/30 shadow-sm'
                        : 'border-subtle hover:border-accent bg-surface'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-bold text-sm text-fg">개방형 한글 (.hwpx)</span>
                      <span className="text-2xs font-bold px-2 py-0.5 rounded bg-sky-500/10 text-sky-600 dark:text-sky-400">
                        공공 표준 XML
                      </span>
                    </div>
                    <p className="text-xs text-fg-muted">
                      PDF/HWP/Word 문서를 공공기관 및 정부 표준 개방형 포맷인 OWPML HWPX로 전환
                    </p>
                  </button>
                )}

                {/* HWP */}
                {showHwpDocumentOption && (
                  <button
                    type="button"
                    onClick={() => setTargetFormat('hwp')}
                    className={`p-4 rounded-xl border text-left transition-all ${
                      targetFormat === 'hwp'
                        ? 'border-accent bg-accent-subtle/80 ring-2 ring-accent/30 shadow-sm'
                        : 'border-subtle hover:border-accent bg-surface'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-bold text-sm text-fg">한글 문서 (.hwp)</span>
                      <span className="text-2xs font-bold px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-600 dark:text-cyan-400">
                        한컴 HWP
                      </span>
                    </div>
                    <p className="text-xs text-fg-muted">
                      PDF 또는 HWPX 문서를 한컴오피스에서 열 수 있는 바이너리 HWP 문서로 변환
                    </p>
                  </button>
                )}

                {/* Excel XLSX from Document Tables */}
                <button
                  type="button"
                  onClick={() => setTargetFormat('xlsx')}
                  className={`p-4 rounded-xl border text-left transition-all ${
                    targetFormat === 'xlsx'
                      ? 'border-accent bg-accent-subtle/80 ring-2 ring-accent/30 shadow-sm'
                      : 'border-subtle hover:border-accent bg-surface'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold text-sm text-fg">Excel 스프레드시트 (.xlsx)</span>
                    <span className="text-2xs font-bold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                      표 자동 추출
                    </span>
                  </div>
                  <p className="text-xs text-fg-muted">
                    한글/워드/PDF 문서 내의 모든 표(Table)를 행·열 구조 그대로 감지하여 엑셀 시트로 완벽 분리 추출
                  </p>
                </button>

                {/* Pure Text TXT */}
                <button
                  type="button"
                  onClick={() => setTargetFormat('txt')}
                  className={`p-4 rounded-xl border text-left transition-all ${
                    targetFormat === 'txt'
                      ? 'border-accent bg-accent-subtle/80 ring-2 ring-accent/30 shadow-sm'
                      : 'border-subtle hover:border-accent bg-surface'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold text-sm text-fg">텍스트 (.txt)</span>
                    <span className="text-2xs font-bold px-2 py-0.5 rounded bg-amber-500/10 text-amber-600 dark:text-amber-400">
                      순수 텍스트
                    </span>
                  </div>
                  <p className="text-xs text-fg-muted">
                    서식 없이 문서 내의 순수 본문 텍스트만 추출하여 UTF-8 텍스트 파일로 저장
                  </p>
                </button>
              </div>
            )}

            {/* If Dataset */}
            {fileCategory === 'dataset' && (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {/* Parquet */}
                <button
                  type="button"
                  onClick={() => setTargetFormat('parquet')}
                  className={`p-3.5 rounded-xl border text-left transition-all ${
                    targetFormat === 'parquet'
                      ? 'border-accent bg-accent-subtle/80 ring-2 ring-accent/30 shadow-sm'
                      : 'border-subtle hover:border-accent bg-surface'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold text-xs sm:text-sm text-fg">Parquet (.parquet)</span>
                    <span className="text-2xs font-bold px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                      고속 압축
                    </span>
                  </div>
                  <p className="text-xs text-fg-muted">
                    빅데이터 분석(Spark, DuckDB) 및 클라우드 적재에 최적화된 컬럼형 저장소 포맷
                  </p>
                </button>

                {/* CSV */}
                <button
                  type="button"
                  onClick={() => setTargetFormat('csv')}
                  className={`p-3.5 rounded-xl border text-left transition-all ${
                    targetFormat === 'csv'
                      ? 'border-accent bg-accent-subtle/80 ring-2 ring-accent/30 shadow-sm'
                      : 'border-subtle hover:border-accent bg-surface'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold text-xs sm:text-sm text-fg">CSV (UTF-8 BOM)</span>
                    <span className="text-2xs font-bold px-1.5 py-0.5 rounded bg-sky-500/10 text-sky-600 dark:text-sky-400">
                      한글 깨짐 방지
                    </span>
                  </div>
                  <p className="text-xs text-fg-muted">
                    엑셀 및 모든 프로그램에서 열람 시 한글이 깨지지 않는 UTF-8 with BOM 쉼표 구분 파일
                  </p>
                </button>

                {/* Excel XLSX */}
                <button
                  type="button"
                  onClick={() => setTargetFormat('xlsx')}
                  className={`p-3.5 rounded-xl border text-left transition-all ${
                    targetFormat === 'xlsx'
                      ? 'border-accent bg-accent-subtle/80 ring-2 ring-accent/30 shadow-sm'
                      : 'border-subtle hover:border-accent bg-surface'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold text-xs sm:text-sm text-fg">Excel (.xlsx)</span>
                    <span className="text-2xs font-bold px-1.5 py-0.5 rounded bg-green-500/10 text-green-600 dark:text-green-400">
                      보고서용
                    </span>
                  </div>
                  <p className="text-xs text-fg-muted">
                    실무진 배포 및 엑셀 분석용 통합 오피스 스프레드시트 문서
                  </p>
                </button>

                {/* Markdown Table */}
                <button
                  type="button"
                  onClick={() => setTargetFormat('md')}
                  className={`p-3.5 rounded-xl border text-left transition-all ${
                    targetFormat === 'md'
                      ? 'border-accent bg-accent-subtle/80 ring-2 ring-accent/30 shadow-sm'
                      : 'border-subtle hover:border-accent bg-surface'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold text-xs sm:text-sm text-fg">마크다운 표 (.md)</span>
                    <span className="text-2xs font-bold px-1.5 py-0.5 rounded bg-teal-500/10 text-teal-600 dark:text-teal-400">
                      GitHub/위키
                    </span>
                  </div>
                  <p className="text-xs text-fg-muted">
                    GitHub, Notion, 사내 위키에 바로 붙여넣어 볼 수 있는 GFM 마크다운 테이블 포맷
                  </p>
                </button>

                {/* HTML Web Table */}
                <button
                  type="button"
                  onClick={() => setTargetFormat('html')}
                  className={`p-3.5 rounded-xl border text-left transition-all ${
                    targetFormat === 'html'
                      ? 'border-accent bg-accent-subtle/80 ring-2 ring-accent/30 shadow-sm'
                      : 'border-subtle hover:border-accent bg-surface'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold text-xs sm:text-sm text-fg">HTML 웹 표 (.html)</span>
                    <span className="text-2xs font-bold px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-600 dark:text-indigo-400">
                      실시간 검색 지원
                    </span>
                  </div>
                  <p className="text-xs text-fg-muted">
                    브라우저에서 즉시 열람하고 데이터 내용을 실시간 검색·필터링할 수 있는 반응형 웹 테이블
                  </p>
                </button>

                {/* JSON */}
                <button
                  type="button"
                  onClick={() => setTargetFormat('json')}
                  className={`p-3.5 rounded-xl border text-left transition-all ${
                    targetFormat === 'json'
                      ? 'border-accent bg-accent-subtle/80 ring-2 ring-accent/30 shadow-sm'
                      : 'border-subtle hover:border-accent bg-surface'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold text-xs sm:text-sm text-fg">JSON (.json)</span>
                    <span className="text-2xs font-bold px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-600 dark:text-amber-400">
                      웹 API/NoSQL
                    </span>
                  </div>
                  <p className="text-xs text-fg-muted">
                    2스페이스 들여쓰기가 적용된 구조화된 JSON 레코드 배열 파일
                  </p>
                </button>

                {/* JSON Lines */}
                <button
                  type="button"
                  onClick={() => setTargetFormat('jsonl')}
                  className={`p-3.5 rounded-xl border text-left transition-all ${
                    targetFormat === 'jsonl'
                      ? 'border-accent bg-accent-subtle/80 ring-2 ring-accent/30 shadow-sm'
                      : 'border-subtle hover:border-accent bg-surface'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold text-xs sm:text-sm text-fg">JSON Lines (.jsonl)</span>
                    <span className="text-2xs font-bold px-1.5 py-0.5 rounded bg-purple-500/10 text-purple-600 dark:text-purple-400">
                      AI 학습/스트리밍
                    </span>
                  </div>
                  <p className="text-xs text-fg-muted">
                    한 줄당 1개의 JSON 객체로 구성되어 대용량 로그 적재 및 LLM 학습에 사용
                  </p>
                </button>

                {/* XML */}
                <button
                  type="button"
                  onClick={() => setTargetFormat('xml')}
                  className={`p-3.5 rounded-xl border text-left transition-all ${
                    targetFormat === 'xml'
                      ? 'border-accent bg-accent-subtle/80 ring-2 ring-accent/30 shadow-sm'
                      : 'border-subtle hover:border-accent bg-surface'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold text-xs sm:text-sm text-fg">XML (.xml)</span>
                    <span className="text-2xs font-bold px-1.5 py-0.5 rounded bg-cyan-500/10 text-cyan-600 dark:text-cyan-400">
                      시스템 연계
                    </span>
                  </div>
                  <p className="text-xs text-fg-muted">
                    행과 컬럼 구조를 XML 레코드로 변환하여 공공·사내 시스템 간 데이터 교환에 사용
                  </p>
                </button>

                {/* SQL INSERT */}
                <button
                  type="button"
                  onClick={() => setTargetFormat('sql')}
                  className={`p-3.5 rounded-xl border text-left transition-all ${
                    targetFormat === 'sql'
                      ? 'border-accent bg-accent-subtle/80 ring-2 ring-accent/30 shadow-sm'
                      : 'border-subtle hover:border-accent bg-surface'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold text-xs sm:text-sm text-fg">SQL INSERT (.sql)</span>
                    <span className="text-2xs font-bold px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-600 dark:text-indigo-400">
                      RDB 직접 적재
                    </span>
                  </div>
                  <p className="text-xs text-fg-muted">
                    사내 개발/운영 데이터베이스에 바로 붙여넣어 실행할 수 있는 INSERT 쿼리문
                  </p>
                </button>
              </div>
            )}
          </div>

          {/* Optional: Table Name for SQL */}
          {fileCategory === 'dataset' && targetFormat === 'sql' && (
            <div className="p-4 rounded-xl bg-surface-muted border border-subtle space-y-2">
              <label className="block text-xs font-bold text-fg">
                SQL 대상 테이블 이름 (Table Name)
              </label>
              <input
                type="text"
                value={tableName}
                onChange={e => setTableName(e.target.value)}
                placeholder="예: user_orders, customer_info"
                className="ui-field text-xs font-mono w-full max-w-xs"
              />
              <p className="text-xs text-fg-muted">
                생성될 INSERT INTO {tableName || '테이블명'} (컬럼...) VALUES (...) 구문에 적용됩니다.
              </p>
            </div>
          )}

          {/* Action Trigger Button */}
          <div className="pt-2 flex items-center justify-end">
            <button
              onClick={handleConvert}
              disabled={isConverting}
              className="ui-button-primary px-8 py-3 text-sm font-bold shadow-md shadow-accent/20 flex items-center gap-2"
            >
              {isConverting ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>
                    {targetFormat === 'md'
                      ? '문서 구조 분석 및 마크다운 변환 중...'
                      : fileCategory === 'document'
                      ? '문서 엔진 구동 및 변환 중...'
                      : '데이터셋 변환 및 압축 중...'}
                  </span>
                </>
              ) : (
                <>
                  <span>{targetFormat.toUpperCase()} 형식으로 변환하기</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </div>
          {isConverting && fileCategory === 'document' && (
            <div className="rounded-xl border border-accent/20 bg-accent-subtle/40 p-4 text-xs text-fg-muted">
              <div className="flex items-center gap-2 font-bold text-fg">
                <RefreshCw className="h-3.5 w-3.5 animate-spin text-accent" />
                <span>페이지 구조와 OCR 품질 정보를 계산하는 중입니다.</span>
              </div>
              <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-3">
                {['업로드 확인', '페이지 분석', '출력 파일 생성'].map((stage, index) => (
                  <div key={stage} className="rounded-lg border border-subtle bg-surface px-3 py-2">
                    <div className="text-2xs font-bold text-fg-muted">단계 {index + 1}</div>
                    <div className="mt-0.5 font-semibold text-fg">{stage}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Step 3: Result Card */}
      {result && (
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
                  onClick={handleReset}
                  className="px-2.5 py-1 rounded-lg text-fg-muted hover:text-fg hover:bg-surface border border-transparent hover:border-subtle transition-all flex items-center gap-1"
                  title="파일 업로드 단계로 이동 (새 파일 선택)"
                >
                  <span className="w-4 h-4 rounded-full bg-surface-muted flex items-center justify-center text-2xs font-mono">1</span>
                  <span>파일 업로드</span>
                </button>
                <ChevronRight className="w-3.5 h-3.5 text-fg-muted/40" />
                <button
                  type="button"
                  onClick={() => setResult(null)}
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
              onClick={() => setResult(null)}
              className="text-xs font-semibold text-accent hover:underline flex items-center gap-1"
            >
              <Sliders className="w-3.5 h-3.5" />
              <span>포맷 변경 후 재변환</span>
            </button>
          </div>

          {hasDocumentPreviewResult ? (
            <div className="shrink-0 flex flex-col gap-2 rounded-xl border border-subtle bg-surface-muted/55 px-3 py-2 sm:flex-row sm:items-center sm:justify-between">
              <div className="min-w-0 flex flex-wrap items-center gap-2">
                <span className={`px-2 py-0.5 rounded-full text-2xs font-bold border flex items-center gap-1 ${requiresQualityReview ? 'bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-500/30' : 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20'}`}>
                  {requiresQualityReview ? <AlertCircle className="w-3 h-3" /> : <CheckCircle2 className="w-3 h-3" />}
                  {requiresQualityReview ? '변환 결과 검토 필요' : '변환 완료'}
                </span>
                {result.document_structure && (
                  <span className={`px-2 py-0.5 rounded-full text-2xs font-bold border flex items-center gap-1 ${ocrStatusClass}`}>
                    {quality?.requires_review || !hasQuality ? (
                      <AlertCircle className="w-3 h-3" />
                    ) : (
                      <CheckCircle2 className="w-3 h-3" />
                    )}
                    {ocrStatusLabel}
                  </span>
                )}
                <span className="text-2xs text-fg-muted font-mono shrink-0">
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
                  onClick={() => setResult(null)}
                  className="ui-button-secondary text-2xs px-2.5 py-1.5 flex items-center gap-1.5"
                  title="현재 파일을 유지하고 다른 포맷(HTML, DOCX, MD 등)으로 설정을 변경하여 재변환합니다"
                >
                  <Sliders className="w-3 h-3 text-accent" />
                  <span>설정 변경</span>
                </button>

                <button
                  type="button"
                  onClick={handleReset}
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
                  <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold border flex items-center gap-1 ${requiresQualityReview ? 'bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-500/30' : 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20'}`}>
                    {requiresQualityReview ? <AlertCircle className="w-3.5 h-3.5" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
                    {requiresQualityReview ? '변환 결과 검토 필요' : '변환 완료'}
                  </span>
                  {result.document_structure && (
                    <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold border flex items-center gap-1 ${ocrStatusClass}`}>
                      {quality?.requires_review || !hasQuality ? (
                        <AlertCircle className="w-3.5 h-3.5" />
                      ) : (
                        <CheckCircle2 className="w-3.5 h-3.5" />
                      )}
                      {ocrStatusLabel}
                    </span>
                  )}
                  <span className="text-xs text-fg-muted font-mono">
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
                  {downloadCheckStatus === 'missing' && (
                    <div className="mt-3 rounded-lg border border-rose-500/20 bg-rose-500/10 p-3 text-xs text-rose-700 dark:text-rose-300">
                      다운로드 URL은 생성되었지만 서버에서 파일을 찾지 못했습니다. 다시 변환해 주세요.
                    </div>
                  )}
                  {downloadCheckStatus === 'failed' && (
                    <div className="mt-3 rounded-lg border border-amber-500/20 bg-amber-500/10 p-3 text-xs text-amber-800 dark:text-amber-200">
                      다운로드 파일 확인에 실패했습니다. 네트워크 상태를 확인한 뒤 다시 시도하세요.
                    </div>
                  )}
                </div>
              )}
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={() => setResult(null)}
                className="ui-button-secondary text-xs px-3.5 py-2.5 flex items-center gap-1.5"
                title="현재 파일을 유지하고 다른 포맷(HTML, DOCX, MD 등)으로 설정을 변경하여 재변환합니다"
              >
                <Sliders className="w-3.5 h-3.5 text-accent" />
                <span>변환 설정 다시 하기 (포맷 변경)</span>
              </button>

              <button
                type="button"
                onClick={handleReset}
                className="ui-button-secondary text-xs px-4 py-2.5"
                title="새로운 파일을 업로드합니다"
              >
                다른 파일 변환
              </button>

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
                targetFormat={result.target_format}
                fileName={result.file_name}
                downloadUrl={downloadReady ? getDownloadUrl(result.download_url) : undefined}
                downloadReady={downloadReady}
                rowsCount={result.rows_count}
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
      )}
    </div>
  );
};
