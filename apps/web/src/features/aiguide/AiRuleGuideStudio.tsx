/**
 * 파일명: AiRuleGuideStudio.tsx
 * 경로: apps/web/src/features/aiguide/AiRuleGuideStudio.tsx
 * 목적: CSV(파일데이터), JSON·XML(API데이터)를 기반으로 공공 AI 친화도 표준 평가,
 *       대량 데이터 파이프라인 최적화 및 HWPX 문서 변환 롤 가이드를 제작·관리함
 * 작성자: 개발팀
 * 작성일: 2026-09-16
 * 수정일: 2026-09-16
 */
import React, { useState, useMemo, useEffect } from 'react';
import {
  Sparkles, Upload, FileText, CheckCircle2, ChevronRight,
  Download, Copy, RefreshCw, Layers, Table, Sliders,
  Eye, Code2, ArrowLeft, ArrowRight, Check, AlertTriangle,
  Loader2, Bot, Zap, Globe, ShieldCheck, Database,
  Settings, SlidersHorizontal, CheckSquare
} from 'lucide-react';
import {
  generateAiRuleGuide, exportAiGuideTemplate, AiGuideFieldAnnotation,
  ReadinessCheckItem, parseGovDocument, exportParsedDocx, GovDocParseResult, ParsedSimpleTable
} from '../../services/api';
import { AiGuideTemplatePanel } from './AiGuideTemplatePanel';
import { UnifiedFileUploader } from '../shared/UnifiedFileUploader';
import * as XLSX from 'xlsx';
import Papa from 'papaparse';

export type SupportedFormat = 'csv' | 'tsv' | 'xlsx' | 'json' | 'jsonld' | 'xml' | 'docx' | 'hwpx';
export type DataCategory = 'file' | 'api';
export type AiProvider = 'gemini' | 'openai' | 'local';

export interface SamplePreviewData {
  format: string;
  sheetName?: string;
  headers: string[];
  rows: string[][];
  totalRows: number;
  totalCols: number;
}

export interface ColumnRule {
  key: string;
  label: string;
  inferredType: string;
  align: 'left' | 'center' | 'right';
  widthPercent: number;
  formatType: 'text' | 'number_comma' | 'date_standard' | 'badge';
  include: boolean;
  sampleValues: string[];
}

export interface DocumentStylePreset {
  id: string;
  name: string;
  description: string;
  headerBgColor: string;
  headerTextColor: string;
  headerFontWeight: 'bold' | 'semibold' | 'normal';
  bodyFontSizePt: number;
  headerFontSizePt: number;
  borderStyle: 'single' | 'double_header' | 'light_gray';
}

interface AiRuleGuideStudioProps {
  isDarkMode: boolean;
  onStepChange?: (step: number) => void;
  activeStep?: number;
  onSelectStep?: (step: number) => void;
}

const STYLE_PRESETS: DocumentStylePreset[] = [
  {
    id: 'gov_standard',
    name: '행정안전부 공문서 표준 서식',
    description: '공공기관 공문서 서식 지침 준수, 헤더 회색 음영(#EAEAEA), 바탕글 10pt 표 서식임',
    headerBgColor: '#e5e7eb',
    headerTextColor: '#111827',
    headerFontWeight: 'bold',
    bodyFontSizePt: 10,
    headerFontSizePt: 10,
    borderStyle: 'single',
  },
  {
    id: 'mfds_deliberation',
    name: '식약처 심의·검토 보고서 양식',
    description: '식약처 기술심의 및 품질평가용 테이블, 헤더 이중 하단선 및 명확한 격자선 적용 서식임',
    headerBgColor: '#e0f2fe',
    headerTextColor: '#0369a1',
    headerFontWeight: 'bold',
    bodyFontSizePt: 9.5,
    headerFontSizePt: 9.5,
    borderStyle: 'double_header',
  },
  {
    id: 'stats_public',
    name: '공공데이터 통계 공시 양식',
    description: '수치 비교 및 집계 데이터 중심, 행 줄무늬 및 오른쪽 숫자 정렬 최적화 서식임',
    headerBgColor: '#f1f5f9',
    headerTextColor: '#334155',
    headerFontWeight: 'semibold',
    bodyFontSizePt: 9,
    headerFontSizePt: 9.5,
    borderStyle: 'light_gray',
  },
];

// 식약처 의약품 허가 대장 CSV 샘플 데이터(파일데이터)
const getSampleCsv = (): string => {
  return `품목기준코드,제품명,업체명,허가일자,전문일반구분,주성분
20240101,타이레놀정500mg,한국존슨앤드존슨,2024-01-15,일반의약품,아세트아미노펜
20240102,아모디핀정,한미약품,2024-02-01,전문의약품,캄실산암로디핀
20240103,글루코파지정,한국머크,2024-02-18,전문의약품,메트포르민염산염
20240104,베아제정,대웅제약,2024-03-05,일반의약품,판크레아틴
20240105,노바스크정,비아트리스코리아,2024-03-22,전문의약품,베실산암로디핀`;
};

// 건강기능식품 영양성분 공시 JSON 샘플 데이터(API데이터)
const getSampleJson = (): string => {
  return JSON.stringify([
    {
      "품목관리번호": "HF-2024-001",
      "제품명": "고함량 비타민C 1000",
      "영업소명": "식약건강산업",
      "신고일자": "2024-04-10",
      "1회분량": "1정(1,200mg)",
      "비타민C_mg": 1000,
      "열량_kcal": 5,
      "유통기한_개월": 24
    },
    {
      "품목관리번호": "HF-2024-002",
      "제품명": "프로바이오틱스 유산균",
      "영업소명": "바이오헬스케어",
      "신고일자": "2024-04-18",
      "1회분량": "1포(2,000mg)",
      "비타민C_mg": 50,
      "열량_kcal": 8,
      "유통기한_개월": 18
    },
    {
      "품목관리번호": "HF-2024-003",
      "제품명": "루테인 지아잔틴 복합제",
      "영업소명": "한국약업연구소",
      "신고일자": "2024-05-02",
      "1회분량": "1캡슐(500mg)",
      "비타민C_mg": 0,
      "열량_kcal": 4,
      "유통기한_개월": 24
    }
  ], null, 2);
};

// 공공보건의료 연계 XML 샘플 데이터(API데이터)
const getSampleXml = (): string => {
  return `<?xml version="1.0" encoding="UTF-8"?>
<response>
  <header>
    <resultCode>00</resultCode>
    <resultMsg>NORMAL SERVICE</resultMsg>
  </header>
  <body>
    <items>
      <item>
        <기관코드>JD001</기관코드>
        <기관명>국립중앙의료원</기관명>
        <종별구분>종합병원</종별구분>
        <소재지>서울특별시 중구</소재지>
        <병상수>505</병상수>
        <응급의료기관지정>권역응급의료센터</응급의료기관지정>
      </item>
      <item>
        <기관코드>JD002</기관코드>
        <기관명>충남대학교병원</기관명>
        <종별구분>상급종합병원</종별구분>
        <소재지>대전광역시 중구</소재지>
        <병상수>1300</병상수>
        <응급의료기관지정>권역응급의료센터</응급의료기관지정>
      </item>
      <item>
        <기관코드>JD003</기관코드>
        <기관명>부산대학교병원</기관명>
        <종별구분>상급종합병원</종별구분>
        <소재지>부산광역시 서구</소재지>
        <병상수>1186</병상수>
        <응급의료기관지정>권역외상센터</응급의료기관지정>
      </item>
    </items>
    <totalCount>3</totalCount>
  </body>
</response>`;
};

