/**
 * 파일명: index.ts
 * 경로: packages/contracts/src/index.ts
 * 목적: 프론트엔드와 백엔드가 공유하는 데이터 계약을 정의함
 * 작성자: 개발팀
 * 작성일: 2026-09-09
 * 수정일: 2026-09-09
 */
export type InformationType = "준식별자" | "일반정보";

export interface ReviewColumnMetadata {
  description?: string;
  information_type?: InformationType | string;
}

export interface ReviewMetadataInput {
  dataset_name?: string;
  special_notes?: string;
  overview?: string;
  privacy_plan?: string;
  columns?: Record<string, ReviewColumnMetadata>;
}

export interface ColumnInfo {
  name: string;
  inferred_type: "numerical" | "categorical" | "pii";
  null_count: number;
  unique_count: number;
  information_type: InformationType;
  pii_detected: boolean;
  pii_type: string;
  samples: string[];
  samples_truncated?: boolean;
  unique_values_total?: number;
}

export interface DatasetProfile {
  filename: string;
  row_count: number;
  column_count: number;
  sha256: string;
  columns: ColumnInfo[];
  preview: Record<string, any>[];
  detected_pii: Record<string, any>;
  suggested_categorical: string[];
  suggested_numerical: string[];
}

export interface SynthesisRequest {
  duplicate_policy?: 'balanced' | 'strict';
  review_metadata?: ReviewMetadataInput;
  file_name: string;
  original_filename?: string;
  department_name: string;
  project_purpose: string;
  model_type: "statistical" | "gaussian_copula" | "ctgan" | "tvae";
  target_rows: number;
  dp_enabled: boolean;
  eps: number;
  quality_threshold: number;
  selected_columns?: string[];
  categorical_columns?: string[];
  numerical_columns?: string[];
  preserve_null_columns?: string[];
  conditions?: Record<string, any>;
  constraints?: Array<Record<string, any>>;
  epochs?: number;
  batch_size?: number;
  pac?: number;
  seed?: number;
  sampling_batch_size?: number;
  max_sampling_attempts?: number;
  enable_gpu?: boolean;
  evaluation_excluded_columns?: string[];
}

export interface JobStatus {
  id: string;
  status: "pending" | "processing" | "completed" | "failed" | "canceled";
  progress: number;
  message: string;
  original_filename: string;
  file_path: string;
  file_sha256: string;
  department_name: string;
  project_purpose: string;
  model_type: string;
  target_rows: number;
  eps: number;
  quality_threshold: number;
  quality_score?: number;
  reid_risk?: number | null;
  assessment_passed?: boolean;
  assessment_grade?: string;
  assessment_score?: number | null;
  package_dir?: string;
  package_zip?: string;
  package_folders?: Record<string, string>;
  hwp_files?: Record<string, string>;
  error?: string;
  created_at: string;
  updated_at: string;
}

export interface AuditLogEntry {
  id?: number;
  job_id: string;
  action: string;
  actor: string;
  detail: string;
  created_at: string;
}
