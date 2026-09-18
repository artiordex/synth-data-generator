/**
 * 파일명: AiRuleGuideStudio.tsx
 * 경로: apps/web/src/features/aiguide/AiRuleGuideStudio.tsx
 * 목적: 공공데이터를 분석하고 기관 검토용 AI 친화 가이드를 생성합니다.
 * 작성일: 2026-09-16
 */
import React, { useState, useMemo, useEffect } from 'react';
import {
  Sparkles, FileText, CheckCircle2,
  Download, Copy, Table, Braces,
  ArrowRight, Check, AlertTriangle,
  Loader2, Globe, Database, Archive
} from 'lucide-react';
import {
  generateAiRuleGuide, generateAiGuideDocuments, AiGuideHumanFormat, AiGuideFieldAnnotation,
  ReadinessCheckItem, parseGovDocument, GovDocParseResult, ParsedSimpleTable
} from '../../services/api';
import { AiGuideTemplatePanel } from './AiGuideTemplatePanel';
import { TaxonomySelects } from './TaxonomySelects';
import { UnifiedFileUploader } from '../shared/UnifiedFileUploader';
import * as XLSX from 'xlsx';
import Papa from 'papaparse';
import JSZip from 'jszip';
import DOMPurify from 'dompurify';

  // AI 가이드 생성 시 원격 AI 추론을 사용합니다.
const AI_GUIDE_REMOTE_INFERENCE_ENABLED = true;

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
  jsonSnippet?: string;
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

interface AiRuleGuideStudioProps {
  isDarkMode: boolean;
  onStepChange?: (step: number) => void;
  activeStep?: number;
  onSelectStep?: (step: number) => void;
}

// 식약처 의약품 허가 대장 CSV 샘플 데이터(파일데이터)
const getSampleCsv = (): string => {
  return `품목기준코드,제품명,업체명,허가일자,전문일반구분,주성분
20240101,타이레놀정500mg,한국존슨앤드존슨,2024-01-15,일반의약품,아세트아미노펜
20240102,아모디핀정,한미약품,2024-02-01,전문의약품,캄실산암로디핀
20240103,글루코파지정,한국머크,2024-02-18,전문의약품,메트포르민염산염
20240104,베아제정,대웅제약,2024-03-05,일반의약품,판크레아틴
20240105,노바스크정,비아트리스코리아,2024-03-22,전문의약품,베실산암로디핀`;
};
const getSampleJson = (): string => {
  return JSON.stringify([
    {
      품목관리번호: 'HF-2024-001',
      제품명: '고함량 비타민C 1000',
      영업소명: '식약건강산업',
      신고일자: '2024-04-10',
      '1회분량': '1정(1,200mg)',
      비타민C_mg: 1000,
      열량_kcal: 5,
      유통기한_개월: 24,
    },
    {
      품목관리번호: 'HF-2024-002',
      제품명: '프로바이오틱스 유산균',
      영업소명: '바이오헬스케어',
      신고일자: '2024-04-18',
      '1회분량': '1포(2,000mg)',
      비타민C_mg: 50,
      열량_kcal: 8,
      유통기한_개월: 18,
    },
    {
      품목관리번호: 'HF-2024-003',
      제품명: '루테인 지아잔틴 복합제',
      영업소명: '한국약업연구소',
      신고일자: '2024-05-02',
      '1회분량': '1캡슐(500mg)',
      비타민C_mg: 0,
      열량_kcal: 4,
      유통기한_개월: 24,
    },
  ], null, 2);
};
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
export function decodeKoreanText(buf: ArrayBuffer): string {
  const raw = new Uint8Array(buf);
  if (raw.length === 0) return '';

  // 1. UTF-8 BOM (0xEF, 0xBB, 0xBF)
  if (raw.length >= 3 && raw[0] === 0xef && raw[1] === 0xbb && raw[2] === 0xbf) {
    return new TextDecoder('utf-8').decode(raw.subarray(3));
  }
  // 2. UTF-16 LE BOM (0xFF, 0xFE)
  if (raw.length >= 2 && raw[0] === 0xff && raw[1] === 0xfe) {
    return new TextDecoder('utf-16le').decode(raw.subarray(2));
  }
  // 3. UTF-16 BE BOM (0xFE, 0xFF)
  if (raw.length >= 2 && raw[0] === 0xfe && raw[1] === 0xff) {
    return new TextDecoder('utf-16be').decode(raw.subarray(2));
  }

  // 4. 엄격한 UTF-8 디코딩을 먼저 시도합니다.
  try {
    const utf8Decoder = new TextDecoder('utf-8', { fatal: true });
    const decoded = utf8Decoder.decode(raw);
    if (!decoded.includes('\uFFFD')) {
      return decoded;
    }
  } catch {
    // UTF-8 실패 시 공공데이터에서 사용하는 EUC-KR/CP949로 대체합니다.
  }

  // 5. EUC-KR/CP949 대체 디코딩
  try {
    const eucDecoder = new TextDecoder('euc-kr');
    return eucDecoder.decode(raw);
  } catch {
    // 최종 단계에서는 기본 UTF-8로 처리합니다.
    return new TextDecoder('utf-8').decode(raw);
  }
}

// CSV 원문 텍스트를 분석하여 행 및 컬럼 구조를 반환합니다.
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

/**
 * JSON 객체 또는 배열에서 실제 데이터 레코드 목록과 상위 15건 미리보기 구조를 추출합니다.
 * 공공데이터 포털 API 표준 래핑 구조(response > body > items > item 등)를 재귀 탐색하여 언래핑하고,
 * 중첩 객체/배열 값도 안전하게 JSON 문자열로 변환하여 [object Object] 표시를 방지합니다.
 */
export function extractJsonPreviewData(
  parsed: unknown,
  format: 'json' | 'jsonld' = 'json'
): SamplePreviewData {
  const findRecordArray = (val: unknown, depth = 0): Record<string, unknown>[] | null => {
    if (depth > 6 || val === null || val === undefined) return null;

    if (Array.isArray(val)) {
      if (val.length === 0) return [];
      const objItems = val.filter(item => item !== null && typeof item === 'object');
      if (objItems.length > 0) {
        return objItems as Record<string, unknown>[];
      }
      return null;
    }

    if (typeof val !== 'object') return null;

    const obj = val as Record<string, unknown>;
    const priorityKeys = ['items', 'item', 'records', 'data', 'results', 'list', 'rows', 'body', 'response'];
    for (const key of priorityKeys) {
      if (key in obj) {
        const sub = obj[key];
        if (key === 'item' && sub && typeof sub === 'object' && !Array.isArray(sub)) {
          return [sub as Record<string, unknown>];
        }
        const found = findRecordArray(sub, depth + 1);
        if (found && found.length > 0) return found;
      }
    }

    for (const [k, v] of Object.entries(obj)) {
      if (!priorityKeys.includes(k) && typeof v === 'object' && v !== null) {
        const found = findRecordArray(v, depth + 1);
        if (found && found.length > 0) return found;
      }
    }

    return null;
  };

  const foundRecords = findRecordArray(parsed);

  if (foundRecords && foundRecords.length > 0) {
    const headerOrder: string[] = [];
    const headerSet = new Set<string>();
    foundRecords.slice(0, 30).forEach(rec => {
      if (rec && typeof rec === 'object') {
        Object.keys(rec).forEach(key => {
          if (!headerSet.has(key)) {
            headerSet.add(key);
            headerOrder.push(key);
          }
        });
      }
    });

    const headers = headerOrder.length > 0 ? headerOrder : ['데이터'];
    const top15 = foundRecords.slice(0, 15);
    const rows = top15.map(rec =>
      headers.map(h => {
        const val = rec[h];
        if (val === null || val === undefined) return '';
        if (typeof val === 'object') {
          try {
            return JSON.stringify(val);
          } catch {
            return String(val);
          }
        }
        return String(val);
      })
    );

    return {
      format,
      headers,
      rows,
      totalRows: foundRecords.length,
      totalCols: headers.length,
      jsonSnippet: JSON.stringify(top15, null, 2),
    };
  }

  // 단일 객체인 경우 (키-값 쌍 구조)
  if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
    const obj = parsed as Record<string, unknown>;
    const entries = Object.entries(obj);
    const top15Entries = entries.slice(0, 15);
    const top15Obj = Object.fromEntries(top15Entries);

    return {
      format,
      headers: ['키(Key)', '값(Value)'],
      rows: top15Entries.map(([k, v]) => [
        k,
        v === null || v === undefined
          ? ''
          : typeof v === 'object'
          ? JSON.stringify(v)
          : String(v),
      ]),
      totalRows: entries.length,
      totalCols: 2,
      jsonSnippet: JSON.stringify(top15Obj, null, 2),
    };
  }

  // 단순 원시값 배열인 경우
  if (Array.isArray(parsed)) {
    const top15 = parsed.slice(0, 15);
    return {
      format,
      headers: ['값(Value)'],
      rows: top15.map(v => [
        v === null || v === undefined ? '' : typeof v === 'object' ? JSON.stringify(v) : String(v),
      ]),
      totalRows: parsed.length,
      totalCols: 1,
      jsonSnippet: JSON.stringify(top15, null, 2),
    };
  }

  return {
    format,
    headers: ['데이터'],
    rows: [[String(parsed ?? '')]],
    totalRows: 1,
    totalCols: 1,
    jsonSnippet: String(parsed ?? ''),
  };
}

