import React from 'react';
import { Upload } from 'lucide-react';
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
  handleBatchFiles: (files: File[]) => void;
}

export const StepUpload: React.FC<StepUploadProps> = ({
  isDarkMode,
  isUploading,
  setIsUploading,
  setUploadedFilename,
  setProfile,
  setTargetRows,
  setStep,
  setErrorMsg,
  handleFileUpload,
  handleBatchFiles,
}) => {
  return (
    <div className={`border rounded-2xl p-8 text-center space-y-6 shadow-sm ${
      isDarkMode ? 'bg-slate-900/60 border-slate-800' : 'bg-white border-slate-200'
    }`}>
      <div className="max-w-md mx-auto space-y-2">
        <h2 className={`text-xl font-bold ${isDarkMode ? 'text-white' : 'text-slate-900'}`}>
          데이터 파일 업로드
        </h2>
        <p className={`text-xs ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>
          정형 데이터셋(CSV, XLSX, XLS, TSV, TXT)을 업로드하면 SHA-256 무결성 검증과 자동 PII 감지가 실행됩니다. 여러 파일은 일괄 처리 화면으로 이동합니다.
        </p>
      </div>

      <div 
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          if (!isUploading && e.dataTransfer.files.length) {
            const files = Array.from(e.dataTransfer.files);
            if (files.length > 20) { setErrorMsg('최대 20개 파일을 선택하세요.'); return; }
            if (files.length > 1) handleBatchFiles(files);
            else handleFileUpload(files[0]);
          }
        }}
        className={`border-2 border-dashed rounded-2xl p-12 transition-all cursor-pointer max-w-2xl mx-auto ${
          isDarkMode 
            ? 'bg-slate-950/40 border-slate-700 hover:border-sky-500' 
            : 'bg-slate-50 border-slate-300 hover:border-sky-500 hover:bg-sky-50/30'
        }`}
        onClick={() => document.getElementById('file-input')?.click()}
      >
        <input 
          id="file-input" 
          type="file" 
          accept=".csv,.xlsx,.xls,.tsv,.txt"
          multiple
          disabled={isUploading}
          className="hidden" 
          onChange={(e) => {
            if (e.target.files?.length) {
              const files = Array.from(e.target.files);
              e.target.value = '';
              if (files.length > 20) { setErrorMsg('최대 20개 파일을 선택하세요.'); return; }
              if (files.length > 1) handleBatchFiles(files);
              else handleFileUpload(files[0]);
            }
          }} 
        />
        <div className="flex flex-col items-center gap-3">
          <div className={`w-14 h-14 rounded-2xl flex items-center justify-center ${
            isDarkMode ? 'bg-sky-500/10 border border-sky-500/20 text-sky-400' : 'bg-sky-100 border border-sky-200 text-sky-600'
          }`}>
            <Upload className="w-7 h-7" />
          </div>
          <div>
            <p className={`text-sm font-bold ${isDarkMode ? 'text-slate-200' : 'text-slate-800'}`}>
              {isUploading ? '파일 분석 및 무결성 해시 계산 중...' : '클릭하여 파일을 선택하거나 이곳으로 드래그 앤 드롭'}
            </p>
            <p className={`text-xs mt-1 ${isDarkMode ? 'text-slate-500' : 'text-slate-400'}`}>
              CSV, Excel(XLSX/XLS), TSV, TXT 지원 (최대 20개, 파일당 100MB)
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
