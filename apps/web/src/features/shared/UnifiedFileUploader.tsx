/**
 * 파일명: UnifiedFileUploader.tsx
 * 경로: apps/web/src/features/shared/UnifiedFileUploader.tsx
 * 목적: 단일·다중 파일 업로드 UI와 입력 검증을 공통 제공함
 * 작성자: 개발팀
 * 작성일: 2026-09-09
 * 수정일: 2026-09-09
 */
import React, { useState, useRef } from 'react';
import { Upload, RefreshCw } from 'lucide-react';

export const SUPPORTED_FILE_EXTENSIONS = '.csv,.xlsx,.xls,.tsv,.txt,.json,.jsonl,.parquet,.pq,.pdf,.hwp,.hwpx,.hwpt,.doc,.docx,.md';
export const SUPPORTED_FORMATS_HINT = 'CSV · XLSX · TSV · JSON · PARQUET · PDF · HWP · HWPX · HWPT · DOCX · MD (최대 100MB)';
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
  title = '데이터 파일 업로드',
  subtitle = 'CSV, Excel(XLSX/XLS), TSV, JSON, Parquet 등 정형 데이터셋을 업로드하여 작업을 시작합니다.',
  accept = SUPPORTED_FILE_EXTENSIONS,
  formatsHint = SUPPORTED_FORMATS_HINT,
  multiple = false,
  isUploading = false,
  busyText = '데이터 분석 및 스키마 검증 중...',
  idleText = '클릭하여 파일 선택 또는 드래그 앤 드롭',
  maxFiles,
  onFilesSelected,
  onError,
  className = '',
}) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFiles = (fileList: FileList | File[] | null) => {
    // 업로드 상태와 파일 개수 조건을 확인한 뒤 선택 파일을 전달함
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

    onFilesSelected(files);
  };

  return (
    <div className={`bg-surface border border-subtle rounded-2xl shadow-sm p-6 sm:p-8 text-center space-y-6 ${className}`}>
      {/* Title & Subtitle */}
      <div className="max-w-md mx-auto space-y-1.5">
        <h2 className="text-lg font-bold text-fg tracking-tight">
          {title}
        </h2>
        <p className="text-xs text-fg-muted break-keep leading-relaxed">
          {subtitle}
        </p>
      </div>

      {/* Drag & Drop Zone */}
      <div
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
        onClick={() => {
          if (!isUploading && inputRef.current) {
            inputRef.current.click();
          }
        }}
        className={`mx-auto max-w-xl p-8 sm:p-10 rounded-2xl border border-dashed transition-all cursor-pointer group ${
          isDragOver
            ? 'border-accent bg-accent-subtle scale-[1.01]'
            : 'border-default hover:border-accent bg-surface-muted/60 hover:bg-accent-subtle'
        }`}
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

        <div className="flex flex-col items-center gap-3">
          <div className="w-12 h-12 rounded-xl flex items-center justify-center bg-accent-subtle border border-accent/20 text-accent transition-transform group-hover:scale-105">
            {isUploading ? (
              <RefreshCw className="w-6 h-6 animate-spin" />
            ) : (
              <Upload className="w-6 h-6" />
            )}
          </div>
          <div>
            <p className="text-sm font-semibold text-fg">
              {isUploading ? busyText : idleText}
            </p>
            <p className="text-xs text-fg-subtle mt-1 font-mono">
              {formatsHint}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
