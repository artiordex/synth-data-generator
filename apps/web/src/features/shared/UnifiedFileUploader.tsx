/**
 * 파일명: UnifiedFileUploader.tsx
 * 경로: apps/web/src/features/shared/UnifiedFileUploader.tsx
 * 목적: 단일·다중 파일 업로드 UI와 입력 검증을 가명데이터와 일관된 파란색 계열 카드 형태로 공통 제공함
 * 작성자: 개발팀
 * 작성일: 2026-09-09
 * 수정일: 2026-09-16
 */
import React, { useState, useRef } from 'react';
import { Upload, Loader2, FileSpreadsheet, FileText, Image as ImageIcon, FileCode, CheckCircle2 } from 'lucide-react';

export const SUPPORTED_FILE_EXTENSIONS = '.csv,.xlsx,.xls,.tsv,.txt,.json,.jsonl,.xml,.parquet,.pq,.pdf,.hwp,.hwpx,.hwpt,.doc,.docx,.md,.png,.jpg,.jpeg,.tif,.tiff,.bmp,.webp,.heic';
export const SUPPORTED_FORMATS_HINT = 'CSV · XLSX · TSV · JSON · XML · PARQUET · PDF · HWP · HWPX · HWPT · DOCX · MD · PNG · JPG · TIFF · WEBP · HEIC (최대 100MB)';
export const TABLE_DATA_FILE_EXTENSIONS = '.csv,.xlsx,.xls,.tsv,.txt,.json,.jsonl,.parquet,.pq';
export const TABLE_DATA_FORMATS_HINT = 'CSV · XLSX · XLS · TSV · TXT · JSON · JSONL · PARQUET/PQ (최대 100MB)';

export interface UnifiedFileUploaderProps {
  title?: string;
  subtitle?: string;
  accept?: string;
  formatsHint?: string;
  multiple?: boolean;
  isUploading?: boolean;
  busyText?: string;
  idleText?: string;
  maxFiles?: number;
  onFilesSelected: (files: File[]) => void;
  onError?: (msg: string) => void;
  className?: string;
}

