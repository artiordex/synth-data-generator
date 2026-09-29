/**
 * 파일명: ConverterSetupStep.tsx
 * 경로: apps/web/src/features/converter/ConverterSetupStep.tsx
 * 목적: 변환 입력 파일과 옵션을 설정함
 * 작성자: 개발팀
 * 작성일: 2026-09-29
 * 수정일: 2026-09-29
 */
import React from 'react';
import {
  ArrowRight,
  Check,
  Database,
  FileText,
  Image as ImageIcon,
  Maximize2,
  RefreshCw,
  RotateCcw,
  ScanLine,
  Sparkles,
} from 'lucide-react';
import type { Dispatch, SetStateAction } from 'react';
import type { FieldNamesResponse } from '../../services/api';
import type { FileCategory } from './converterTypes';
import { formatFileSize } from './converterTypes';

interface ConverterSetupStepProps {
  selectedFile: File;
  fileCategory: FileCategory | null;
  targetFormat: string;
  setTargetFormat: Dispatch<SetStateAction<string>>;
  tableName: string;
  setTableName: Dispatch<SetStateAction<string>>;
  isConverting: boolean;
  imagePreviewUrl: string | null;
  fileExt: string;
  showWordDocumentOption: boolean;
  showHwpxDocumentOption: boolean;
  showHwpDocumentOption: boolean;
  handleReset: () => void;
  usesPublicData: boolean;
  datasetProfile: 'public_data' | 'records';
  setDatasetProfile: Dispatch<SetStateAction<'public_data' | 'records'>>;
  structuredInput: boolean;
  recordPath: string;
  setRecordPath: Dispatch<SetStateAction<string>>;
  needsFieldNames: boolean;
  csvEncoding: string;
  setCsvEncoding: Dispatch<SetStateAction<string>>;
  fieldNames: FieldNamesResponse | null;
  setFieldNames: Dispatch<SetStateAction<FieldNamesResponse | null>>;
  sheetName: string;
  setSheetName: Dispatch<SetStateAction<string>>;
  isSuggestingNames: boolean;
  setNameRequestVersion: Dispatch<SetStateAction<number>>;
  nameError: string | null;
  setNamesConfirmed: Dispatch<SetStateAction<boolean>>;
  namesConfirmed: boolean;
  validFieldNames: boolean;
  handleConvert: () => void;
}