// CSV 원문 텍스트를 분석하여 행 및 컬럼 구조를 반환함
function parseCsvPayload(raw: string): { columns: string[]; rows: Record<string, string>[] } {
  const lines = raw.trim().split(/\r?\n/).filter(line => line.trim().length > 0);
  if (lines.length === 0) return { columns: [], rows: [] };
  const delimiter = lines[0].includes('\t') ? '\t' : ',';
  const headers = lines[0].split(delimiter).map(h => h.trim().replace(/^["']|["']$/g, ''));
  const rows: Record<string, string>[] = [];
  for (let i = 1; i < lines.length; i++) {
    const values = lines[i].split(delimiter).map(v => v.trim().replace(/^["']|["']$/g, ''));
    const rowObj: Record<string, string> = {};
    headers.forEach((h, idx) => {
      rowObj[h] = values[idx] || '';
    });
    rows.push(rowObj);
  }
  return { columns: headers, rows };
}

// 컬럼 값들의 분포를 보고 적절한 데이터 타입과 정렬을 추론함
function inferRuleProperties(key: string, sampleValues: string[]): {
  inferredType: string;
  align: 'left' | 'center' | 'right';
  formatType: 'text' | 'number_comma' | 'date_standard' | 'badge';
} {
  const nonEmpties = sampleValues.filter(v => v.trim().length > 0);
  if (nonEmpties.length === 0) {
    return { inferredType: 'string', align: 'left', formatType: 'text' };
  }

  const isNumeric = nonEmpties.every(v => {
    const clean = v.replace(/,/g, '').trim();
    return !isNaN(Number(clean)) && clean.length > 0;
  });
  if (isNumeric) {
    if (key.includes('코드') || key.includes('번호') || key.includes('연번') || key.includes('id')) {
      return { inferredType: 'string', align: 'center', formatType: 'text' };
    }
    return { inferredType: 'number', align: 'right', formatType: 'number_comma' };
  }

  const isDate = nonEmpties.every(v => /^\d{4}[-./]\d{1,2}[-./]\d{1,2}$/.test(v.trim()));
  if (isDate || key.includes('일자') || key.includes('일시') || key.includes('날짜')) {
    return { inferredType: 'date', align: 'center', formatType: 'date_standard' };
  }

  if (key.includes('구분') || key.includes('유형') || key.includes('상태') || key.includes('등급')) {
    return { inferredType: 'string', align: 'center', formatType: 'badge' };
  }

  return { inferredType: 'string', align: 'left', formatType: 'text' };
}

export const AiRuleGuideStudio: React.FC<AiRuleGuideStudioProps> = ({
  isDarkMode,
  onStepChange,
  activeStep: controlledStep,
  onSelectStep,
}) => {
  // 단계 관리 (1: 업로드 & 감지, 2: AI 친화도 진단 & 스키마, 3: 서식 롤 상세, 4: 가이드 내보내기)
  const [internalStep, setInternalStep] = useState<number>(1);
  const currentStep = controlledStep !== undefined ? controlledStep : internalStep;

  const handleStepTransition = (nextStep: number) => {
    if (onSelectStep) onSelectStep(nextStep);
    if (onStepChange) onStepChange(nextStep);
    setInternalStep(nextStep);
  };

  // 데이터 입력 및 포맷 상태
  const [inputFormat, setInputFormat] = useState<SupportedFormat>('csv');
  const [dataCategory, setDataCategory] = useState<DataCategory>('file');
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [rawText, setRawText] = useState<string>('');
  const [documentTitle, setDocumentTitle] = useState<string>('식약처 의약품 품목허가 표준 공시서');
  const [errorNotice, setErrorNotice] = useState<string | null>(null);
  const [samplePreview, setSamplePreview] = useState<SamplePreviewData | null>(null);

  // 대량 데이터 관련 상태
  const [isLargeDataset, setIsLargeDataset] = useState<boolean>(false);
  const [fileSizeBytes, setFileSizeBytes] = useState<number>(0);
  const [estimatedTotalRows, setEstimatedTotalRows] = useState<number>(0);

  // 파싱 결과 상태
  const [parsedData, setParsedData] = useState<{ columns: string[]; rows: Record<string, string>[] }>(() =>
    parseCsvPayload(getSampleCsv())
  );

  // HWPX 룰 설정 상태
  const [rules, setRules] = useState<ColumnRule[]>(() => {
    const init = parseCsvPayload(getSampleCsv());
    const totalCols = init.columns.length || 1;
    const baseWidth = Math.floor(100 / totalCols);
    return init.columns.map(col => {
      const samples = init.rows.map(r => r[col] || '').slice(0, 5);
      const inferred = inferRuleProperties(col, samples);
      return {
        key: col,
        label: col,
        inferredType: inferred.inferredType,
        align: inferred.align,
        widthPercent: baseWidth,
        formatType: inferred.formatType,
        include: true,
        sampleValues: samples,
      };
    });
  });

  // 서식 프리셋 및 문서 옵션
  const [selectedPresetId, setSelectedPresetId] = useState<string>('gov_standard');
  const [orientation, setOrientation] = useState<'portrait' | 'landscape'>('landscape');
  const [repeatHeader, setRepeatHeader] = useState<boolean>(true);
  const [showRowNumber, setShowRowNumber] = useState<boolean>(true);
  const [previewSubTab, setPreviewSubTab] = useState<'hwpx_render' | 'ai_guide' | 'json_ld' | 'quality_report' | 'large_data' | 'json' | 'xml' | 'parsed_tables'>('hwpx_render');
  const [copySuccess, setCopySuccess] = useState<boolean>(false);

  // AI 친화도 및 에이전트 연동 상태
  const [isAiLoading, setIsAiLoading] = useState<boolean>(false);
  const [isAiPowered, setIsAiPowered] = useState<boolean>(false);
  const [aiSummary, setAiSummary] = useState<string>('');
  const [aiReadinessScore, setAiReadinessScore] = useState<number>(0);
  const [aiReadinessChecklist, setAiReadinessChecklist] = useState<ReadinessCheckItem[]>([]);
  const [largeDataGuide, setLargeDataGuide] = useState<string | null>(null);
  const [customMarkdownGuide, setCustomMarkdownGuide] = useState<string | null>(null);
  const [customJsonRule, setCustomJsonRule] = useState<string | null>(null);

  const [fileBase64, setFileBase64] = useState<string | undefined>();
  const [canonicalMetadata, setCanonicalMetadata] = useState<Record<string, unknown> | null>(null);
  const [templateMetadata, setTemplateMetadata] = useState<Record<string, string>>({});
  const [fieldAnnotations, setFieldAnnotations] = useState<Record<string, AiGuideFieldAnnotation>>({});
  const [isExportingTemplate, setIsExportingTemplate] = useState(false);
  const [isExportingDocx, setIsExportingDocx] = useState(false);
  const [docParseResult, setDocParseResult] = useState<GovDocParseResult | null>(null);
  const [metadataXml, setMetadataXml] = useState('');
  const [serverJsonLd, setServerJsonLd] = useState('');


  // 현재 선택된 서식 프리셋 객체
  const currentPreset = useMemo(() => {
    return STYLE_PRESETS.find(p => p.id === selectedPresetId) || STYLE_PRESETS[0];
  }, [selectedPresetId]);

  // 분석 실행 핸들러
  const handleParseData = async (
    textToParse: string,
    format: SupportedFormat,
    category: DataCategory,
    useAiAgent: boolean = true,
    titleOverride?: string
  ) => {
    setErrorNotice(null);
    setCustomMarkdownGuide(null); setCustomJsonRule(null); setServerJsonLd(''); setMetadataXml('');
    setCanonicalMetadata(null);
    setIsAiLoading(true);
    try {
      const aiRes = await generateAiRuleGuide({
        payload_text: format === 'xlsx' ? '' : textToParse,
        file_base64: format === 'xlsx' ? fileBase64 : undefined,
        format,
        data_category: category,
        preset_style: selectedPresetId,
        document_title: titleOverride ?? documentTitle,
        orientation,
        is_large_dataset: isLargeDataset,
        file_size_bytes: fileSizeBytes,
        provider: useAiAgent ? 'auto' : 'local',
      });
      setCanonicalMetadata(aiRes.canonical_metadata);
      setRules(aiRes.columns);
      setParsedData({columns: aiRes.columns.map(c => c.key), rows: [0,1,2].map(i => Object.fromEntries(aiRes.columns.map(c => [c.key, c.sampleValues[i] ?? ''])))});
      setDataCategory(aiRes.data_category ?? category);
      setIsAiPowered(aiRes.ai_powered); setAiSummary(aiRes.ai_summary);
      setAiReadinessScore(aiRes.ai_readiness_score ?? 0);
      setAiReadinessChecklist(aiRes.ai_readiness_checklist ?? []);
      setLargeDataGuide(aiRes.large_data_guide ?? null);
      setCustomMarkdownGuide(aiRes.markdown_guide); setCustomJsonRule(aiRes.json_rule);
      setServerJsonLd(aiRes.json_ld); setMetadataXml(aiRes.metadata_xml);
      handleStepTransition(2);
    } catch (err) {
      setErrorNotice(err instanceof Error ? err.message : '분석 실패');
    } finally { setIsAiLoading(false); }
  };
  // 공공 샘플 데이터 즉시 로드 핸들러
  const handleLoadSample = (type: SupportedFormat) => {
    setCanonicalMetadata(null); setTemplateMetadata({}); setFieldAnnotations({});
    setFileBase64(undefined); setIsLargeDataset(false);
    setInputFormat(type);
    const cat: DataCategory = type === 'csv' ? 'file' : 'api';
    setDataCategory(cat);
    setIsLargeDataset(false);
    setFileSizeBytes(type === 'csv' ? 1024 : 2048);
    setEstimatedTotalRows(type === 'csv' ? 5 : 3);

    let sample = '';
    let title = '';
    if (type === 'csv') {
      sample = getSampleCsv();
      title = '식약처 의약품 품목허가 표준 공시서';
      const parsed = Papa.parse<string[]>(sample, { skipEmptyLines: 'greedy' });
      if (parsed.data && parsed.data.length > 0) {
        setSamplePreview({
          format: 'csv',
          headers: parsed.data[0] || [],
          rows: parsed.data.slice(1, 8),
          totalRows: parsed.data.length - 1,
          totalCols: (parsed.data[0] || []).length,
        });
      }
    } else if (type === 'json') {
      sample = getSampleJson();
      title = '건강기능식품 영양성분 공시 보고서';
      try {
        const j = JSON.parse(sample);
        const arr = Array.isArray(j) ? j : [j];
        const headers = Object.keys(arr[0] || {});
        setSamplePreview({
          format: 'json',
          headers,
          rows: arr.slice(0, 7).map(item => headers.map(k => String(item[k] ?? ''))),
          totalRows: arr.length,
          totalCols: headers.length,
        });
      } catch { /* ignore */ }
    } else {
      sample = getSampleXml();
      title = '공공보건의료기관 현황 연계 명세서';
      try {
        const xmlDoc = new DOMParser().parseFromString(sample, 'text/xml');
        const items = xmlDoc.querySelectorAll('item, row, record');
        if (items.length > 0) {
          const headers = Array.from(items[0].children).map(c => c.tagName);
          setSamplePreview({
            format: 'xml',
            headers,
            rows: Array.from(items).slice(0, 7).map(it => headers.map(h => it.querySelector(h)?.textContent || '')),
            totalRows: items.length,
            totalCols: headers.length,
          });
        }
      } catch { /* ignore */ }
    }
    setUploadedFile(new File([sample], `${title}.${type}`, { type: 'text/plain' }));
    setRawText(sample);
    setDocumentTitle(title);
    handleParseData(sample, type, cat, false, title);
  };

  // 파일 선택 및 데이터 샘플 무손실 미리보기 파싱 핸들러 (XLSX, CSV, TSV, JSON, XML 글자 깨짐 0%)
  const handleFileSelect = async (file: File) => {
    setCanonicalMetadata(null);
    setTemplateMetadata({});
    setFieldAnnotations({});
    setUploadedFile(file);
    setErrorNotice(null);
    setSamplePreview(null);

    const ext = file.name.split('.').pop()?.toLowerCase() || '';
    if (!['csv', 'tsv', 'xlsx', 'xls', 'json', 'jsonld', 'xml', 'docx', 'hwpx'].includes(ext)) {
      setErrorNotice('CSV, TSV, XLSX, JSON, JSON-LD, XML, DOCX, HWPX 파일을 선택하세요.');
      return;
    }
    if (file.size > 32 * 1024 * 1024) {
      setErrorNotice('32 MiB 이하의 유효한 파일 단위로 분할하세요.');
      return;
    }

    const normFormat: SupportedFormat = (ext === 'xls' ? 'xlsx' : ext) as SupportedFormat;
    setCustomMarkdownGuide(null);
    setCustomJsonRule(null);
    setServerJsonLd('');
    setMetadataXml('');
    setFileBase64(undefined);
    setRawText('');
    setDocParseResult(null);
    setInputFormat(normFormat);
    setDataCategory(['json', 'jsonld', 'xml'].includes(normFormat) ? 'api' : 'file');
    setDocumentTitle(file.name.replace(/\.[^/.]+$/, ''));

    setFileSizeBytes(file.size);
    setIsLargeDataset(file.size > 2 * 1024 * 1024);

    try {
      if (normFormat === 'xlsx') {
        // 1. 엑셀 파일 (SheetJS로 시트 및 셀 내용 완벽 추출)
        const arrayBuf = await file.arrayBuffer();
        
        // base64 보관 (서버 openpyxl 분석용)
        const reader = new FileReader();
        reader.onload = () => {
          const res = String(reader.result || '');
          const b64 = res.split(',')[1];
          if (b64) setFileBase64(b64);
        };
        reader.readAsDataURL(file);

        const workbook = XLSX.read(arrayBuf, { type: 'array', cellDates: true });
        const sheetName = workbook.SheetNames[0] || 'Sheet1';
        const worksheet = workbook.Sheets[sheetName];
        const rows = XLSX.utils.sheet_to_json<any[]>(worksheet, { header: 1, defval: '' });

        if (rows && rows.length > 0) {
          const rawHeaders = (rows[0] || []).map(h => String(h ?? '').trim());
          const headers = rawHeaders.length > 0 ? rawHeaders : ['열1', '열2', '열3'];
          const sampleRows = rows.slice(1, 8).map(r => headers.map((_, i) => String(r[i] ?? '')));

          setSamplePreview({
            format: 'xlsx',
            sheetName,
            headers,
            rows: sampleRows,
            totalRows: Math.max(0, rows.length - 1),
            totalCols: headers.length,
          });
          setEstimatedTotalRows(Math.max(1, rows.length - 1));

          // 엑셀 시트를 표준 CSV 텍스트로 변환하여 payload_text로 활용
          const csvContent = XLSX.utils.sheet_to_csv(worksheet);
          setRawText(csvContent);
        } else {
          setRawText('엑셀 시트에 데이터가 비어 있습니다.');
        }
      } else if (normFormat === 'csv' || normFormat === 'tsv') {
        // 2. CSV / TSV 파일 (PapaParse로 정밀 파싱)
        const text = await file.text();
        const parsed = Papa.parse<string[]>(text, {
          delimiter: normFormat === 'tsv' ? '\t' : undefined,
          skipEmptyLines: 'greedy',
        });
        if (parsed.data && parsed.data.length > 0) {
          const headers = (parsed.data[0] || []).map(h => String(h ?? '').trim());
          const sampleRows = parsed.data.slice(1, 8).map(r => headers.map((_, i) => String(r[i] ?? '')));
          setSamplePreview({
            format: normFormat,
            headers,
            rows: sampleRows,
            totalRows: Math.max(0, parsed.data.length - 1),
            totalCols: headers.length,
          });
          setEstimatedTotalRows(Math.max(1, parsed.data.length - 1));
        }
        setRawText(text);
      } else if (normFormat === 'json' || normFormat === 'jsonld') {
        // 3. JSON / JSON-LD 파일
        const text = await file.text();
        try {
          const parsed = JSON.parse(text);
          const list = Array.isArray(parsed) ? parsed : (parsed.data || parsed.items || parsed.records || [parsed]);
          if (Array.isArray(list) && list.length > 0 && typeof list[0] === 'object' && list[0] !== null) {
            const headers = Object.keys(list[0]);
            const sampleRows = list.slice(0, 7).map(item => headers.map(k => String(item[k] ?? '')));
            setSamplePreview({
              format: normFormat,
              headers,
              rows: sampleRows,
              totalRows: list.length,
              totalCols: headers.length,
            });
            setEstimatedTotalRows(list.length);
          } else {
            const keys = Object.keys(parsed);
            setSamplePreview({
              format: normFormat,
              headers: ['속성(Key)', '값(Value)'],
              rows: keys.slice(0, 7).map(k => [k, typeof parsed[k] === 'object' ? JSON.stringify(parsed[k]) : String(parsed[k] ?? '')]),
              totalRows: keys.length,
              totalCols: 2,
            });
            setEstimatedTotalRows(keys.length);
          }
          setRawText(JSON.stringify(parsed, null, 2));
        } catch {
          setRawText(text);
        }
      } else if (normFormat === 'xml') {
        // 4. XML 파일 (백엔드 표 파서 및 로컬 DOMParser 연동)
        const text = await file.text();
        setRawText(text);
        try {
          const docRes = await parseGovDocument({
            text_content: text,
            format: 'xml',
            filename: file.name,
          });
          setDocParseResult(docRes.data);
          const grid = docRes.data.payload_data_tables.find(t => t.category === 'data_grid')
            || docRes.data.payload_data_tables[0];
          if (grid && grid.headers.length > 0) {
            setSamplePreview({
              format: 'xml',
              headers: grid.headers,
              rows: grid.rows.slice(0, 7),
              totalRows: grid.rows.length,
              totalCols: grid.headers.length,
            });
            setEstimatedTotalRows(grid.rows.length);
          }
        } catch {
          // DOMParser fallback
          const xmlDoc = new DOMParser().parseFromString(text, 'text/xml');
          const records = xmlDoc.querySelectorAll('item, row, record, data, entry');
          if (records.length > 0) {
            const first = records[0];
            const headers = Array.from(first.children).map(c => c.tagName);
            const sampleRows = Array.from(records).slice(0, 7).map(rec => {
              return headers.map(h => rec.querySelector(h)?.textContent || '');
            });
            setSamplePreview({
              format: 'xml',
              headers,
              rows: sampleRows,
              totalRows: records.length,
              totalCols: headers.length,
            });
            setEstimatedTotalRows(records.length);
          }
        }
      } else if (normFormat === 'docx' || normFormat === 'hwpx') {
        // 5. DOCX / HWPX 공공 기술검토 문서 파싱 (XML/JSON 응답 및 표 자동 추출)
        const reader = new FileReader();
        reader.onload = async () => {
          const res = String(reader.result || '');
          const b64 = res.split(',')[1];
          if (b64) {
            setFileBase64(b64);
            try {
              const docRes = await parseGovDocument({
                file_base64: b64,
                format: normFormat,
                filename: file.name,
              });
              setDocParseResult(docRes.data);
              setDocumentTitle(docRes.data.title || file.name.replace(/\.[^/.]+$/, ''));
              setCustomMarkdownGuide(docRes.markdown);

              const primaryTable = docRes.data.payload_data_tables.find(t => t.category === 'data_grid')
                || docRes.data.payload_data_tables[0]
                || docRes.data.parameter_tables[0]
                || docRes.data.overview_tables[0];

              if (primaryTable && primaryTable.headers.length > 0) {
                setSamplePreview({
                  format: normFormat,
                  headers: primaryTable.headers,
                  rows: primaryTable.rows.slice(0, 7),
                  totalRows: primaryTable.rows.length,
                  totalCols: primaryTable.headers.length,
                });
                setEstimatedTotalRows(primaryTable.rows.length);

                const totalCols = primaryTable.headers.length || 1;
                const baseWidth = Math.floor(100 / totalCols);
                setRules(primaryTable.headers.map(col => ({
                  key: col,
                  label: col,
                  inferredType: 'string',
                  align: 'left',
                  widthPercent: baseWidth,
                  formatType: 'text',
                  include: true,
                  sampleValues: primaryTable.rows.map(r => r[primaryTable.headers.indexOf(col)] || '').slice(0, 5),
                })));
              }
            } catch (err) {
              setErrorNotice(err instanceof Error ? err.message : '공문서 표 파싱 실패');
            }
          }
        };
        reader.readAsDataURL(file);
      }

    } catch (err: any) {
      setErrorNotice(`파일 분석 중 오류가 발생했습니다: ${err?.message || err}`);
    }
  };

  // 특정 컬럼의 룰 프로퍼티를 갱신함
  const handleUpdateRule = (index: number, partial: Partial<ColumnRule>) => {
    setRules(prev => {
      const copy = [...prev];
      copy[index] = { ...copy[index], ...partial };
      return copy;
    });
  };

  // 생성된 AI 친화 가이드 마크다운 전문
  const generatedMarkdownGuide = useMemo(() => {
    if (customMarkdownGuide) {
      return customMarkdownGuide;
    }
    const activeCols = rules.filter(r => r.include);
    let md = `# [AI 친화 가이드] ${documentTitle}\n\n`;
    md += `## 1. 데이터 개요 및 AI 친화도 진단\n`;
    md += `- **데이터 범주**: ${dataCategory === 'file' ? '[파일] 파일데이터 (CSV/TSV)' : '[API] API 데이터 (JSON/XML)'}\n`;
    md += `- **관측 값 완전성**: ${aiReadinessScore}점 / 100점\n`;
    md += `- **문서 양식 프리셋**: ${currentPreset.name}\n`;
    md += `- **용지 방향**: ${orientation === 'landscape' ? '가로 (Landscape / A4)' : '세로 (Portrait / A4)'}\n`;
    md += `- **추정 레코드 수**: ${estimatedTotalRows.toLocaleString()}행 (용량: ${(fileSizeBytes / 1024).toFixed(1)} KB)\n\n`;

    if (largeDataGuide) {
      md += `${largeDataGuide}\n---\n\n`;
    }

    md += `## 2. 공문서 HWPX 표준 표(Table) 서식 롤\n\n`;
    md += `| 원본 필드 | 표시명 | 데이터형 | 정렬 | 너비 비율 | 출력 서식 |\n`;
    md += `| :--- | :--- | :---: | :---: | :---: | :--- |\n`;
    if (showRowNumber) {
      md += `| \`(시스템연번)\` | 연번 | number | center | 6% | 순번(1, 2, 3...) |\n`;
    }
    activeCols.forEach(col => {
      md += `| \`${col.key}\` | **${col.label}** | ${col.inferredType} | ${col.align} | ${col.widthPercent}% | ${col.formatType} |\n`;
    });

    md += `\n## 3. AI 친화도 점검 체크리스트\n\n`;
    aiReadinessChecklist.forEach(chk => {
      const icon = chk.status === 'pass' ? '✅' : chk.status === 'warn' ? '⚠️' : '❌';
      md += `- ${icon} **${chk.item}**: ${chk.message}\n`;
    });

    return md;
  }, [
    customMarkdownGuide, isAiPowered, documentTitle, dataCategory, aiReadinessScore,
    currentPreset, orientation, estimatedTotalRows, fileSizeBytes, largeDataGuide,
    showRowNumber, rules, aiReadinessChecklist
  ]);

  // AI-Ready 메타데이터 JSON-LD (DCAT 3.0 / DCT / RAI / DQV 표준) 자동 생성
  const generatedJsonLd = serverJsonLd || '{}';

  // 공공데이터 AI 품질평가 보고서 마크다운 생성
  const generatedQualityReport = `# 품질 관측 보고서
${documentTitle}
관측 값 완전성: ${aiReadinessScore}% (종합 적합도 점수가 아님)
${aiReadinessChecklist.map(c => `- ${c.item}: ${c.message}`).join('\n')}
개인정보·권리·정확성·편향: 기관 확인 필요`;


  // 클립보드 복사
  const handleCopyClipboard = (text: string) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 2000);
    });
  };

  // 파일 다운로드
  const handleDownloadFile = (content: string, filename: string, mimeType: string) => {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      {/* 2단계 이상일 때 상단 단계 네비게이션 및 이전/다음 버튼 */}
      {currentStep > 1 && (
        <div className="flex items-center justify-between p-3.5 rounded-xl bg-surface-muted border border-subtle">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-fg">
              {currentStep === 2 && '2단계: 데이터 자동 분석 (구조 경로·관측 타입·결측)'}
              {currentStep === 3 && '3단계: AI-Ready 메타데이터 검토 (DCAT/DCT/RAI 메타데이터 & HWPX 서식)'}
              {currentStep === 4 && '4단계: 가이드 생성 및 내보내기 (HWPX · JSON · JSON-LD · 품질보고서)'}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => handleStepTransition(currentStep - 1)}
              className="ui-button-secondary text-xs px-3 py-1.5 cursor-pointer flex items-center gap-1.5"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              이전 단계
            </button>
            {currentStep < 4 && (
              <button
                onClick={() => handleStepTransition(currentStep + 1)}
                className="ui-button-primary text-xs px-3.5 py-1.5 cursor-pointer flex items-center gap-1.5 font-bold"
              >
                {currentStep === 2 && '메타데이터 검토'}
                {currentStep === 3 && '가이드 생성·내보내기'}
                <ArrowRight className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
        </div>
      )}

      {/* 에러 발생 알림 */}
      {errorNotice && (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-xs text-rose-700 dark:text-rose-300 flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 shrink-0 text-rose-500" />
          <span>{errorNotice}</span>
        </div>
      )}

      {/* AI 친화도 종합 스코어카드 배너 (2단계 이상) */}
      {currentStep > 1 && (
        <div className="ui-panel p-5 space-y-4 border-l-4 border-l-accent">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-2xl bg-accent/10 text-accent flex items-center justify-center shrink-0">
                <ShieldCheck className="w-6 h-6" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-base font-black text-fg">AI 친화도 표준 평가 결과</h3>
                  <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full whitespace-nowrap ${
                    dataCategory === 'file'
                      ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300'
                      : 'bg-sky-500/15 text-sky-700 dark:text-sky-300'
                  }`}>
                    {dataCategory === 'file' ? '[파일] 파일데이터 모드 (XLSX/CSV/TSV)' : '[API] API 데이터 모드 (JSON/JSON-LD/XML)'}
                  </span>
                  {isLargeDataset && (
                    <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-700 dark:text-amber-300 flex items-center gap-1">
                      <Zap className="w-3 h-3" />
                      대용량 최적화
                    </span>
                  )}
                </div>
                <p className="text-xs text-fg-muted mt-0.5">
                  행정안전부·NIA 공공데이터 AI 친화도 가이드라인 및 HWPX 공문서 서식 지침 기준 평가
                </p>
              </div>
            </div>

            <div className="flex items-center gap-4 self-end sm:self-auto bg-surface-muted px-4 py-2 rounded-xl border border-subtle">
              <div className="text-right">
                <div className="text-2xs text-fg-muted uppercase font-mono font-semibold">관측 값 완전성</div>
                <div className="text-2xl font-black text-accent">{aiReadinessScore} <span className="text-xs text-fg-muted font-normal">/ 100</span></div>
              </div>
              <div className="w-12 h-12 rounded-full border-4 border-accent/20 border-t-accent flex items-center justify-center font-black text-xs text-accent">
                {'관측'}
              </div>
            </div>
          </div>

          {/* 세부 점검 체크리스트 */}
          {aiReadinessChecklist.length > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-3 border-t border-subtle">
              {aiReadinessChecklist.map((chk, idx) => (
                <div key={idx} className="flex items-start gap-2 p-2 rounded-lg bg-surface-muted/50 text-xs">
                  {chk.status === 'pass' ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
                  ) : (
                    <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
                  )}
                  <div className="min-w-0">
                    <span className="font-bold text-fg">{chk.item}:</span>{' '}
                    <span className="text-fg-muted">{chk.message}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* 1단계: 단일 파일 업로드 및 포맷 자동 감지 뷰 */}
      {/* ========================================================================= */}
      {currentStep === 1 && (
        <div className="space-y-6">
          <div className="space-y-4">
            {!uploadedFile ? (
              <div className="space-y-4">
                <UnifiedFileUploader
                  title="AI 친화 가이드 생성을 위한 데이터 업로드"
                  subtitle="XLSX, CSV, TSV, JSON, XML 정형 데이터를 업로드하여 AI 친화도 표준 평가 및 HWPX 가이드를 생성하세요."
                  accept=".xlsx,.csv,.tsv,.json,.jsonld,.xml"
                  formatsHint="XLSX · CSV · TSV · JSON · JSON-LD · XML (최대 32 MiB)"
                  onFilesSelected={([file]) => {
                    if (file) handleFileSelect(file);
                  }}
                  onError={msg => setErrorNotice(msg)}
                />
              </div>
            ) : (
              <div className="ui-panel p-6 space-y-5">
                {/* 선택된 파일 정보 카드 */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-xl bg-surface-muted border border-subtle">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-12 h-12 rounded-xl bg-accent/10 text-accent flex items-center justify-center shrink-0">
                      {dataCategory === 'file' ? <FileText className="w-6 h-6" /> : <Globe className="w-6 h-6" />}
                    </div>
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <h4 className="text-sm font-bold text-fg truncate">{uploadedFile.name}</h4>
                        <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-accent/15 text-accent uppercase whitespace-nowrap">
                          {inputFormat}
                        </span>
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded whitespace-nowrap ${
                          dataCategory === 'file'
                            ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300'
                            : 'bg-sky-500/15 text-sky-700 dark:text-sky-300'
                        }`}>
                          {dataCategory === 'file' ? '[파일] 파일데이터 모드' : '[API] API 데이터 모드'}
                        </span>
                        {isLargeDataset && (
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-amber-500/15 text-amber-700 dark:text-amber-300 flex items-center gap-1">
                            <Zap className="w-3 h-3" />
                            대용량 스트리밍 모드
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-fg-muted mt-0.5">
                        용량: {(uploadedFile.size / 1024).toFixed(1)} KB · 추정 레코드: {estimatedTotalRows.toLocaleString()}행
                      </p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      setUploadedFile(null);
                      setRawText('');
                      setIsLargeDataset(false);
                    }}
                    className="ui-button-secondary text-xs px-3 py-1.5 shrink-0 cursor-pointer"
                  >
                    다른 파일 선택
                  </button>
                </div>

                {/* 대용량 데이터 감지 안내 배너 */}
                {isLargeDataset && (
                  <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-xs text-amber-900 dark:text-amber-200 flex items-start gap-2.5">
                    <Zap className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
                    <div>
                      <span className="font-bold">대용량 데이터 분석:</span> 브라우저 멈춤을 방지하기 위해 파일 전체를 서버에서 분석합니다. 분석 한도를 초과하면 유효한 레코드 단위로 분할해 주세요.
                    </div>
                  </div>
                )}

                {/* 정돈된 표 형태의 데이터 샘플 미리보기 (XLSX, CSV, TSV, JSON, XML 글자 깨짐 0%) */}
                {samplePreview ? (
                  <div className="space-y-2">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <Table className="w-4 h-4 text-accent" />
                        <span className="text-xs font-bold text-fg">데이터 샘플 미리보기</span>
                        {samplePreview.sheetName && (
                          <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-700 dark:text-emerald-300">
                            시트: {samplePreview.sheetName}
                          </span>
                        )}
                        <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-surface-muted text-fg-muted uppercase">
                          {samplePreview.format}
                        </span>
                      </div>
                      <span className="text-2xs text-fg-muted font-mono">
                        총 {samplePreview.totalCols}개 컬럼 · 상위 {samplePreview.rows.length}행 미리보기 (전체 약 {samplePreview.totalRows.toLocaleString()}행)
                      </span>
                    </div>

                    <div className="rounded-xl border border-subtle overflow-hidden bg-surface shadow-2xs">
                      <div className="overflow-x-auto max-h-72">
                        <table className="w-full text-left text-xs border-collapse font-mono">
                          <thead className="sticky top-0 bg-surface-muted border-b border-subtle z-10">
                            <tr>
                              <th className="py-2 px-3 text-2xs font-bold text-fg-muted uppercase w-12 text-center border-r border-subtle/50">
                                #
                              </th>
                              {samplePreview.headers.map((h, i) => (
                                <th key={i} className="py-2 px-3 text-xs font-bold text-fg whitespace-nowrap border-r border-subtle/50 last:border-r-0">
                                  {h || `열${i + 1}`}
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-subtle/60 text-fg">
                            {samplePreview.rows.map((row, rIdx) => (
                              <tr key={rIdx} className="hover:bg-surface-muted/40 transition-colors">
                                <td className="py-1.5 px-3 text-2xs text-fg-muted text-center bg-surface-muted/30 border-r border-subtle/50">
                                  {rIdx + 1}
                                </td>
                                {samplePreview.headers.map((_, cIdx) => (
                                  <td
                                    key={cIdx}
                                    className="py-1.5 px-3 text-xs whitespace-nowrap max-w-[260px] truncate border-r border-subtle/50 last:border-r-0"
                                    title={row[cIdx] || ''}
                                  >
                                    {row[cIdx] !== undefined && row[cIdx] !== '' ? (
                                      row[cIdx]
                                    ) : (
                                      <span className="text-fg-muted/40 italic">null</span>
                                    )}
                                  </td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </div>
                ) : rawText ? (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-fg">데이터 텍스트 샘플</span>
                      <span className="text-2xs text-fg-muted font-mono">{rawText.split('\n').length}행</span>
                    </div>
                    <pre className="p-3.5 rounded-xl bg-surface-muted/60 border border-subtle font-mono text-xs text-fg-muted overflow-x-auto max-h-56 whitespace-pre-wrap">
                      {rawText.slice(0, 1200)}
                      {rawText.length > 1200 && '\n... (이하 생략)'}
                    </pre>
                  </div>
                ) : null}

                {/* 문서 제목 및 행안부·NIA 표준 가이드라인 템플릿 고정 안내 */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4 border-t border-subtle">
                  <div>
                    <label className="text-xs font-bold text-fg block mb-1.5">문서 제목</label>
                    <input
                      type="text"
                      value={documentTitle}
                      onChange={e => setDocumentTitle(e.target.value)}
                      className="ui-input w-full text-xs font-medium"
                      placeholder="생성될 문서 제목을 입력하세요"
                    />
                  </div>
                  <div className="p-3 rounded-xl bg-surface-muted/70 border border-subtle flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2.5 min-w-0">
                      <div className="w-8 h-8 rounded-lg bg-accent/10 text-accent flex items-center justify-center shrink-0">
                        <ShieldCheck className="w-4 h-4" />
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center gap-1.5">
                          <span className="text-xs font-bold text-fg">행안부·NIA 표준 가이드라인 템플릿</span>
                          <span className="text-[10px] font-bold px-1.5 py-0.2 rounded bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 whitespace-nowrap">
                            규격 고정
                          </span>
                        </div>
                        <p className="text-2xs text-fg-muted truncate mt-0.5">
                          공문서 표준 HWPX 서식 및 A4 규격이 자동으로 적용됩니다.
                        </p>
                      </div>
                    </div>
                    <div
                      className="inline-flex items-center gap-1.5 text-2xs text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 px-2.5 py-1.5 rounded-lg border border-emerald-500/20 shrink-0 font-medium select-none"
                      title="서버 환경변수(.env) 기반 AI 엔진이 자동으로 적용됩니다."
                    >
                      <Bot className="w-3.5 h-3.5 text-emerald-500" />
                      <span>AI 엔진 활성화됨</span>
                    </div>
                  </div>
                </div>

                {/* 단일 통합 분석 실행 액션 버튼 */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-3 border-t border-subtle">
                  <div className="flex items-center gap-2">
                    {isAiLoading ? (
                      <div className="flex items-center gap-2 text-xs text-sky-600 dark:text-sky-400 font-medium">
                        <Loader2 className="h-4 w-4 animate-spin text-sky-500" />
                        <span>데이터 스키마와 AI 친화도 품질을 정밀 분석하는 중입니다...</span>
                      </div>
                    ) : (
                      <p className="text-xs text-fg-muted">
                        추측 금지 및 무환각 원칙에 따라 정밀 프로파일링 및 메타데이터를 자동 생성합니다.
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-2.5 justify-end">
                    <button
                      type="button"
                      disabled={isAiLoading || (!rawText.trim() && !samplePreview)}
                      onClick={() => handleParseData(rawText, inputFormat, dataCategory, true)}
                      className="ui-button-primary px-6 py-2.5 text-xs font-bold flex items-center gap-2 cursor-pointer shadow-sm disabled:opacity-50"
                    >
                      {isAiLoading ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Sparkles className="h-4 w-4" />
                      )}
                      <span>AI-Ready 데이터 자동 분석 시작</span>
                      <ArrowRight className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* 2단계: 데이터 구조 및 컬럼 스키마 확인 */}
      {/* ========================================================================= */}
      {currentStep === 2 && (
        <div className="space-y-6">
          <div className="ui-panel p-6 space-y-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-subtle pb-4">
              <div>
                <h3 className="text-sm font-bold text-fg">추출된 필드 스키마 및 데이터 자동 분석</h3>
                <p className="text-xs text-fg-muted mt-0.5">
                  총 {rules.length}개 필드의 구조 경로·관측 타입·결측을 분석했습니다. 불필요한 필드는 제외하거나 정렬/너비를 조정하세요.
                </p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => handleStepTransition(3)}
                  className="ui-button-primary px-4 py-2 text-xs font-bold flex items-center gap-1.5 cursor-pointer shadow-sm"
                >
                  메타데이터 검토
                  <ChevronRight className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>

            {/* 컬럼 목록 카드 그리드 */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {rules.map((rule, idx) => {
                const kLower = rule.key.toLowerCase();
                const isCandidate = kLower.includes('코드') || kLower.includes('번호') || kLower.includes('id') || kLower.includes('연번') || kLower.includes('seq') || kLower.includes('no');
                return (
                <div
                  key={rule.key}
                  className={`p-3.5 rounded-xl border transition-all ${
                    rule.include
                      ? 'bg-surface border-subtle shadow-2xs'
                      : 'bg-surface-muted/50 border-subtle/50 opacity-60'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 mb-2">
                    <div className="flex items-center gap-2 min-w-0">
                      <input
                        type="checkbox"
                        checked={rule.include}
                        onChange={e => handleUpdateRule(idx, { include: e.target.checked })}
                        className="rounded border-subtle text-accent focus:ring-accent"
                      />
                      <span className="font-mono text-xs font-bold text-fg truncate" title={rule.key}>
                        {rule.key}
                      </span>
                    </div>
                    <div className="flex items-center gap-1">
                      {isCandidate ? (
                        <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 whitespace-nowrap">
                          식별자 이름 후보 (미검증)
                        </span>
                      ) : (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface-muted text-fg-muted whitespace-nowrap">
                          일반 속성
                        </span>
                      )}
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-sky-500/10 text-sky-600 dark:text-sky-400 whitespace-nowrap">
                        통계는 가이드 참조
                      </span>
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-surface-muted text-fg-muted whitespace-nowrap">
                        {rule.inferredType}
                      </span>
                    </div>
                  </div>

                  <div className="space-y-2 text-xs">
                    <div>
                      <label className="text-2xs text-fg-muted block mb-0.5">표시 헤더명</label>
                      <input
                        type="text"
                        value={rule.label}
                        onChange={e => handleUpdateRule(idx, { label: e.target.value })}
                        className="ui-input w-full py-1 text-xs"
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="text-2xs text-fg-muted block mb-0.5">정렬</label>
                        <select
                          value={rule.align}
                          onChange={e => handleUpdateRule(idx, { align: e.target.value as any })}
                          className="ui-input w-full py-1 text-xs"
                        >
                          <option value="left">왼쪽 (left)</option>
                          <option value="center">가운데 (center)</option>
                          <option value="right">오른쪽 (right)</option>
                        </select>
                      </div>
                      <div>
                        <label className="text-2xs text-fg-muted block mb-0.5">너비 비율</label>
                        <div className="flex items-center gap-1">
                          <input
                            type="number"
                            min="3"
                            max="60"
                            value={rule.widthPercent}
                            onChange={e => handleUpdateRule(idx, { widthPercent: parseInt(e.target.value) || 10 })}
                            className="ui-input w-full py-1 text-xs"
                          />
                          <span className="text-xs text-fg-muted">%</span>
                        </div>
                      </div>
                    </div>

                    {rule.sampleValues && rule.sampleValues.length > 0 && (
                      <div className="pt-1.5 border-t border-subtle">
                        <span className="text-2xs text-fg-muted block mb-0.5">샘플값:</span>
                        <div className="flex flex-wrap gap-1">
                          {rule.sampleValues.slice(0, 2).map((s, sIdx) => (
                            <span key={sIdx} className="text-[10px] bg-surface-muted px-1.5 py-0.5 rounded truncate max-w-[140px]" title={s}>
                              {s}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* 3단계: AI-Ready 메타데이터 검토 및 HWPX 서식 지침 */}
      {/* ========================================================================= */}
      {currentStep === 3 && (
        <div className="space-y-6">
          <div className="ui-panel p-6 space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-subtle pb-4">
              <div>
                <h3 className="text-sm font-bold text-fg">AI-Ready 메타데이터 검토 및 HWPX 서식 지침</h3>
                <p className="text-xs text-fg-muted mt-0.5">
                  분석 결과를 검토하고 샘플 템플릿에 반영할 기관 정보·필드 설명·단위·코드를 입력합니다.
                </p>
              </div>
              <button
                type="button"
                onClick={() => handleStepTransition(4)}
                className="ui-button-primary px-4 py-2 text-xs font-bold flex items-center gap-1.5 cursor-pointer shadow-sm"
              >
                가이드 생성·내보내기
                <ChevronRight className="h-3.5 w-3.5" />
              </button>
            </div>

            {/* 1. AI-Ready 표준 메타데이터 명세 패널 */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Database className="w-4 h-4 text-accent" />
                  <h4 className="text-xs font-bold text-fg">공공 AI-Ready 표준 메타데이터 자동 생성 (DCAT 3.0 / Dublin Core / RAI)</h4>
                </div>
                <span className="text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  REVIEW_REQUIRED 기관 확인 필요
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 p-4 rounded-xl bg-surface-muted/60 border border-subtle text-xs">
                <div className="space-y-1">
                  <span className="text-2xs text-fg-muted font-mono block">dct:title (데이터셋 명칭)</span>
                  <p className="font-bold text-fg truncate">{documentTitle}</p>
                </div>
                <div className="space-y-1">
                  <span className="text-2xs text-fg-muted font-mono block">dct:format (수집·개방 규격)</span>
                  <p className="font-mono text-fg font-bold uppercase">{inputFormat} ({dataCategory === 'file' ? '파일데이터' : 'API 데이터'})</p>
                </div>
                <div className="space-y-1">
                  <span className="text-2xs text-fg-muted font-mono block">dcat:theme (데이터 분류)</span>
                  <p className="font-semibold text-fg">기관 확인 필요</p>
                </div>
                <div className="space-y-1">
                  <span className="text-2xs text-fg-muted font-mono block">rai:transparency (책임감 있는 AI)</span>
                  <div className="flex items-center gap-1.5">
                    <span className="px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-600 font-bold text-2xs">미검증</span>
                    <span className="text-2xs text-fg-muted">비식별화·개인정보 검토 필요</span>
                  </div>
                </div>
                <div className="space-y-1">
                  <span className="text-2xs text-fg-muted font-mono block">dqv:QualityMeasurement (품질 지표)</span>
                  <p className="font-semibold text-emerald-600 dark:text-emerald-400">관측 값 완전성 {aiReadinessScore}% · 기타 품질 검토 필요</p>
                </div>
                <div className="space-y-1">
                  <span className="text-2xs text-fg-muted font-mono block">유효 필드 및 속성</span>
                  <p className="font-semibold text-fg">총 {rules.filter(r => r.include).length}개 관측 필드</p>
                </div>
              </div>
            </div>

            <AiGuideTemplatePanel canonical={canonicalMetadata} metadata={templateMetadata}
              onMetadataChange={setTemplateMetadata} annotations={fieldAnnotations} onAnnotationsChange={setFieldAnnotations} />

            {/* 2. 공공 HWPX 공문서 서식 옵션 */}
            <div className="space-y-3 pt-4 border-t border-subtle">
              <div className="flex items-center gap-2">
                <Table className="w-4 h-4 text-accent" />
                <h4 className="text-xs font-bold text-fg">표 미리보기 옵션 (HWPX는 샘플 템플릿 서식 사용)</h4>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {STYLE_PRESETS.map(preset => (
                  <div
                    key={preset.id}
                    onClick={() => setSelectedPresetId(preset.id)}
                    className={`p-4 rounded-xl border cursor-pointer transition-all ${
                      selectedPresetId === preset.id
                        ? 'border-accent ring-2 ring-accent/20 bg-accent/5'
                        : 'border-subtle bg-surface hover:bg-surface-muted/40'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-bold text-xs text-fg">{preset.name}</span>
                      {selectedPresetId === preset.id && <Check className="w-4 h-4 text-accent" />}
                    </div>
                    <p className="text-xs text-fg-muted leading-relaxed mb-3">{preset.description}</p>
                    <div className="space-y-1.5 text-2xs text-fg-muted font-mono pt-2 border-t border-subtle">
                      <div>헤더 음영: <span className="font-bold" style={{ color: preset.headerTextColor }}>{preset.headerBgColor}</span></div>
                      <div>본문 폰트: {preset.bodyFontSizePt}pt / 헤더: {preset.headerFontSizePt}pt</div>
                    </div>
                  </div>
                ))}
              </div>

              {/* 표 세부 제어 옵션 */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-3 border-t border-subtle">
                <label className="flex items-center gap-3 p-3 rounded-xl bg-surface-muted cursor-pointer">
                  <input
                    type="checkbox"
                    checked={repeatHeader}
                    onChange={e => setRepeatHeader(e.target.checked)}
                    className="rounded border-subtle text-accent focus:ring-accent"
                  />
                  <div>
                    <div className="text-xs font-bold text-fg">페이지 넘김 시 표 머리글 자동 반복</div>
                    <div className="text-2xs text-fg-muted">행이 많은 대용량 표에서 다음 페이지 상단에 헤더를 재표시합니다.</div>
                  </div>
                </label>
                <label className="flex items-center gap-3 p-3 rounded-xl bg-surface-muted cursor-pointer">
                  <input
                    type="checkbox"
                    checked={showRowNumber}
                    onChange={e => setShowRowNumber(e.target.checked)}
                    className="rounded border-subtle text-accent focus:ring-accent"
                  />
                  <div>
                    <div className="text-xs font-bold text-fg">첫 번째 열에 연번(순번) 자동 부여</div>
                    <div className="text-2xs text-fg-muted">표 좌측에 시스템 순번(1, 2, 3...) 컬럼을 6% 너비로 자동 삽입합니다.</div>
                  </div>
                </label>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* 4단계: 완성된 AI 친화 가이드 및 서식 롤 확인 & 내보내기 */}
      {/* ========================================================================= */}
      {currentStep === 4 && (
        <div className="space-y-6">
          <div className="ui-panel p-6 space-y-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-subtle pb-4">
              <div>
                <h3 className="text-sm font-bold text-fg">AI 친화 가이드 완성 및 내보내기</h3>
                <p className="text-xs text-fg-muted mt-0.5">
                  샘플 템플릿 HWPX와 구조 분석 JSON·XML·JSON-LD를 다운로드할 수 있습니다.
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={() => handleCopyClipboard(generatedMarkdownGuide)}
                  className="ui-button-secondary text-xs px-3 py-1.5 flex items-center gap-1.5 cursor-pointer"
                >
                  {copySuccess ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copySuccess ? '복사 완료' : '가이드 복사'}</span>
                </button>
                <button
                  type="button"
                  onClick={() =>
                    handleDownloadFile(
                      generatedMarkdownGuide,
                      `${documentTitle}_AI친화가이드.md`,
                      'text/markdown;charset=utf-8'
                    )
                  }
                  className="ui-button-secondary text-xs px-3 py-1.5 flex items-center gap-1.5 cursor-pointer font-semibold"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>가이드 MD</span>
                </button>
                <button
                  type="button"
                  onClick={() =>
                    handleDownloadFile(
                      generatedJsonLd,
                      `${documentTitle}_DCAT_Metadata.jsonld`,
                      'application/ld+json;charset=utf-8'
                    )
                  }
                  className="ui-button-secondary text-xs px-3 py-1.5 flex items-center gap-1.5 cursor-pointer font-semibold"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>JSON-LD 메타데이터</span>
                </button>
                <button
                  type="button"
                  onClick={() =>
                    handleDownloadFile(
                      generatedQualityReport,
                      `${documentTitle}_품질보고서.md`,
                      'text/markdown;charset=utf-8'
                    )
                  }
                  className="ui-button-primary text-xs px-3.5 py-1.5 flex items-center gap-1.5 cursor-pointer font-bold shadow-xs"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>품질보고서</span>
                </button>
              </div>
            </div>

            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                className="ui-button-primary"
                disabled={isExportingDocx}
                onClick={async () => {
                  setIsExportingDocx(true);
                  setErrorNotice(null);
                  try {
                    const blob = await exportParsedDocx({
                      file_base64: fileBase64,
                      text_content: rawText,
                      format: inputFormat,
                      filename: uploadedFile?.name || `${documentTitle}.${inputFormat}`,
                    });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `${documentTitle}_표파싱보고서.docx`;
                    a.click();
                    URL.revokeObjectURL(url);
                  } catch (err) {
                    setErrorNotice(err instanceof Error ? err.message : 'DOCX 보고서 생성 실패');
                  } finally {
                    setIsExportingDocx(false);
                  }
                }}
              >
                {isExportingDocx ? 'DOCX 생성 중…' : '표 파싱 보고서 (DOCX 표준 디자인 다운로드)'}
              </button>
              <button className="ui-button-secondary" disabled={!canonicalMetadata || isExportingTemplate} onClick={async () => {
                if (!canonicalMetadata) return;
                setIsExportingTemplate(true); setErrorNotice(null);
                try {
                  const blob = await exportAiGuideTemplate({canonical_metadata: canonicalMetadata, metadata: templateMetadata, field_annotations: fieldAnnotations});
                  const url = URL.createObjectURL(blob); const a = document.createElement('a');
                  a.href=url; a.download=`${documentTitle}_템플릿가이드.hwpx`; a.click(); URL.revokeObjectURL(url);
                } catch (err) { setErrorNotice(err instanceof Error ? err.message : 'HWPX 생성 실패'); }
                finally { setIsExportingTemplate(false); }
              }}>{isExportingTemplate ? '템플릿 문서 생성 중…' : '샘플 템플릿 HWPX 다운로드'}</button>
              <button className="ui-button-secondary" onClick={() => handleDownloadFile(customJsonRule || '{}', `${documentTitle}.json`, 'application/json;charset=utf-8')}>구조 분석 JSON 다운로드</button>
              <button className="ui-button-secondary" onClick={() => handleDownloadFile(metadataXml, `${documentTitle}.xml`, 'application/xml;charset=utf-8')}>XML 다운로드 (내부 규격)</button>
            </div>

            {/* 서브 탭 전환 */}
            <div className="flex flex-wrap items-center gap-1 p-1 bg-surface-muted rounded-xl border border-subtle w-fit">
              <button
                type="button"
                onClick={() => setPreviewSubTab('hwpx_render')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                  previewSubTab === 'hwpx_render'
                    ? 'bg-accent text-accent-fg shadow-xs'
                    : 'text-fg-muted hover:text-fg hover:bg-surface'
                }`}
              >
                <Table className="w-3.5 h-3.5" />
                <span>데이터 표 미리보기</span>
              </button>
              <button
                type="button"
                onClick={() => setPreviewSubTab('ai_guide')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                  previewSubTab === 'ai_guide'
                    ? 'bg-accent text-accent-fg shadow-xs'
                    : 'text-fg-muted hover:text-fg hover:bg-surface'
                }`}
              >
                <FileText className="w-3.5 h-3.5" />
                <span>AI 친화 가이드 전문</span>
              </button>
              <button
                type="button"
                onClick={() => setPreviewSubTab('json_ld')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                  previewSubTab === 'json_ld'
                    ? 'bg-accent text-accent-fg shadow-xs'
                    : 'text-fg-muted hover:text-fg hover:bg-surface'
                }`}
              >
                <Database className="w-3.5 h-3.5" />
                <span>AI-Ready 메타데이터 (JSON-LD)</span>
              </button>
              <button
                type="button"
                onClick={() => setPreviewSubTab('quality_report')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                  previewSubTab === 'quality_report'
                    ? 'bg-accent text-accent-fg shadow-xs'
                    : 'text-fg-muted hover:text-fg hover:bg-surface'
                }`}
              >
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>AI 품질보고서</span>
              </button>
              {isLargeDataset && (
                <button
                  type="button"
                  onClick={() => setPreviewSubTab('large_data')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                    previewSubTab === 'large_data'
                      ? 'bg-accent text-accent-fg shadow-xs'
                      : 'text-fg-muted hover:text-fg hover:bg-surface'
                  }`}
                >
                  <Zap className="w-3.5 h-3.5 text-amber-500" />
                  <span>대용량 최적화 가이드</span>
                </button>
              )}
              <button
                type="button"
                onClick={() => setPreviewSubTab('json')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                  previewSubTab === 'json'
                    ? 'bg-accent text-accent-fg shadow-xs'
                    : 'text-fg-muted hover:text-fg hover:bg-surface'
                }`}
              >
                <Code2 className="w-3.5 h-3.5" />
                <span>구조 분석 JSON</span>
              </button>
              {docParseResult && (
                <button
                  type="button"
                  onClick={() => setPreviewSubTab('parsed_tables')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                    previewSubTab === 'parsed_tables'
                      ? 'bg-accent text-accent-fg shadow-xs'
                      : 'text-fg-muted hover:text-fg hover:bg-surface'
                  }`}
                >
                  <Layers className="w-3.5 h-3.5 text-blue-500" />
                  <span>문서 추출 표 ({docParseResult.total_tables_count}개)</span>
                </button>
              )}
            </div>


            <button className="ui-button-secondary" onClick={() => setPreviewSubTab('xml')}>XML 미리보기</button>
            {previewSubTab === 'xml' && <pre className="p-4 bg-surface-muted overflow-auto max-h-[500px] text-xs">{metadataXml}</pre>}
            {/* 1. 데이터 표 미리보기 (HWPX는 샘플 서식) */}
            {previewSubTab === 'hwpx_render' && (
              <div className="p-4 rounded-xl border border-subtle bg-surface overflow-x-auto space-y-3">
                <div className="text-center font-bold text-sm text-fg pb-2 border-b border-subtle">
                  {documentTitle}
                </div>
                <p className="text-xs text-fg-muted">경로별 관측값 예시입니다. 같은 행의 값이 실제 동일 레코드에 속한다는 의미는 아닙니다.</p>
                <table className="w-full text-xs border-collapse border border-subtle">
                  <thead>
                    <tr style={{ backgroundColor: currentPreset.headerBgColor, color: currentPreset.headerTextColor }}>
                      {showRowNumber && (
                        <th className="border border-subtle px-2.5 py-2 text-center font-bold w-[6%]">연번</th>
                      )}
                      {rules
                        .filter(r => r.include)
                        .map(r => (
                          <th
                            key={r.key}
                            style={{ width: `${r.widthPercent}%` }}
                            className="border border-subtle px-2.5 py-2 text-center font-bold"
                          >
                            {r.label}
                          </th>
                        ))}
                    </tr>
                  </thead>
                  <tbody>
                    {parsedData.rows.slice(0, 5).map((row, rIdx) => (
                      <tr key={rIdx} className="hover:bg-surface-muted/40 transition-colors">
                        {showRowNumber && (
                          <td className="border border-subtle px-2 py-1.5 text-center text-fg-muted font-mono">
                            {rIdx + 1}
                          </td>
                        )}
                        {rules
                          .filter(r => r.include)
                          .map(r => {
                            const val = row[r.key] || '';
                            const alignClass =
                              r.align === 'right' ? 'text-right' : r.align === 'center' ? 'text-center' : 'text-left';
                            return (
                              <td key={r.key} className={`border border-subtle px-2.5 py-1.5 ${alignClass}`}>
                                {r.formatType === 'badge' ? (
                                  <span className="inline-block px-1.5 py-0.5 rounded text-[11px] bg-accent/10 text-accent font-medium">
                                    {val}
                                  </span>
                                ) : (
                                  val
                                )}
                              </td>
                            );
                          })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* 공공 기술검토 문서 파싱 표 렌더러 (Data Grid & Parameters) */}
            {previewSubTab === 'parsed_tables' && docParseResult && (
              <div className="p-4 rounded-xl border border-subtle bg-surface overflow-x-auto space-y-6">
                <div className="text-center font-bold text-base text-fg pb-2 border-b border-subtle">
                  [{docParseResult.title}] 공공 기술문서 표 파싱 보고서 (총 {docParseResult.total_tables_count}개 표)
                </div>

                {/* 1. XML/JSON 파싱 데이터 그리드 표 */}
                {docParseResult.payload_data_tables.length > 0 && (
                  <div className="space-y-4">
                    <h3 className="text-sm font-bold text-blue-600 dark:text-blue-400 flex items-center gap-1.5">
                      <Table className="w-4 h-4" />
                      <span>XML·JSON 응답 파싱 데이터 그리드 표 (Data Grid)</span>
                    </h3>
                    <p className="text-xs text-fg-muted">원문 문서에 텍스트로 수록되어 있던 XML/JSON 응답 페이로드를 행·열 2차원 표로 정밀 전개한 결과입니다.</p>
                    {docParseResult.payload_data_tables.map((tbl, idx) => (
                      <div key={idx} className="space-y-2 border border-subtle rounded-lg p-3 bg-surface-muted/30">
                        <div className="font-semibold text-xs text-fg">□ {tbl.title}</div>
                        <table className="w-full text-xs border-collapse border border-subtle">
                          <thead>
                            <tr style={{ backgroundColor: '#EBF2FA', color: '#1F2937' }}>
                              {tbl.headers.map((h, i) => (
                                <th key={i} className="border border-subtle px-2.5 py-1.5 text-center font-bold">{h}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {tbl.rows.slice(0, 10).map((r, rIdx) => (
                              <tr key={rIdx} className={rIdx % 2 === 1 ? 'bg-surface-muted/50' : ''}>
                                {r.map((val, cIdx) => (
                                  <td key={cIdx} className={`border border-subtle px-2.5 py-1.5 ${cIdx === 0 ? 'bg-slate-50 dark:bg-slate-900/50 font-medium' : ''}`}>{val}</td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ))}
                  </div>
                )}

                {/* 2. 파라미터 명세 표 */}
                {docParseResult.parameter_tables.length > 0 && (
                  <div className="space-y-4">
                    <h3 className="text-sm font-bold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                      <Code2 className="w-4 h-4" />
                      <span>API 파라미터 및 필드 스키마 명세 표</span>
                    </h3>
                    {docParseResult.parameter_tables.map((tbl, idx) => (
                      <div key={idx} className="space-y-2 border border-subtle rounded-lg p-3 bg-surface-muted/30">
                        <div className="font-semibold text-xs text-fg">□ {tbl.title}</div>
                        <table className="w-full text-xs border-collapse border border-subtle">
                          <thead>
                            <tr style={{ backgroundColor: '#EBF2FA', color: '#1F2937' }}>
                              {tbl.headers.map((h, i) => (
                                <th key={i} className="border border-subtle px-2.5 py-1.5 text-center font-bold">{h}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {tbl.rows.slice(0, 10).map((r, rIdx) => (
                              <tr key={rIdx} className={rIdx % 2 === 1 ? 'bg-surface-muted/50' : ''}>
                                {r.map((val, cIdx) => (
                                  <td key={cIdx} className={`border border-subtle px-2.5 py-1.5 ${cIdx === 0 ? 'bg-slate-50 dark:bg-slate-900/50 font-medium' : ''}`}>{val}</td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ))}
                  </div>
                )}

                {/* 3. 에러코드 명세 표 */}
                {docParseResult.error_code_tables.length > 0 && (
                  <div className="space-y-4">
                    <h3 className="text-sm font-bold text-amber-600 dark:text-amber-400 flex items-center gap-1.5">
                      <AlertTriangle className="w-4 h-4" />
                      <span>오류 및 에러 코드 명세 표</span>
                    </h3>
                    {docParseResult.error_code_tables.map((tbl, idx) => (
                      <div key={idx} className="space-y-2 border border-subtle rounded-lg p-3 bg-surface-muted/30">
                        <div className="font-semibold text-xs text-fg">□ {tbl.title}</div>
                        <table className="w-full text-xs border-collapse border border-subtle">
                          <thead>
                            <tr style={{ backgroundColor: '#EBF2FA', color: '#1F2937' }}>
                              {tbl.headers.map((h, i) => (
                                <th key={i} className="border border-subtle px-2.5 py-1.5 text-center font-bold">{h}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {tbl.rows.slice(0, 10).map((r, rIdx) => (
                              <tr key={rIdx} className={rIdx % 2 === 1 ? 'bg-surface-muted/50' : ''}>
                                {r.map((val, cIdx) => (
                                  <td key={cIdx} className={`border border-subtle px-2.5 py-1.5 ${cIdx === 0 ? 'bg-slate-50 dark:bg-slate-900/50 font-medium' : ''}`}>{val}</td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ))}
                  </div>
                )}

                {/* 4. 서비스 및 데이터셋 개요 표 */}
                {docParseResult.overview_tables.length > 0 && (
                  <div className="space-y-4">
                    <h3 className="text-sm font-bold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                      <FileText className="w-4 h-4" />
                      <span>서비스 및 데이터셋 일반 개요 표</span>
                    </h3>
                    {docParseResult.overview_tables.map((tbl, idx) => (
                      <div key={idx} className="space-y-2 border border-subtle rounded-lg p-3 bg-surface-muted/30">
                        <div className="font-semibold text-xs text-fg">□ {tbl.title}</div>
                        <table className="w-full text-xs border-collapse border border-subtle">
                          <thead>
                            <tr style={{ backgroundColor: '#EBF2FA', color: '#1F2937' }}>
                              {tbl.headers.map((h, i) => (
                                <th key={i} className="border border-subtle px-2.5 py-1.5 text-center font-bold">{h}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {tbl.rows.slice(0, 10).map((r, rIdx) => (
                              <tr key={rIdx} className={rIdx % 2 === 1 ? 'bg-surface-muted/50' : ''}>
                                {r.map((val, cIdx) => (
                                  <td key={cIdx} className={`border border-subtle px-2.5 py-1.5 ${cIdx === 0 ? 'bg-slate-50 dark:bg-slate-900/50 font-medium' : ''}`}>{val}</td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}


            {/* 2. AI 친화 가이드 마크다운 전문 */}
            {previewSubTab === 'ai_guide' && (
              <pre className="p-4 rounded-xl bg-surface-muted font-mono text-xs text-fg overflow-x-auto max-h-[500px] whitespace-pre-wrap leading-relaxed">
                {generatedMarkdownGuide}
              </pre>
            )}

            {/* 3. AI-Ready 메타데이터 JSON-LD (DCAT 3.0) */}
            {previewSubTab === 'json_ld' && (
              <div className="p-4 rounded-xl border border-subtle bg-surface-muted/50 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Database className="w-4 h-4 text-accent" />
                    <span className="text-xs font-bold text-fg">DCAT 어휘 기반 JSON-LD (기관 메타데이터 확인 필요)</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleDownloadFile(generatedJsonLd, `${documentTitle}_DCAT_Metadata.jsonld`, 'application/ld+json;charset=utf-8')}
                    className="ui-button-secondary text-2xs px-2.5 py-1 cursor-pointer"
                  >
                    JSON-LD 다운로드
                  </button>
                </div>
                <pre className="font-mono text-xs text-fg-muted overflow-x-auto p-3.5 bg-surface rounded-xl border border-subtle max-h-[460px] leading-relaxed">
                  {generatedJsonLd}
                </pre>
              </div>
            )}

            {/* 4. AI 품질보고서 */}
            {previewSubTab === 'quality_report' && (
              <div className="p-4 rounded-xl border border-subtle bg-surface-muted/50 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-emerald-500" />
                    <span className="text-xs font-bold text-fg">공공데이터 AI 품질평가 진단 보고서</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleDownloadFile(generatedQualityReport, `${documentTitle}_품질진단보고서.md`, 'text/markdown;charset=utf-8')}
                    className="ui-button-secondary text-2xs px-2.5 py-1 cursor-pointer"
                  >
                    품질보고서 다운로드
                  </button>
                </div>
                <pre className="font-mono text-xs text-fg-muted overflow-x-auto p-3.5 bg-surface rounded-xl border border-subtle max-h-[460px] whitespace-pre-wrap leading-relaxed">
                  {generatedQualityReport}
                </pre>
              </div>
            )}

            {/* 5. 대용량 최적화 가이드 */}
            {previewSubTab === 'large_data' && (
              <div className="p-4 rounded-xl bg-surface-muted space-y-4">
                <div className="flex items-center gap-2 text-sm font-bold text-fg">
                  <Zap className="w-4 h-4 text-amber-500" />
                  <span>대용량 데이터셋 처리 파이프라인 권고</span>
                </div>
                <pre className="p-3.5 rounded-lg bg-surface border border-subtle font-mono text-xs text-fg-muted whitespace-pre-wrap leading-relaxed">
                  {largeDataGuide || '대용량 데이터 최적화 가이드가 없습니다.'}
                </pre>
              </div>
            )}

            {/* 6. 구조 분석 JSON */}
            {previewSubTab === 'json' && (
              <pre className="p-4 rounded-xl bg-surface-muted font-mono text-xs text-fg overflow-x-auto max-h-[500px] leading-relaxed">
                {customJsonRule ||
                  JSON.stringify(
                    {
                      documentTitle,
                      dataCategory,
                      aiReadinessScore,
                      selectedPresetId,
                      orientation,
                      repeatHeader,
                      showRowNumber,
                      rules: rules.filter(r => r.include),
                    },
                    null,
                    2
                  )}
              </pre>
            )}
          </div>
        </div>
      )}

    </div>
  );
};
