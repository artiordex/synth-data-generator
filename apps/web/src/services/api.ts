/**
 * 파일명: api.ts
 * 경로: apps/web/src/services/api.ts
 * 목적: 프론트엔드의 백엔드 API 호출과 응답 타입을 제공함
 * 작성자: 개발팀
 * 작성일: 2026-09-09
 * 수정일: 2026-09-16
 */
import { DatasetProfile, JobStatus, SynthesisRequest, AuditLogEntry, ColumnDistribution, BatchStatus, BatchUploadItem, JobAssessmentReport, SyntheticPreviewData } from '../types';

const BASE_URL = '/api/v1';

// 여러 데이터 파일을 일괄 업로드하고 프로파일 정보를 수신함
export async function uploadDatasets(files: File[]): Promise<BatchUploadItem[]> {
  // 여러 데이터 파일을 일괄 업로드함
  const body = new FormData();
  files.forEach(file => body.append('files', file));
  const res = await fetch(`${BASE_URL}/datasets/upload-batch`, { method: 'POST', body });
  if (!res.ok) throw new Error('일괄 업로드 실패: ' + await res.text());
  return (await res.json()).files;
}

// 등록된 여러 데이터셋에 대한 배치 합성 작업을 시작함
export async function startBatch(requests: SynthesisRequest[]): Promise<BatchStatus> {
  const res = await fetch(`${BASE_URL}/batches`, { method: 'POST',
    headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ requests }) });
  if (!res.ok) throw new Error('일괄 실행 실패: ' + await res.text());
  return res.json();
}

// 지정한 배치 작업 ID의 상세 진행 상태를 조회함
export async function getBatch(id: string): Promise<BatchStatus> {
  const res = await fetch(`${BASE_URL}/batches/${encodeURIComponent(id)}`);
  if (!res.ok) throw new Error('일괄 작업 조회 실패: ' + await res.text());
  return res.json();
}

// 최근 실행된 일괄(배치) 작업 목록을 조회함
export async function getBatchesList(): Promise<(BatchStatus & { created_at: string })[]> {
  const res = await fetch(`${BASE_URL}/batches`);
  if (!res.ok) throw new Error('일괄 작업 이력 조회 실패');
  return res.json();
}

// 진행 중인 일괄(배치) 합성 작업을 즉시 취소함
export async function cancelBatch(id: string): Promise<BatchStatus> {
  const res = await fetch(`${BASE_URL}/batches/${encodeURIComponent(id)}/cancel`, { method: 'POST' });
  if (!res.ok) throw new Error('일괄 작업 취소 실패: ' + await res.text());
  return res.json();
}

// 단일 원본 데이터셋 파일을 서버에 안전하게 업로드함
export async function uploadDataset(file: File): Promise<{ filename: string; path: string; sha256: string; size_bytes: number }> {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`${BASE_URL}/datasets/upload`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) throw new Error('파일 업로드 실패: ' + (await res.text()));
  return res.json();
}

// 업로드된 데이터셋의 컬럼 유형, 결측치 및 프로파일 정보를 조회함
export async function getDatasetProfile(filename: string, pseudonym = false): Promise<DatasetProfile> {
  const res = await fetch(`${BASE_URL}/datasets/profile?file_name=${encodeURIComponent(filename)}${pseudonym ? '&pseudonym=true' : ''}`);
  if (!res.ok) throw new Error('프로파일링 정보 로드 실패: ' + (await res.text()));
  return res.json();
}