/** 변환할 원본과 출력 형식을 설정함 */
export const ConverterSetupStep: React.FC<ConverterSetupStepProps> = ({
  selectedFile,
  fileCategory,
  targetFormat,
  setTargetFormat,
  tableName,
  setTableName,
  isConverting,
  imagePreviewUrl,
  fileExt,
  showWordDocumentOption,
  showHwpxDocumentOption,
  showHwpDocumentOption,
  handleReset,
  usesPublicData,
  datasetProfile,
  setDatasetProfile,
  structuredInput,
  recordPath,
  setRecordPath,
  needsFieldNames,
  csvEncoding,
  setCsvEncoding,
  fieldNames,
  setFieldNames,
  sheetName,
  setSheetName,
  isSuggestingNames,
  setNameRequestVersion,
  nameError,
  setNamesConfirmed,
  namesConfirmed,
  validFieldNames,
  handleConvert,
}) => (
    <div className="bg-surface border border-subtle rounded-2xl p-6 sm:p-8 space-y-6 shadow-sm">
      {/* Selected File Card */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-xl bg-surface-muted border border-subtle">
        <div className="flex items-center gap-3 min-w-0">
          <div
            className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${
              fileCategory === 'image'
                ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
                : fileCategory === 'document'
                ? 'bg-accent-subtle text-accent'
                : 'bg-blue-500/10 text-blue-600 dark:text-blue-400'
            }`}
          >
            {fileCategory === 'image' ? (
              <ImageIcon className="w-5 h-5" />
            ) : fileCategory === 'document' ? (
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
              <span
                className={`font-semibold uppercase ${
                  fileCategory === 'image'
                    ? 'text-emerald-600 dark:text-emerald-400'
                    : 'text-accent'
                }`}
              >
                {fileExt}{' '}
                {fileCategory === 'image'
                  ? '스캔/이미지 문서 (고정밀 OCR 엔진 가동)'
                  : fileCategory === 'document'
                  ? '사내 문서'
                  : '정형 데이터'}
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

      {/* If Image: Visual Thumbnail Preview & OCR Specs Panel */}
      {fileCategory === 'image' && (
        <div className="p-4 sm:p-5 rounded-2xl border border-emerald-500/20 bg-emerald-500/5 space-y-4">
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
            {imagePreviewUrl && (
              <div className="relative group shrink-0">
                <img
                  src={imagePreviewUrl}
                  alt="Uploaded Scan Preview"
                  className="w-24 h-24 sm:w-28 sm:h-28 object-cover rounded-xl border border-emerald-500/30 shadow-xs bg-white"
                />
                <div className="absolute inset-0 bg-black/40 rounded-xl opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity">
                  <a
                    href={imagePreviewUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="text-[11px] font-bold text-white bg-black/60 px-2 py-1 rounded-md flex items-center gap-1"
                  >
                    <Maximize2 className="w-3 h-3" />
                    원본 확대
                  </a>
                </div>
              </div>
            )}
            <div className="space-y-1.5 flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-emerald-700 dark:text-emerald-300 flex items-center gap-1.5">
                  <ScanLine className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                  고정밀 로컬 하이브리드 OCR 파이프라인 가동
                </span>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-700 dark:text-emerald-300">
                  ONNX 가속
                </span>
              </div>
              <p className="text-xs text-fg-muted leading-relaxed">
                RapidOCR(고속 ONNX 추론) 및 EasyOCR 하이브리드 앙상블로 한글·영문 문자를 판독하고, OpenCV 모폴로지 표 격자 검출 알고리즘으로 스캔 문서 내의 표와 서식을 1:1 디지털 구조로 복원합니다.
              </p>
              <div className="flex flex-wrap gap-2 pt-1 text-[11px]">
                <span className="px-2.5 py-1 rounded-lg bg-surface border border-subtle text-fg font-medium flex items-center gap-1.5 shadow-2xs">
                  <Check className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                  <span>기울기 자동 보정 (±0.1° Deskew)</span>
                </span>
                <span className="px-2.5 py-1 rounded-lg bg-surface border border-subtle text-fg font-medium flex items-center gap-1.5 shadow-2xs">
                  <Check className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                  <span>표 격자(Table Grid) 자동 복원</span>
                </span>
                <span className="px-2.5 py-1 rounded-lg bg-surface border border-subtle text-fg font-medium flex items-center gap-1.5 shadow-2xs">
                  <Check className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                  <span>한국어·영어 CJK 최적화</span>
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Target Format Selector */}
      <div className="space-y-3">
        <label className="block text-xs font-bold text-fg uppercase tracking-wider">
          변환 대상 포맷 선택
        </label>

        {/* If Image (OCR Targets) */}
        {fileCategory === 'image' && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {/* Markdown */}
            <button
              type="button"
              onClick={() => setTargetFormat('md')}
              className={`p-4 rounded-xl border text-left transition-all ${
                targetFormat === 'md'
                  ? 'border-emerald-500 bg-emerald-500/10 ring-2 ring-emerald-500/30 shadow-sm'
                  : 'border-subtle hover:border-emerald-500/50 bg-surface'
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="font-bold text-sm text-fg">마크다운 (.md)</span>
                <span className="text-2xs font-bold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                  추천 · LLM/RAG
                </span>
              </div>
              <p className="text-xs text-fg-muted">
                OCR 인식 본문 문단과 검출된 표를 마크다운으로 변환합니다. 결과 미리보기에서 인식 내용을 확인할 수 있습니다.
              </p>
            </button>

            {/* HTML Web Document */}
            <button
              type="button"
              onClick={() => setTargetFormat('html')}
              className={`p-4 rounded-xl border text-left transition-all ${
                targetFormat === 'html'
                  ? 'border-emerald-500 bg-emerald-500/10 ring-2 ring-emerald-500/30 shadow-sm'
                  : 'border-subtle hover:border-emerald-500/50 bg-surface'
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="font-bold text-sm text-fg">HTML 웹 문서 (.html)</span>
                <span className="text-2xs font-bold px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-600 dark:text-indigo-400">
                  반응형 웹 · 브라우저 열람
                </span>
              </div>
              <p className="text-xs text-fg-muted">
                스캔 이미지의 원본 레이아웃, 글꼴 크기 계층 및 표 스타일을 보존한 반응형 단독 실행형 웹 문서
              </p>
            </button>

            {/* Word Document */}
            <button
              type="button"
              onClick={() => setTargetFormat('docx')}
              className={`p-4 rounded-xl border text-left transition-all ${
                targetFormat === 'docx'
                  ? 'border-emerald-500 bg-emerald-500/10 ring-2 ring-emerald-500/30 shadow-sm'
                  : 'border-subtle hover:border-emerald-500/50 bg-surface'
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="font-bold text-sm text-fg">Word 문서 (.docx)</span>
                <span className="text-2xs font-bold px-2 py-0.5 rounded bg-blue-500/10 text-blue-600 dark:text-blue-400">
                  MS Word 편집
                </span>
              </div>
              <p className="text-xs text-fg-muted">
                OCR로 추출된 본문 텍스트와 표를 편집 가능한 MS Word(DOCX) 오피스 문서로 생성
              </p>
            </button>

            {/* PDF Document */}
            <button
              type="button"
              onClick={() => setTargetFormat('pdf')}
              className={`p-4 rounded-xl border text-left transition-all ${
                targetFormat === 'pdf'
                  ? 'border-emerald-500 bg-emerald-500/10 ring-2 ring-emerald-500/30 shadow-sm'
                  : 'border-subtle hover:border-emerald-500/50 bg-surface'
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="font-bold text-sm text-fg">PDF 문서 (.pdf)</span>
                <span className="text-2xs font-bold px-2 py-0.5 rounded bg-rose-500/10 text-rose-600 dark:text-rose-400">
                  인쇄 및 검색 가능
                </span>
              </div>
              <p className="text-xs text-fg-muted">
                스캔 이미지에 검색 가능한 투명 텍스트 레이어를 합성한 고해상도 Searchable PDF 변환
              </p>
            </button>

            {/* Pure Text TXT */}
            <button
              type="button"
              onClick={() => setTargetFormat('txt')}
              className={`p-4 rounded-xl border text-left transition-all ${
                targetFormat === 'txt'
                  ? 'border-emerald-500 bg-emerald-500/10 ring-2 ring-emerald-500/30 shadow-sm'
                  : 'border-subtle hover:border-emerald-500/50 bg-surface'
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="font-bold text-sm text-fg">텍스트 (.txt)</span>
                <span className="text-2xs font-bold px-2 py-0.5 rounded bg-amber-500/10 text-amber-600 dark:text-amber-400">
                  순수 텍스트
                </span>
              </div>
              <p className="text-xs text-fg-muted">
                서식 및 레이아웃을 제외하고 OCR로 판독된 순수 한글/영문 텍스트만 추출
              </p>
            </button>
          </div>
        )}

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
                제목, 본문 단락, 글머리 기호와 검출된 표를 마크다운으로 내보냅니다. 변환 결과는 미리보기에서 확인할 수 있습니다.
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
                한글·워드·PDF 문서에서 검출된 표를 행·열 구조로 Excel 시트에 내보냅니다. 병합 셀이나 스캔 표는 결과를 확인하세요.
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
                공공데이터 응답 구조(response/header/body/items) 또는 일반 레코드 배열
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
                공공데이터 응답 구조(response/body/items/item) 또는 일반 XML 레코드
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

      {usesPublicData && (
        <div className="ui-panel space-y-4">
          <h3 className="ui-section-title">응답 구조와 영문 변수명</h3>
          <label className="block space-y-2 text-sm">
            <span>출력 구조</span>
            <select className="ui-field" value={datasetProfile} disabled={isConverting}
              onChange={event => setDatasetProfile(event.target.value as 'public_data' | 'records')}>
              <option value="public_data">공공데이터 응답 구조 (청주시 CCTV 예시)</option>
              {!structuredInput && <option value="records">기존 일반 레코드 구조 (원천 컬럼명 유지)</option>}
            </select>
          </label>
          {structuredInput && datasetProfile === 'public_data' && (
            <div className="space-y-2">
              <p className="ui-help-text">청주시 CCTV 원본처럼 JSON은 response.body.items 배열, XML은 body/items/item 반복 요소로 변환합니다. body.items.item[2].필드 같은 경로형 컬럼으로 평탄화하지 않습니다. 기존 응답 헤더와 페이지 정보를 유지합니다.</p>
              <label className="block space-y-2 text-sm">
                <span>데이터 목록 경로 (자동 인식이 모호한 경우)</span>
                <input className="ui-field" value={recordPath} disabled={isConverting}
                  placeholder="예: /data/items 또는 /root/records/record"
                  onChange={event => setRecordPath(event.target.value)} />
              </label>
              <p className="ui-help-text">CSV의 중첩 셀은 JSON 텍스트로 저장됩니다. CSV만으로는 응답 헤더, 타입, null과 빈 문자열을 구분할 수 없으며 응답 정보는 별도 매핑 파일에 보존됩니다.</p>
            </div>
          )}
          {needsFieldNames && (
            <>
              <p className="ui-help-text">
                원천 컬럼명만 GPT-4o-mini에 보내 추천하며 데이터 값은 보내지 않습니다.
                추천명은 검토용 초안입니다. 직접 수정하고 확인한 이름을 JSON과 XML에 동일하게 적용합니다.
                이는 예시의 구조를 적용하는 것이며 국가 표준 인증이나 운영 API 계약을 생성하는 것이 아닙니다.
              </p>
              {fileExt === 'csv' && (
                <label className="block space-y-2 text-sm">
                  <span>CSV 인코딩</span>
                  <select className="ui-field" value={csvEncoding} disabled={isConverting}
                    onChange={event => setCsvEncoding(event.target.value)}>
                    <option value="utf-8">UTF-8</option><option value="cp949">CP949 (한글 Windows)</option>
                  </select>
                </label>
              )}
              {fieldNames && fieldNames.sheets.length > 0 && (
                <label className="block space-y-2 text-sm">
                  <span>변환할 엑셀 시트</span>
                  <select className="ui-field" value={sheetName || fieldNames.sheet_name || ''} disabled={isConverting}
                    onChange={event => setSheetName(event.target.value)}>
                    {fieldNames.sheets.map(sheet => <option key={sheet} value={sheet}>{sheet}</option>)}
                  </select>
                  <span className="ui-help-text block">선택한 시트만 변환합니다. 서로 다른 시트를 자동 합치지 않습니다.</span>
                </label>
              )}
              <div className="flex flex-wrap items-center justify-between gap-3">
                <span className="ui-help-text">
                  {isSuggestingNames ? '컬럼을 읽고 영문 변수명을 추천하는 중…' : fieldNames ? `${fieldNames.rows_count.toLocaleString()}행 · ${fieldNames.fields.length}컬럼` : '컬럼명 확인 필요'}
                </span>
                <button type="button" className="ui-button-secondary" disabled={isSuggestingNames || isConverting}
                  onClick={() => setNameRequestVersion(version => version + 1)}>
                  <Sparkles className="w-4 h-4" />영문명 다시 추천
                </button>
              </div>
              {nameError && <p className="ui-error" role="alert">{nameError}</p>}
              {fieldNames?.warning && <p className="ui-help-text" role="status">{fieldNames.warning}</p>}
              {fieldNames && (
                <div className="ui-table-shell">
                  <table className="ui-table">
                    <thead><tr><th>원천 컬럼명</th><th>적용할 영문 변수명</th><th>추천 상태·사유</th></tr></thead>
                    <tbody>{fieldNames.fields.map((field, index) => (
                      <tr key={field.original_name}>
                        <td>{field.original_name}</td>
                        <td><input className="ui-field font-mono min-w-44" value={field.english_name}
                          aria-label={`${field.original_name} 영문 변수명`} disabled={isConverting || isSuggestingNames}
                          onChange={event => {
                            const name = event.target.value;
                            setNamesConfirmed(false);
                            setFieldNames(current => current ? { ...current, fields: current.fields.map((entry, i) => i === index
                              ? { ...entry, english_name: name, status: 'REVIEW_REQUIRED', sourceType: 'USER_INPUT', confidence: null, reason: '사용자가 수정한 변수명 초안. 확인 후 적용.' }
                              : entry) } : current);
                          }} /></td>
                        <td><span className="font-mono">{field.status}</span><p>{field.reason}</p></td>
                      </tr>
                    ))}</tbody>
                  </table>
                </div>
              )}
              {fieldNames && !validFieldNames && <p className="ui-error" role="alert">
                영문자로 시작하는 영문·숫자·밑줄 1~64자로 입력하세요. xml 접두사와 중복 이름은 사용할 수 없습니다.
              </p>}
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={namesConfirmed} disabled={!validFieldNames || isSuggestingNames || isConverting}
                  onChange={event => setNamesConfirmed(event.target.checked)} />
                위 영문 변수명을 확인했습니다. 확인한 이름으로 변환합니다.
              </label>
              <p className="ui-help-text">실제 행 수를 totalCount와 numOfRows에 기록하고 pageNo=0인 단일 배포 묶음으로 생성합니다. 원천 데이터는 수정하지 않습니다.</p>
            </>
          )}
        </div>
      )}

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
          disabled={isConverting || (needsFieldNames && (isSuggestingNames || !validFieldNames || !namesConfirmed))}
          className={`px-8 py-3 text-sm font-bold shadow-md flex items-center gap-2 rounded-xl transition-all cursor-pointer ${
            fileCategory === 'image'
              ? 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-600/20'
              : 'ui-button-primary shadow-accent/20'
          }`}
        >
          {isConverting ? (
            <>
              <RefreshCw className="w-4 h-4 animate-spin" />
              <span>
                {fileCategory === 'image'
                  ? '고정밀 OCR 텍스트 인식 및 표 격자 복원 중...'
                  : targetFormat === 'md'
                  ? '문서 구조 분석 및 마크다운 변환 중...'
                  : fileCategory === 'document'
                  ? '문서 엔진 구동 및 변환 중...'
                  : '데이터셋 변환 및 압축 중...'}
              </span>
            </>
          ) : (
            <>
              {fileCategory === 'image' && <ScanLine className="w-4 h-4" />}
              <span>
                {fileCategory === 'image'
                  ? `스캔 이미지 OCR ${targetFormat.toUpperCase()} 변환 시작`
                  : `${targetFormat.toUpperCase()} 형식으로 변환하기`}
              </span>
              <ArrowRight className="w-4 h-4" />
            </>
          )}
        </button>
      </div>
      {isConverting && (fileCategory === 'document' || fileCategory === 'image') && (
        <div className={`rounded-xl border p-4 text-xs ${
          fileCategory === 'image'
            ? 'border-emerald-500/20 bg-emerald-500/5 text-fg-muted'
            : 'border-accent/20 bg-accent-subtle/40 text-fg-muted'
        }`}>
          <div className="flex items-center gap-2 font-bold text-fg">
            <RefreshCw className={`h-3.5 w-3.5 animate-spin ${fileCategory === 'image' ? 'text-emerald-500' : 'text-accent'}`} />
            <span>
              {fileCategory === 'image'
                ? '고정밀 로컬 하이브리드 OCR 엔진이 문자 및 표 격자를 인식하고 있습니다.'
                : '페이지 구조와 OCR 품질 정보를 계산하는 중입니다.'}
            </span>
          </div>
          <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-3">
            {(fileCategory === 'image'
              ? ['이미지 전처리 (기울기 보정)', '하이브리드 OCR 문자·표 인식', '타깃 문서 구조화 출력']
              : ['업로드 확인', '페이지 분석', '출력 파일 생성']
            ).map((stage, index) => (
              <div key={stage} className="rounded-lg border border-subtle bg-surface px-3 py-2">
                <div className="text-2xs font-bold text-fg-muted">단계 {index + 1}</div>
                <div className="mt-0.5 font-semibold text-fg">{stage}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
);