/**
 * 비개발자 실무자도 한눈에 편안하게 읽을 수 있도록 밝은 테마에 맞춘 부드러운 색상으로 JSON 구문을 강조합니다.
 */
export function highlightJsonToHtml(jsonStr: string): string {
  if (!jsonStr) return '';
  const escaped = jsonStr
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  const highlighted = escaped.replace(
    /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g,
    match => {
      let cls = 'text-amber-700 dark:text-amber-400 font-medium'; // 숫자
      if (/^"/.test(match)) {
        if (/:$/.test(match)) {
          cls = 'text-blue-700 dark:text-sky-400 font-bold'; // 속성 키
        } else {
          cls = 'text-emerald-800 dark:text-emerald-300 font-medium'; // 문자열 값
        }
      } else if (/true|false/.test(match)) {
        cls = 'text-purple-700 dark:text-purple-400 font-semibold'; // 불리언
      } else if (/null/.test(match)) {
        cls = 'text-rose-600 dark:text-rose-400 italic font-semibold'; // null
      }
      return `<span class="${cls}">${match}</span>`;
    }
  );

  return DOMPurify.sanitize(highlighted);
}

// 컬럼 값 분포를 확인하여 데이터 유형과 정렬 방식을 추론합니다.
function inferRuleProperties(key: string, sampleValues: string[]): {
  inferredType: string;
  align: 'left' | 'center' | 'right';
  formatType: 'text' | 'number_comma' | 'date_standard' | 'badge';
} {
  const nonEmpties = sampleValues.filter(value => value.trim().length > 0);
  if (nonEmpties.length === 0) {
    return { inferredType: 'string', align: 'left', formatType: 'text' };
  }

  const isNumeric = nonEmpties.every(value => {
    const clean = value.replace(/,/g, '').trim();
    return !isNaN(Number(clean)) && clean.length > 0;
  });
  if (isNumeric) {
    if (key.includes('코드') || key.includes('번호') || key.includes('연번') || key.toLowerCase().includes('id')) {
      return { inferredType: 'string', align: 'center', formatType: 'text' };
    }
    return { inferredType: 'number', align: 'right', formatType: 'number_comma' };
  }

  const isDate = nonEmpties.every(value => /^\d{4}[-./]\d{1,2}[-./]\d{1,2}$/.test(value.trim()));
  if (isDate || key.includes('일자') || key.includes('일시') || key.includes('날짜')) {
    return { inferredType: 'date', align: 'center', formatType: 'date_standard' };
  }

  if (key.includes('구분') || key.includes('유형') || key.includes('상태') || key.includes('등급')) {
    return { inferredType: 'string', align: 'center', formatType: 'badge' };
  }

  return { inferredType: 'string', align: 'left', formatType: 'text' };
}

export interface KoglTypeItem {
  id: string;
  name: string;
  shortName: string;
  typeNum: string;
  conditions: string;
  commercial: boolean;
  modification: boolean;
  attribution: boolean;
  tags: string[];
}

export const KOGL_TYPES: Record<string, KoglTypeItem> = {
  KOGL_TYPE_0: {
    id: 'KOGL_TYPE_0',
    name: '제0유형 : 자유이용',
    shortName: '자유이용',
    typeNum: '0',
    conditions: '출처표시 조건 없음 · 상업적/비상업적 이용가능 · 변형 등 2차적 저작물 작성 가능',
    commercial: true,
    modification: true,
    attribution: false,
    tags: ['출처표시 불필요', '상업적 이용가능', '변형가능'],
  },
  KOGL_TYPE_1: {
    id: 'KOGL_TYPE_1',
    name: '제1유형 : 출처표시 (추천)',
    shortName: '출처표시',
    typeNum: '1',
    conditions: '출처표시 필수 · 상업적/비상업적 이용가능 · 변형 등 2차적 저작물 작성 가능',
    commercial: true,
    modification: true,
    attribution: true,
    tags: ['출처표시 필수', '상업적 이용가능', '변형가능'],
  },
  KOGL_TYPE_2: {
    id: 'KOGL_TYPE_2',
    name: '제2유형 : 출처표시 + 상업적이용금지',
    shortName: '출처표시+상업금지',
    typeNum: '2',
    conditions: '출처표시 필수 · 비상업적 이용만 가능 · 변형 등 2차적 저작물 작성 가능',
    commercial: false,
    modification: true,
    attribution: true,
    tags: ['출처표시 필수', '상업적이용 금지', '변형가능'],
  },
  KOGL_TYPE_3: {
    id: 'KOGL_TYPE_3',
    name: '제3유형 : 출처표시 + 변경금지',
    shortName: '출처표시+변경금지',
    typeNum: '3',
    conditions: '출처표시 필수 · 상업적/비상업적 이용가능 · 내용 및 형식 변경금지',
    commercial: true,
    modification: false,
    attribution: true,
    tags: ['출처표시 필수', '상업적 이용가능', '변경금지'],
  },
  KOGL_TYPE_4: {
    id: 'KOGL_TYPE_4',
    name: '제4유형 : 출처표시 + 상업적이용금지 + 변경금지',
    shortName: '출처표시+상업/변경금지',
    typeNum: '4',
    conditions: '출처표시 필수 · 비상업적 이용만 가능 · 내용 및 형식 변경금지',
    commercial: false,
    modification: false,
    attribution: true,
    tags: ['출처표시 필수', '상업적이용 금지', '변경금지'],
  },
  KOGL_TYPE_AI: {
    id: 'KOGL_TYPE_AI',
    name: 'AI유형 : 인공지능(AI) 모델 학습용 이용허락',
    shortName: 'AI 학습허용',
    typeNum: 'AI',
    conditions: '인공지능 모델 학습 및 연구개발 전용 이용허락',
    commercial: true,
    modification: true,
    attribution: true,
    tags: ['AI 모델 학습 허용', '연구·개발 특화'],
  },
};

export const KoglBadge: React.FC<{ typeKey: string; compact?: boolean }> = ({ typeKey, compact = false }) => {
  const item = KOGL_TYPES[typeKey] || KOGL_TYPES.KOGL_TYPE_1;

  return (
    <div className="inline-flex items-center gap-2.5 bg-white dark:bg-slate-900 border border-slate-900 dark:border-slate-400 rounded px-2.5 py-1 text-slate-900 dark:text-slate-100 shadow-sm shrink-0">
      {/* 공식 공공누리 OPEN 심볼 박스 */}
      <div className="flex items-center gap-1.5 border-r border-slate-300 dark:border-slate-700 pr-2">
        <span className="font-black text-sm tracking-tighter text-slate-900 dark:text-white">OPEN</span>
        <div className="flex flex-col text-[8px] leading-tight text-slate-500 dark:text-slate-400 font-semibold">
          <span>공공누리</span>
          <span className="text-[7px]">자유이용허락</span>
        </div>
      </div>

      {/* 유형별 아이콘 및 명칭 */}
      <div className="flex items-center gap-1.5">
        {item.typeNum === '0' && (
          <span className="bg-slate-900 dark:bg-white text-white dark:text-slate-900 text-[10px] font-bold px-1.5 py-0.5 rounded">
            자유이용
          </span>
        )}
        {item.typeNum === '1' && (
          <div className="flex items-center gap-1">
            <span className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-slate-900 dark:bg-white text-white dark:text-slate-900 text-[9px] font-bold">
              BY
            </span>
            <span className="text-xs font-bold">출처표시</span>
          </div>
        )}
        {item.typeNum === '2' && (
          <div className="flex items-center gap-1">
            <span className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-slate-900 dark:bg-white text-white dark:text-slate-900 text-[9px] font-bold">BY</span>
            <span className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-rose-600 text-white text-[9px] font-bold">NC</span>
            <span className="text-xs font-bold">상업용금지</span>
          </div>
        )}
        {item.typeNum === '3' && (
          <div className="flex items-center gap-1">
            <span className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-slate-900 dark:bg-white text-white dark:text-slate-900 text-[9px] font-bold">BY</span>
            <span className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-amber-600 text-white text-[9px] font-bold">ND</span>
            <span className="text-xs font-bold">변경금지</span>
          </div>
        )}
        {item.typeNum === '4' && (
          <div className="flex items-center gap-1">
            <span className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-slate-900 dark:bg-white text-white dark:text-slate-900 text-[9px] font-bold">BY</span>
            <span className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-rose-600 text-white text-[9px] font-bold">NC</span>
            <span className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-amber-600 text-white text-[9px] font-bold">ND</span>
          </div>
        )}
        {item.typeNum === 'AI' && (
          <div className="flex items-center gap-1">
            <span className="bg-indigo-600 text-white text-[10px] font-bold px-1.5 py-0.5 rounded">
              AI 학습허용
            </span>
          </div>
        )}
      </div>

      {!compact && (
        <span className="text-[11px] text-slate-600 dark:text-slate-400 font-medium pl-1 border-l border-slate-200 dark:border-slate-700 hidden sm:inline">
          {item.conditions}
        </span>
      )}
    </div>
  );
};

