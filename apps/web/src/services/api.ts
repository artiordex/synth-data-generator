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
  columns: { name: string; domain_id?: string; rule?: any }[];
  target_rows: number;
  export_format: string;
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
}): Promise<{
  status: string;
  file_name: string;
  download_url: string;
  rows_count: number;
  columns: string[];
  summary: Record<string, any>;
  original_preview: Record<string, any>[];
  pseudonymized_preview: Record<string, any>[];
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