// 정형 데이터 합성 작업을 등록하고 비동기 생성을 시작함
export async function startSynthesis(req: SynthesisRequest): Promise<JobStatus> {
  const res = await fetch(`${BASE_URL}/synthesis/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error('합성 작업 시작 실패: ' + (await res.text()));
  return res.json();
}

// 실행 중인 정형 데이터 합성 작업을 취소함
export async function cancelSynthesis(jobId: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/synthesis/cancel/${jobId}`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('작업 취소 실패: ' + (await res.text()));
}

// 특정 합성 작업 ID의 현재 진행률 및 상태를 조회함
export async function getJobStatus(jobId: string): Promise<JobStatus> {
  const res = await fetch(`${BASE_URL}/jobs/${jobId}`);
  if (!res.ok) throw new Error('작업 상태 조회 실패: ' + (await res.text()));
  return res.json();
}

// 최근 수행된 합성 작업 목록 전체를 조회함
export async function listJobs(): Promise<JobStatus[]> {
  const res = await fetch(`${BASE_URL}/jobs`);
  if (!res.ok) throw new Error('작업 목록 로드 실패: ' + (await res.text()));
  return res.json();
}

// 작업 수행에 대한 시스템 감사(Audit) 로그 목록을 조회함
export async function getAuditLogs(jobId: string): Promise<AuditLogEntry[]> {
  const res = await fetch(`${BASE_URL}/review/audit-logs/${jobId}`);
  if (!res.ok) return [];
  return res.json();
}

// 결과 산출물 파일의 다운로드 URL 경로를 반환함
export function getDownloadUrl(path: string): string {
  if (path.startsWith(`${BASE_URL}/files/download`)) return path;
  return `${BASE_URL}/files/download?path=${encodeURIComponent(path)}`;
}

// 파일 다운로드 URL의 유효성 및 실제 접근 가능 여부를 검증함
export async function verifyDownloadUrl(path: string): Promise<boolean> {
  try {
    const url = getDownloadUrl(path);
    const res = await fetch(url, { method: 'HEAD' });
    return res.ok;
  } catch {
    return false;
  }
}

// 지원하는 더미 데이터 도메인 목록을 조회함
export async function getDummyDomains(): Promise<{ categories: string[]; total_count: number; grouped_domains: Record<string, any[]>; domains: any[] }> {
  const res = await fetch(`${BASE_URL}/dummy/domains`);
  if (!res.ok) throw new Error('도메인 사전 로드 실패');
  return res.json();
}

// 특정 도메인에 대한 표준 더미 데이터 템플릿 목록을 조회함
export async function getDummyTemplates(): Promise<{ templates: any[] }> {
  const res = await fetch(`${BASE_URL}/dummy/templates`);
  if (!res.ok) throw new Error('템플릿 로드 실패');
  return res.json();
}

// 컬럼명과 샘플 데이터를 기반으로 적합한 더미 데이터 생성 규칙을 추론함
export async function inferDummyColumn(columnName: string): Promise<{ column_name: string; inferred_domain: any }> {
  const res = await fetch(`${BASE_URL}/dummy/infer-column`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ column_name: columnName }),
  });
  if (!res.ok) throw new Error('컬럼 도메인 추론 실패');
  return res.json();
}

