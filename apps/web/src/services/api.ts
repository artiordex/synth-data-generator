import { DatasetProfile, JobStatus, SynthesisRequest, AuditLogEntry } from '../types';

const BASE_URL = '/api/v1';

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
