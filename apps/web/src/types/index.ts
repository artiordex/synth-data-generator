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
  notebook_preset?: { name: string | null; options: Partial<SynthesisRequest> };
}

export interface SynthesisRequest {
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
  duplicate_policy?: 'balanced' | 'strict';
}

export interface BatchUploadItem {
  original_filename: string;
  filename?: string;
  profile?: DatasetProfile;
  error: string | null;
}

export interface BatchStatus {
  id: string;
  status: 'pending' | 'processing' | 'completed' | 'completed_with_errors' | 'failed' | 'canceled';
  total: number;
  finished: number;
  completed: number;
  failed: number;
  canceled: number;
  progress: number;
  jobs: JobStatus[];
  package_zip: string | null;
  error: string | null;
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

export interface AssessmentIssue {
  code: string;
  label: string;
  severity?: "pass" | "review" | "fail" | string;
  detail: string;
  value?: number | null;
  threshold?: number | null;
  errors?: Record<string, string>;
}

export interface JobAssessmentReport {
  job_id: string;
  assessment: {
    overall_status?: string;
    overall_label?: string;
    score?: number | null;
    grade?: string | null;
    passed?: boolean;
    recommendation?: string;
    note?: string;
    issues?: AssessmentIssue[];
    summary?: Record<string, any>;
  } | null;
  quality_score?: number | null;
  safety?: Record<string, any>;
  utility?: Record<string, any>;
  guardrails?: Record<string, any>;
  config?: Record<string, any>;
}

export interface DistributionBin {
  label: string;
  low?: number | null;
  high?: number | null;
  original_count: number;
  synthetic_count: number;
  original_pct: number;
  synthetic_pct: number;
  diff_pct: number;
}

export interface NumericStats {
  count: number;
  null_count?: number;
  mean: number | null;
  std: number;
  median: number | null;
  min: number | null;
  max: number | null;
}

export interface CategoricalStats {
  count: number;
  unique: number;
  top: string;
  top_pct: number;
}

export interface ColumnDistribution {
  name: string;
  type: "numerical" | "categorical";
  jsd: number;
  similarity_pct: number;
  stats: {
    original: NumericStats | CategoricalStats;
    synthetic: NumericStats | CategoricalStats;
  };
  bins: DistributionBin[];
}