// 설정된 스키마와 규칙에 따라 더미 데이터를 생성함
export async function generateDummyData(payload: {
  table_name: string;
  columns: { name: string; domain_id?: string; rule?: any; primary_key?: boolean; unique?: boolean; nullable?: boolean; constraints?: any }[];
  target_rows: number;
  export_format: string;
  scenario?: string;
}): Promise<{
  status: string;
  table_name: string;
  rows_generated: number;
  columns: string[];
  preview: Record<string, any>[];
  download_url: string;
  file_name: string;
  file_path: string;
}> {
  const res = await fetch(`${BASE_URL}/dummy/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error('더미 데이터 생성 실패: ' + (await res.text()));
  return res.json();
}

// 여러 합성 알고리즘 모델 간 충실도 및 품질 지표를 비교함
export async function compareSynthesisModels(fileName: string): Promise<any> {
  const res = await fetch(`${BASE_URL}/synthesis/compare-models`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ file_name: fileName, sample_rows: 300 }),
  });
  if (!res.ok) throw new Error('모델 비교 실패: ' + await res.text());
  return res.json();
}

// 외부 DDL 또는 파일로부터 더미 데이터 스키마를 가져옴
export async function importDummySchema(sourceType: 'ddl' | 'json-schema' | 'openapi', content: string): Promise<any> {
  const res = await fetch(`${BASE_URL}/dummy/import-schema`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ source_type: sourceType, content }),
  });
  if (!res.ok) throw new Error('스키마 가져오기 실패: ' + await res.text());
  return res.json();
}

// 도메인과 템플릿 설정을 기반으로 더미 데이터 생성 스키마를 구성함
export async function generateDummySchema(schemaDefinition: any, targetRows: number, scenario: string): Promise<any> {
  const res = await fetch(`${BASE_URL}/dummy/generate-schema`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ schema_definition: schemaDefinition, target_rows: targetRows, scenario }),
  });
  if (!res.ok) throw new Error('다중 테이블 더미 생성 실패: ' + await res.text());
  return res.json();
}

// 관계형 다중 테이블 간 참조 무결성 및 외래키 구조를 프로파일링함
export async function profileRelational(payload: any): Promise<any> {
  const res = await fetch(`${BASE_URL}/relational/profile`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error('관계 분석 실패: ' + await res.text());
  return res.json();
}

// 외래키 관계를 준수하며 다중 관계형 테이블 합성 데이터를 생성함
export async function generateRelational(payload: any): Promise<any> {
  const res = await fetch(`${BASE_URL}/relational/generate`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error('관계형 합성 실패: ' + await res.text());
  return res.json();
}

// 시계열 데이터의 시간 순서 및 연속성을 보존하며 합성 데이터를 생성함
export async function generateTimeSeries(payload: any): Promise<any> {
  const res = await fetch(`${BASE_URL}/time-series/generate`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error('시계열 합성 실패: ' + await res.text());
  return res.json();
}

// 원본 데이터와 합성 데이터 간 컬럼별 통계 분포를 비교 조회함
export async function getJobDistributions(jobId: string): Promise<{ job_id: string; columns: ColumnDistribution[] }> {
  const res = await fetch(`${BASE_URL}/jobs/${jobId}/distributions`);
  if (!res.ok) throw new Error('분포 비교 데이터 조회 실패');
  return res.json();
}

// 합성 작업 결과의 품질 및 프라이버시 종합 평가 리포트를 조회함
export async function getJobAssessment(jobId: string): Promise<JobAssessmentReport> {
  const res = await fetch(`${BASE_URL}/jobs/${jobId}/assessment`);
  if (!res.ok) throw new Error('자동 심의 판정 데이터 조회 실패');
  return res.json();
}

// 생성된 합성 데이터셋의 상위 레코드 샘플 미리보기를 조회함
export async function getJobPreview(jobId: string, limit = 15): Promise<SyntheticPreviewData> {
  const res = await fetch(`${BASE_URL}/jobs/${jobId}/preview?limit=${limit}`);
  if (!res.ok) throw new Error('합성 데이터 샘플 미리보기 조회 실패');
  return res.json();
}

// 정형 데이터 컬럼별 가명화 기법을 적용하고 지정 포맷으로 내보냄
export async function pseudonymizeDataset(payload: {
  file_name: string;
  pii_actions: Record<string, string>;
  export_format: string;
  project_id?: string;
  token_key_version?: string;
  quasi_identifiers?: string[];
  sensitive_columns?: string[];
}): Promise<{
  status: string;
  file_name: string;
  download_url: string;
  rows_count: number;
  columns: string[];
  summary: Record<string, any>;
  original_preview: Record<string, any>[];
  pseudonymized_preview: Record<string, any>[];
  privacy_metrics?: Record<string, any>;
}> {
  const res = await fetch(`${BASE_URL}/datasets/pseudonymize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error('가명화 처리 실패: ' + (await res.text()));
  return res.json();
}

// 최근 수행된 데이터셋 가명화 작업 이력 목록을 조회함
export async function getPseudonymHistory(): Promise<any[]> {
  const res = await fetch(`${BASE_URL}/datasets/pseudonymize/history`);
  if (!res.ok) throw new Error('가명처리 이력 조회 실패');
  return res.json();
}

// 최근 수행된 더미 데이터 생성 작업 이력 목록을 조회함
export async function getDummyHistory(): Promise<any[]> {
  const res = await fetch(`${BASE_URL}/dummy/history`);
  if (!res.ok) throw new Error('더미데이터 이력 조회 실패');
  return res.json();
}

// 전체 합성 작업 목록 및 요약 상태를 조회함
export async function getJobsList(): Promise<JobStatus[]> {
  const res = await fetch(`${BASE_URL}/jobs`);
  if (!res.ok) throw new Error('합성 작업 이력 조회 실패');
  return res.json();
}

// 모든 작업 이력(합성, 가명화, 더미)을 일괄 삭제 초기화함
export async function clearAllHistory(): Promise<{ status: string; deleted: Record<string, number> }> {
  const res = await fetch(`${BASE_URL}/history`, { method: 'DELETE' });
  if (!res.ok) throw new Error('통합 작업 이력 삭제 실패: ' + await res.text());
  return res.json();
}

// 선택한 작업 이력 항목들을 식별자 기준으로 삭제함
export async function deleteSelectedHistory(items: Array<{ type: string; id: string; filename?: string }>): Promise<{ status: string; deleted: Record<string, number> }> {
  const res = await fetch(`${BASE_URL}/history/delete-selected`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ items }),
  });
  if (!res.ok) throw new Error('선택 이력 삭제 실패: ' + await res.text());
  return res.json();
}

