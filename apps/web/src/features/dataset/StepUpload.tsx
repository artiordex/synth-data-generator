/**
 * 파일명: StepUpload.tsx
 * 경로: apps/web/src/features/dataset/StepUpload.tsx
 * 목적: 데이터 업로드 단계를 표시함
 * 작성자: 개발팀
 * 작성일: 2026-09-09
 * 수정일: 2026-09-09
 */
import React from 'react';
import { TABLE_DATA_FILE_EXTENSIONS, TABLE_DATA_FORMATS_HINT, UnifiedFileUploader } from '../shared/UnifiedFileUploader';
import { DatasetProfile } from '../../types';

interface StepUploadProps {
  isDarkMode: boolean;
  isUploading: boolean;
  setIsUploading: (val: boolean) => void;
  setUploadedFilename: (name: string) => void;
  setProfile: (profile: DatasetProfile) => void;
  setTargetRows: (rows: number) => void;
  setStep: (step: number) => void;
  setErrorMsg: (msg: string | null) => void;
  handleFileUpload: (file: File) => Promise<void>;
}

export const StepUpload: React.FC<StepUploadProps> = ({
  isUploading,
  setErrorMsg,
  handleFileUpload,
}) => {
  return (
    <UnifiedFileUploader
      title="데이터 파일 업로드"
      subtitle="CSV, Excel(XLSX/XLS), TSV, TXT, JSON, JSONL, Parquet 등 표 형식 데이터셋을 업로드하여 합성을 시작합니다."
      accept={TABLE_DATA_FILE_EXTENSIONS}
      formatsHint={TABLE_DATA_FORMATS_HINT}
      isUploading={isUploading}
      multiple={false}
      onFilesSelected={([file]) => handleFileUpload(file)}
      onError={setErrorMsg}
    />
  );
};
