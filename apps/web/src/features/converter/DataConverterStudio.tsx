/**
 * 파일명: DataConverterStudio.tsx
 * 경로: apps/web/src/features/converter/DataConverterStudio.tsx
 * 목적: 데이터·문서·스캔 이미지 변환 및 고정밀 OCR 작업 화면을 제공함
 * 작성자: 개발팀
 * 작성일: 2026-09-09
 * 수정일: 2026-09-17
 */
import React, { useState, useEffect, useRef } from 'react';
import type { DownloadCheckStatus, FileCategory } from './converterTypes';
import { ConverterSetupStep } from './ConverterSetupStep';
import { ConverterResultStep } from './ConverterResultStep';
import { AlertCircle } from 'lucide-react';
import { UnifiedFileUploader } from '../shared/UnifiedFileUploader';
import { convertFile, verifyDownloadUrl, suggestConverterFieldNames } from '../../services/api';
import type { ConvertResponse, FieldNamesResponse } from '../../services/api';
export type { FileCategory } from './converterTypes';

interface Props {
  isDarkMode: boolean;
  onStepChange?: (step: number) => void;
  activeStep?: number;
  onSelectStep?: (step: number) => void;
}

const SUPPORTED_CONVERTER_EXTENSIONS =
  '.csv,.xlsx,.xls,.tsv,.txt,.json,.jsonl,.xml,.parquet,.pq,.hwp,.hwpx,.doc,.docx,.pdf,.md,.png,.jpg,.jpeg,.tif,.tiff,.bmp,.webp,.heic';

const IMAGE_EXTENSIONS = new Set([
  'png',
  'jpg',
  'jpeg',
  'tif',
  'tiff',
  'bmp',
  'webp',
  'heic',
]);

const DOCUMENT_EXTENSIONS = new Set([
  'hwp',
  'hwpx',
  'doc',
  'docx',
  'pdf',
  'md',
]);