export interface ConvertResponse {
  status: string;
  category: 'document' | 'dataset';
  file_name: string;
  original_filename: string;
  original_file_url?: string;
  download_url: string;
  download_ready?: boolean;
  file_size: number;
  source_format: string;
  target_format: string;
  rows_count?: number;
  columns_count?: number;
  columns?: string[];
  preview?: Record<string, any>[];
  markdown_preview?: string;
  html_preview?: string;
  document_structure?: {
    format: string;
    parser_engines: string[];
    fidelity_level: 'high' | 'best_effort' | string;
    fidelity_target: string;
    pages_count: number;
    block_count: number;
    table_count: number;
    image_count: number;
    text_length: number;
    blocks?: Array<Record<string, any>>;
    tables?: Array<Record<string, any>>;
    ocr_engine?: string;
    quality?: {
      source_format: string;
      text_coverage: number | null;
      metric: string;
      warnings: string[];
      ocr_status?: string;
      ocr_engine?: string;
      average_confidence?: number | null;
      requires_review?: boolean;
      ocr_review_pages?: number[];
      page_progress?: Array<{
        page: number;
        progress: number;
        status: string;
        message: string;
      }>;
      low_confidence_regions?: Array<{
        page: number;
        confidence: number | null;
        label: string;
        reason: string;
      }>;
    };
  };
  message: string;
}


// 업로드된 문서 또는 정형 데이터 파일을 대상 포맷으로 변환 요청함
export async function convertFile(params: {
  file: File;
  targetFormat: string;
  encoding?: string;
  tableName?: string;
}): Promise<ConvertResponse> {
  const formData = new FormData();
  formData.append('file', params.file);
  formData.append('target_format', params.targetFormat);
  if (params.encoding) formData.append('encoding', params.encoding);
  if (params.tableName) formData.append('table_name', params.tableName);

  const res = await fetch(`${BASE_URL}/converter/convert`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    let errMsg = '변환 실패';
    try {
      const text = await res.text();
      try {
        const errJson = JSON.parse(text);
        errMsg = errJson.detail || errJson.message || text;
      } catch {
        errMsg = text || `HTTP ${res.status} 오류가 발생했습니다.`;
      }
    } catch {
      errMsg = `HTTP ${res.status} 오류가 발생했습니다.`;
    }
    throw new Error(errMsg);
  }
  return res.json();
}

// 과거 수행된 문서 및 데이터 변환 작업 이력 목록을 조회함
export async function getConverterHistory(): Promise<any[]> {
  const res = await fetch(`${BASE_URL}/converter/history`);
  if (!res.ok) throw new Error('변환 이력 조회 실패');
  return res.json();
}

