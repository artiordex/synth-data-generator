/**
 * 파일명: StepConfig.tsx
 * 경로: apps/web/src/features/synthesis/StepConfig.tsx
 * 목적: 합성 설정 단계를 표시함
 * 작성자: 개발팀
 * 작성일: 2026-09-09
 * 수정일: 2026-09-09
 */
import React, { useState } from 'react';
import { Sliders, Cpu, RefreshCw } from 'lucide-react';
import { compareSynthesisModels } from '../../services/api';
import { DatasetProfile, ReviewMetadataInput } from '../../types';
import { AdvancedSynthesisSettings, SynthesisOptions } from './AdvancedSynthesisSettings';
import { SectionHeader } from '../../components/SectionHeader';

const reviewFields: Array<[keyof Pick<ReviewMetadataInput, 'dataset_name' | 'special_notes' | 'overview' | 'privacy_plan'>, string, string]> = [
  ['dataset_name', '데이터명', '비워두면 파일명 사용'],
  ['special_notes', '특이사항', '희소 항목, 수집상 유의사항 등'],
  ['overview', '정보 개요', '수집 출처, 기간, 배경, 정보 설명'],
  ['privacy_plan', '개인정보 처리계획', '보유기간, 접근권한, 제공범위, 파기절차'],
];

interface StepConfigProps {
  synthesisOptions: SynthesisOptions;
  setSynthesisOptions: (value: SynthesisOptions) => void;
  profile: DatasetProfile | null;
  fileName: string;
  reviewMetadata: ReviewMetadataInput;
  setReviewMetadata: (value: ReviewMetadataInput) => void;
  isDarkMode: boolean;
  departmentName: string;
  setDepartmentName: (val: string) => void;
  projectPurpose: string;
  setProjectPurpose: (val: string) => void;
  targetRows: number;
  setTargetRows: (val: number) => void;
  qualityThreshold: number;
  setQualityThreshold: (val: number) => void;
  modelType: 'statistical' | 'gaussian_copula' | 'ctgan' | 'tvae';
  setModelType: (val: 'statistical' | 'gaussian_copula' | 'ctgan' | 'tvae') => void;
  dpEnabled: boolean;
  setDpEnabled: (val: boolean) => void;
  dpEpsilon: number;
  setDpEpsilon: (val: number) => void;
  setStep: (step: number) => void;
  handleStartSynthesis: () => Promise<void>;
}

