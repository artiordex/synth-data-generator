import React from 'react';
import { Database, Shield } from 'lucide-react';
import { DatasetProfile } from '../../types';

interface StepProfileProps {
  isDarkMode: boolean;
  profile: DatasetProfile;
  setStep: (step: number) => void;
}

export const StepProfile: React.FC<StepProfileProps> = ({
  isDarkMode,
  profile,
  setStep,
}) => {
  return (
    <div className="space-y-6">
      {/* Summary Bar */}
      <div className="grid grid-cols-4 gap-4">
        <div className={`p-4 rounded-2xl border ${isDarkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200 shadow-sm'}`}>
          <div className={`text-[11px] ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>파일명</div>
          <div className={`text-sm font-bold truncate mt-0.5 ${isDarkMode ? 'text-white' : 'text-slate-900'}`}>{profile.filename}</div>
        </div>
        <div className={`p-4 rounded-2xl border ${isDarkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200 shadow-sm'}`}>
          <div className={`text-[11px] ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>레코드 및 컬럼 수</div>
          <div className="text-sm font-bold text-sky-600 dark:text-sky-400 mt-0.5">{profile.row_count.toLocaleString()} 행 / {profile.column_count} 컬럼</div>
        </div>
        <div className={`p-4 rounded-2xl border ${isDarkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200 shadow-sm'}`}>
          <div className={`text-[11px] ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>개인정보(PII) 감지</div>
          <div className="text-sm font-bold text-amber-600 dark:text-amber-400 mt-0.5">{Object.keys(profile.detected_pii).length}개 컬럼 감지됨</div>
        </div>
        <div className={`p-4 rounded-2xl border ${isDarkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200 shadow-sm'}`}>
          <div className={`text-[11px] ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>SHA-256 무결성 해시</div>
          <div className={`text-xs font-mono truncate mt-0.5 ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>{profile.sha256}</div>
        </div>
      </div>

      {/* Column Schema Table */}
      <div className={`border rounded-2xl overflow-hidden shadow-sm ${
        isDarkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'
      }`}>
        <div className={`px-6 py-4 border-b flex justify-between items-center ${
          isDarkMode ? 'border-slate-800' : 'border-slate-200 bg-slate-50/50'
        }`}>
          <h3 className={`font-bold text-sm flex items-center gap-2 ${isDarkMode ? 'text-slate-100' : 'text-slate-900'}`}>
            <Database className="w-4 h-4 text-sky-500" />
            컬럼 스키마 및 가명화 변환 계획
          </h3>
          <span className={`text-xs ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>한국형 Faker 10종 고유 식별자 일관 매핑</span>
        </div>
        <div className="overflow-x-auto max-h-80">
          <table className="w-full text-left text-xs">
            <thead className={`uppercase font-bold sticky top-0 ${
              isDarkMode ? 'bg-slate-950/90 text-slate-400' : 'bg-slate-100 text-slate-600'
            }`}>
              <tr>
                <th className="px-4 py-3">컬럼명</th>
                <th className="px-4 py-3">추론 유형</th>
                <th className="px-4 py-3">결측치 수</th>
                <th className="px-4 py-3">고유값 수</th>
                <th className="px-4 py-3">PII 판별 및 가명화 조치</th>
                <th className="px-4 py-3">값 예시 (중복 제외)</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDarkMode ? 'divide-slate-800/60' : 'divide-slate-200'}`}>
              {profile.columns.map((c) => (
                <tr key={c.name} className={isDarkMode ? 'hover:bg-slate-800/30' : 'hover:bg-slate-50'}>
                  <td className={`px-4 py-2.5 font-bold ${isDarkMode ? 'text-white' : 'text-slate-900'}`}>{c.name}</td>
                  <td className="px-4 py-2.5">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      c.inferred_type === 'numerical' 
                        ? 'bg-sky-500/10 text-sky-600 dark:text-sky-400 border border-sky-500/20' 
                        : c.inferred_type === 'pii' 
                        ? 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20' 
                        : 'bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/20'
                    }`}>
                      {c.inferred_type}
                    </span>
                  </td>
                  <td className={`px-4 py-2.5 ${isDarkMode ? 'text-slate-400' : 'text-slate-600'}`}>{c.null_count}</td>
                  <td className={`px-4 py-2.5 ${isDarkMode ? 'text-slate-400' : 'text-slate-600'}`}>{c.unique_count}</td>
                  <td className="px-4 py-2.5">
                    {c.pii_detected ? (
                      <span className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-700 dark:text-amber-300 border border-amber-500/30 text-[10px] font-bold flex items-center gap-1 w-fit">
                        <Shield className="w-3 h-3" />
                        Faker ({c.pii_type || '가명화'})
                      </span>
                    ) : (
                      <span className={isDarkMode ? 'text-slate-500 text-[11px]' : 'text-slate-400 text-[11px]'}>통계/AI 모델링</span>
                    )}
                  </td>
                  <td className={`px-4 py-2.5 text-[11px] min-w-[240px] max-w-lg ${
                    isDarkMode ? 'text-slate-400' : 'text-slate-600'
                  }`}>
                    <div className="flex flex-wrap gap-1.5">
                      {c.samples.length ? c.samples.map(value => (
                        <span key={value} className={`rounded px-2 py-1 whitespace-normal break-words max-w-full ${
                          isDarkMode ? 'bg-slate-800 text-slate-300' : 'bg-slate-100 text-slate-700'
                        }`}>{value}</span>
                      )) : <span className="text-slate-400">값 없음</span>}
                    </div>
                    {c.unique_count > c.samples.length && (
                      <div className="mt-1.5 text-[10px] text-slate-400">
                        전체 고유값 {c.unique_count.toLocaleString()}개 중 일부 표시
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Navigation Button */}
      <div className="flex justify-between items-center">
        <button
          onClick={() => setStep(1)}
          className={`px-4 py-2 rounded-xl text-xs font-bold border transition-colors ${
            isDarkMode 
              ? 'bg-slate-800 hover:bg-slate-700 text-slate-300 border-slate-700' 
              : 'bg-white hover:bg-slate-100 text-slate-700 border-slate-300 shadow-sm'
          }`}
        >
          ← 파일 다시 선택
        </button>
        <button
          onClick={() => setStep(3)}
          className="px-6 py-2.5 rounded-xl bg-sky-600 hover:bg-sky-500 text-xs font-bold text-white transition-all shadow-md shadow-sky-600/30"
        >
          합성 모델 및 파라미터 설정 →
        </button>
      </div>
    </div>
  );
};