export interface SurveyInspectionResponse {
  modules: Array<{
    file_key: string;
    original_filename: string;
    sheet_name: string;
    columns: string[];
    row_count: number;
    column_count: number;
    unique_columns: string[];
  }>;
  common_keys: string[];
  is_aligned: boolean;
  total_rows: number;
  total_columns: number;
  preview_columns: string[];
  sample_preview: Record<string, any>[];
  detected_rules?: Array<{
    rule_id: string;
    condition_col: string;
    condition_val: string;
    target_col: string;
    target_val: string;
    confidence: number;
    support: number;
    description: string;
  }>;
  likert_columns_count?: number;
  likert_column_names?: string[];
  k_anonymity_risk?: Record<string, any>;
}

export interface SurveyJobStatusResponse {
  job_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  message: string;
  target_rows?: number;
  model_type?: string;
  file_count?: number;
  tables?: Array<{
    file_key: string;
    filename: string;
    rows: number;
    columns: number;
    download_url: string;
  }>;
  quality?: {
    overall_quality: number | null;
    k_anonymity?: Record<string, any>;
    utility?: Record<string, any>;
    safety?: Record<string, any>;
  };
  logic_integrity?: {
    integrity_score: number | null;
    passed: boolean | null;
    total_checked_rules: number;
    total_applicable_rows: number;
    total_violations: number;
    rule_details?: Array<{
      description: string;
      applicable_rows: number;
      violations: number;
      compliance_rate: number;
    }>;
  };
  k_anonymity?: Record<string, any>;
  extra_meta?: Record<string, any>;
  download_url?: string;
  error?: string;
}

// 설문조사 데이터셋의 문항 모듈 및 분기 논리를 분석함
export async function inspectSurveyModules(fileNames: string[]): Promise<SurveyInspectionResponse> {
  const res = await fetch(`${BASE_URL}/survey/inspect`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ file_names: fileNames }),
  });
  if (!res.ok) {
    let errMsg = '설문 분석 실패';
    try { const j = await res.json(); errMsg = j.detail || errMsg; } catch { errMsg = await res.text() || errMsg; }
    throw new Error(errMsg);
  }
  return res.json();
}

