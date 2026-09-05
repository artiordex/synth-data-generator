import React from 'react';
import { UnifiedFileUploader } from '../shared/UnifiedFileUploader';
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
      subtitle="CSV, Excel(XLSX/XLS), TSV, JSON, Parquet 등 정형 데이터셋을 업로드하여 합성을 시작합니다."
      formatsHint="CSV · XLSX · XLS · TSV · JSON · PARQUET (최대 100MB)"
      isUploading={isUploading}
      multiple={false}
      onFilesSelected={([file]) => handleFileUpload(file)}
      onError={setErrorMsg}
    />
  );
};
