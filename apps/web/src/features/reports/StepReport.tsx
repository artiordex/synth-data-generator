/**
 * 파일명: StepReport.tsx
 * 경로: apps/web/src/features/reports/StepReport.tsx
 * 목적: 합성 결과 보고서 단계를 표시함
 * 작성자: 개발팀
 * 작성일: 2026-09-09
 * 수정일: 2026-09-09
 */
import React, { useEffect, useState } from 'react';
import { FileText, Download, AlertCircle, CheckCircle2, Table, Copy, Check, Search, RefreshCw, Layers } from 'lucide-react';
import { AssessmentIssue, JobAssessmentReport, JobStatus, SyntheticPreviewData } from '../../types';
import { getDownloadUrl, getJobAssessment, getJobPreview } from '../../services/api';
import { DistributionComparisonChart } from './DistributionComparisonChart';
import { SectionHeader } from '../../components/SectionHeader';

interface StepReportProps {
  isDarkMode: boolean;
  activeJob: JobStatus;
  setStep: (step: number) => void;
  setProfile: (profile: any) => void;
  setActiveJob: (job: JobStatus | null) => void;
}

export const StepReport: React.FC<StepReportProps> = ({
  isDarkMode,
  activeJob,
  setStep,
  setProfile,
  setActiveJob,
}) => {
  const [assessmentReport, setAssessmentReport] = useState<JobAssessmentReport | null>(null);
  const [assessmentLoading, setAssessmentLoading] = useState(false);

  // Synthetic sample preview states
  const [previewData, setPreviewData] = useState<SyntheticPreviewData | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewTab, setPreviewTab] = useState<'synthetic' | 'original'>('synthetic');
  const [previewSearch, setPreviewSearch] = useState('');
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    let isMounted = true;

    const loadAssessment = async () => {
      setAssessmentLoading(true);
      try {
        const report = await getJobAssessment(activeJob.id);
        if (isMounted) setAssessmentReport(report);
      } catch {
        if (isMounted) setAssessmentReport(null);
      } finally {
        if (isMounted) setAssessmentLoading(false);
      }
    };

    const loadPreview = async () => {
      setPreviewLoading(true);
      try {
        const preview = await getJobPreview(activeJob.id, 15);
        if (isMounted) setPreviewData(preview);
      } catch {
        if (isMounted) setPreviewData(null);
      } finally {
        if (isMounted) setPreviewLoading(false);
      }
    };

    loadAssessment();
    loadPreview();
    return () => { isMounted = false; };
  }, [activeJob.id]);

  const percent = (value?: number | null) => (
    value == null ? '-' : `${(value * 100).toFixed(1)}%`
  );

  const buildFallbackIssues = (): AssessmentIssue[] => {
    const report = assessmentReport;
    const issues = report?.assessment?.issues || [];
    if (issues.length > 0) return issues;

    const fallback: AssessmentIssue[] = [];
    const qualityScore = report?.quality_score ?? activeJob.quality_score;
    const threshold = Number(report?.config?.quality_threshold ?? activeJob.quality_threshold ?? 0.8);
    const anonymeter = report?.safety?.anonymeter || {};
    const guardrails = report?.guardrails || {};
    const correlation = report?.utility?.correlation?.overall_correlation_score;

    if (qualityScore != null && qualityScore < threshold) {
      fallback.push({
        code: 'QUALITY_THRESHOLD',
        label: '분포 품질 기준 미달',
        detail: `분포 품질 ${percent(qualityScore)}가 설정 기준 ${percent(threshold)}보다 낮습니다.`,
      });
    }
    if (typeof correlation === 'number' && correlation < 0.7) {
      fallback.push({
        code: 'CORRELATION_LOW',
        label: '상관관계 보존율 낮음',
        detail: `2D 상관관계 점수 ${percent(correlation)}가 기준 70.0%보다 낮습니다.`,
      });
    }
    if (anonymeter.evaluated_with_anonymeter === false) {
      const failed = Object.keys(anonymeter.errors || {});
      fallback.push({
        code: 'ANONYMETER_UNMEASURED',
        label: 'Anonymeter 평가 미측정/실패',
        detail: failed.length
          ? `일부 평가가 완료되지 않았습니다: ${failed.join(', ')}`
          : (anonymeter.reason || '안전성 평가가 완료되지 않았습니다.'),
        errors: anonymeter.errors,
      });
    }
    if ((guardrails.final_exact_duplicates || 0) > 0) {
      fallback.push({
        code: 'FINAL_EXACT_DUPLICATES',
        label: '원본 조합 일치 레코드 감지',
        detail: `생성 결과 ${guardrails.final_exact_duplicates}건이 원본의 빈번한 값 조합과 일치합니다.`,
        value: guardrails.final_exact_duplicate_rate,
      });
    }
    if (!activeJob.assessment_passed && fallback.length === 0) {
      fallback.push({
        code: 'MANUAL_REVIEW',
        label: '수동 검토 필요',
        detail: '자동 통과 조건을 모두 만족하지 못했습니다. 평가 JSON과 심의자료를 확인하세요.',
      });
    }
    return fallback;
  };

  const issues = buildFallbackIssues();
  const summary = assessmentReport?.assessment?.summary || {};
  const isPassed = activeJob.assessment_passed || assessmentReport?.assessment?.passed;

  return (
    <div className="space-y-6">
      {/* Scorecard Hero */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <div className="ui-panel flex min-w-0 flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0">
            <div className={`text-xs ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>심의 종합 판정</div>
            <div className={`mt-1 break-keep text-2xl font-black leading-tight ${isDarkMode ? 'text-white' : 'text-slate-900'}`}>
              {activeJob.assessment_passed ? `${activeJob.assessment_grade ?? '-'} 등급` : '검토 필요'}
            </div>
            <div className="mt-0.5 break-keep text-2xs font-bold text-emerald-600 dark:text-emerald-400">
              {activeJob.assessment_passed ? '자동 점검 통과' : '측정 결과와 누락 항목 확인'}
            </div>
          </div>
          <div className="flex h-10 min-w-[76px] shrink-0 items-center justify-center whitespace-nowrap rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-3 text-sm font-black text-emerald-600 dark:text-emerald-400">
            {activeJob.assessment_score == null ? '미측정' : `${activeJob.assessment_score}점`}
          </div>
        </div>

        <div className="ui-panel min-w-0 p-5">
          <div className={`break-keep text-xs ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>분포 품질 지수 (1 − 평균 JSD)</div>
          <div className="mt-1 break-keep text-2xl font-black leading-tight text-sky-600 dark:text-sky-400">
            {activeJob.quality_score == null ? '미측정' : `${(activeJob.quality_score * 100).toFixed(1)}%`}
          </div>
          <div className={`mt-0.5 break-keep text-2xs ${isDarkMode ? 'text-slate-500' : 'text-slate-400'}`}>수치형 공통 20구간·결측 포함</div>
        </div>

        <div className="ui-panel min-w-0 p-5">
          <div className={`break-keep text-xs ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>Anonymeter 재식별 위험도</div>
          <div className="mt-1 break-keep text-2xl font-black leading-tight text-amber-600 dark:text-amber-400">
            {activeJob.reid_risk == null ? '미측정' : `${(activeJob.reid_risk * 100).toFixed(2)}%`}
          </div>
          <div className={`mt-0.5 break-keep text-2xs leading-snug ${isDarkMode ? 'text-slate-500' : 'text-slate-400'}`}>독립 대조 데이터를 이용한 단일 식별 위험도</div>
        </div>

        <div className="ui-panel min-w-0 p-5">
          <div className={`text-xs ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>생성 레코드 수</div>
          <div className="mt-1 break-keep text-2xl font-black leading-tight text-indigo-600 dark:text-indigo-400">
            {activeJob.target_rows.toLocaleString()} 건
          </div>
          <div className={`mt-0.5 break-keep text-2xs ${isDarkMode ? 'text-slate-500' : 'text-slate-400'}`}>{activeJob.model_type.toUpperCase()} 엔진</div>
        </div>
      </div>

      <div className="ui-panel p-5">
        <div className="flex flex-col gap-3 border-b pb-4 dark:border-slate-800 sm:flex-row sm:items-center sm:justify-between">
          <SectionHeader
            title="자동 심의 판정 사유"
            description="설정 품질 기준, Anonymeter, DCR, 중복 guardrail을 종합한 판정입니다."
            Icon={isPassed ? CheckCircle2 : AlertCircle}
            meta={
              <div className={`rounded-xl border px-3 py-2 text-xs font-bold ${
                isPassed
                  ? isDarkMode ? 'border-emerald-700 bg-emerald-950/50 text-emerald-300' : 'border-emerald-200 bg-emerald-50 text-emerald-700'
                  : isDarkMode ? 'border-amber-700 bg-amber-950/50 text-amber-300' : 'border-amber-200 bg-amber-50 text-amber-700'
              }`}>
                {assessmentLoading ? '판정 로드 중' : isPassed ? '자동 점검 통과' : '검토 필요'}
              </div>
            }
            className="w-full sm:items-center"
          />
        </div>

        <div className="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-4">
          {[
            ['분포 품질', percent(summary.distribution_quality ?? activeJob.quality_score), `기준 ${percent(summary.quality_threshold ?? activeJob.quality_threshold)}`],
            ['상관관계', percent(summary.correlation_score), '기준 70.0%'],
            ['Anonymeter', activeJob.reid_risk == null ? '미측정' : percent(activeJob.reid_risk), '위험도 기준 5.0%'],
            ['DCR 기억위험', summary.memorization_risk == null ? '미측정' : percent(summary.memorization_risk), '기준 5.0%'],
          ].map(([label, value, hint]) => (
            <div key={label} className={`rounded-xl border p-3 ${
              isDarkMode ? 'border-slate-800 bg-slate-950' : 'border-slate-200 bg-slate-50'
            }`}>
              <div className={`text-xs ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>{label}</div>
              <div className={`mt-1 text-sm font-black ${isDarkMode ? 'text-slate-100' : 'text-slate-900'}`}>{value}</div>
              <div className={`mt-0.5 text-2xs ${isDarkMode ? 'text-slate-500' : 'text-slate-400'}`}>{hint}</div>
            </div>
          ))}
        </div>

        {!isPassed && (
          <div className="mt-4 space-y-2">
            {issues.map((issue) => (
              <div key={issue.code} className={`rounded-xl border p-3 ${
                isDarkMode ? 'border-amber-900/70 bg-amber-950/20' : 'border-amber-200 bg-amber-50/70'
              }`}>
                <div className={`text-xs font-bold ${isDarkMode ? 'text-amber-300' : 'text-amber-800'}`}>
                  {issue.label}
                </div>
                <div className={`mt-1 text-xs leading-relaxed ${isDarkMode ? 'text-slate-300' : 'text-slate-700'}`}>
                  {issue.detail}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Interactive Distribution Comparison Overlay Chart */}
      <DistributionComparisonChart jobId={activeJob.id} isDarkMode={isDarkMode} />

      {/* Generated Synthetic Data Preview Table */}
      {(() => {
        const rows = previewTab === 'synthetic' ? previewData?.synthetic_rows : previewData?.original_rows;
        const filteredRows = (rows || []).filter(row => {
          if (!previewSearch.trim()) return true;
          const query = previewSearch.toLowerCase();
          return Object.values(row).some(val => String(val ?? '').toLowerCase().includes(query));
        });

        const copyTableToClipboard = () => {
          if (!previewData || !rows || rows.length === 0) return;
          const headers = previewData.columns.join('\t');
          const body = rows.map(r => previewData.columns.map(c => r[c] ?? '').join('\t')).join('\n');
          navigator.clipboard.writeText(`${headers}\n${body}`);
          setCopied(true);
          setTimeout(() => setCopied(false), 2000);
        };

        return (
          <div className="ui-panel space-y-4 p-6">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between border-b pb-4 dark:border-slate-800">
              <SectionHeader
                title="생성된 합성데이터 샘플 미리보기"
                description={
                  previewData
                    ? `전체 ${previewData.total_rows.toLocaleString()}건 중 상위 ${rows?.length || 0}행 샘플 (총 ${previewData.columns.length}개 컬럼)`
                    : '생성된 합성 데이터를 불러오는 중입니다.'
                }
                Icon={Table}
              />
              <div className="flex items-center gap-2 flex-wrap">
                {/* Tab switcher: Synthetic vs Original */}
                <div className="inline-flex rounded-xl border border-subtle bg-surface-muted p-0.5 text-xs font-semibold">
                  <button
                    type="button"
                    onClick={() => setPreviewTab('synthetic')}
                    className={`px-3 py-1.5 rounded-lg transition-all cursor-pointer ${
                      previewTab === 'synthetic'
                        ? 'bg-accent text-accent-fg shadow-xs font-bold'
                        : 'text-fg-muted hover:text-fg'
                    }`}
                  >
                    합성데이터 ({previewData?.synthetic_rows.length || 0})
                  </button>
                  {previewData?.original_rows && previewData.original_rows.length > 0 && (
                    <button
                      type="button"
                      onClick={() => setPreviewTab('original')}
                      className={`px-3 py-1.5 rounded-lg transition-all cursor-pointer ${
                        previewTab === 'original'
                          ? 'bg-accent text-accent-fg shadow-xs font-bold'
                          : 'text-fg-muted hover:text-fg'
                      }`}
                    >
                      원본 대조
                    </button>
                  )}
                </div>

                {/* Copy button */}
                <button
                  type="button"
                  onClick={copyTableToClipboard}
                  disabled={!rows || rows.length === 0}
                  className="ui-button-secondary px-2.5 py-1.5 text-xs cursor-pointer"
                  title="표 데이터를 클립보드에 복사 (Excel 붙여넣기 가능)"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
                  <span className="hidden sm:inline">{copied ? '복사됨' : '샘플 복사'}</span>
                </button>
              </div>
            </div>

            {/* Search & sub-info bar */}
            <div className="flex items-center justify-between gap-3">
              <div className="relative flex-1 max-w-xs">
                <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-fg-muted" />
                <input
                  type="text"
                  value={previewSearch}
                  onChange={(e) => setPreviewSearch(e.target.value)}
                  placeholder="샘플 내 값 검색..."
                  className="ui-field w-full py-1.5 pl-8 pr-3 text-xs"
                />
              </div>
              <div className="text-2xs text-fg-muted font-mono">
                {previewTab === 'synthetic' ? '[합성] 딥러닝 100% 가상 생성본' : '[원본] 원본 데이터 레퍼런스'}
              </div>
            </div>

            {/* Table container */}
            <div className="rounded-xl border border-subtle bg-surface overflow-hidden">
              {previewLoading ? (
                <div className="py-12 text-center text-xs text-fg-muted space-y-2">
                  <RefreshCw className="w-5 h-5 animate-spin mx-auto text-accent" />
                  <p>합성데이터 샘플을 로드하는 중입니다...</p>
                </div>
              ) : !previewData || !rows || rows.length === 0 ? (
                <div className="py-12 text-center text-xs text-fg-muted">
                  미리보기 가능한 데이터가 없습니다.
                </div>
              ) : (
                <div className="overflow-x-auto max-h-[380px] scrollbar-thin">
                  <table className="w-full text-left text-xs font-mono border-collapse">
                    <thead className="sticky top-0 bg-surface-muted border-b border-subtle text-fg font-bold z-10">
                      <tr>
                        <th className="px-3 py-2.5 border-r border-subtle text-center text-2xs text-fg-muted bg-surface-muted w-12 shrink-0">
                          #
                        </th>
                        {previewData.columns.map((col) => (
                          <th key={col} className="px-3.5 py-2.5 border-r border-subtle last:border-r-0 whitespace-nowrap text-2xs">
                            {col}
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
                          {previewData.columns.map((col) => {
                            const val = row[col];
                            const isNull = val === null || val === undefined || val === '';
                            return (
                              <td key={col} className="px-3.5 py-2 border-r border-subtle last:border-r-0 whitespace-nowrap text-fg/90">
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
          </div>
        );
      })()}

      {/* Submission Package Directory Structure & Download Box */}
      <div className="ui-panel space-y-4 p-6">
        <SectionHeader
          title="제출용 3대 패키지 및 공문서 다운로드"
          description="한글(HWPX) 심의자료 3종과 HTML 확인본 생성 완료"
          Icon={FileText}
          action={activeJob.package_zip && (
            <a
              href={getDownloadUrl(activeJob.package_zip)}
              className="ui-button-primary px-5 py-2.5"
            >
              <Download className="w-4 h-4" />
              전체 패키지 압축 ZIP 다운로드
            </a>
          )}
        />

        {/* Folder structure cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
          <div className={`p-4 rounded-xl border space-y-2 ${
            isDarkMode ? 'bg-slate-950 border-slate-800' : 'bg-slate-50 border-slate-200'
          }`}>
            <div className="text-xs font-bold text-sky-600 dark:text-sky-400 flex items-center gap-1.5">
              1. 원본데이터 폴더
            </div>
            <div className={`text-xs font-semibold ${isDarkMode ? 'text-slate-300' : 'text-slate-700'}`}>
              {activeJob.original_filename}
            </div>
            <div className="text-2xs text-slate-400 font-mono truncate">
              SHA-256: {activeJob.file_sha256}
            </div>
          </div>

          <div className={`p-4 rounded-xl border space-y-2 ${
            isDarkMode ? 'bg-slate-950 border-slate-800' : 'bg-slate-50 border-slate-200'
          }`}>
            <div className="text-xs font-bold text-indigo-600 dark:text-indigo-400 flex items-center gap-1.5">
              2. 합성데이터 폴더
            </div>
            <div className={`text-xs font-semibold ${isDarkMode ? 'text-slate-300' : 'text-slate-700'}`}>
              합성데이터.csv & 합성데이터.xlsx
            </div>
            <div className="text-2xs text-slate-400">
              {activeJob.target_rows}건 생성 완료 (체크포인트 저장됨)
            </div>
          </div>

          <div className={`p-4 rounded-xl border space-y-2 ${
            isDarkMode ? 'bg-slate-950 border-slate-800' : 'bg-slate-50 border-slate-200'
          }`}>
            <div className="text-xs font-bold text-rose-600 dark:text-rose-400 flex items-center gap-1.5">
              3. 심의위원회 심의자료 (HWPX 3종)
            </div>
            <div className={`text-xs space-y-0.5 ${isDarkMode ? 'text-slate-300' : 'text-slate-700'}`}>
              <div>[제출용] 원본데이터 명세서.hwpx</div>
              <div>[제출용] 합성데이터 명세서.hwpx</div>
              <div>[제출용] 안전성 및 유용성 측정결과서.hwpx</div>
              <div>[확인용] HTML 확인본 / 입력내용 JSON</div>
            </div>
          </div>
        </div>
      </div>

      {/* Restart Button */}
      <div className="text-center pt-2">
        <button
          onClick={() => {
            setStep(1);
            setProfile(null);
            setActiveJob(null);
          }}
          className="ui-button-secondary px-6 py-2.5"
        >
          + 새 데이터셋 합성 작업 시작
        </button>
      </div>
    </div>
  );
};
