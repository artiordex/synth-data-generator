import React from 'react';
import { DatasetProfile, SynthesisRequest } from '../../types';

export type SynthesisOptions = Pick<SynthesisRequest, 'epochs' | 'batch_size' | 'pac' | 'seed' |
  'sampling_batch_size' | 'max_sampling_attempts' | 'enable_gpu' | 'evaluation_excluded_columns' |
  'categorical_columns' | 'numerical_columns' | 'preserve_null_columns' | 'duplicate_policy'>;

export const defaultSynthesisOptions: SynthesisOptions = {
  epochs: 30, batch_size: 64, pac: 1, seed: 42, sampling_batch_size: 800,
  max_sampling_attempts: 10, enable_gpu: false, duplicate_policy: 'balanced',
};

export function AdvancedSynthesisSettings({ options, onChange, profile, isDarkMode }: {
  options: SynthesisOptions; onChange: (value: SynthesisOptions) => void;
  profile: DatasetProfile | null; isDarkMode: boolean;
}) {
  const columns = profile?.columns.filter(c => !c.pii_detected) || [];
  const cats = options.categorical_columns ?? profile?.suggested_categorical ?? [];
  const nums = options.numerical_columns ?? profile?.suggested_numerical ?? [];
  const fieldStyle = `rounded border p-2 ${isDarkMode ? 'bg-slate-950 border-slate-700' : 'bg-white border-slate-300'}`;
  const toggle = (key: 'preserve_null_columns' | 'evaluation_excluded_columns', name: string, selected: boolean) => {
    onChange({ ...options, [key]: selected ? [...(options[key] || []), name] : (options[key] || []).filter(c => c !== name) });
  };
  return <details className={`p-6 rounded-2xl border ${isDarkMode ? 'bg-slate-900 border-slate-800 text-slate-100' : 'bg-white border-slate-200 text-slate-900'}`}>
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
    <div className="overflow-auto max-h-80"><table className="w-full text-xs text-left">
      <thead><tr><th className="p-2">항목</th><th>학습 유형</th><th>결측 의미 보존</th><th>평가 제외</th></tr></thead>
      <tbody>{columns.map(c => <tr key={c.name} className="border-t border-slate-300/30">
        <td className="p-2">{c.name}</td><td><select aria-label={`${c.name} 학습 유형`} className={fieldStyle}
          value={nums.includes(c.name) ? 'numerical' : 'categorical'}
          onChange={e => onChange({ ...options,
            categorical_columns: [...cats.filter(x => x !== c.name), ...(e.target.value === 'categorical' ? [c.name] : [])],
            numerical_columns: [...nums.filter(x => x !== c.name), ...(e.target.value === 'numerical' ? [c.name] : [])],
          })}><option value="categorical">범주형</option><option value="numerical">수치형</option></select></td>
        <td><input aria-label={`${c.name} 결측 의미 보존`} type="checkbox" checked={options.preserve_null_columns?.includes(c.name) ?? false}
          onChange={e => toggle('preserve_null_columns', c.name, e.target.checked)} /></td>
        <td><input aria-label={`${c.name} 평가 제외`} type="checkbox" checked={options.evaluation_excluded_columns?.includes(c.name) ?? false}
          onChange={e => toggle('evaluation_excluded_columns', c.name, e.target.checked)} /></td>
      </tr>)}</tbody>
    </table></div>
  </details>;
}