export const UnifiedFileUploader: React.FC<UnifiedFileUploaderProps> = ({
  title = '업로드할 파일 선택',
  subtitle = '파일을 이곳에 놓거나 직접 선택하세요.',
  accept = TABLE_DATA_FILE_EXTENSIONS,
  formatsHint,
  multiple = false,
  isUploading = false,
  busyText = '파일 업로드 및 분석 중...',
  idleText = '파일을 이곳에 놓거나 직접 선택하세요.',
  maxFiles,
  onFilesSelected,
  onError,
  className = '',
}) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const [uploadedFilesSummary, setUploadedFilesSummary] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFiles = (fileList: FileList | File[] | null) => {
    if (!fileList || !fileList.length || isUploading) return;
    const files = Array.from(fileList);

    if (!multiple && files.length > 1) {
      if (onError) {
        onError('단일 파일 모드에서는 1개의 파일만 업로드할 수 있습니다.');
      }
      return;
    }

    if (maxFiles && files.length > maxFiles) {
      if (onError) {
        onError(`한 번에 최대 ${maxFiles}개 파일까지 업로드할 수 있습니다.`);
      }
      return;
    }

    setUploadedFilesSummary(files.length === 1 ? files[0].name : `${files[0].name} 외 ${files.length - 1}개 파일`);
    onFilesSelected(files);
  };

  // 각 모듈별 실제 지원 포맷 정밀 판별
  const acceptLower = (accept || '').toLowerCase();
  const acceptTokens = acceptLower
    .split(',')
    .map((s) => s.trim().replace(/^\./, ''))
    .filter(Boolean);

  const supportsImages = acceptTokens.some((ext) => ['png', 'jpg', 'jpeg', 'tif', 'tiff', 'bmp', 'webp', 'heic'].includes(ext));
  const supportsTable = acceptTokens.some((ext) => ['csv', 'xlsx', 'xls', 'tsv', 'parquet', 'pq'].includes(ext));
  const supportsDocs = (acceptTokens.length > 15 || !supportsImages) && acceptTokens.some((ext) => ['hwp', 'hwpx', 'hwpt', 'doc', 'docx', 'pdf', 'md'].includes(ext));
  const supportsSchema = acceptTokens.some((ext) => ['sql', 'ddl', 'yaml', 'yml'].includes(ext));
  const isApiGuide = !supportsDocs && !supportsImages && acceptTokens.includes('json') && acceptTokens.includes('xml');

  // 모듈별 실제 지원 형식 목록 생성
  const formatRows: { icon: any; label: string; extensions: string; colorClass: string }[] = [];

  if (supportsSchema) {
    formatRows.push({
      icon: FileCode,
      label: '스키마 명세',
      extensions: 'SQL · DDL · JSON SCHEMA · YAML · OPENAPI',
      colorClass: 'text-sky-500',
    });
  } else if (isApiGuide) {
    formatRows.push({
      icon: FileSpreadsheet,
      label: '파일데이터',
      extensions: 'XLSX · CSV · TSV',
      colorClass: 'text-emerald-500',
    });
    formatRows.push({
      icon: FileCode,
      label: 'API 데이터',
      extensions: 'JSON · XML',
      colorClass: 'text-purple-500',
    });
  } else {
    if (supportsTable) {
      formatRows.push({
        icon: FileSpreadsheet,
        label: '표 데이터',
        extensions: 'CSV · XLSX · TSV · JSON · PARQUET',
        colorClass: 'text-emerald-500',
      });
    }
    if (supportsDocs) {
      formatRows.push({
        icon: FileText,
        label: '전자문서',
        extensions: 'PDF · HWP · HWPX · DOCX · MD',
        colorClass: 'text-blue-500',
      });
    }
    if (supportsImages) {
      formatRows.push({
        icon: ImageIcon,
        label: '스캔·이미지',
        extensions: 'PDF(스캔) · PNG · JPG · JPEG · TIFF · WEBP',
        colorClass: 'text-amber-500',
      });
    }
  }

  // 모듈에 맞는 하단 안내 문구 결정
  const bottomNotice = (() => {
    if (supportsImages) {
      return '파일당 최대 100MB · 스캔·이미지 문서는 고정밀 OCR 문자·표 구조 복원';
    }
    if (supportsDocs && !supportsTable) {
      return '파일당 최대 100MB · 사내 전자문서 서식 보존 변환 지원';
    }
    if (isApiGuide) {
      return '파일당 최대 100MB · 공공데이터 및 API 표준 AI 친화 분석';
    }
    if (supportsSchema) {
      return '파일당 최대 100MB · 테이블 및 컬럼 스키마 명세 자동 분석';
    }
    return '파일당 최대 100MB · 정형 표 데이터셋 지원';
  })();

  return (
    <section
      onDragOver={(e) => {
        e.preventDefault();
        if (!isUploading) setIsDragOver(true);
      }}
      onDragLeave={(e) => {
        e.preventDefault();
        setIsDragOver(false);
      }}
      onDrop={(e) => {
        e.preventDefault();
        setIsDragOver(false);
        handleFiles(e.dataTransfer.files);
      }}
      className={`relative w-full max-w-4xl mx-auto rounded-xl border border-dashed text-center transition-all p-8 sm:p-12 ${
        isDragOver
          ? 'border-accent bg-accent-subtle shadow-inner scale-[1.005]'
          : 'border-default bg-surface'
      } ${className}`}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        multiple={multiple}
        disabled={isUploading}
        className="hidden"
        onChange={(e) => {
          handleFiles(e.target.files);
          e.target.value = '';
        }}
      />

      {/* 스텝 파란색(accent) 계열 아이콘 박스 */}
      <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-xl bg-accent-subtle text-accent border border-accent/25 shadow-xs transition-transform hover:scale-105">
        {isUploading ? (
          <Loader2 className="h-7 w-7 animate-spin text-accent" />
        ) : (
          <Upload className="h-7 w-7 text-accent" />
        )}
      </div>

      {/* 제목 & 설명 */}
      <h3 className="text-lg sm:text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
        {isUploading ? busyText : title}
      </h3>
      <p className="mx-auto mt-2 mb-5 max-w-xl text-xs sm:text-sm text-slate-500 dark:text-slate-400 break-keep leading-relaxed">
        {isUploading
          ? uploadedFilesSummary || '선택된 데이터셋의 스키마와 무결성을 분석 중입니다.'
          : subtitle || idleText}
      </p>

      {/* 스텝 파란색(accent) 계열 파일 선택 버튼 */}
      <div className="flex justify-center">
        <button
          type="button"
          disabled={isUploading}
          onClick={() => inputRef.current?.click()}
          className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg text-sm font-semibold text-accent-fg bg-accent hover:bg-accent-hover active:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed shadow-sm transition-all hover:shadow cursor-pointer"
        >
          {isUploading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>처리 중...</span>
            </>
          ) : (
            <>
              <Upload className="h-4 w-4" />
              <span>파일 선택</span>
            </>
          )}
        </button>
      </div>

      {/* 하단 지원 포맷 구분 영역 (실제 지원하는 형식만 노출) */}
      {formatRows.length > 0 && (
        <div className="mt-7 pt-5 mx-auto max-w-lg border-t border-slate-200/80 dark:border-slate-800 space-y-2.5 text-left text-xs">
          {formatRows.map((row, idx) => {
            const Icon = row.icon;
            return (
              <div key={idx} className="flex items-center gap-3 text-slate-600 dark:text-slate-400">
                <div className="flex items-center gap-1.5 min-w-[92px] shrink-0 text-slate-400 dark:text-slate-500 font-medium whitespace-nowrap">
                  <Icon className={`w-4 h-4 shrink-0 ${row.colorClass}`} />
                  <span className="whitespace-nowrap">{row.label}</span>
                </div>
                <strong className="font-semibold text-slate-700 dark:text-slate-300 font-mono text-[11px] sm:text-xs whitespace-nowrap">
                  {row.extensions}
                </strong>
              </div>
            );
          })}
          <div className="pt-1 text-center">
            <span className="text-[11px] text-slate-400 dark:text-slate-500">
              {bottomNotice}
            </span>
          </div>
        </div>
      )}
    </section>
  );
};