export const DataConverterStudio: React.FC<Props> = ({
  isDarkMode,
  onStepChange,
  activeStep,
  onSelectStep,
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileCategory, setFileCategory] = useState<FileCategory | null>(null);
  const [targetFormat, setTargetFormat] = useState<string>('md');
  const [tableName, setTableName] = useState<string>('converted_data');
  const [isConverting, setIsConverting] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [result, setResult] = useState<ConvertResponse | null>(null);
  const [copied, setCopied] = useState<boolean>(false);
  const [copiedHtml, setCopiedHtml] = useState<boolean>(false);
  const [htmlPreviewTab, setHtmlPreviewTab] = useState<'visual' | 'code'>('visual');
  const [isHtmlFullScreen, setIsHtmlFullScreen] = useState<boolean>(false);
  const [downloadCheckStatus, setDownloadCheckStatus] = useState<DownloadCheckStatus>('idle');
  const [imagePreviewUrl, setImagePreviewUrl] = useState<string | null>(null);
  const [datasetProfile, setDatasetProfile] = useState<'public_data' | 'records'>('public_data');
  const [fieldNames, setFieldNames] = useState<FieldNamesResponse | null>(null);
  const [isSuggestingNames, setIsSuggestingNames] = useState(false);
  const [namesConfirmed, setNamesConfirmed] = useState(false);
  const [sheetName, setSheetName] = useState('');
  const [recordPath, setRecordPath] = useState('');
  const [csvEncoding, setCsvEncoding] = useState('utf-8');
  const [nameRequestVersion, setNameRequestVersion] = useState(0);
  const [nameError, setNameError] = useState<string | null>(null);
  const resultRef = useRef(result);
  const isRetryingDownloadCheckRef = useRef(false);
  resultRef.current = result;
  const inputExtension = selectedFile?.name.split('.').pop()?.toLowerCase() || '';
  const structuredInput = ['json', 'xml'].includes(inputExtension);
  const supportsPublicData = Boolean(selectedFile && ['csv', 'xlsx', 'xls', 'json', 'xml'].includes(inputExtension));
  const usesPublicData = supportsPublicData && (['json', 'xml'].includes(targetFormat) || (structuredInput && targetFormat === 'csv'));
  const needsFieldNames = usesPublicData && !structuredInput && datasetProfile === 'public_data';
  const editedNames = fieldNames?.fields.map(field => field.english_name) || [];
  const validFieldNames = editedNames.length > 0 && editedNames.every(name => /^[A-Za-z][A-Za-z0-9_]{0,63}$/.test(name) && !/^xml/i.test(name))
    && new Set(editedNames.map(name => name.toLowerCase())).size === editedNames.length;
  useEffect(() => {
    onStepChange?.(result ? 4 : isConverting ? 3 : selectedFile ? 2 : 1);
  }, [isConverting, onStepChange, result, selectedFile]);

  // 오래된 추천 응답이 다른 파일·시트의 변수명을 덮어쓰지 않도록 취소함
  useEffect(() => {
    if (!selectedFile || !needsFieldNames || result) return;
    const controller = new AbortController();
    setIsSuggestingNames(true);
    setFieldNames(null);
    setNamesConfirmed(false);
    setNameError(null);
    suggestConverterFieldNames(selectedFile, sheetName || undefined, controller.signal, csvEncoding)
      .then(data => { if (!controller.signal.aborted) setFieldNames(data); })
      .catch(error => { if (!controller.signal.aborted) setNameError(error.message || '변수명 추천 실패'); })
      .finally(() => { if (!controller.signal.aborted) setIsSuggestingNames(false); });
    return () => controller.abort();
  }, [selectedFile, needsFieldNames, sheetName, csvEncoding, nameRequestVersion, result]);

  // 업로드된 이미지 파일의 썸네일 미리보기 URL을 생성 및 정리함
  useEffect(() => {
    if (selectedFile) {
      const ext = selectedFile.name.split('.').pop()?.toLowerCase() || '';
      if (IMAGE_EXTENSIONS.has(ext)) {
        const url = URL.createObjectURL(selectedFile);
        setImagePreviewUrl(url);
        return () => {
          URL.revokeObjectURL(url);
        };
      }
    }
    setImagePreviewUrl(null);
  }, [selectedFile]);

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
    isRetryingDownloadCheckRef.current = false;
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

  // 업로드 파일 선택 시 확장자를 분석하여 카테고리(이미지/문서/데이터셋) 및 기본 타깃 포맷을 자동 설정함
  const handleSelectFile = (file: File) => {
    setErrorMsg(null);
    setResult(null);
    setSelectedFile(file);
    setDatasetProfile('public_data');
    setRecordPath('');
    setFieldNames(null);
    setNamesConfirmed(false);
    setSheetName('');
    setCsvEncoding('utf-8');
    setNameError(null);

    const ext = file.name.split('.').pop()?.toLowerCase() || '';
    const cleanName = file.name
      .replace(/\.[^/.]+$/, '')
      .replace(/[^\p{L}\p{N}_]/gu, '_')
      .replace(/_+/g, '_')
      .replace(/^_|_$/g, '');
    setTableName(cleanName || 'converted_data');

    if (IMAGE_EXTENSIONS.has(ext)) {
      setFileCategory('image');
      setTargetFormat('md');
    } else if (DOCUMENT_EXTENSIONS.has(ext)) {
      setFileCategory('document');
      if (ext === 'md') {
        setTargetFormat('html');
      } else {
        setTargetFormat('md');
      }
    } else {
      setFileCategory('dataset');
      if (['csv', 'xlsx', 'xls', 'xml'].includes(ext)) {
        setTargetFormat('json');
      } else if (ext === 'tsv') {
        setTargetFormat('parquet');
      } else {
        setTargetFormat('csv');
      }
    }
  };

  // 선택된 파일과 설정값을 백엔드 API로 전송하여 포맷 변환을 비동기 수행함
  const handleConvert = async () => {
    if (!selectedFile) return;
    if (needsFieldNames && (isSuggestingNames || !validFieldNames || !namesConfirmed || !fieldNames)) {
      setErrorMsg('영문 변수명을 수정·확인한 뒤 변환하세요.');
      return;
    }
    setIsConverting(true);
    setErrorMsg(null);
    setResult(null);
    setDownloadCheckStatus('idle');

    try {
      const res = await convertFile({
        file: selectedFile,
        targetFormat,
        tableName: fileCategory === 'dataset' ? tableName : undefined,
        encoding: csvEncoding,
        datasetProfile: usesPublicData ? datasetProfile : undefined,
        recordPath: structuredInput && usesPublicData && datasetProfile === 'public_data' && recordPath ? recordPath : undefined,
        fieldNames: needsFieldNames && fieldNames ? Object.fromEntries(fieldNames.fields.map(field => [field.original_name, field.english_name])) : undefined,
        fieldNamesConfirmed: needsFieldNames ? namesConfirmed : undefined,
        sheetName: needsFieldNames ? (sheetName || fieldNames?.sheet_name || undefined) : undefined,
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
    setImagePreviewUrl(null);
    setFieldNames(null);
    setNamesConfirmed(false);
    setIsSuggestingNames(false);
    setNameError(null);
    setSheetName('');
  };

  // 변환을 다시 실행하지 않고 기존 다운로드 경로의 접근 가능 여부만 확인함
  const handleRetryDownloadCheck = async () => {
    const targetResult = result;
    if (!targetResult?.download_url || isRetryingDownloadCheckRef.current) return;

    isRetryingDownloadCheckRef.current = true;
    setDownloadCheckStatus('checking');
    try {
      const isAvailable = await verifyDownloadUrl(targetResult.download_url);
      if (resultRef.current === targetResult) {
        setDownloadCheckStatus(isAvailable ? 'ready' : 'missing');
      }
    } catch {
      if (resultRef.current === targetResult) {
        setDownloadCheckStatus('failed');
      }
    } finally {
      if (resultRef.current === targetResult) {
        isRetryingDownloadCheckRef.current = false;
      }
    }
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

  const fileExt = selectedFile?.name.split('.').pop()?.toLowerCase() || '';
  const showWordDocumentOption = fileCategory === 'document' && !['doc', 'docx'].includes(fileExt);
  const showHwpxDocumentOption = fileCategory === 'document' && fileExt !== 'hwpx';
  const showHwpDocumentOption = fileCategory === 'document' && ['pdf', 'hwpx'].includes(fileExt);

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
        <div className="space-y-6">
          <UnifiedFileUploader
            title="변환할 데이터셋 또는 사내 문서·스캔 이미지 파일 업로드"
            subtitle="CSV, Excel, TSV, JSON, XML, Parquet 데이터셋 또는 HWP, HWPX, Word, PDF, 이미지 문서를 드래그하거나 선택하세요."
            accept={SUPPORTED_CONVERTER_EXTENSIONS}
            formatsHint="CSV · XLSX · TSV · JSON · XML · PARQUET · HWP · HWPX · DOCX · PDF · PNG · JPG · TIFF · BMP · WEBP (최대 100MB)"
            onFilesSelected={([file]) => {
              if (file) handleSelectFile(file);
            }}
            onError={msg => setErrorMsg(msg)}
          />
        </div>
      )}

      {/* Step 2: File Configuration & Conversion Options */}
      {selectedFile && !result && (
        <ConverterSetupStep
          selectedFile={selectedFile}
          fileCategory={fileCategory}
          targetFormat={targetFormat}
          setTargetFormat={setTargetFormat}
          tableName={tableName}
          setTableName={setTableName}
          isConverting={isConverting}
          imagePreviewUrl={imagePreviewUrl}
          fileExt={fileExt}
          showWordDocumentOption={showWordDocumentOption}
          showHwpxDocumentOption={showHwpxDocumentOption}
          showHwpDocumentOption={showHwpDocumentOption}
          handleReset={handleReset}
          usesPublicData={usesPublicData}
          datasetProfile={datasetProfile}
          setDatasetProfile={setDatasetProfile}
          structuredInput={structuredInput}
          recordPath={recordPath}
          setRecordPath={setRecordPath}
          needsFieldNames={needsFieldNames}
          csvEncoding={csvEncoding}
          setCsvEncoding={setCsvEncoding}
          fieldNames={fieldNames}
          setFieldNames={setFieldNames}
          sheetName={sheetName}
          setSheetName={setSheetName}
          isSuggestingNames={isSuggestingNames}
          setNameRequestVersion={setNameRequestVersion}
          nameError={nameError}
          setNamesConfirmed={setNamesConfirmed}
          namesConfirmed={namesConfirmed}
          validFieldNames={validFieldNames}
          handleConvert={handleConvert}
        />
      )}

      {result && (
        <ConverterResultStep
          result={result}
          selectedFile={selectedFile}
          csvEncoding={csvEncoding}
          sourceSheetName={fieldNames?.sheet_name || undefined}
          downloadCheckStatus={downloadCheckStatus}
          onRetryDownloadCheck={handleRetryDownloadCheck}
          onReset={handleReset}
          onReconfigure={() => setResult(null)}
        />
      )}
    </div>
  );
};
