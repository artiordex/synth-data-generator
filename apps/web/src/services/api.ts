import { DatasetProfile, JobStatus, SynthesisRequest, AuditLogEntry, ColumnDistribution, BatchStatus, BatchUploadItem, JobAssessmentReport } from '../types';

const BASE_URL = '/api/v1';

export async function uploadDatasets(files: File[]): Promise<BatchUploadItem[]> {
  const body = new FormData();
  files.forEach(file => body.append('files', file));
  const res = await fetch(`${BASE_URL}/datasets/upload-batch`, { method: 'POST', body });
  if (!res.ok) throw new Error('일괄 업로드 실패: ' + await res.text());
  return (await res.json()).files;
}

export async function startBatch(requests: SynthesisRequest[]): Promise<BatchStatus> {
  const res = await fetch(`${BASE_URL}/batches`, { method: 'POST',
    headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ requests }) });
  if (!res.ok) throw new Error('일괄 실행 실패: ' + await res.text());
  return res.json();
}

export async function getBatch(id: string): Promise<BatchStatus> {
  const res = await fetch(`${BASE_URL}/batches/${encodeURIComponent(id)}`);
  if (!res.ok) throw new Error('일괄 작업 조회 실패: ' + await res.text());
  return res.json();
}

export async function getBatchesList(): Promise<(BatchStatus & { created_at: string })[]> {
  const res = await fetch(`${BASE_URL}/batches`);
  if (!res.ok) throw new Error('일괄 작업 이력 조회 실패');
  return res.json();
}

export async function cancelBatch(id: string): Promise<BatchStatus> {
  const res = await fetch(`${BASE_URL}/batches/${encodeURIComponent(id)}/cancel`, { method: 'POST' });
  if (!res.ok) throw new Error('일괄 작업 취소 실패: ' + await res.text());
  return res.json();
}

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

export async function getDatasetProfile(filename: string): Promise<DatasetProfile> {
  const res = await fetch(`${BASE_URL}/datasets/profile?file_name=${encodeURIComponent(filename)}`);
  if (!res.ok) throw new Error('프로파일링 정보 로드 실패: ' + (await res.text()));
  return res.json();
}

export async function startSynthesis(req: SynthesisRequest): Promise<JobStatus> {
  const res = await fetch(`${BASE_URL}/synthesis/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error('합성 작업 시작 실패: ' + (await res.text()));
  return res.json();
}

export async function cancelSynthesis(jobId: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/synthesis/cancel/${jobId}`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('작업 취소 실패: ' + (await res.text()));
}

export async function getJobStatus(jobId: string): Promise<JobStatus> {
  const res = await fetch(`${BASE_URL}/jobs/${jobId}`);
  if (!res.ok) throw new Error('작업 상태 조회 실패: ' + (await res.text()));
  return res.json();
}

export async function listJobs(): Promise<JobStatus[]> {
  const res = await fetch(`${BASE_URL}/jobs`);
  if (!res.ok) throw new Error('작업 목록 로드 실패: ' + (await res.text()));
  return res.json();
}

export async function getAuditLogs(jobId: string): Promise<AuditLogEntry[]> {
  const res = await fetch(`${BASE_URL}/review/audit-logs/${jobId}`);
  if (!res.ok) return [];
  return res.json();
}

export function getDownloadUrl(path: string): string {
  if (path.startsWith(`${BASE_URL}/files/download`)) return path;
  return `${BASE_URL}/files/download?path=${encodeURIComponent(path)}`;
}

export async function getDummyDomains(): Promise<{ categories: string[]; total_count: number; grouped_domains: Record<string, any[]>; domains: any[] }> {
  const res = await fetch(`${BASE_URL}/dummy/domains`);
  if (!res.ok) throw new Error('도메인 사전 로드 실패');
  return res.json();
}

export async function getDummyTemplates(): Promise<{ templates: any[] }> {
  const res = await fetch(`${BASE_URL}/dummy/templates`);
  if (!res.ok) throw new Error('템플릿 로드 실패');
  return res.json();
}

export async function inferDummyColumn(columnName: string): Promise<{ column_name: string; inferred_domain: any }> {
  const res = await fetch(`${BASE_URL}/dummy/infer-column`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ column_name: columnName }),
  });
  if (!res.ok) throw new Error('컬럼 도메인 추론 실패');
  return res.json();
}

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

