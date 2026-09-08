import React from 'react';
import { DatasetProfile, InformationType, ReviewMetadataInput, SynthesisRequest } from '../../types';

export type SynthesisOptions = Pick<SynthesisRequest, 'epochs' | 'batch_size' | 'pac' | 'seed' |
  'sampling_batch_size' | 'max_sampling_attempts' | 'enable_gpu' | 'evaluation_excluded_columns' |
  'categorical_columns' | 'numerical_columns' | 'preserve_null_columns' | 'duplicate_policy'>;

export const defaultSynthesisOptions: SynthesisOptions = {
  epochs: 30, batch_size: 64, pac: 1, seed: 42, sampling_batch_size: 800,
  max_sampling_attempts: 10, enable_gpu: false, duplicate_policy: 'balanced',
};

const informationTypes: InformationType[] = ['준식별자', '일반정보'];

export function AdvancedSynthesisSettings({ options, onChange, profile, isDarkMode, reviewMetadata, onReviewMetadataChange }: {
  options: SynthesisOptions; onChange: (value: SynthesisOptions) => void;
  profile: DatasetProfile | null; isDarkMode: boolean;
  reviewMetadata?: ReviewMetadataInput; onReviewMetadataChange?: (value: ReviewMetadataInput) => void;
}) {
  const columns = profile?.columns.filter(c => !c.pii_detected) || [];
  const cats = options.categorical_columns ?? profile?.suggested_categorical ?? [];
  const nums = options.numerical_columns ?? profile?.suggested_numerical ?? [];
  const fieldStyle = `rounded border p-2 ${isDarkMode ? 'bg-slate-950 border-slate-700' : 'bg-white border-slate-300'}`;
  const toggle = (key: 'preserve_null_columns' | 'evaluation_excluded_columns', name: string, selected: boolean) => {
    onChange({ ...options, [key]: selected ? [...(options[key] || []), name] : (options[key] || []).filter(c => c !== name) });
  };
  const updateInformationType = (name: string, informationType: InformationType) => {
    if (!onReviewMetadataChange) return;
    const previousColumn = reviewMetadata?.columns?.[name] || {};
    onReviewMetadataChange({
      ...reviewMetadata,
      columns: {
        ...(reviewMetadata?.columns || {}),
        [name]: { ...previousColumn, information_type: informationType },
      },
    });
  };
  return <details className="ui-panel p-6">
    <summary className="cursor-pointer font-bold text-sm">학습·평가 상세 설정</summary>
    {profile?.notebook_preset?.name && <p className="text-sm mt-3 text-sky-600">노트북 설정 자동 적용: {profile.notebook_preset.name}. 아래에서 변경한 값이 우선합니다.</p>}
    <p className="text-xs my-3">결측치가 ‘비적용’을 뜻하는 항목은 의미 보존을 선택하세요. sin/cos 등 학습용 파생변수는 평가에서 제외할 수 있습니다.</p>
    <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-xs">
      {([
        ['epochs', '학습 반복 수', 1], ['batch_size', '학습 배치 크기', 1], ['pac', 'CTGAN PAC', 1],
        ['seed', '재현용 시드', 0], ['sampling_batch_size', '최소 생성 묶음 크기', 1],
        ['max_sampling_attempts', '최대 생성 시도 횟수', 1],
      ] as const).map(([key, label, min]) => <label key={key} className="grid gap-1">
        {label}<input aria-label={label} className={fieldStyle} type="number" min={min} step={1}
          max={key === 'max_sampling_attempts' ? 100 : key === 'seed' ? 4294967295 : undefined}
          value={options[key] ?? defaultSynthesisOptions[key]}
          onChange={e => onChange({ ...options, [key]: Number(e.target.value) })} />
      </label>)}
    </div>
    <label className="flex gap-2 items-center text-xs my-4"><input type="checkbox" checked={options.enable_gpu ?? false}
      onChange={e => onChange({ ...options, enable_gpu: e.target.checked })} />사용 가능한 GPU 사용 (기본 CPU)</label>
    <label className="grid gap-1 text-xs mb-3">원본 일치 행 처리
      <select className={fieldStyle} value={options.duplicate_policy ?? 'balanced'} onChange={e => onChange({ ...options, duplicate_policy: e.target.value as 'balanced' | 'strict' })}>
        <option value="balanced">균형: 원본에서 5회 이상 나타난 조합은 유지, 희귀 일치 행 제거</option>
        <option value="strict">엄격: 원본 일치 행 모두 제거</option>
      </select>
    </label>
    <p className="text-xs mb-3">균형 모드에서 유지한 원본 일치 행은 보고서에 기록하고 검토 필요로 표시합니다. 새 행을 보충해도 부족하면 실패 사유를 표시합니다. 안전성 평가는 50행 이상 입력에서 학습 전 20%를 분리하며, 평가 자료가 부족하면 미측정으로 표시합니다.</p>
    <div className="overflow-auto max-h-96"><table className="w-full min-w-[1120px] text-xs text-left">
      <thead><tr><th className="p-2 w-[22%]">항목</th><th className="w-[12%]">학습 유형</th><th className="w-[13%]">정보영역</th><th className="w-[37%]">고유값 미리보기</th><th className="w-[8%] text-center">결측 의미 보존</th><th className="w-[8%] text-center">평가 제외</th></tr></thead>
      <tbody>{columns.map(c => {
        const values = c.samples || [];
        const selectedInformationType = (reviewMetadata?.columns?.[c.name]?.information_type || c.information_type || '일반정보') as InformationType;
        return <tr key={c.name} className="border-t border-slate-300/30 align-top">
          <td className="p-2 font-medium">{c.name}</td><td className="py-2 pr-2"><select aria-label={`${c.name} 학습 유형`} className={fieldStyle}
            value={nums.includes(c.name) ? 'numerical' : 'categorical'}
            onChange={e => onChange({ ...options,
              categorical_columns: [...cats.filter(x => x !== c.name), ...(e.target.value === 'categorical' ? [c.name] : [])],
              numerical_columns: [...nums.filter(x => x !== c.name), ...(e.target.value === 'numerical' ? [c.name] : [])],
            })}><option value="categorical">범주형</option><option value="numerical">수치형</option></select></td>
          <td className="py-2 pr-2"><select aria-label={`${c.name} 정보영역`} className={fieldStyle}
            value={informationTypes.includes(selectedInformationType) ? selectedInformationType : '일반정보'}
            onChange={e => updateInformationType(c.name, e.target.value as InformationType)}
            disabled={!onReviewMetadataChange}>
            <option value="준식별자">준식별자</option><option value="일반정보">일반정보</option>
          </select></td>
          <td className="py-2 pr-3">
            <div className={`max-h-20 overflow-y-auto rounded border p-2 ${isDarkMode ? 'border-slate-800 bg-slate-950/70' : 'border-slate-200 bg-slate-50'}`}>
              <div className="mb-1 text-[10px] text-slate-500">
                고유값 {(c.unique_values_total ?? c.unique_count).toLocaleString()}개{c.samples_truncated ? ` · 상위 ${values.length.toLocaleString()}개 표시` : ''}
              </div>
              {values.length ? <div className="flex flex-wrap gap-1">
                {values.map((value, index) => <span key={`${c.name}-${value}-${index}`} className={`max-w-full rounded px-1.5 py-0.5 text-[10px] leading-5 ${isDarkMode ? 'bg-slate-800 text-slate-200' : 'bg-white text-slate-700 border border-slate-200'}`} title={value}>{value}</span>)}
              </div> : <span className="text-[10px] text-slate-400">표시할 값 없음</span>}
            </div>
          </td>
          <td className="py-3 text-center"><input aria-label={`${c.name} 결측 의미 보존`} type="checkbox" checked={options.preserve_null_columns?.includes(c.name) ?? false}
            onChange={e => toggle('preserve_null_columns', c.name, e.target.checked)} /></td>
          <td className="py-3 text-center"><input aria-label={`${c.name} 평가 제외`} type="checkbox" checked={options.evaluation_excluded_columns?.includes(c.name) ?? false}
            onChange={e => toggle('evaluation_excluded_columns', c.name, e.target.checked)} /></td>
        </tr>;
      })}</tbody>
    </table></div>
  </details>;
}
