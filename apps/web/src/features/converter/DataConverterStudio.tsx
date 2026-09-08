import React, { useState } from 'react';
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
} from 'lucide-react';
import { UnifiedFileUploader } from '../shared/UnifiedFileUploader';
import { convertFile, ConvertResponse, getDownloadUrl } from '../../services/api';

interface Props {
  isDarkMode: boolean;
}

const SUPPORTED_CONVERTER_EXTENSIONS =
  '.csv,.xlsx,.xls,.tsv,.txt,.json,.jsonl,.parquet,.pq,.hwp,.hwpx,.doc,.docx,.pdf,.md';

export const DataConverterStudio: React.FC<Props> = ({ isDarkMode }) => {
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

    if (['hwp', 'hwpx', 'doc', 'docx', 'pdf', 'md'].includes(ext)) {
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

  const handleConvert = async () => {
    if (!selectedFile) return;
    setIsConverting(true);
    setErrorMsg(null);

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

  const handleReset = () => {
    setSelectedFile(null);
    setFileCategory(null);
    setResult(null);
    setErrorMsg(null);
    setCopied(false);
    setCopiedHtml(false);
    setHtmlPreviewTab('visual');
  };

  const handleCopyMarkdown = () => {
    if (result?.markdown_preview) {
      void navigator.clipboard.writeText(result.markdown_preview);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleCopyHtml = () => {
    if (result?.html_preview) {
      void navigator.clipboard.writeText(result.html_preview);
      setCopiedHtml(true);
      setTimeout(() => setCopiedHtml(false), 2000);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const fileExt = selectedFile?.name.split('.').pop()?.toLowerCase() || '';

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
          subtitle="CSV, Excel, TSV, JSON, Parquet 데이터셋 또는 HWP, HWPX, Word, PDF 문서를 드래그하거나 선택하세요."
          accept={SUPPORTED_CONVERTER_EXTENSIONS}
          formatsHint="CSV · XLSX · TSV · JSON · PARQUET · HWP · HWPX · DOCX · PDF (최대 100MB)"
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
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
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
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-600 dark:text-indigo-400">
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
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-rose-500/10 text-rose-600 dark:text-rose-400">
                        인쇄 품질 1:1 보존
                      </span>
                    </div>
                    <p className="text-xs text-fg-muted">
                      한컴/MS Word 공식 엔진을 통한 표, 줄바꿈, 폰트 깨짐 없는 배포용 고해상도 PDF 변환
                    </p>
                  </button>
                )}

                {/* HWPX (for HWP only) */}
                {fileExt === 'hwp' && (
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
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-sky-500/10 text-sky-600 dark:text-sky-400">
                        공공 표준 XML
                      </span>
                    </div>
                    <p className="text-xs text-fg-muted">
                      구형 바이너리 HWP를 공공기관 및 정부 표준 개방형 포맷인 OWPML HWPX로 전환
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
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
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
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-amber-500/10 text-amber-600 dark:text-amber-400">
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
                    <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                      고속 압축
                    </span>
                  </div>
                  <p className="text-[11px] text-fg-muted">
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
                    <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-sky-500/10 text-sky-600 dark:text-sky-400">
                      한글 깨짐 방지
                    </span>
                  </div>
                  <p className="text-[11px] text-fg-muted">
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
                    <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-green-500/10 text-green-600 dark:text-green-400">
                      보고서용
                    </span>
                  </div>
                  <p className="text-[11px] text-fg-muted">
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
                    <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-teal-500/10 text-teal-600 dark:text-teal-400">
                      GitHub/위키
                    </span>
                  </div>
                  <p className="text-[11px] text-fg-muted">
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
                    <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-600 dark:text-indigo-400">
                      실시간 검색 지원
                    </span>
                  </div>
                  <p className="text-[11px] text-fg-muted">
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
                    <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-600 dark:text-amber-400">
                      웹 API/NoSQL
                    </span>
                  </div>
                  <p className="text-[11px] text-fg-muted">
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
                    <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-purple-500/10 text-purple-600 dark:text-purple-400">
                      AI 학습/스트리밍
                    </span>
                  </div>
                  <p className="text-[11px] text-fg-muted">
                    한 줄당 1개의 JSON 객체로 구성되어 대용량 로그 적재 및 LLM 학습에 사용
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
                    <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-600 dark:text-indigo-400">
                      RDB 직접 적재
                    </span>
                  </div>
                  <p className="text-[11px] text-fg-muted">
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
              <p className="text-[11px] text-fg-muted">
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
        </div>
      )}

      {/* Step 3: Result Card */}
      {result && (
        <div className="bg-surface border border-subtle rounded-2xl p-6 sm:p-8 space-y-6 shadow-sm">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-subtle pb-5">
            <div>
              <div className="flex items-center gap-2">
                <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  변환 완료
                </span>
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
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={handleReset}
                className="ui-button-secondary text-xs px-4 py-2.5"
              >
                다른 파일 변환
              </button>

              <a
                href={getDownloadUrl(result.download_url)}
                className="ui-button-primary text-xs px-5 py-2.5 shadow-md shadow-accent/20 flex items-center gap-2"
              >
                <Download className="w-4 h-4" />
                <span>변환 파일 다운로드</span>
              </a>
            </div>
          </div>

          {/* HTML Content Preview & Live Web Viewer */}
          {result.html_preview && (
            <div className="space-y-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-2 text-xs font-bold text-fg">
                    <Globe className="w-4 h-4 text-accent" />
                    <span>생성된 HTML 웹 문서 미리보기</span>
                  </div>
                  {/* Tabs: Visual Preview vs Source Code */}
                  <div className="flex items-center bg-surface-muted p-0.5 rounded-lg border border-subtle">
                    <button
                      type="button"
                      onClick={() => setHtmlPreviewTab('visual')}
                      className={`text-[11px] font-bold px-2.5 py-1 rounded-md transition-all flex items-center gap-1 ${
                        htmlPreviewTab === 'visual'
                          ? 'bg-surface text-accent shadow-xs'
                          : 'text-fg-muted hover:text-fg'
                      }`}
                    >
                      <Eye className="w-3 h-3" />
                      <span>웹 화면</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => setHtmlPreviewTab('code')}
                      className={`text-[11px] font-bold px-2.5 py-1 rounded-md transition-all flex items-center gap-1 ${
                        htmlPreviewTab === 'code'
                          ? 'bg-surface text-accent shadow-xs'
                          : 'text-fg-muted hover:text-fg'
                      }`}
                    >
                      <Code2 className="w-3 h-3" />
                      <span>소스 코드</span>
                    </button>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <a
                    href={getDownloadUrl(result.download_url)}
                    target="_blank"
                    rel="noreferrer"
                    className="ui-button-secondary text-xs px-3 py-1.5 flex items-center gap-1.5 text-fg-muted hover:text-fg"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                    <span>새 탭에서 열기</span>
                  </a>
                  <button
                    type="button"
                    onClick={handleCopyHtml}
                    className="ui-button-secondary text-xs px-3 py-1.5 flex items-center gap-1.5 text-accent"
                  >
                    {copiedHtml ? (
                      <>
                        <Check className="w-3.5 h-3.5 text-emerald-500" />
                        <span className="text-emerald-500 font-bold">복사 완료!</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3.5 h-3.5" />
                        <span>HTML 복사</span>
                      </>
                    )}
                  </button>
                </div>
              </div>

              {htmlPreviewTab === 'visual' ? (
                <div className="rounded-xl border border-subtle overflow-hidden bg-surface shadow-xs">
                  <iframe
                    srcDoc={result.html_preview}
                    title="HTML Preview"
                    sandbox="allow-same-origin allow-scripts"
                    className="w-full h-[480px] border-0 bg-white"
                  />
                </div>
              ) : (
                <div className="relative rounded-xl border border-subtle bg-surface-muted/40 p-4 max-h-96 overflow-y-auto font-mono text-xs text-fg leading-relaxed whitespace-pre-wrap select-all">
                  {result.html_preview}
                </div>
              )}
            </div>
          )}

          {/* Markdown / SQL Content Preview & Copy Panel */}
          {result.markdown_preview && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-xs font-bold text-fg">
                  <Code2 className="w-4 h-4 text-accent" />
                  <span>
                    {result.target_format === 'SQL'
                      ? '생성된 SQL INSERT 구문 미리보기'
                      : '변환된 마크다운 내용 미리보기'}
                  </span>
                </div>
                <button
                  onClick={handleCopyMarkdown}
                  className="ui-button-secondary text-xs px-3 py-1.5 flex items-center gap-1.5 text-accent"
                >
                  {copied ? (
                    <>
                      <Check className="w-3.5 h-3.5 text-emerald-500" />
                      <span className="text-emerald-500 font-bold">복사 완료!</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5" />
                      <span>{result.target_format === 'SQL' ? 'SQL 구문 복사' : '마크다운 복사'}</span>
                    </>
                  )}
                </button>
              </div>

              <div className="relative rounded-xl border border-subtle bg-surface-muted/40 p-4 max-h-96 overflow-y-auto font-mono text-xs text-fg leading-relaxed whitespace-pre-wrap select-all">
                {result.markdown_preview}
              </div>
            </div>
          )}

          {/* Preview for tabular datasets */}
          {result.preview && result.preview.length > 0 && result.columns && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-xs font-bold text-fg">
                  <Table className="w-4 h-4 text-accent" />
                  <span>변환 데이터 미리보기 (상위 15행)</span>
                </div>
                <span className="text-[11px] text-fg-muted">
                  총 {result.columns.length}개 컬럼
                </span>
              </div>

              <div className="overflow-x-auto rounded-xl border border-subtle bg-surface-muted/30">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-subtle bg-surface-muted/70 text-fg-muted">
                      {result.columns.map((col, idx) => (
                        <th key={idx} className="p-2.5 font-semibold whitespace-nowrap">
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-subtle">
                    {result.preview.map((row, rIdx) => (
                      <tr key={rIdx} className="hover:bg-surface-muted/50">
                        {result.columns!.map((col, cIdx) => (
                          <td key={cIdx} className="p-2.5 whitespace-nowrap text-fg-muted font-mono text-[11px]">
                            {row[col] != null ? String(row[col]) : ''}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Document Result Notice */}
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