export async function compareSynthesisModels(fileName: string): Promise<any> {
  const res = await fetch(`${BASE_URL}/synthesis/compare-models`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ file_name: fileName, sample_rows: 300 }),
  });
  if (!res.ok) throw new Error('모델 비교 실패: ' + await res.text());
  return res.json();
}

export async function importDummySchema(sourceType: 'ddl' | 'json-schema' | 'openapi', content: string): Promise<any> {
  const res = await fetch(`${BASE_URL}/dummy/import-schema`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ source_type: sourceType, content }),
  });
  if (!res.ok) throw new Error('스키마 가져오기 실패: ' + await res.text());
  return res.json();
}

export async function generateDummySchema(schemaDefinition: any, targetRows: number, scenario: string): Promise<any> {
  const res = await fetch(`${BASE_URL}/dummy/generate-schema`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ schema_definition: schemaDefinition, target_rows: targetRows, scenario }),
  });
  if (!res.ok) throw new Error('다중 테이블 더미 생성 실패: ' + await res.text());
  return res.json();
}

export async function profileRelational(payload: any): Promise<any> {
  const res = await fetch(`${BASE_URL}/relational/profile`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error('관계 분석 실패: ' + await res.text());
  return res.json();
}

export async function generateRelational(payload: any): Promise<any> {
  const res = await fetch(`${BASE_URL}/relational/generate`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error('관계형 합성 실패: ' + await res.text());
  return res.json();
}

export async function generateTimeSeries(payload: any): Promise<any> {
  const res = await fetch(`${BASE_URL}/time-series/generate`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error('시계열 합성 실패: ' + await res.text());
  return res.json();
}

export async function getJobDistributions(jobId: string): Promise<{ job_id: string; columns: ColumnDistribution[] }> {
  const res = await fetch(`${BASE_URL}/jobs/${jobId}/distributions`);
  if (!res.ok) throw new Error('분포 비교 데이터 조회 실패');
  return res.json();
}

export async function getJobAssessment(jobId: string): Promise<JobAssessmentReport> {
  const res = await fetch(`${BASE_URL}/jobs/${jobId}/assessment`);
  if (!res.ok) throw new Error('자동 심의 판정 데이터 조회 실패');
  return res.json();
}

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

export async function getPseudonymHistory(): Promise<any[]> {
  const res = await fetch(`${BASE_URL}/datasets/pseudonymize/history`);
  if (!res.ok) throw new Error('가명처리 이력 조회 실패');
  return res.json();
}

export async function getDummyHistory(): Promise<any[]> {
  const res = await fetch(`${BASE_URL}/dummy/history`);
  if (!res.ok) throw new Error('더미데이터 이력 조회 실패');
  return res.json();
}

export async function getJobsList(): Promise<JobStatus[]> {
  const res = await fetch(`${BASE_URL}/jobs`);
  if (!res.ok) throw new Error('합성 작업 이력 조회 실패');
  return res.json();
}

export async function clearAllHistory(): Promise<{ status: string; deleted: Record<string, number> }> {
  const res = await fetch(`${BASE_URL}/history`, { method: 'DELETE' });
  if (!res.ok) throw new Error('통합 작업 이력 삭제 실패: ' + await res.text());
  return res.json();
}

export interface ConvertResponse {
  status: string;
  category: 'document' | 'dataset';
  file_name: string;
  original_filename: string;
  download_url: string;
  file_size: number;
  source_format: string;
  target_format: string;
  rows_count?: number;
  columns_count?: number;
  columns?: string[];
  preview?: Record<string, any>[];
  markdown_preview?: string;
  html_preview?: string;
  message: string;
}

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
      const errJson = await res.json();
      errMsg = errJson.detail || errMsg;
    } catch {
      errMsg = await res.text() || errMsg;
    }
    throw new Error(errMsg);
  }
  return res.json();
}

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

export async function getSurveyJobStatus(jobId: string): Promise<SurveyJobStatusResponse> {
  const res = await fetch(`${BASE_URL}/survey/status/${encodeURIComponent(jobId)}`);
  if (!res.ok) throw new Error('작업 상태 조회 실패: ' + await res.text());
  return res.json();
}



