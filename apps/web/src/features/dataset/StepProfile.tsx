/**
 * 파일명: StepProfile.tsx
 * 경로: apps/web/src/features/dataset/StepProfile.tsx
 * 목적: 업로드 데이터 프로파일링 단계를 표시함
 * 작성자: 개발팀
 * 작성일: 2026-09-09
 * 수정일: 2026-09-09
 */
import React from 'react';
import { Database, Shield, FileSpreadsheet, ArrowRight, ArrowLeft } from 'lucide-react';
import { DatasetProfile } from '../../types';
import { SectionHeader } from '../../components/SectionHeader';

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
  const piiCount = Object.keys(profile.detected_pii).length;

  return (
    <div className="space-y-6">
      {/* File Meta Strip */}
      <div className="ui-panel flex flex-col justify-between gap-4 p-5 md:flex-row md:items-center">
        <div className="flex items-center gap-3.5 min-w-0">
          <div className="w-11 h-11 rounded-xl bg-accent-subtle border border-accent/20 text-accent flex items-center justify-center shrink-0">
            <FileSpreadsheet className="w-5 h-5" />
          </div>
          <div className="min-w-0 space-y-1">
            <div className="flex items-center gap-2 flex-wrap">
              <h2 className="text-base font-bold text-fg truncate tracking-tight">{profile.filename}</h2>
              <span className="px-2.5 py-0.5 rounded-md text-2xs font-mono font-medium bg-surface-muted text-fg-muted border border-subtle">
                {profile.row_count.toLocaleString()} 행 · {profile.column_count} 컬럼
              </span>
              {piiCount > 0 ? (
                <span className="px-2.5 py-0.5 rounded-md text-2xs font-medium bg-warning-subtle text-warning border border-warning/20 flex items-center gap-1">
                  <Shield className="w-3 h-3" />
                  PII {piiCount}개 컬럼 감지됨
                </span>
              ) : (
                <span className="px-2.5 py-0.5 rounded-md text-2xs font-medium bg-success-subtle text-success border border-success/20">
                  안전 (PII 미감지)
                </span>
              )}
            </div>
            <p className="text-2xs font-mono text-fg-subtle truncate">
              무결성 해시: {profile.sha256}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2.5 shrink-0 self-end md:self-center">
          <button
            onClick={() => setStep(1)}
            className="ui-button-secondary"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            파일 다시 선택
          </button>
          <button
            onClick={() => setStep(3)}
            className="ui-button-primary"
          >
            합성 모델 설정
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Column Schema Table */}
      <div className="ui-panel overflow-hidden">
        <SectionHeader
          title="컬럼 스키마 및 가명화 변환 계획"
          Icon={Database}
          className="border-b border-subtle bg-surface-muted/40 px-6 py-4"
          meta={<span className="font-mono text-xs text-fg-subtle">총 {profile.columns.length}개 컬럼</span>}
        />
        <div className="overflow-x-auto max-h-96">
          <table className="w-full text-left text-xs">
            <thead className="sticky top-0 bg-surface-muted text-fg-muted font-medium border-b border-subtle text-2xs uppercase tracking-wider">
              <tr>
                <th className="px-5 py-3">컬럼명</th>
                <th className="px-5 py-3">유형</th>
                <th className="px-5 py-3">정보영역</th>
                <th className="px-5 py-3 text-right">결측치</th>
                <th className="px-5 py-3 text-right">고유값</th>
                <th className="px-5 py-3">PII 판별 및 조치</th>
                <th className="px-5 py-3">값 샘플 미리보기</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-subtle">
              {profile.columns.map((c) => (
                <tr key={c.name} className="hover:bg-surface-muted/40 transition-colors">
                  <td className="px-5 py-3 font-semibold text-fg font-mono">
                    {c.name}
                  </td>
                  <td className="px-5 py-3">
                    <span className={`px-2 py-0.5 rounded-md text-2xs font-mono font-medium border ${
                      c.inferred_type === 'numerical'
                        ? 'bg-accent-subtle text-accent border-accent/20'
                        : c.inferred_type === 'pii'
                        ? 'bg-danger-subtle text-danger border-danger/20'
                        : 'bg-surface-muted text-fg-muted border-default'
                    }`}>
                      {c.inferred_type}
                    </span>
                  </td>
                  <td className="px-5 py-3">
                    <span className={`px-2 py-0.5 rounded-md text-2xs font-semibold border ${
                      c.information_type === '준식별자'
                        ? 'bg-warning-subtle text-warning border-warning/20'
                        : 'bg-success-subtle text-success border-success/20'
                    }`}>
                      {c.information_type}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-right font-mono text-fg-muted">
                    {c.null_count.toLocaleString()}
                  </td>
                  <td className="px-5 py-3 text-right font-mono text-fg-muted">
                    {c.unique_count.toLocaleString()}
                  </td>
                  <td className="px-5 py-3">
                    {c.pii_detected ? (
                      <span className="px-2.5 py-0.5 rounded-md bg-warning-subtle text-warning border border-warning/20 text-2xs font-medium flex items-center gap-1 w-fit">
                        <Shield className="w-3 h-3" />
                        Faker ({c.pii_type || '가명화'})
                      </span>
                    ) : (
                      <span className="text-fg-subtle text-2xs">
                        AI 합성 모델링
                      </span>
                    )}
                  </td>
                  <td className="px-5 py-3 min-w-[240px] max-w-lg">
                    <div className="flex flex-wrap gap-1.5">
                      {c.samples.length ? c.samples.map((value, idx) => (
                        <span 
                          key={idx} 
                          className="rounded-md px-2 py-0.5 text-2xs font-mono bg-surface-muted text-fg-muted border border-subtle truncate max-w-[200px]"
                          title={String(value)}
                        >
                          {String(value)}
                        </span>
                      )) : <span className="text-fg-subtle">값 없음</span>}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Bottom Action Bar */}
      <div className="flex justify-between items-center pt-2">
        <button
          onClick={() => setStep(1)}
          className="ui-button-secondary"
        >
          <ArrowLeft className="w-4 h-4" />
          파일 다시 선택
        </button>
        <button
          onClick={() => setStep(3)}
          className="ui-button-primary"
        >
          합성 모델 및 파라미터 설정
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