export interface UpdateFrequencyOption {
  value: string;
  label: string;
}

export const UPDATE_FREQUENCY_OPTIONS: UpdateFrequencyOption[] = [
  { value: 'DAILY_OR_MORE', label: '수시 (1일 1회 이상)' },
  { value: 'AUTO', label: '수시 (자동 갱신)' },
  { value: 'ONE_TIME', label: '수시 (1회성 데이터)' },

  { value: 'DAILY', label: '일간' },
  { value: 'WEEKLY', label: '주간' },
  { value: 'MONTHLY', label: '월간' },
  { value: 'QUARTERLY', label: '분기' },
  { value: 'SEMIANNUAL', label: '반기' },
  { value: 'ANNUAL', label: '연간' },

  { value: 'OTHER', label: '기타' },
];

export const AiRuleGuideStudio: React.FC<AiRuleGuideStudioProps> = ({
  isDarkMode,
  onStepChange,
  activeStep: controlledStep,
  onSelectStep,
}) => {
  // 화면 단계 상태: 1단계 데이터 적재, 2단계 추천 검토 및 문서 설정
  const [internalStep, setInternalStep] = useState<number>(1);
  const currentStep = controlledStep !== undefined ? controlledStep : internalStep;

  const handleStepTransition = (nextStep: number) => {
    if (onSelectStep) onSelectStep(nextStep);
    if (onStepChange) onStepChange(nextStep);
    setInternalStep(nextStep);
  };

  // 데이터 입력 및 파일 형식 상태
  const [inputFormat, setInputFormat] = useState<SupportedFormat>('csv');
  const [dataCategory, setDataCategory] = useState<DataCategory>('file');
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [rawText, setRawText] = useState<string>('');
  const [documentTitle, setDocumentTitle] = useState<string>('공공데이터 AI 가이드');
  const [errorNotice, setErrorNotice] = useState<string | null>(null);
  const [samplePreview, setSamplePreview] = useState<SamplePreviewData | null>(null);
  const [previewTab, setPreviewTab] = useState<'table' | 'json'>('table');
  const [jsonSnippetCopied, setJsonSnippetCopied] = useState<boolean>(false);

  const handleCopyJsonSnippet = async () => {
    if (!samplePreview?.jsonSnippet) return;
    try {
      await navigator.clipboard.writeText(samplePreview.jsonSnippet);
      setJsonSnippetCopied(true);
      setTimeout(() => setJsonSnippetCopied(false), 2000);
    } catch {
      // 클립보드 접근 불가 시 무시
    }
  };

  // 대용량 데이터 상태
  const [isLargeDataset, setIsLargeDataset] = useState<boolean>(false);
  const [fileSizeBytes, setFileSizeBytes] = useState<number>(0);
  const [estimatedTotalRows, setEstimatedTotalRows] = useState<number>(0);

  // 파싱 결과 상태
  const [parsedData, setParsedData] = useState<{ columns: string[]; rows: Record<string, string>[] }>(() =>
    parseCsvPayload(getSampleCsv())
  );

  // HWPX 출력 설정 상태
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

  const [downloadSuccessNotice, setDownloadSuccessNotice] = useState<string | null>(null);
  const [copySuccess, setCopySuccess] = useState<boolean>(false);

  // AI 추론 상태
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
  const [templateMetadata, setTemplateMetadata] = useState<Record<string, string>>({
    publisher: '식품의약품안전처',
    creator: '식품의약품안전처 의약품관리과',
    contact_name: '043-719-2700',
    theme_label: '보건 - 식품·의약품안전',
    legal_basis: '공공데이터의 제공 및 이용 활성화에 관한 법률',
    collection_process: '식품의약품안전처 행정정보시스템 및 공공데이터 연계',
    update_frequency: '수시 (1일 1회 이상)',
    next_registration_date: '',
    license_type: 'KOGL_TYPE_1',
  });
  const [fieldAnnotations, setFieldAnnotations] = useState<Record<string, AiGuideFieldAnnotation>>({});
  const [docParseResult, setDocParseResult] = useState<GovDocParseResult | null>(null);
  const [metadataXml, setMetadataXml] = useState('');
  const [serverJsonLd, setServerJsonLd] = useState('');
  const [humanFormat, setHumanFormat] = useState<AiGuideHumanFormat>('docx');
  const [humanDocumentBase64, setHumanDocumentBase64] = useState('');
  const [humanDocumentFilename, setHumanDocumentFilename] = useState('');
  const [allDocumentsBase64, setAllDocumentsBase64] = useState<Record<string, string>>({});
  const [zipDocumentBase64, setZipDocumentBase64] = useState<string>('');
  const [zipFilename, setZipFilename] = useState<string>('');
  const [isGeneratingFinal, setIsGeneratingFinal] = useState(false);
  const [aiModel, setAiModel] = useState<string | null>(null);

  // 분석 실행 핸들러
  const handleParseData = async (
    textToParse: string,
    format: SupportedFormat,
    category: DataCategory,
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
        preset_style: 'fixed_template',
        document_title: titleOverride ?? documentTitle,
        orientation: 'landscape',
        is_large_dataset: isLargeDataset,
        file_size_bytes: fileSizeBytes,
        provider: AI_GUIDE_REMOTE_INFERENCE_ENABLED ? 'openai' : 'local',
        user_metadata: {
          publisher: '공공기관',
          creator: '데이터 관리부서',
          contact_name: '02-000-0000',
          ...templateMetadata,
          ...(templateMetadata.publisher?.trim() ? { publisher: templateMetadata.publisher.trim() } : {}),
          ...(templateMetadata.creator?.trim() ? { creator: templateMetadata.creator.trim() } : {}),
          ...(templateMetadata.contact_name?.trim() ? { contact_name: templateMetadata.contact_name.trim() } : {}),
        },
      });
      setCanonicalMetadata(aiRes.canonical_metadata);
      setTemplateMetadata(previous => ({...previous, ...(aiRes.suggested_metadata ?? {})}));
      setFieldAnnotations(aiRes.suggested_field_annotations ?? {});
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
      setErrorNotice(err instanceof Error ? err.message : '데이터 분석에 실패했습니다.');
    } finally { setIsAiLoading(false); }
  };
  // 공공 샘플 데이터 즉시 로드 핸들러
  const handleLoadSample = (type: SupportedFormat) => {
    setCanonicalMetadata(null); setFieldAnnotations({});
    setFileBase64(undefined); setIsLargeDataset(false);
    setInputFormat(type);
    const category: DataCategory = type === 'csv' ? 'file' : 'api';
    setDataCategory(category);
    setFileSizeBytes(type === 'csv' ? 1024 : 2048);
    setEstimatedTotalRows(type === 'csv' ? 5 : 3);

    let sample = '';
    let title = '';
    if (type === 'csv') {
      sample = getSampleCsv();
      title = '식약처 의약품 품목허가 표준 공시 데이터';
      setTemplateMetadata({
        publisher: '식품의약품안전처',
        creator: '식품의약품안전처 의약품관리과',
        contact_name: '043-719-2700',
        theme_label: '보건 - 식품·의약품안전',
        legal_basis: '공공데이터의 제공 및 이용 활성화에 관한 법률',
        collection_process: '식품의약품안전처 행정정보시스템 및 공공데이터 연계',
        update_frequency: '수시 (1일 1회 이상)',
        next_registration_date: '',
      });
      const parsed = Papa.parse<string[]>(sample, { skipEmptyLines: 'greedy' });
      if (parsed.data.length > 0) {
        const headers = parsed.data[0] || [];
        const top15 = parsed.data.slice(1, 16);
        setSamplePreview({
          format: 'csv',
          headers,
          rows: top15,
          totalRows: parsed.data.length - 1,
          totalCols: headers.length,
          jsonSnippet: JSON.stringify(
            top15.map(row => Object.fromEntries(headers.map((h, i) => [h, row[i] ?? '']))),
            null,
            2
          ),
        });
        setPreviewTab('table');
      }
    } else if (type === 'json') {
      sample = getSampleJson();
      title = '건강기능식품 영양성분 공시 데이터';
      setTemplateMetadata({
        publisher: '식품의약품안전처',
        creator: '식품의약품안전처 건강기능식품정책과',
        contact_name: '043-719-2450',
        theme_label: '보건 - 식품·의약품안전',
        legal_basis: '건강기능식품에 관한 법률',
        collection_process: '식품안전나라 시스템 연계 API',
        update_frequency: '수시 (1일 1회 이상)',
        next_registration_date: '',
      });
      const parsed = JSON.parse(sample);
      const previewData = extractJsonPreviewData(parsed, 'json');
      setSamplePreview(previewData);
      setPreviewTab('json');
    } else {
      sample = getSampleXml();
      title = '공공보건의료기관 현황 통계 데이터';
      setTemplateMetadata({
        publisher: '보건복지부',
        creator: '공공의료과',
        contact_name: '044-202-2530',
        theme_label: '보건 - 보건의료',
        legal_basis: '공공보건의료에 관한 법률',
        collection_process: '국립중앙의료원 연계 API 수집',
        update_frequency: '수시 (1일 1회 이상)',
        next_registration_date: '',
      });
      const xmlDoc = new DOMParser().parseFromString(sample, 'text/xml');
      const items = xmlDoc.querySelectorAll('item, row, record');
      if (items.length > 0) {
        const headers = Array.from(items[0].children).map(child => child.tagName);
        setSamplePreview({
          format: 'xml', headers,
          rows: Array.from(items).slice(0, 15).map(item => headers.map(header => item.querySelector(header)?.textContent || '')),
          totalRows: items.length, totalCols: headers.length,
        });
      }
    }
    setUploadedFile(new File([sample], `${title}.${type}`, { type: 'text/plain' }));
    setRawText(sample);
    setDocumentTitle(title);
  };
  // 파일 선택
  const handleFileSelect = async (file: File) => {
    setCanonicalMetadata(null);
    const fileStem = file.name.replace(/\.[^/.]+$/, '');
    const parts = fileStem.split('_');
    const guessedPublisher = parts.length > 1 && parts[0].length >= 2 ? parts[0] : '';
    let guessedTheme = '';
    if (fileStem.includes('교통') || fileStem.includes('도로') || fileStem.includes('철도') || fileStem.includes('버스')) {
      guessedTheme = '교통 및 물류 - 도로';
    } else if (fileStem.includes('의약') || fileStem.includes('병원') || fileStem.includes('의료')) {
      guessedTheme = '보건 - 보건의료';
    } else if (fileStem.includes('주택') || fileStem.includes('토지') || fileStem.includes('도시')) {
      guessedTheme = '지역개발 - 지역 및 도시';
    } else if (fileStem.includes('재정') || fileStem.includes('금융') || fileStem.includes('보증')) {
      guessedTheme = '일반공공행정 - 재정·금융';
    } else if (fileStem.includes('식품') || fileStem.includes('보건')) {
      guessedTheme = '보건 - 식품·의약품안전';
    }
    setTemplateMetadata({
      publisher: guessedPublisher,
      creator: '',
      contact_name: '',
      theme_label: guessedTheme,
      legal_basis: '',
      collection_process: '',
      update_frequency: '수시 (1일 1회 이상)',
      next_registration_date: '',
    });
    setFieldAnnotations({});
    setFileBase64(undefined);
    setUploadedFile(file);
    setErrorNotice(null);
    setSamplePreview(null);

    const ext = file.name.split('.').pop()?.toLowerCase() || '';
    if (!['csv', 'tsv', 'xlsx', 'xls', 'json', 'jsonld', 'xml', 'docx', 'hwpx'].includes(ext)) {
      setErrorNotice('지원 형식은 CSV, TSV, XLSX, JSON, JSON-LD, XML, DOCX, HWPX입니다.');
      return;
    }
    if (file.size > 32 * 1024 * 1024) {
      setErrorNotice('파일은 32 MiB 이하로 업로드해 주세요.');
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
        // 1. XLSX 파일을 SheetJS로 읽고 시트 데이터를 추출합니다.
        const arrayBuf = await file.arrayBuffer();
        
        // 서버 분석을 위한 base64를 보관합니다.
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
          const sampleRows = rows.slice(1, 16).map(r => headers.map((_, i) => String(r[i] ?? '')));
          const jsonSnippet = JSON.stringify(
            sampleRows.map(r => Object.fromEntries(headers.map((h, i) => [h, r[i] ?? '']))),
            null,
            2
          );

          setSamplePreview({
            format: 'xlsx',
            sheetName,
            headers,
            rows: sampleRows,
            totalRows: Math.max(0, rows.length - 1),
            totalCols: headers.length,
            jsonSnippet,
          });
          setEstimatedTotalRows(Math.max(1, rows.length - 1));
          setPreviewTab('table');

          // 2. CSV/TSV 파일을 인코딩을 보존하여 파싱합니다.
          const csvContent = XLSX.utils.sheet_to_csv(worksheet);
          setRawText(csvContent);
        } else {
          setRawText('엑셀 시트에 데이터가 비어 있습니다.');
        }
      } else if (normFormat === 'csv' || normFormat === 'tsv') {
        // 2. CSV/TSV 파일은 EUC-KR/CP949와 UTF-8을 자동 판별합니다.
        const arrayBuf = await file.arrayBuffer();
        const text = decodeKoreanText(arrayBuf);
        const parsed = Papa.parse<string[]>(text, {
          delimiter: normFormat === 'tsv' ? '\t' : undefined,
          skipEmptyLines: 'greedy',
        });
        if (parsed.data && parsed.data.length > 0) {
          const headers = (parsed.data[0] || []).map(h => String(h ?? '').trim());
          const sampleRows = parsed.data.slice(1, 16).map(r => headers.map((_, i) => String(r[i] ?? '')));
          const jsonSnippet = JSON.stringify(
            sampleRows.map(r => Object.fromEntries(headers.map((h, i) => [h, r[i] ?? '']))),
            null,
            2
          );
          setSamplePreview({
            format: normFormat,
            headers,
            rows: sampleRows,
            totalRows: Math.max(0, parsed.data.length - 1),
            totalCols: headers.length,
            jsonSnippet,
          });
          setEstimatedTotalRows(Math.max(1, parsed.data.length - 1));
          setPreviewTab('table');
        }
        setRawText(text);
      } else if (normFormat === 'json' || normFormat === 'jsonld') {
        // 3. JSON/JSON-LD 파일을 파싱합니다.
        const arrayBuf = await file.arrayBuffer();
        const text = decodeKoreanText(arrayBuf);
        try {
          const parsed = JSON.parse(text);
          const previewData = extractJsonPreviewData(parsed, normFormat as 'json' | 'jsonld');
          setSamplePreview(previewData);
          setEstimatedTotalRows(previewData.totalRows);
          setRawText(JSON.stringify(parsed, null, 2));
          setPreviewTab('json');
        } catch {
          setRawText(text);
        }
      } else if (normFormat === 'xml') {
        // XML 파일은 서버 파싱을 우선하고 브라우저 DOMParser를 보조로 사용합니다.
        const arrayBuf = await file.arrayBuffer();
        const text = decodeKoreanText(arrayBuf);
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
              rows: grid.rows.slice(0, 15),
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
            const sampleRows = Array.from(records).slice(0, 15).map(rec => {
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
        // 5. DOCX/HWPX 문서의 공공데이터 표를 추출합니다.
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
                  rows: primaryTable.rows.slice(0, 15),
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
              setErrorNotice(err instanceof Error ? err.message : '공문서 파싱에 실패했습니다.');
            }
          }
        };
        reader.readAsDataURL(file);
      }

    } catch (err: any) {
      setErrorNotice(`파일 분석 중 오류가 발생했습니다: ${err?.message || err}`);
    }
  };

  // 생성된 AI 친화 가이드 Markdown 문서
  const generatedMarkdownGuide = useMemo(() => {
    if (customMarkdownGuide) return customMarkdownGuide;
    const activeCols = rules.filter(rule => rule.include);
    let markdown = `# AI 친화 데이터 가이드

`;
    markdown += `## 1. 데이터 개요 및 AI 친화도 진단
`;
    markdown += `- **데이터 범주**: ${dataCategory === 'file' ? '파일데이터 (CSV/TSV/XLSX)' : 'API 데이터 (JSON/XML)'}
`;
    markdown += `- **관측값 완전성**: ${aiReadinessScore}%
`;
    markdown += `- **예상 레코드 수**: ${estimatedTotalRows.toLocaleString()}건

`;
    if (largeDataGuide) markdown += `${largeDataGuide}

`;
    markdown += `## 2. 데이터 사전

`;
    markdown += `| 원본 필드 | 표시명 | 데이터 유형 | 정렬 | 너비 | 출력 형식 |
`;
    markdown += `| :--- | :--- | :---: | :---: | :---: | :--- |
`;
    activeCols.forEach(rule => {
      markdown += `| \`${rule.key}\` | **${rule.label}** | ${rule.inferredType} | ${rule.align} | ${rule.widthPercent}% | ${rule.formatType} |
`;
    });
    markdown += `
## 3. AI 품질 점검
`;
    aiReadinessChecklist.forEach(check => {
      const icon = check.status === 'pass' ? '✅' : check.status === 'warn' ? '⚠️' : '❌';
      markdown += `- ${icon} **${check.item}**: ${check.message}
`;
    });
    return markdown;
  }, [customMarkdownGuide, documentTitle, dataCategory, aiReadinessScore, estimatedTotalRows, fileSizeBytes, largeDataGuide, rules, aiReadinessChecklist]);

  // AI-Ready
  // AI-Ready 메타데이터 JSON-LD
  const generatedJsonLd = serverJsonLd || '{}';

  // 공공데이터 AI 품질 점검 보고서
  const generatedQualityReport = `# 공공데이터 AI 품질 점검 보고서: ${documentTitle}

관측값 완전성: ${aiReadinessScore}%
${aiReadinessChecklist.map(check => `- ${check.item}: ${check.message}`).join('\\n')}

대표성·편향·개인정보·권리 관계는 기관 검토가 필요합니다.`;

  // 클립보드 복사
  // 클립보드 복사
  const handleCopyClipboard = (text: string) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 2000);
    });
  };

  // 파일 다운로드
  const downloadBlob = (blob: Blob, filename: string) => {
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = filename;
    anchor.rel = 'noopener';
    anchor.style.display = 'none';
    document.body.appendChild(anchor);
    anchor.click();
    // Chromium can cancel a download when the object URL is revoked in the
    // same task as click(). Keep it alive until the browser has consumed it.
    window.setTimeout(() => {
      anchor.remove();
      URL.revokeObjectURL(url);
    }, 1000);
  };

  const handleDownloadFile = (content: string, filename: string, mimeType: string) => {
    downloadBlob(new Blob([content], { type: mimeType }), filename);
  };

  const textToBase64 = (value: string) => {
    const bytes = new TextEncoder().encode(value);
    let binary = '';
    for (let offset = 0; offset < bytes.length; offset += 0x8000) {
      binary += String.fromCharCode(...bytes.subarray(offset, offset + 0x8000));
    }
    return btoa(binary);
  };

  const handleDownloadBase64 = (content: string, filename: string, mimeType: string) => {
    if (!content) throw new Error('다운로드할 파일 내용이 없습니다.');
    const cleanB64 = content.replace(/\s+/g, '');
    const raw = atob(cleanB64);
    const bytes = new Uint8Array(raw.length);
    for (let index = 0; index < raw.length; index += 1) bytes[index] = raw.charCodeAt(index);
    downloadBlob(new Blob([bytes], { type: mimeType }), filename);
  };

  const handleCreateFinalGuideAndDownload = async () => {
    if (!rawText && !fileBase64) {
      setErrorNotice('먼저 데이터 파일을 선택하거나 샘플 데이터를 불러오세요.');
      return;
    }

    const stem = documentTitle.replace(/[\/:*?"<>|]+/g, '_').trim() || 'AI_guide';
    if (zipDocumentBase64) {
      try {
        handleDownloadBase64(zipDocumentBase64, zipFilename || `${stem}_전체산출물.zip`, 'application/zip');
        setDownloadSuccessNotice('ZIP 파일을 다운로드했습니다.');
      } catch (error) {
        setErrorNotice(error instanceof Error ? error.message : 'ZIP 다운로드에 실패했습니다.');
      }
      return;
    }

    setIsGeneratingFinal(true);
    setErrorNotice(null);
    setDownloadSuccessNotice(null);
    try {
      const ext = inputFormat || 'csv';
      let filename = uploadedFile?.name || `${documentTitle}.${ext}`;
      if (!filename.includes('.')) {
        filename = `${filename}.${ext}`;
      }
      let sourceBase64 = fileBase64 || textToBase64(rawText);
      if ((inputFormat === 'docx' || inputFormat === 'hwpx') && docParseResult) {
        const table = docParseResult.payload_data_tables[0]
          || docParseResult.parameter_tables[0]
          || docParseResult.overview_tables[0];
        if (!table) throw new Error('문서에서 데이터 표를 찾지 못했습니다.');
        sourceBase64 = textToBase64(Papa.unparse([table.headers, ...table.rows]));
        filename = `${documentTitle}.csv`;
      }

      const cleanMetadata: Record<string, string> = {};
      for (const [key, value] of Object.entries(templateMetadata)) {
        cleanMetadata[key] = value == null ? '' : String(value);
      }
      const cleanAnnotations: Record<string, { english_name: string; label: string; description: string; unit: string; codes: string }> = {};
      for (const [fieldPath, annotation] of Object.entries(fieldAnnotations)) {
        cleanAnnotations[fieldPath] = {
          english_name: annotation?.english_name ?? '',
          label: annotation?.label ?? '',
          description: annotation?.description ?? '',
          unit: annotation?.unit ?? '',
          codes: annotation?.codes ?? '',
        };
      }

      const result = await generateAiGuideDocuments({
        sources: [{ filename, file_base64: sourceBase64 }],
        document_title: documentTitle,
        user_metadata: cleanMetadata,
        field_annotations: cleanAnnotations,
        human_format: humanFormat,
        provider: AI_GUIDE_REMOTE_INFERENCE_ENABLED ? 'openai' : 'local',
      });
      setCustomMarkdownGuide(result.markdown_guide);
      setCustomJsonRule(result.canonical_json);
      setMetadataXml(result.metadata_xml);
      setServerJsonLd(result.json_ld);
      setHumanDocumentBase64(result.human_document_base64);
      setHumanDocumentFilename(result.human_filename);
      setAllDocumentsBase64(result.all_documents_base64 || {});
      setZipDocumentBase64(result.zip_document_base64 || '');
      const finalZipName = result.zip_filename || `${stem}_전체산출물.zip`;
      setZipFilename(finalZipName);
      setIsAiPowered(result.ai_powered);
      setAiModel(result.ai_model || null);
      setAiSummary(result.ai_powered
        ? `${result.ai_model || 'OpenAI 4 mini'}가 데이터와 입력 정보를 반영해 초안을 생성했습니다.`
        : '로컬 분석 결과와 직접 입력한 값을 바탕으로 초안을 생성했습니다.');

      if (result.zip_document_base64) {
        handleDownloadBase64(result.zip_document_base64, finalZipName, 'application/zip');
      } else {
        const zip = new JSZip();
        const documents = result.all_documents_base64 || {};
        if (documents.hwpx) zip.file(`${stem}_AI_가이드.hwpx`, documents.hwpx, { base64: true });
        if (documents.docx) zip.file(`${stem}_AI_가이드.docx`, documents.docx, { base64: true });
        if (documents.html) zip.file(`${stem}_AI_가이드.html`, documents.html, { base64: true });
        if (documents.md) zip.file(`${stem}_AI_가이드.md`, documents.md, { base64: true });
        if (!zip.file(`${stem}_AI_가이드.md`)) zip.file(`${stem}_AI_가이드.md`, result.markdown_guide);
        if (result.canonical_json) zip.file(`${stem}_메타데이터.json`, result.canonical_json);
        if (result.metadata_xml) zip.file(`${stem}_메타데이터.xml`, result.metadata_xml);
        if (result.json_ld) zip.file(`${stem}_메타데이터.jsonld`, result.json_ld);
        if (documents.ttl) zip.file(`${stem}_온톨로지.ttl`, documents.ttl, { base64: true });
        zip.file(`${stem}_품질보고서.md`, generatedQualityReport);
        const blob = await zip.generateAsync({ type: 'blob' });
        downloadBlob(blob, finalZipName);
      }
      setDownloadSuccessNotice('HWPX·DOCX·HTML·MD 문서와 JSON·XML·JSON-LD 메타데이터를 ZIP으로 다운로드했습니다.');
    } catch (error) {
      setErrorNotice(error instanceof Error ? error.message : '최종 AI 가이드와 ZIP 생성에 실패했습니다.');
    } finally {
      setIsGeneratingFinal(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* 오류 알림 */}
      {errorNotice && (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-xs text-rose-700 dark:text-rose-300 flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 shrink-0 text-rose-500" />
          <span>{errorNotice}</span>
        </div>
      )}


      {/* ========================================================================= */}
      {/* 1단계: 데이터 적재 및 기본 기관 정보 입력 */}
      {/* ========================================================================= */}
      {currentStep === 1 && (
        <div className="space-y-6">
          <div className="space-y-4">
            {!uploadedFile ? (
              <div className="space-y-4">
                <UnifiedFileUploader
                  title="AI 친화 공공데이터 가이드 생성에 사용할 데이터 업로드"
                  subtitle="XLSX, CSV, TSV, JSON, XML 형식 데이터를 업로드하여 AI 친화도 표준 진단 및 HWPX 가이드를 생성하세요."
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
                {/* 선택한 파일 정보 */}
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
                      </div>
                      <p className="text-xs text-fg-muted mt-0.5">
                        파일 크기: {(uploadedFile.size / 1024).toFixed(1)} KB · 예상 레코드: {estimatedTotalRows.toLocaleString()}건
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

                {/* 데이터 샘플 미리보기 */}
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

                      <div className="flex items-center gap-3">
                        {/* 보기 모드 탭 (표 미리보기 vs JSON 구조) */}
                        <div className="flex items-center gap-1 bg-surface-muted p-0.5 rounded-lg border border-subtle">
                          <button
                            type="button"
                            onClick={() => setPreviewTab('table')}
                            className={`flex items-center gap-1.5 px-2.5 py-1 text-2xs font-medium rounded-md transition-colors cursor-pointer ${
                              previewTab === 'table'
                                ? 'bg-surface text-fg shadow-2xs font-bold'
                                : 'text-fg-muted hover:text-fg'
                            }`}
                          >
                            <Table className="w-3.5 h-3.5" />
                            <span>표 미리보기</span>
                          </button>
                          {samplePreview.jsonSnippet && (
                            <button
                              type="button"
                              onClick={() => setPreviewTab('json')}
                              className={`flex items-center gap-1.5 px-2.5 py-1 text-2xs font-medium rounded-md transition-colors cursor-pointer ${
                                previewTab === 'json'
                                  ? 'bg-surface text-accent shadow-2xs font-bold'
                                  : 'text-fg-muted hover:text-fg'
                              }`}
                            >
                              <Braces className="w-3.5 h-3.5 text-accent" />
                              <span>JSON 구조 (상위 15건)</span>
                            </button>
                          )}
                        </div>

                        <span className="text-2xs text-fg-muted font-mono hidden sm:inline">
                          {samplePreview.totalCols}개 컬럼 · 상위 {samplePreview.rows.length}건 (전체 {samplePreview.totalRows.toLocaleString()}건)
                        </span>
                      </div>
                    </div>

                    {previewTab === 'json' && samplePreview.jsonSnippet ? (
                      <div className="rounded-xl border border-slate-200/90 dark:border-subtle overflow-hidden bg-white dark:bg-surface shadow-2xs">
                        <div className="flex items-center justify-between px-3.5 py-2.5 bg-slate-50 dark:bg-surface-muted/60 border-b border-slate-200/80 dark:border-subtle">
                          <div className="flex items-center gap-2">
                            <span className="text-2xs font-bold text-slate-800 dark:text-fg">JSON 구조 미리보기 (상위 15건)</span>
                            <span className="text-[10px] text-slate-600 dark:text-fg-muted font-mono bg-white dark:bg-surface px-2 py-0.5 rounded border border-slate-200 dark:border-subtle">
                              전체 {samplePreview.totalRows.toLocaleString()}건 중 상위 {Math.min(15, samplePreview.totalRows)}건
                            </span>
                          </div>
                          <button
                            type="button"
                            onClick={handleCopyJsonSnippet}
                            className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-white dark:bg-surface hover:bg-slate-100 dark:hover:bg-surface-muted text-slate-700 dark:text-fg text-2xs border border-slate-300/80 dark:border-subtle transition-colors cursor-pointer font-medium shadow-2xs"
                            title="상위 15건 JSON 복사"
                          >
                            {jsonSnippetCopied ? (
                              <>
                                <Check className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                                <span className="text-emerald-600 dark:text-emerald-400 font-semibold">복사 완료</span>
                              </>
                            ) : (
                              <>
                                <Copy className="w-3.5 h-3.5 text-slate-500 dark:text-fg-muted" />
                                <span>JSON 복사</span>
                              </>
                            )}
                          </button>
                        </div>
                        <pre
                          className="p-4 font-mono text-xs overflow-x-auto max-h-84 leading-relaxed bg-[#f8fafc] text-slate-800 dark:bg-[#0f172a]/20 dark:text-fg whitespace-pre selection:bg-blue-100 selection:text-blue-900 border-t border-slate-200/40 dark:border-subtle/30"
                          dangerouslySetInnerHTML={{ __html: highlightJsonToHtml(samplePreview.jsonSnippet) }}
                        />
                      </div>
                    ) : (
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
                                      title={typeof row[cIdx] === 'object' ? JSON.stringify(row[cIdx]) : String(row[cIdx] || '')}
                                    >
                                      {row[cIdx] !== undefined && row[cIdx] !== '' ? (
                                        typeof row[cIdx] === 'object' ? (
                                          <span className="font-mono text-fg-muted">{JSON.stringify(row[cIdx])}</span>
                                        ) : (
                                          row[cIdx]
                                        )
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
                    )}
                  </div>
                ) : rawText ? (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-fg">데이터 텍스트 샘플</span>
                      <span className="text-2xs text-fg-muted font-mono">{rawText.split('\n').length}</span>
                    </div>
                    <pre className="p-3.5 rounded-xl bg-surface-muted/60 border border-subtle font-mono text-xs text-fg-muted overflow-x-auto max-h-56 whitespace-pre-wrap">
                      {rawText.slice(0, 1200)}
                      {rawText.length > 1200 && '\n... (이하 생략)'}
                    </pre>
                  </div>
                ) : null}

                {/* 기관 및 데이터 기본 정보 */}
                <div className="space-y-3 pt-4">
                  <h4 className="text-sm font-bold text-fg">기본 정보</h4>

                  <div className="border-t border-b border-subtle py-2.5 space-y-3 text-xs">
                    {/* 문서 제목 */}
                    <div className="grid grid-cols-1 md:grid-cols-12 items-center gap-2">
                      <span className="md:col-span-2 font-bold text-fg shrink-0">문서 제목</span>
                      <div className="md:col-span-10">
                        <input
                          type="text"
                          required
                          value={documentTitle}
                          onChange={event => setDocumentTitle(event.target.value)}
                          className="w-full bg-surface-muted/20 hover:bg-surface-muted/40 focus:bg-surface border border-subtle/60 focus:border-accent rounded px-2.5 py-1.5 text-xs text-fg font-medium outline-none transition-colors"
                          placeholder="생성할 문서 제목을 입력하세요"
                        />
                      </div>
                    </div>

                    {/* 분류체계 및 제공기관 */}
                    <div className="grid grid-cols-1 md:grid-cols-2 items-center gap-x-8 gap-y-3">
                      <div className="grid grid-cols-12 items-center gap-2">
                        <span className="col-span-4 font-bold text-fg shrink-0">분류체계</span>
                        <div className="col-span-8">
                          <TaxonomySelects
                            value={templateMetadata.theme_label || ''}
                            onChange={value => setTemplateMetadata({...templateMetadata, theme_label: value})}
                          />
                        </div>
                      </div>
                      <div className="grid grid-cols-12 items-center gap-2">
                        <span className="col-span-4 font-bold text-fg shrink-0">제공기관</span>
                        <div className="col-span-8">
                          <input
                            type="text"
                            value={templateMetadata.publisher || ''}
                            onChange={event => setTemplateMetadata({...templateMetadata, publisher: event.target.value})}
                            className="w-full bg-surface-muted/20 hover:bg-surface-muted/40 focus:bg-surface border border-subtle/60 focus:border-accent rounded px-2.5 py-1.5 text-xs text-fg outline-none transition-colors"
                            placeholder="예: 식품의약품안전처"
                          />
                        </div>
                      </div>
                    </div>

                    {/* 소관부서 및 담당자 연락처 */}
                    <div className="grid grid-cols-1 md:grid-cols-2 items-center gap-x-8 gap-y-3">
                      <div className="grid grid-cols-12 items-center gap-2">
                        <span className="col-span-4 font-bold text-fg shrink-0">소관부서</span>
                        <div className="col-span-8">
                          <input
                            type="text"
                            value={templateMetadata.creator || ''}
                            onChange={event => setTemplateMetadata({...templateMetadata, creator: event.target.value})}
                            className="w-full bg-surface-muted/20 hover:bg-surface-muted/40 focus:bg-surface border border-subtle/60 focus:border-accent rounded px-2.5 py-1.5 text-xs text-fg outline-none transition-colors"
                            placeholder="예: 식품의약품안전처 의약품관리과"
                          />
                        </div>
                      </div>
                      <div className="grid grid-cols-12 items-center gap-2">
                        <span className="col-span-4 font-bold text-fg shrink-0">담당자 연락처 / 이메일</span>
                        <div className="col-span-8">
                          <input
                            type="text"
                            value={templateMetadata.contact_name || ''}
                            onChange={event => setTemplateMetadata({...templateMetadata, contact_name: event.target.value})}
                            className="w-full bg-surface-muted/20 hover:bg-surface-muted/40 focus:bg-surface border border-subtle/60 focus:border-accent rounded px-2.5 py-1.5 text-xs text-fg outline-none transition-colors"
                            placeholder="예: 043-719-2700 / 담당자 이메일"
                          />
                        </div>
                      </div>
                    </div>

                    {/* 보유근거 및 수집방법 */}
                    <div className="grid grid-cols-1 md:grid-cols-2 items-center gap-x-8 gap-y-3">
                      <div className="grid grid-cols-12 items-center gap-2">
                        <span className="col-span-4 font-bold text-fg shrink-0">보유근거</span>
                        <div className="col-span-8">
                          <input
                            type="text"
                            value={templateMetadata.legal_basis || ''}
                            onChange={event => setTemplateMetadata({...templateMetadata, legal_basis: event.target.value})}
                            className="w-full bg-surface-muted/20 hover:bg-surface-muted/40 focus:bg-surface border border-subtle/60 focus:border-accent rounded px-2.5 py-1.5 text-xs text-fg outline-none transition-colors"
                            placeholder="관련 법령 또는 데이터 구축 근거"
                          />
                        </div>
                      </div>
                      <div className="grid grid-cols-12 items-center gap-2">
                        <span className="col-span-4 font-bold text-fg shrink-0">수집방법</span>
                        <div className="col-span-8">
                          <input
                            type="text"
                            value={templateMetadata.collection_process || ''}
                            onChange={event => setTemplateMetadata({...templateMetadata, collection_process: event.target.value})}
                            className="w-full bg-surface-muted/20 hover:bg-surface-muted/40 focus:bg-surface border border-subtle/60 focus:border-accent rounded px-2.5 py-1.5 text-xs text-fg outline-none transition-colors"
                            placeholder="수집방법을 입력하세요 (선택)"
                          />
                        </div>
                      </div>
                    </div>

                    {/* 업데이트 주기 및 차기 등록 예정 */}
                    <div className="grid grid-cols-1 md:grid-cols-2 items-center gap-x-8 gap-y-3">
                      <div className="grid grid-cols-12 items-start gap-2">
                        <span className="col-span-4 font-bold text-fg shrink-0 pt-1.5">업데이트 주기</span>
                        <div className="col-span-8 flex flex-col gap-1.5">
                          <select
                            value={
                              UPDATE_FREQUENCY_OPTIONS.find(
                                opt => opt.value === templateMetadata.update_frequency || opt.label === templateMetadata.update_frequency
                              )?.value || 'OTHER'
                            }
                            onChange={event => {
                              const selectedVal = event.target.value;
                              const matched = UPDATE_FREQUENCY_OPTIONS.find(opt => opt.value === selectedVal);
                              if (matched && matched.value !== 'OTHER') {
                                setTemplateMetadata({ ...templateMetadata, update_frequency: matched.label });
                              } else {
                                setTemplateMetadata({ ...templateMetadata, update_frequency: '기타' });
                              }
                            }}
                            className="w-full bg-surface-muted/20 hover:bg-surface-muted/40 focus:bg-surface border border-subtle/60 focus:border-accent rounded px-2.5 py-1.5 text-xs text-fg outline-none transition-colors cursor-pointer"
                          >
                            {UPDATE_FREQUENCY_OPTIONS.map(item => (
                              <option key={item.value} value={item.value}>
                                {item.label}
                              </option>
                            ))}
                          </select>
                          {/* '기타' 선택 시 또는 표준 옵션 외의 커스텀 주기 입력 시 직접 입력 input 표시 */}
                          {(
                            !UPDATE_FREQUENCY_OPTIONS.some(
                              opt => opt.value !== 'OTHER' && (opt.value === templateMetadata.update_frequency || opt.label === templateMetadata.update_frequency)
                            )
                          ) && (
                            <input
                              type="text"
                              value={templateMetadata.update_frequency === '기타' ? '' : (templateMetadata.update_frequency || '')}
                              onChange={event => setTemplateMetadata({ ...templateMetadata, update_frequency: event.target.value || '기타' })}
                              className="w-full bg-surface-muted/20 hover:bg-surface-muted/40 focus:bg-surface border border-subtle/60 focus:border-accent rounded px-2.5 py-1 text-xs text-fg outline-none transition-colors"
                              placeholder="주기를 직접 입력하세요 (예: 1시간 주기 자동 계측 수집)"
                            />
                          )}
                        </div>
                      </div>
                      <div className="grid grid-cols-12 items-center gap-2">
                        <span className="col-span-4 font-bold text-fg shrink-0">차기 등록 예정</span>
                        <div className="col-span-8">
                          <input
                            type="text"
                            value={templateMetadata.next_registration_date || ''}
                            onChange={event => setTemplateMetadata({...templateMetadata, next_registration_date: event.target.value})}
                            className="w-full bg-surface-muted/20 hover:bg-surface-muted/40 focus:bg-surface border border-subtle/60 focus:border-accent rounded px-2.5 py-1.5 text-xs text-fg outline-none transition-colors"
                            placeholder="차기 등록 예정일 (선택)"
                          />
                        </div>
                      </div>
                    </div>

                    {/* 이용 조건 (공공누리 유형 및 공식 마크 배지) */}
                    <div className="pt-2 border-t border-subtle/40">
                      <div className="grid grid-cols-12 items-start gap-2">
                        <span className="col-span-12 sm:col-span-2 font-bold text-fg shrink-0 pt-1.5">이용조건 (공공누리)</span>
                        <div className="col-span-12 sm:col-span-10 flex flex-col gap-2.5">
                          <div className="flex flex-wrap items-center gap-3">
                            <select
                              value={templateMetadata.license_type || 'KOGL_TYPE_1'}
                              onChange={event => setTemplateMetadata({...templateMetadata, license_type: event.target.value})}
                              className="bg-surface-muted/20 hover:bg-surface-muted/40 focus:bg-surface border border-subtle/60 focus:border-accent rounded px-2.5 py-1.5 text-xs text-fg outline-none transition-colors max-w-sm"
                            >
                              {Object.values(KOGL_TYPES).map(item => (
                                <option key={item.id} value={item.id}>
                                  {item.name}
                                </option>
                              ))}
                            </select>
                            <KoglBadge typeKey={templateMetadata.license_type || 'KOGL_TYPE_1'} />
                          </div>
                          {/* 권리 칩 태그 */}
                          <div className="flex flex-wrap items-center gap-1.5 text-[11px]">
                            {(KOGL_TYPES[templateMetadata.license_type || 'KOGL_TYPE_1'] || KOGL_TYPES.KOGL_TYPE_1).tags.map((tag, idx) => (
                              <span
                                key={idx}
                                className={`px-2 py-0.5 rounded-full font-medium ${
                                  tag.includes('금지') || tag.includes('불가')
                                    ? 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20'
                                    : 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20'
                                }`}
                              >
                                {tag}
                              </span>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* 입력 정보 기반 AI 분석 */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2">
                  <div className="flex items-center gap-2">
                    {isAiLoading ? (
                      <div className="flex items-center gap-2 text-xs text-sky-600 dark:text-sky-400 font-medium">
                        <Loader2 className="h-4 w-4 animate-spin text-sky-500" />
                        <span>데이터 구조를 분석하고 AI 가이드 초안을 생성하는 중입니다...</span>
                      </div>
                    ) : (
                      <p className="text-xs text-fg-muted">
                        입력한 기본 정보를 반영해 AI가 영문 컬럼명과 설명을 추천합니다.
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-2.5 justify-end">
                    <button
                      type="button"
                      disabled={isAiLoading || (!rawText.trim() && !samplePreview) || !documentTitle.trim()}
                      onClick={() => handleParseData(rawText, inputFormat, dataCategory)}
                      className="ui-button-primary px-6 py-2.5 text-xs font-bold flex items-center gap-2 cursor-pointer shadow-sm disabled:opacity-50"
                    >
                      {isAiLoading ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Sparkles className="h-4 w-4" />
                      )}
                      <span>입력 정보 기반 AI 가이드 초안 생성</span>
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
      {/* 2단계: AI 추천 검토 및 문서 설정 */}
      {/* ========================================================================= */}
      {/* AI 추천 메타데이터와 필드 설명을 검토하고 수정합니다. */}
      {/* ========================================================================= */}
      {currentStep === 2 && (
        <div className="space-y-6">
          <div className="ui-panel p-6 space-y-6">
            {/* 공공 표준 메타데이터 요약 */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Database className="w-4 h-4 text-accent" />
                  <h4 className="text-xs font-bold text-fg">공공 표준 메타데이터 요약 (DCAT 3.0)</h4>
                </div>
                <span className="text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  기관 확인 필요 항목을 검토해 주세요
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 p-4 rounded-xl bg-surface-muted/60 border border-subtle text-xs">
                <div className="space-y-1">
                  <span className="text-2xs text-fg-muted font-mono block">dct:title (데이터셋 명칭)</span>
                  <p className="font-bold text-fg truncate">{documentTitle}</p>
                </div>
                <div className="space-y-1">
                  <span className="text-2xs text-fg-muted font-mono block">dct:format (수집·개방 규격)</span>
                  <p className="font-mono text-fg font-bold uppercase">{inputFormat} ({dataCategory === 'file' ? 'file data' : 'API data'})</p>
                </div>
                <div className="space-y-1">
                  <span className="text-2xs text-fg-muted font-mono block">dcat:theme (데이터 분류)</span>
                  <p className="font-semibold text-fg">{templateMetadata.theme_label || '기관 확인 필요'}</p>
                </div>
                <div className="space-y-1">
                  <span className="text-2xs text-fg-muted font-mono block">rai:transparency (책임 있는 AI)</span>
                  <div className="flex items-center gap-1.5">
                    <span className="px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-600 font-bold text-2xs">미검증</span>
                    <span className="text-2xs text-fg-muted">비식별화·개인정보 검토 필요</span>
                  </div>
                </div>
                <div className="space-y-1">
                  <span className="text-2xs text-fg-muted font-mono block">dqv:QualityMeasurement (품질 지표)</span>
                  <p className="font-semibold text-emerald-600 dark:text-emerald-400">관측값 완전성 {aiReadinessScore}% · 대표성·편향·정확성은 별도 검토</p>
                </div>
              </div>
            </div>

            <AiGuideTemplatePanel canonical={canonicalMetadata} metadata={templateMetadata}
              onMetadataChange={value => { setTemplateMetadata(value); setHumanDocumentBase64(''); setZipDocumentBase64(''); setDownloadSuccessNotice(null); }}
              annotations={fieldAnnotations}
              onAnnotationsChange={value => { setFieldAnnotations(value); setHumanDocumentBase64(''); setZipDocumentBase64(''); setDownloadSuccessNotice(null); }} />

            <div className="space-y-2 pt-4 border-t border-subtle">
              <label className="ui-label" htmlFor="ai-guide-human-format">AI 가이드 문서 형식</label>
              <select id="ai-guide-human-format" className="ui-input w-full md:w-80 text-sm"
                value={humanFormat} onChange={event => { setHumanFormat(event.target.value as AiGuideHumanFormat); setHumanDocumentBase64(''); setZipDocumentBase64(''); setDownloadSuccessNotice(null); }}>
                <option value="hwpx">한글 표준 문서 (.hwpx)</option>
                <option value="docx">Word 문서 (.docx)</option>
                <option value="html">HTML (.html)</option>
                <option value="md">Markdown (.md)</option>
              </select>
              <p className="text-xs text-fg-muted">
                ZIP 일괄 다운로드를 선택하면 문서 4종(HWPX·DOCX·HTML·MD), 메타데이터 3종(JSON·XML·JSON-LD), 품질보고서를 함께 제공합니다.
              </p>
            </div>

            {/* 최종 산출물 ZIP 다운로드 */}
            <div className="pt-6 border-t border-subtle space-y-4">
              {downloadSuccessNotice && (
                <div className="p-3.5 rounded-xl border border-emerald-500/30 bg-emerald-500/10 text-xs text-emerald-700 dark:text-emerald-300 flex items-center justify-between gap-3 shadow-xs">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
                    <span className="font-medium">{downloadSuccessNotice}</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => setDownloadSuccessNotice(null)}
                    className="text-2xs text-fg-muted hover:text-fg underline cursor-pointer"
                  >
                    닫기
                  </button>
                </div>
              )}

              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-xl bg-accent/10 border border-accent/25">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-10 h-10 rounded-xl bg-accent text-accent-fg flex items-center justify-center shrink-0 shadow-xs">
                    <Archive className="w-5 h-5" />
                  </div>
                  <div className="min-w-0">
                    <h4 className="text-sm font-bold text-fg">완성본 전체 다운로드 (ZIP)</h4>
                    <p className="text-xs text-fg-muted mt-0.5">
                      문서 4종(HWPX·DOCX·HTML·MD) · 메타데이터 3종(JSON·XML·JSON-LD) · 품질보고서
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <button
                    type="button"
                    onClick={handleCreateFinalGuideAndDownload}
                    disabled={isGeneratingFinal}
                    className="ui-button-primary px-6 py-3 text-sm font-bold flex items-center gap-2 cursor-pointer shadow-md hover:shadow-lg transition-all"
                  >
                    {isGeneratingFinal ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        <span>산출물 생성 및 ZIP 압축 중…</span>
                      </>
                    ) : (
                      <>
                        <Download className="h-4 w-4" />
                        <span>ZIP 일괄 다운로드</span>
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* 진행 상태 및 피드백 알림 (버튼 바로 아래 표시) */}
              {isGeneratingFinal && (
                <div className="p-3.5 rounded-xl bg-indigo-50 dark:bg-indigo-950/40 border border-indigo-200 dark:border-indigo-800/60 text-xs text-indigo-700 dark:text-indigo-300 flex items-center gap-2.5 animate-pulse">
                  <Loader2 className="h-4 w-4 animate-spin shrink-0 text-indigo-600 dark:text-indigo-400" />
                  <span>문서 4종(HWPX·DOCX·HTML·MD) 및 메타데이터 3종(JSON·XML·JSON-LD)을 실시간 생성하고 압축하고 있습니다. (데이터 건수에 따라 약 10~25초 소요됩니다)</span>
                </div>
              )}
              {errorNotice && (
                <div className="p-3.5 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800/60 text-xs text-rose-700 dark:text-rose-300 flex items-center gap-2.5">
                  <AlertTriangle className="h-4 w-4 shrink-0 text-rose-600 dark:text-rose-400" />
                  <span>{errorNotice}</span>
                </div>
              )}
              {downloadSuccessNotice && (
                <div className="p-3.5 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800/60 text-xs text-emerald-700 dark:text-emerald-300 flex items-center gap-2.5">
                  <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600 dark:text-emerald-400" />
                  <span>{downloadSuccessNotice}</span>
                </div>
              )}

              {/* 생성 완료 후 개별 문서와 메타데이터 다운로드 */}
              {(zipDocumentBase64 || humanDocumentBase64) && (
                <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-xl bg-surface-muted/60 border border-subtle">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-2xs font-bold text-fg-muted mr-1">개별 문서 다운로드:</span>
                    <button
                      type="button"
                      className="text-xs px-2.5 py-1.5 rounded-lg border border-subtle bg-surface text-fg hover:bg-surface-muted font-medium flex items-center gap-1 cursor-pointer transition-colors"
                      onClick={() => {
                        const b64 = allDocumentsBase64['hwpx'] || (humanFormat === 'hwpx' ? humanDocumentBase64 : '');
                        if (b64) handleDownloadBase64(b64, `${documentTitle}_AI_가이드.hwpx`, 'application/hwp+zip');
                      }}
                      title="한글 표준 문서 (HWPX)"
                    >
                      <Download className="w-3 h-3" /> HWPX
                    </button>
                    <button
                      type="button"
                      className="text-xs px-2.5 py-1.5 rounded-lg border border-subtle bg-surface text-fg hover:bg-surface-muted font-medium flex items-center gap-1 cursor-pointer transition-colors"
                      onClick={() => {
                        const b64 = allDocumentsBase64['docx'] || (humanFormat === 'docx' ? humanDocumentBase64 : '');
                        if (b64) handleDownloadBase64(b64, `${documentTitle}_AI_가이드.docx`, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document');
                      }}
                      title="Word 문서 (DOCX)"
                    >
                      <Download className="w-3 h-3" /> DOCX
                    </button>
                    <button
                      type="button"
                      className="text-xs px-2.5 py-1.5 rounded-lg border border-subtle bg-surface text-fg hover:bg-surface-muted font-medium flex items-center gap-1 cursor-pointer transition-colors"
                      onClick={() => {
                        const b64 = allDocumentsBase64['md'] || (humanFormat === 'md' ? humanDocumentBase64 : '');
                        if (b64) handleDownloadBase64(b64, `${documentTitle}_AI_가이드.md`, 'text/markdown;charset=utf-8');
                        else handleDownloadFile(customMarkdownGuide || generatedMarkdownGuide, `${documentTitle}_AI_가이드.md`, 'text/markdown;charset=utf-8');
                      }}
                      title="마크다운 문서 (MD)"
                    >
                      <Download className="w-3 h-3" /> MD
                    </button>

                    <button
                      type="button"
                      className="text-xs px-2.5 py-1.5 rounded-lg border border-subtle bg-surface text-fg hover:bg-surface-muted font-medium flex items-center gap-1 cursor-pointer transition-colors"
                      onClick={() => {
                        const b64 = allDocumentsBase64['html'] || (humanFormat === 'html' ? humanDocumentBase64 : '');
                        if (b64) handleDownloadBase64(b64, `${documentTitle}_AI_Guide.html`, 'text/html;charset=utf-8');
                      }}
                      title="HTML 문서"
                    >
                      <Download className="w-3 h-3" /> HTML
                    </button>

                    <span className="text-subtle mx-1">|</span>
                    <span className="text-2xs font-bold text-fg-muted mr-1">메타데이터</span>

                    <button
                      type="button"
                      className="text-xs px-2.5 py-1.5 rounded-lg border border-subtle bg-surface text-fg hover:bg-surface-muted font-medium flex items-center gap-1 cursor-pointer transition-colors"
                      onClick={() => handleDownloadFile(customJsonRule || '{}', `${documentTitle}_메타데이터.json`, 'application/json;charset=utf-8')}
                      title="표준 JSON 메타데이터"
                    >
                      <Download className="w-3 h-3" /> JSON
                    </button>
                    <button
                      type="button"
                      className="text-xs px-2.5 py-1.5 rounded-lg border border-subtle bg-surface text-fg hover:bg-surface-muted font-medium flex items-center gap-1 cursor-pointer transition-colors"
                      onClick={() => handleDownloadFile(metadataXml, `${documentTitle}_메타데이터.xml`, 'application/xml;charset=utf-8')}
                      title="표준 XML 메타데이터"
                    >
                      <Download className="w-3 h-3" /> XML
                    </button>
                    <button
                      type="button"
                      className="text-xs px-2.5 py-1.5 rounded-lg border border-subtle bg-surface text-fg hover:bg-surface-muted font-medium flex items-center gap-1 cursor-pointer transition-colors"
                      onClick={() => handleDownloadFile(serverJsonLd || generatedJsonLd, `${documentTitle}_메타데이터.jsonld`, 'application/ld+json;charset=utf-8')}
                      title="W3C DCAT 3.0 JSON-LD"
                    >
                      <Download className="w-3 h-3" /> JSON-LD
                    </button>
                  </div>

                  <button
                    type="button"
                    onClick={() => handleCopyClipboard(customMarkdownGuide || generatedMarkdownGuide)}
                    className="ui-button-secondary text-xs px-3 py-1.5 flex items-center gap-1.5 cursor-pointer shrink-0"
                  >
                    {copySuccess ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5 text-fg-muted" />}
                    <span>{copySuccess ? '복사 완료' : 'Markdown 가이드 복사'}</span>
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

    </div>
  );
};
