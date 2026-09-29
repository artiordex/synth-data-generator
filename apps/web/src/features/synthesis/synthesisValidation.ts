/**
 * 파일명: synthesisValidation.ts
 * 경로: apps/web/src/features/synthesis/synthesisValidation.ts
 * 목적: 합성 요청 수치 옵션의 유효성을 확인함
 * 작성자: 개발팀
 * 작성일: 2026-09-29
 * 수정일: 2026-09-29
 */
import type { SynthesisOptions } from './AdvancedSynthesisSettings';

type TrainingNumberField = {
  key: keyof Pick<
    SynthesisOptions,
    'epochs' | 'batch_size' | 'pac' | 'seed' | 'sampling_batch_size' | 'max_sampling_attempts'
  >;
  label: string;
  min: number;
  max?: number;
};

/** 학습 및 샘플링 숫자 설정의 검증 범위를 정의함 */
export const trainingNumberFields: TrainingNumberField[] = [
  { key: 'epochs', label: '학습 반복 수', min: 1 },
  { key: 'batch_size', label: '학습 배치 크기', min: 1 },
  { key: 'pac', label: 'CTGAN PAC', min: 1 },
  { key: 'seed', label: '재현용 시드', min: 0, max: 4294967295 },
  { key: 'sampling_batch_size', label: '최소 생성 묶음 크기', min: 1 },
  { key: 'max_sampling_attempts', label: '최대 생성 시도 횟수', min: 1, max: 100 },
];

export type SynthesisValidationInput = {
  targetRows: number;
  qualityThreshold: number;
  dpEnabled: boolean;
  dpEpsilon: number;
  options: SynthesisOptions;
};

/** 합성 요청의 행 수, 임계값, 모델 수치 설정을 검사함 */
export function validateSynthesisSettings({
  targetRows,
  qualityThreshold,
  dpEnabled,
  dpEpsilon,
  options,
}: SynthesisValidationInput): string[] {
  const errors: string[] = [];

  if (!Number.isInteger(targetRows) || targetRows <= 0) {
    errors.push('합성 생성 행 수는 1 이상의 정수로 입력해 주세요.');
  }

  if (!Number.isFinite(qualityThreshold) || qualityThreshold < 0.5 || qualityThreshold > 0.99) {
    errors.push('심의 통과 품질 임계점은 0.5~0.99 범위로 입력해 주세요.');
  }

  if (dpEnabled && (!Number.isFinite(dpEpsilon) || dpEpsilon < 0.1 || dpEpsilon > 5.0)) {
    errors.push('차분 프라이버시 예산(Epsilon)은 0.1~5.0 범위로 입력해 주세요.');
  }

  for (const field of trainingNumberFields) {
    const value = options[field.key];
    if (
      typeof value !== 'number' ||
      !Number.isFinite(value) ||
      !Number.isInteger(value) ||
      value < field.min ||
      (field.max !== undefined && value > field.max)
    ) {
      errors.push(
        field.max === undefined
          ? `${field.label}은(는) ${field.min} 이상의 정수로 입력해 주세요.`
          : `${field.label}은(는) ${field.min}~${field.max} 범위의 정수로 입력해 주세요.`,
      );
    }
  }

  return errors;
}