// 설문조사 응답 상관성을 보존하는 결합 합성 작업을 요청함
export async function generateSurveySynthesis(params: {
  file_names: string[];
  target_rows: number;
  model_type: string;
  epochs?: number;
  batch_size?: number;
  pac?: number;
  seed?: number;
  apply_logic_rules?: boolean;
  preserve_likert_order?: boolean;
  protect_k_anonymity?: boolean;
  dp_enabled?: boolean;
  eps?: number;
  department_name?: string;
  project_purpose?: string;
}): Promise<{ job_id: string; status: string; message: string }> {
  const res = await fetch(`${BASE_URL}/survey/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    let errMsg = '설문 합성 시작 실패';
    try { const j = await res.json(); errMsg = j.detail || errMsg; } catch { errMsg = await res.text() || errMsg; }
    throw new Error(errMsg);
  }
  return res.json();
}

// 설문 합성 작업의 비동기 진행 상태 및 로그를 조회함
export async function getSurveyJobStatus(jobId: string): Promise<SurveyJobStatusResponse> {
  const res = await fetch(`${BASE_URL}/survey/status/${encodeURIComponent(jobId)}`);
  if (!res.ok) throw new Error('작업 상태 조회 실패: ' + await res.text());
  return res.json();
}

export interface ReadinessCheckItem {
  item: string;
  status: 'pass' | 'warn' | 'fail';
  message: string;
}

export interface GenerateAiRuleGuideRequest {
  file_base64?: string;
  payload_text: string;
  format?: string;
  data_category?: 'file' | 'api';
  preset_style?: string;
  document_title?: string;
  orientation?: string;
  is_large_dataset?: boolean;
  file_size_bytes?: number;
  estimated_total_rows?: number;
  api_key?: string;
  model?: string;
  provider?: 'gemini' | 'openai' | 'auto' | 'local';
}

export interface GenerateAiRuleGuideResponse {
  json_ld: string;
  metadata_xml: string;
  canonical_metadata: Record<string, unknown>;
  success: boolean;
  ai_powered: boolean;
  document_title: string;
  preset_style: string;
  orientation: string;
  columns: Array<{
    key: string;
    label: string;
    inferredType: string;
    align: 'left' | 'center' | 'right';
    widthPercent: number;
    formatType: 'text' | 'number_comma' | 'date_standard' | 'badge';
    include: boolean;
    sampleValues: string[];
  }>;
  markdown_guide: string;
  json_rule: string;
  ai_summary: string;
  data_category?: 'file' | 'api';
  is_large_dataset?: boolean;
  ai_readiness_score?: number;
  ai_readiness_checklist?: ReadinessCheckItem[];
  large_data_guide?: string | null;
}

// OpenAI API를 통해 CSV/JSON/XML 데이터 기반 HWPX 롤 가이드 생성을 요청함
export async function generateAiRuleGuide(
  params: GenerateAiRuleGuideRequest
): Promise<GenerateAiRuleGuideResponse> {
  const res = await fetch(`${BASE_URL}/ai-guide/generate-rule`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    let errMsg = 'AI 롤 가이드 생성 실패';
    try {
      const j = await res.json();
      errMsg = j.detail || errMsg;
    } catch {
      errMsg = (await res.text()) || errMsg;
    }
    throw new Error(errMsg);
  }
  return res.json();
}




export async function exportAiGuideHwpx(markdown: string): Promise<Blob> {
  const res = await fetch(`${BASE_URL}/ai-guide/export-hwpx`, {
    method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({markdown}),
  });
  if (!res.ok) throw new Error('HWPX 생성 실패: ' + await res.text());
  return res.blob();
}

export interface AiGuideFieldAnnotation {
  label: string;
  description: string;
  unit: string;
  codes: string;
}

export interface AiGuideTemplateRequest {
  canonical_metadata: Record<string, unknown>;
  metadata: Record<string, string>;
  field_annotations: Record<string, AiGuideFieldAnnotation>;
}

export async function exportAiGuideTemplate(params: AiGuideTemplateRequest): Promise<Blob> {
  const res = await fetch(`${BASE_URL}/ai-guide/export-template-hwpx`, {
    method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(params),
  });
  if (!res.ok) {
    const error = await res.json();
    throw new Error(typeof error.detail === 'string' ? error.detail : '템플릿 가이드 생성 실패');
  }
  return res.blob();
}

export async function parseAiGuideTemplate(fileBase64: string): Promise<{
  title: string;
  document_status: string;
  dictionary: unknown[];
  review_required: string[];
}> {
  const res = await fetch(`${BASE_URL}/ai-guide/parse-template-hwpx`, {
    method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({file_base64: fileBase64}),
  });
  if (!res.ok) {
    const error = await res.json();
    throw new Error(typeof error.detail === 'string' ? error.detail : 'HWPX 재파싱 실패');
  }
  return res.json();
}

export interface ParsedSimpleTable {
  title: string;
  headers: string[];
  rows: string[][];
  category: string;
}

export interface GovDocParseResult {
  filename: string;
  format: string;
  title: string;
  paragraph_count: number;
  total_tables_count: number;
  overview_tables: ParsedSimpleTable[];
  operation_tables: ParsedSimpleTable[];
  parameter_tables: ParsedSimpleTable[];
  payload_data_tables: ParsedSimpleTable[];
  error_code_tables: ParsedSimpleTable[];
  quality_tables: ParsedSimpleTable[];
  other_tables: ParsedSimpleTable[];
}

export async function parseGovDocument(params: {
  file_base64?: string;
  text_content?: string;
  format: string;
  filename: string;
}): Promise<{ success: boolean; data: GovDocParseResult; markdown: string }> {
  const res = await fetch(`${BASE_URL}/ai-guide/parse-document`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    const error = await res.json();
    throw new Error(typeof error.detail === 'string' ? error.detail : '문서 표 파싱 실패');
  }
  return res.json();
}

export async function exportParsedDocx(params: {
  file_base64?: string;
  text_content?: string;
  format: string;
  filename: string;
}): Promise<Blob> {
  const res = await fetch(`${BASE_URL}/ai-guide/export-parsed-docx`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    const error = await res.json();
    throw new Error(typeof error.detail === 'string' ? error.detail : 'DOCX 보고서 생성 실패');
  }
  return res.blob();
}

