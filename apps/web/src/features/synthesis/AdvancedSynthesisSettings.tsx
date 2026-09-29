/**
 * 파일명: AdvancedSynthesisSettings.tsx
 * 경로: apps/web/src/features/synthesis/AdvancedSynthesisSettings.tsx
 * 목적: 합성 학습·평가 상세 설정을 구성함
 * 작성자: 개발팀
 * 작성일: 2026-09-09
 * 수정일: 2026-09-09
 */
import React from 'react';
import { DatasetProfile, ReviewMetadataInput, SynthesisRequest } from '../../types';
import { AdvancedSynthesisColumnTable } from './AdvancedSynthesisColumnTable';
import { trainingNumberFields } from './synthesisValidation';

export type SynthesisOptions = Pick<SynthesisRequest, 'epochs' | 'batch_size' | 'pac' | 'seed' |
  'sampling_batch_size' | 'max_sampling_attempts' | 'enable_gpu' | 'evaluation_excluded_columns' |
  'categorical_columns' | 'numerical_columns' | 'preserve_null_columns' | 'duplicate_policy'>;

export const defaultSynthesisOptions: SynthesisOptions = {
  epochs: 30,
  batch_size: 64,
  pac: 1,
  seed: 42,
  sampling_batch_size: 800,
  max_sampling_attempts: 10,
  enable_gpu: false,
  duplicate_policy: 'balanced',
};

type AdvancedSynthesisSettingsProps = {
  options: SynthesisOptions;
  onChange: (value: SynthesisOptions) => void;
  profile: DatasetProfile | null;
  isDarkMode: boolean;
  reviewMetadata?: ReviewMetadataInput;
  onReviewMetadataChange?: (value: ReviewMetadataInput) => void;
};

export function AdvancedSynthesisSettings({
  options,
  onChange,
  profile,
  isDarkMode,
  reviewMetadata,
  onReviewMetadataChange,
}: AdvancedSynthesisSettingsProps) {
  const fieldStyle = `rounded border p-2 ${isDarkMode ? 'bg-slate-950 border-slate-700' : 'bg-white border-slate-300'}`;

  return (
    <details className="ui-panel p-6">
      <summary className="cursor-pointer text-sm font-bold">학습·평가 상세 설정</summary>
      {profile?.notebook_preset?.name && (
        <p className="mt-3 text-sm text-sky-600">
          노트북 설정 자동 적용: {profile.notebook_preset.name}. 아래에서 변경한 값이 우선합니다.
        </p>
      )}
      <p className="my-3 text-xs">
        결측치가 ‘비적용’을 뜻하는 항목은 의미 보존을 선택하세요. sin/cos 등 학습용 파생변수는 평가에서 제외할 수 있습니다.
      </p>
      <div className="grid grid-cols-2 gap-3 text-xs md:grid-cols-3">
        {trainingNumberFields.map((field) => (
          <label key={field.key} className="grid gap-1">
            {field.label}
            <input
              aria-label={field.label}
              className={fieldStyle}
              type="number"
              min={field.min}
              step={1}
              max={field.max}
              value={options[field.key] ?? defaultSynthesisOptions[field.key]}
              onChange={(event) => onChange({ ...options, [field.key]: Number(event.target.value) })}
            />
          </label>
        ))}
      </div>
      <label className="my-4 flex items-center gap-2 text-xs">
        <input
          type="checkbox"
          checked={options.enable_gpu ?? false}
          onChange={(event) => onChange({ ...options, enable_gpu: event.target.checked })}
        />
        사용 가능한 GPU 사용 (기본 CPU)
      </label>
      <label className="mb-3 grid gap-1 text-xs">
        원본 일치 행 처리
        <select
          className={fieldStyle}
          value={options.duplicate_policy ?? 'balanced'}
          onChange={(event) => onChange({ ...options, duplicate_policy: event.target.value as 'balanced' | 'strict' })}
        >
          <option value="balanced">균형: 원본에서 5회 이상 나타난 조합은 유지, 희귀 일치 행 제거</option>
          <option value="strict">엄격: 원본 일치 행 모두 제거</option>
        </select>
      </label>
      <p className="mb-3 text-xs">
        균형 모드에서 유지한 원본 일치 행은 보고서에 기록하고 검토 필요로 표시합니다. 새 행을 보충해도 부족하면 실패 사유를 표시합니다. 안전성 평가는 50행 이상 입력에서 학습 전 20%를 분리하며, 평가 자료가 부족하면 미측정으로 표시합니다.
      </p>
      <AdvancedSynthesisColumnTable
        options={options}
        onChange={onChange}
        profile={profile}
        isDarkMode={isDarkMode}
        reviewMetadata={reviewMetadata}
        onReviewMetadataChange={onReviewMetadataChange}
      />
    </details>
  );
}
