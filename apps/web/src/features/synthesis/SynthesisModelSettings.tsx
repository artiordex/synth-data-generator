/**
 * 파일명: SynthesisModelSettings.tsx
 * 경로: apps/web/src/features/synthesis/SynthesisModelSettings.tsx
 * 목적: 합성 모델과 평가 결과를 설정하고 비교함
 * 작성자: 개발팀
 * 작성일: 2026-09-29
 * 수정일: 2026-09-29
 */
import React, { useState } from 'react';
import { Cpu, RefreshCw } from 'lucide-react';
import { compareSynthesisModels } from '../../services/api';
import { SynthesisRequest } from '../../types';
import { SectionHeader } from '../../components/SectionHeader';

type SynthesisModelType = SynthesisRequest['model_type'];

const modelOptions: Array<{ id: SynthesisModelType; label: string; description: string }> = [
  { id: 'statistical', label: '통계 샘플러', description: '빠른 컬럼별 추출 · 컬럼 간 관계 학습 없음' },
  { id: 'gaussian_copula', label: '가우시안 코퓰라', description: '상관관계 보존 준모수 모델' },
  { id: 'ctgan', label: 'CTGAN 딥러닝 (기본)', description: '노트북과 동일한 모델 · 컬럼 간 관계 학습' },
  { id: 'tvae', label: 'TVAE 딥러닝', description: '변분 오토인코더 신경망' },
];

type SynthesisModelSettingsProps = {
  fileName: string;
  modelType: SynthesisModelType;
  setModelType: (value: SynthesisModelType) => void;
  isDarkMode: boolean;
  dpEnabled: boolean;
  setDpEnabled: (value: boolean) => void;
  dpEpsilon: number;
  setDpEpsilon: (value: number) => void;
};

/** 합성 모델 선택과 비교 결과를 관리함 */
export function SynthesisModelSettings({
  fileName,
  modelType,
  setModelType,
  isDarkMode,
  dpEnabled,
  setDpEnabled,
  dpEpsilon,
  setDpEpsilon,
}: SynthesisModelSettingsProps) {
  const [comparison, setComparison] = useState<any>(null);
  const [comparing, setComparing] = useState(false);
  const [compareError, setCompareError] = useState('');

  // 선택한 파일의 합성 모델 적합도를 비교함
  const runComparison = async () => {
    setComparing(true);
    setCompareError('');
    try {
      const result = await compareSynthesisModels(fileName);
      setComparison(result);
      if (result.recommended_model) setModelType(result.recommended_model);
    } catch (error: any) {
      setCompareError(error.message || '모델 비교 실패');
    } finally {
      setComparing(false);
    }
  };

  return (
    <section className="ui-panel space-y-4 p-6">
      <SectionHeader title="생성 모델 & 차분 프라이버시(DP)" Icon={Cpu} />

      <div>
        <label className={`mb-2 block text-xs font-semibold ${isDarkMode ? 'text-slate-400' : 'text-slate-600'}`}>
          AI 합성 엔진 선택
        </label>
        <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
          {modelOptions.map((model) => (
            <button
              key={model.id}
              type="button"
              onClick={() => setModelType(model.id)}
              className={`min-h-[86px] rounded-xl border p-3 text-left transition-all ${
                modelType === model.id
                  ? isDarkMode
                    ? 'bg-sky-950/60 border-sky-500 text-white shadow'
                    : 'bg-sky-50 border-sky-500 text-sky-900 shadow-sm ring-1 ring-sky-400'
                  : isDarkMode
                    ? 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'
                    : 'bg-slate-50 border-slate-200 text-slate-600 hover:border-slate-300'
              }`}
            >
              <div className="break-keep text-xs font-bold">{model.label}</div>
              <div className={`mt-0.5 break-keep text-2xs leading-snug ${isDarkMode ? 'text-slate-500' : 'text-slate-400'}`}>
                {model.description}
              </div>
            </button>
          ))}
        </div>

        <button
          type="button"
          disabled={comparing}
          onClick={runComparison}
          className="ui-button-secondary mt-3 border-sky-500 text-sky-700 dark:text-sky-400"
        >
          {comparing && <RefreshCw className="mr-2 inline h-3.5 w-3.5 animate-spin" />}
          4개 모델 축소 학습 비교 및 자동 선택
        </button>
        {compareError && <p className="mt-2 text-xs text-rose-500">{compareError}</p>}
        {comparison && (
          <div className="mt-3 rounded-xl bg-sky-500/10 p-3 text-xs">
            <div className="font-bold">추천: {comparison.recommended_model?.toUpperCase()}</div>
            <div className="mt-2 grid grid-cols-2 gap-2">
              {comparison.leaderboard.map((item: any) => (
                <div key={item.model_type} className="rounded-lg border border-slate-500/20 p-2">
                  <b>{item.model_type.toUpperCase()}</b>
                  <br />
                  {item.score == null ? '실패' : `종합 ${(item.score * 100).toFixed(1)}% · ${item.duration_seconds}초`}
                </div>
              ))}
            </div>
            <p className="mt-2 text-slate-400">{comparison.note}</p>
          </div>
        )}
      </div>

      <div className={`space-y-3 border-t pt-2 ${isDarkMode ? 'border-slate-800' : 'border-slate-200'}`}>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0">
            <div className={`text-xs font-bold ${isDarkMode ? 'text-slate-200' : 'text-slate-800'}`}>
              차분 프라이버시 (Laplace DP) 적용
            </div>
            <div className={`text-2xs ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>
              수학적 라플라스 노이즈로 엄격한 개인정보 차단
            </div>
          </div>
          <input
            type="checkbox"
            checked={dpEnabled}
            onChange={(event) => setDpEnabled(event.target.checked)}
            className="h-4 w-4 rounded text-sky-600"
          />
        </div>

        {dpEnabled && (
          <div className={`space-y-2 rounded-xl border p-3 ${isDarkMode ? 'bg-slate-950 border-slate-800' : 'bg-slate-50 border-slate-200'}`}>
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
              onChange={(event) => setDpEpsilon(Number(event.target.value))}
              className="w-full accent-sky-500"
            />
            <div className="flex justify-between text-2xs text-slate-400">
              <span>강력한 프라이버시 (0.1)</span>
              <span>높은 통계 정확도 (5.0)</span>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