export const StepConfig: React.FC<StepConfigProps> = ({
  synthesisOptions, setSynthesisOptions, profile, fileName,
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
  const [comparison, setComparison] = useState<any>(null);
  const [comparing, setComparing] = useState(false);
  const [compareError, setCompareError] = useState('');
  const runComparison = async () => {
    setComparing(true); setCompareError('');
    try {
      const result = await compareSynthesisModels(fileName);
      setComparison(result);
      if (result.recommended_model) setModelType(result.recommended_model);
    } catch (e: any) { setCompareError(e.message || '모델 비교 실패'); }
    finally { setComparing(false); }
  };
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        {/* Left: General Settings */}
        <div className="ui-panel space-y-4 p-6">
          <SectionHeader title="프로젝트 및 합성 대상 정보" Icon={Sliders} />
          <div className="space-y-3">
            <div>
              <label className="ui-label">담당 부서명</label>
              <input 
                type="text" 
                value={departmentName} 
                onChange={(e) => setDepartmentName(e.target.value)} 
                className="ui-field"
              />
            </div>
            <div>
              <label className="ui-label">연구 및 심의 목적</label>
              <input 
                type="text" 
                value={projectPurpose} 
                onChange={(e) => setProjectPurpose(e.target.value)} 
                className="ui-field"
              />
            </div>
            <div>
              <label className="ui-label">합성 생성 행 수 (Target Rows)</label>
              <input 
                type="number" 
                value={targetRows} 
                onChange={(e) => setTargetRows(Number(e.target.value))} 
                className="ui-field"
              />
            </div>
            <div>
              <label className="ui-label">심의 통과 품질 임계점 (기준 80점)</label>
              <input 
                type="number" 
                step="0.05"
                min="0.5"
                max="0.99"
                value={qualityThreshold} 
                onChange={(e) => setQualityThreshold(Number(e.target.value))} 
                className="ui-field"
              />
            </div>
          </div>
        </div>

        {/* Right: AI Model & Privacy */}
        <div className="ui-panel space-y-4 p-6">
          <SectionHeader title="생성 모델 & 차분 프라이버시(DP)" Icon={Cpu} />
          
          {/* Model Selector */}
          <div>
            <label className={`block text-xs font-semibold mb-2 ${isDarkMode ? 'text-slate-400' : 'text-slate-600'}`}>AI 합성 엔진 선택</label>
            <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
              {[
                { id: 'statistical', label: '통계 샘플러', desc: '빠른 컬럼별 추출 · 컬럼 간 관계 학습 없음' },
                { id: 'gaussian_copula', label: '가우시안 코퓰라', desc: '상관관계 보존 준모수 모델' },
                { id: 'ctgan', label: 'CTGAN 딥러닝 (기본)', desc: '노트북과 동일한 모델 · 컬럼 간 관계 학습' },
                { id: 'tvae', label: 'TVAE 딥러닝', desc: '변분 오토인코더 신경망' },
              ].map((m) => (
                <button
                  key={m.id}
                  type="button"
                  onClick={() => setModelType(m.id as any)}
                  className={`min-h-[86px] rounded-xl border p-3 text-left transition-all ${
                    modelType === m.id 
                      ? isDarkMode
                        ? 'bg-sky-950/60 border-sky-500 text-white shadow'
                        : 'bg-sky-50 border-sky-500 text-sky-900 shadow-sm ring-1 ring-sky-400'
                      : isDarkMode
                      ? 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'
                      : 'bg-slate-50 border-slate-200 text-slate-600 hover:border-slate-300'
                  }`}
                >
                  <div className="break-keep text-xs font-bold">{m.label}</div>
                  <div className={`mt-0.5 break-keep text-2xs leading-snug ${isDarkMode ? 'text-slate-500' : 'text-slate-400'}`}>{m.desc}</div>
                </button>
              ))}
            </div>
            <button type="button" disabled={comparing} onClick={runComparison} className="ui-button-secondary mt-3 border-sky-500 text-sky-700 dark:text-sky-400">
              {comparing && <RefreshCw className="mr-2 inline h-3.5 w-3.5 animate-spin"/>}4개 모델 축소 학습 비교 및 자동 선택
            </button>
            {compareError && <p className="mt-2 text-xs text-rose-500">{compareError}</p>}
            {comparison && <div className="mt-3 rounded-xl bg-sky-500/10 p-3 text-xs">
              <div className="font-bold">추천: {comparison.recommended_model?.toUpperCase()}</div>
              <div className="mt-2 grid grid-cols-2 gap-2">{comparison.leaderboard.map((item: any) => <div key={item.model_type} className="rounded-lg border border-slate-500/20 p-2"><b>{item.model_type.toUpperCase()}</b><br/>{item.score == null ? '실패' : `종합 ${(item.score * 100).toFixed(1)}% · ${item.duration_seconds}초`}</div>)}</div>
              <p className="mt-2 text-slate-400">{comparison.note}</p>
            </div>}
          </div>

          {/* Differential Privacy Toggle */}
          <div className={`pt-2 border-t space-y-3 ${isDarkMode ? 'border-slate-800' : 'border-slate-200'}`}>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="min-w-0">
                <div className={`text-xs font-bold ${isDarkMode ? 'text-slate-200' : 'text-slate-800'}`}>차분 프라이버시 (Laplace DP) 적용</div>
                <div className={`text-2xs ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>수학적 라플라스 노이즈로 엄격한 개인정보 차단</div>
              </div>
              <input 
                type="checkbox" 
                checked={dpEnabled} 
                onChange={(e) => setDpEnabled(e.target.checked)} 
                className="w-4 h-4 text-sky-600 rounded"
              />
            </div>

            {dpEnabled && (
              <div className={`p-3 rounded-xl border space-y-2 ${
                isDarkMode ? 'bg-slate-950 border-slate-800' : 'bg-slate-50 border-slate-200'
              }`}>
                <div className="flex justify-between text-xs font-semibold">
                  <span className={isDarkMode ? 'text-slate-400' : 'text-slate-600'}>프라이버시 예산 (Epsilon, ε):</span>
                  <span className="font-bold text-sky-600 dark:text-sky-400">{dpEpsilon}</span>
                </div>
                <input 
                  type="range" 
                  min="0.1" 
                  max="5.0" 
                  step="0.1" 
                  value={dpEpsilon} 
                  onChange={(e) => setDpEpsilon(Number(e.target.value))} 
                  className="w-full accent-sky-500"
                />
                <div className="flex justify-between text-2xs text-slate-400">
                  <span>강력한 프라이버시 (0.1)</span>
                  <span>높은 통계 정확도 (5.0)</span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="ui-panel space-y-4 p-6">
        <SectionHeader
          title="심의자료 한글 문서 입력"
          description="데이터 규모·전체 항목·결측 현황·처리방법·측정결과는 자동 입력됩니다. 아래 내용은 문서에 함께 반영되며, 미입력 사항은 자동 분석 또는 담당자 확인 필요로 표시됩니다."
        />
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {reviewFields.map(([key, label, placeholder]) => (
            <label key={key} className="block text-xs font-semibold">
              {label}
              <textarea value={reviewMetadata[key] || ''} placeholder={placeholder} rows={3}
                onChange={(event) => setReviewMetadata({ ...reviewMetadata, [key]: event.target.value })}
                className="ui-field mt-1" />
            </label>
          ))}
        </div>
        <p className="text-xs">원본 예시는 값 비공개 상태로 구조와 결측 여부를 표시합니다. HWPX 문서 3종과 HTML 확인본을 ZIP에 포함합니다.</p>
      </div>

      <AdvancedSynthesisSettings
        options={synthesisOptions}
        onChange={setSynthesisOptions}
        profile={profile}
        isDarkMode={isDarkMode}
        reviewMetadata={reviewMetadata}
        onReviewMetadataChange={setReviewMetadata}
      />
      {/* Navigation Button */}
      <div className="flex flex-col-reverse gap-3 sm:flex-row sm:items-center sm:justify-between">
        <button
          onClick={() => setStep(2)}
          className="ui-button-secondary"
        >
          ← 이전 단계
        </button>
        <button
          onClick={handleStartSynthesis}
          className="ui-button-primary px-6 py-3 text-sm sm:px-8"
        >
           실시간 합성 및 심의 패키지 파이프라인 가동
        </button>
      </div>
    </div>
  );
};
