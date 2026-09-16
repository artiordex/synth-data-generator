/**
 * 파일명: StepProfile.tsx
 * 경로: apps/web/src/features/dataset/StepProfile.tsx
 * 목적: 업로드 데이터 프로파일링 단계를 표시함
 * 작성자: 개발팀
 * 작성일: 2026-09-09
 * 수정일: 2026-09-09
 */
import React, { useState } from 'react';
import { Database, Shield, FileSpreadsheet, ArrowRight, ArrowLeft, Table, Search, Layers } from 'lucide-react';
import { DatasetProfile } from '../../types';
import { SectionHeader } from '../../components/SectionHeader';

interface StepProfileProps {
  isDarkMode: boolean;
  profile: DatasetProfile;
  profiles?: DatasetProfile[];
  activeProfileIndex?: number;
  setActiveProfileIndex?: (index: number) => void;
  setStep: (step: number) => void;
}

export const StepProfile: React.FC<StepProfileProps> = ({
  isDarkMode,
  profile,
  profiles,
  activeProfileIndex = 0,
  setActiveProfileIndex,
  setStep,
}) => {
  const [previewSearch, setPreviewSearch] = useState('');
  const piiCount = Object.keys(profile.detected_pii || {}).length;
  const rawRows = profile.preview || [];

  const filteredRows = rawRows.filter((row) => {
    if (!previewSearch.trim()) return true;
    const query = previewSearch.toLowerCase();
    return Object.values(row).some((val) =>
      String(val ?? '').toLowerCase().includes(query)
    );
  });

  return (
    <div className="space-y-6">
      {/* Multiple Files Tab Bar (Rendered when 2 or more files are uploaded) */}
      {profiles && profiles.length > 1 && (
        <div className="ui-panel p-4 space-y-2.5">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-2 text-xs font-semibold text-fg">
              <Layers className="w-4 h-4 text-accent" />
              <span>업로드된 파일 목록 ({profiles.length}개 파일)</span>
            </div>
            <span className="text-2xs text-fg-muted">확인할 파일을 클릭하여 미리보기와 스키마를 전환하세요</span>
          </div>
          <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-thin">
            {profiles.map((p, idx) => {
              const isActive = idx === activeProfileIndex;
              const pii = Object.keys(p.detected_pii || {}).length;
              return (
                <button
                  key={p.filename || idx}
                  type="button"
                  onClick={() => setActiveProfileIndex?.(idx)}
                  className={`flex items-center gap-2.5 px-3.5 py-2 rounded-xl text-xs transition-all shrink-0 border text-left cursor-pointer ${
                    isActive
                      ? 'bg-accent/10 border-accent/40 text-accent font-semibold shadow-xs ring-1 ring-accent/20'
                      : 'bg-surface-muted/60 border-subtle text-fg-muted hover:text-fg hover:bg-surface-muted'
                  }`}
                >
                  <FileSpreadsheet className="w-3.5 h-3.5 shrink-0" />
                  <div className="min-w-0">
                    <div className="truncate max-w-[170px] font-medium">{p.filename}</div>
                    <div className="text-3xs font-mono opacity-80">
                      {p.row_count.toLocaleString()}행 · {p.column_count}열{pii > 0 ? ` · PII ${pii}` : ''}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}

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

      {/* Raw Data Sample Preview (15 Rows) */}
      <div className="ui-panel overflow-hidden">
        <div className="border-b border-subtle bg-surface-muted/40 px-6 py-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-accent-subtle border border-accent/20 text-accent flex items-center justify-center shrink-0">
              <Table className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-fg flex items-center gap-2">
                <span>원본 데이터 샘플 미리보기</span>
                <span className="px-2 py-0.5 rounded-full text-2xs font-mono font-medium bg-accent/15 text-accent border border-accent/30">
                  상위 {rawRows.length}행
                </span>
              </h3>
              <p className="text-2xs text-fg-muted">
                전체 {profile.row_count.toLocaleString()}행 중 상위 {rawRows.length}행의 실제 데이터 형태를 확인합니다.
              </p>
            </div>
          </div>
          <div className="relative flex-1 max-w-xs">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-fg-muted" />
            <input
              type="text"
              value={previewSearch}
              onChange={(e) => setPreviewSearch(e.target.value)}
              placeholder="미리보기 내 값 검색..."
              className="ui-field w-full py-1.5 pl-8 pr-3 text-xs"
            />
          </div>
        </div>

        {rawRows.length === 0 ? (
          <div className="py-10 text-center text-xs text-fg-muted">미리보기 가능한 데이터가 없습니다.</div>
        ) : (
          <div className="overflow-x-auto max-h-[420px] scrollbar-thin">
            <table className="w-full text-left text-xs font-mono border-collapse">
              <thead className="sticky top-0 bg-surface-muted border-b border-subtle text-fg font-bold z-10">
                <tr>
                  <th className="px-3 py-2.5 border-r border-subtle text-center text-2xs text-fg-muted bg-surface-muted w-12 shrink-0">
                    #
                  </th>
                  {profile.columns.map((col) => (
                    <th key={col.name} className="px-3.5 py-2.5 border-r border-subtle last:border-r-0 whitespace-nowrap text-2xs">
                      <div className="flex items-center gap-1.5">
                        <span>{col.name}</span>
                        <span className={`px-1.5 py-0.2 rounded text-3xs font-mono font-normal border ${
                          col.inferred_type === 'numerical'
                            ? 'bg-accent-subtle text-accent border-accent/20'
                            : col.inferred_type === 'pii'
                            ? 'bg-danger-subtle text-danger border-danger/20'
                            : 'bg-surface text-fg-subtle border-subtle'
                        }`}>
                          {col.inferred_type}
                        </span>
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-subtle">
                {filteredRows.map((row, idx) => (
                  <tr key={idx} className="hover:bg-surface-muted/40 transition-colors">
                    <td className="px-3 py-2 border-r border-subtle text-center text-2xs text-fg-muted select-none bg-surface-muted/20">
                      {idx + 1}
                    </td>
                    {profile.columns.map((col) => {
                      const val = row[col.name];
                      const isNull = val === null || val === undefined || val === '';
                      return (
                        <td key={col.name} className="px-3.5 py-2 border-r border-subtle last:border-r-0 whitespace-nowrap text-fg/90">
                          {isNull ? (
                            <span className="italic text-fg-muted/50 text-2xs">null</span>
                          ) : (
                            String(val)
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
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
