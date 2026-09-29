/**
 * 파일명: StepConfig.tsx
 * 경로: apps/web/src/features/synthesis/StepConfig.tsx
 * 목적: 합성 설정 단계를 조합함
 * 작성자: 개발팀
 * 작성일: 2026-09-09
 * 수정일: 2026-09-09
 */
import React, { useState } from 'react';
import { DatasetProfile, ReviewMetadataInput } from '../../types';
import { AdvancedSynthesisSettings, defaultSynthesisOptions, SynthesisOptions } from './AdvancedSynthesisSettings';
import { ReviewMetadataEditor } from './ReviewMetadataEditor';
import { SynthesisModelSettings } from './SynthesisModelSettings';
import { SynthesisProjectSettings } from './SynthesisProjectSettings';
import { validateSynthesisSettings } from './synthesisValidation';

interface StepConfigProps {
  synthesisOptions: SynthesisOptions;
  setSynthesisOptions: (value: SynthesisOptions) => void;
  profile: DatasetProfile | null;
  fileName: string;
  reviewMetadata: ReviewMetadataInput;
  setReviewMetadata: (value: ReviewMetadataInput) => void;
  isDarkMode: boolean;
  departmentName: string;
  setDepartmentName: (value: string) => void;
  projectPurpose: string;
  setProjectPurpose: (value: string) => void;
  targetRows: number;
  setTargetRows: (value: number) => void;
  qualityThreshold: number;
  setQualityThreshold: (value: number) => void;
  modelType: 'statistical' | 'gaussian_copula' | 'ctgan' | 'tvae';
  setModelType: (value: 'statistical' | 'gaussian_copula' | 'ctgan' | 'tvae') => void;
  dpEnabled: boolean;
  setDpEnabled: (value: boolean) => void;
  dpEpsilon: number;
  setDpEpsilon: (value: number) => void;
  setStep: (step: number) => void;
  handleStartSynthesis: () => Promise<void>;
}

export const StepConfig: React.FC<StepConfigProps> = ({
  synthesisOptions,
  setSynthesisOptions,
  profile,
  fileName,
  reviewMetadata,
  setReviewMetadata,
  isDarkMode,
  departmentName,
  setDepartmentName,
  projectPurpose,
  setProjectPurpose,
  targetRows,
  setTargetRows,
  qualityThreshold,
  setQualityThreshold,
  modelType,
  setModelType,
  dpEnabled,
  setDpEnabled,
  dpEpsilon,
  setDpEpsilon,
  setStep,
  handleStartSynthesis,
}) => {
  const [hasAttemptedStart, setHasAttemptedStart] = useState(false);
  const validationErrors = validateSynthesisSettings({
    targetRows,
    qualityThreshold,
    dpEnabled,
    dpEpsilon,
    options: { ...defaultSynthesisOptions, ...synthesisOptions },
  });

  const handleValidatedSynthesisStart = async () => {
    setHasAttemptedStart(true);
    if (validationErrors.length > 0) return;
    await handleStartSynthesis();
  };

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <SynthesisProjectSettings
          departmentName={departmentName}
          setDepartmentName={setDepartmentName}
          projectPurpose={projectPurpose}
          setProjectPurpose={setProjectPurpose}
          targetRows={targetRows}
          setTargetRows={setTargetRows}
          qualityThreshold={qualityThreshold}
          setQualityThreshold={setQualityThreshold}
        />
        <SynthesisModelSettings
          fileName={fileName}
          modelType={modelType}
          setModelType={setModelType}
          isDarkMode={isDarkMode}
          dpEnabled={dpEnabled}
          setDpEnabled={setDpEnabled}
          dpEpsilon={dpEpsilon}
          setDpEpsilon={setDpEpsilon}
        />
      </div>

      <ReviewMetadataEditor reviewMetadata={reviewMetadata} setReviewMetadata={setReviewMetadata} />

      <AdvancedSynthesisSettings
        options={synthesisOptions}
        onChange={setSynthesisOptions}
        profile={profile}
        isDarkMode={isDarkMode}
        reviewMetadata={reviewMetadata}
        onReviewMetadataChange={setReviewMetadata}
      />

      {hasAttemptedStart && validationErrors.length > 0 && (
        <div role="alert" className="rounded-lg border border-rose-500/40 bg-rose-500/5 p-4 text-sm text-rose-600 dark:text-rose-400">
          <p className="font-semibold">합성을 시작하기 전에 설정값을 확인해 주세요.</p>
          <ul className="mt-2 list-disc space-y-1 pl-5">
            {validationErrors.map((error) => <li key={error}>{error}</li>)}
          </ul>
        </div>
      )}

      <div className="flex flex-col-reverse gap-3 sm:flex-row sm:items-center sm:justify-between">
        <button onClick={() => setStep(2)} className="ui-button-secondary">
          ← 이전 단계
        </button>
        <button onClick={handleValidatedSynthesisStart} className="ui-button-primary px-6 py-3 text-sm sm:px-8">
          실시간 합성 및 심의 패키지 파이프라인 가동
        </button>
      </div>
    </div>
  );
};
