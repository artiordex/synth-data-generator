/**
 * 파일명: SurveySynthesisPanel.tsx
 * 경로: apps/web/src/features/synthesis/SurveySynthesisPanel.tsx
 * 목적: 설문 합성 작업 화면을 제공함
 * 작성자: 개발팀
 * 작성일: 2026-09-09
 * 수정일: 2026-09-09
 */
import React, { useState, useEffect } from 'react';
import {
  ClipboardList,
  Download,
  Link2,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  FileSpreadsheet,
  Layers,
  Sparkles,
  ShieldCheck,
  X,
  FileText,
  ChevronRight,
  Database,
  ArrowRight,
  GitBranch,
  SlidersHorizontal,
  Check
} from 'lucide-react';
import {
  uploadDatasets,
  inspectSurveyModules,
  generateSurveySynthesis,
  getSurveyJobStatus,
  SurveyInspectionResponse,
  SurveyJobStatusResponse
} from '../../services/api';
import { UnifiedFileUploader } from '../shared/UnifiedFileUploader';

interface Props {
  isDarkMode: boolean;
  onClose: () => void;
  onStepChange?: (step: number) => void;
}

export const SurveySynthesisPanel: React.FC<Props> = ({ isDarkMode, onClose, onStepChange }) => {
  const [files, setFiles] = useState<File[]>([]);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysis, setAnalysis] = useState<SurveyInspectionResponse | null>(null);
  const [uploadedNames, setUploadedNames] = useState<string[]>([]);
  const [error, setError] = useState<string>('');

  // Synthesis Config
  const [modelType, setModelType] = useState<string>('ctgan');
  const [targetRows, setTargetRows] = useState<number>(1000);
  const [epochs, setEpochs] = useState<number>(30);
  const [batchSize, setBatchSize] = useState<number>(64);
  const [dpEnabled, setDpEnabled] = useState<boolean>(false);
  const [dpEpsilon, setDpEpsilon] = useState<number>(1.0);

  // Advanced Integrity & Preservation Options
  const [applyLogicRules, setApplyLogicRules] = useState<boolean>(true);
  const [preserveLikertOrder, setPreserveLikertOrder] = useState<boolean>(true);
  const [protectKAnonymity, setProtectKAnonymity] = useState<boolean>(true);

  // Active Job State
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<SurveyJobStatusResponse | null>(null);
  const [isGenerating, setIsGenerating] = useState<boolean>(false);

  useEffect(() => {
    const completed = jobStatus?.status === 'completed';
    onStepChange?.(completed ? 4 : activeJobId || isGenerating ? 3 : analysis ? 2 : 1);
  }, [activeJobId, analysis, isGenerating, jobStatus?.status, onStepChange]);

  // Poll Job Status
  useEffect(() => {
    if (!activeJobId) return;
    if (jobStatus && (jobStatus.status === 'completed' || jobStatus.status === 'failed')) {
      setIsGenerating(false);
      return;
    }

    const interval = setInterval(async () => {
      try {
        const st = await getSurveyJobStatus(activeJobId);
        setJobStatus(st);
        if (st.status === 'completed' || st.status === 'failed') {
          setIsGenerating(false);
        }
      } catch (e: any) {
        console.error(e);
      }
    }, 1500);

    return () => clearInterval(interval);
  }, [activeJobId, jobStatus]);

  const handleAnalyze = async () => {
    if (files.length < 2) return;
    setIsAnalyzing(true);
    setError('');
    setAnalysis(null);
    setJobStatus(null);
    try {
      const uploaded = await uploadDatasets(files);
      const names = uploaded.flatMap(x => (!x.error && x.filename ? [x.filename] : []));
      if (names.length < 2) throw new Error('정상 업로드된 설문 파일이 2개 미만입니다.');
      setUploadedNames(names);

      const res = await inspectSurveyModules(names);
      setAnalysis(res);
      setTargetRows(res.total_rows);
    } catch (e: any) {
      setError(e.message || '설문 모듈 분석 실패');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleStartSynthesis = async () => {
    if (!uploadedNames.length) return;
    setIsGenerating(true);
    setError('');
    setJobStatus(null);
    try {
      const res = await generateSurveySynthesis({
        file_names: uploadedNames,
        target_rows: Number(targetRows),
        model_type: modelType,
        epochs: Number(epochs),
        batch_size: Number(batchSize),
        apply_logic_rules: applyLogicRules,
        preserve_likert_order: preserveLikertOrder,
        protect_k_anonymity: protectKAnonymity,
        dp_enabled: dpEnabled,
        eps: Number(dpEpsilon),
        department_name: '설문조사 합성팀',
        project_purpose: '다중 모듈 설문 연계 무결성 합성데이터 생성',
      });
      setActiveJobId(res.job_id);
    } catch (e: any) {
      setError(e.message || '설문 합성 시작 실패');
      setIsGenerating(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* 1. Upload & Header Panel */}
      <div className="ui-panel p-6">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="ui-section-title text-base flex items-center gap-2">
              <ClipboardList className="h-5 w-5 text-emerald-500" />
              설문 모듈 연계 및 무결성 합성 (Survey Module Fusion & Logic Engine)
            </h2>
            <p className="ui-help-text mt-1">
              동일 학생 대상 분할 설문 엑셀 파일들을 공통 키로 통합 학습하고, 
              <strong>분기 로직(Skip-Logic) 무결성 100% 보정</strong>과 <strong>5점 리커트 척도 서열성 보존</strong>을 거쳐 원본 파일별로 자동 분할 저장합니다.
            </p>
          </div>
          <button
            aria-label="화면 닫기"
            onClick={onClose}
            className="ui-button-secondary px-2"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <UnifiedFileUploader
          multiple
          maxFiles={30}
          title="설문조사 모듈 파일 일괄 업로드 (2~30개)"
          subtitle="동일 응답자 대상 설문 엑셀/CSV 파일들을 드래그하거나 선택하세요. (예: 1. 진로수업.xlsx ~ 10. 가정소통.xlsx)"
          onFilesSelected={selectedFiles => setFiles(selectedFiles)}
          className="mt-5"
        />

        {files.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2">
            {files.map((f, i) => (
              <span
                key={i}
                className="inline-flex items-center gap-1.5 rounded-lg border border-slate-500/20 bg-slate-50 px-2.5 py-1 text-xs text-slate-700 dark:bg-slate-900/50 dark:text-slate-300"
              >
                <FileSpreadsheet className="h-3.5 w-3.5 text-emerald-500" />
                {f.name}
              </span>
            ))}
          </div>
        )}

        <button
          disabled={files.length < 2 || isAnalyzing || isGenerating}
          onClick={handleAnalyze}
          className="ui-button-primary mt-5 px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold"
        >
          {isAnalyzing ? (
            <RefreshCw className="mr-2 inline h-4 w-4 animate-spin" />
          ) : (
            <Link2 className="mr-2 inline h-4 w-4" />
          )}
          설문 모듈 구조, 분기 로직 및 리커트 척도 자동 분석
        </button>

        {error && (
          <div className="mt-4 rounded-xl border border-rose-500/20 bg-rose-500/10 p-3.5 text-xs text-rose-500 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* 2. Analysis & Detected Logic Rules Card */}
      {analysis && (
        <div className="ui-panel p-6 space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-500/20 pb-4">
            <div>
              <h3 className="text-sm font-bold flex items-center gap-2">
                <Layers className="h-4 w-4 text-emerald-500" />
                설문 모듈 & 무결성 분석 결과
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                총 {analysis.modules.length}개 모듈 · 원본 {analysis.total_rows.toLocaleString()}행 · 통합 {analysis.total_columns}개 문항 (5점 척도 {analysis.likert_columns_count}개 감지)
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {analysis.is_aligned && (
                <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-3 py-1 text-xs font-semibold text-emerald-500 border border-emerald-500/20">
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  1:1 행 매핑 정상
                </span>
              )}
              {analysis.detected_rules && (
                <span className="inline-flex items-center gap-1.5 rounded-full bg-sky-500/10 px-3 py-1 text-xs font-semibold text-sky-500 border border-sky-500/20">
                  <GitBranch className="h-3.5 w-3.5" />
                  분기 규칙 {analysis.detected_rules.length}개 탐지
                </span>
              )}
            </div>
          </div>

          {/* Common Quasi-Identifier Keys */}
          <div>
            <div className="text-xs font-bold text-slate-400 mb-2">
              자동 탐지된 공통 준식별자 / 결합 키 (Common Quasi-Identifiers):
            </div>
            <div className="flex flex-wrap gap-1.5">
              {analysis.common_keys.map((k, i) => (
                <span
                  key={i}
                  className="rounded-md bg-emerald-500/15 px-2.5 py-1 text-xs font-medium text-emerald-600 dark:text-emerald-400 border border-emerald-500/20"
                >
                  {k}
                </span>
              ))}
            </div>
          </div>

          {/* Auto-detected Skip Logic Rules */}
          {analysis.detected_rules && analysis.detected_rules.length > 0 && (
            <div className="rounded-xl border border-sky-500/20 bg-sky-50/40 dark:bg-sky-950/20 p-4 space-y-3">
              <div className="flex items-center justify-between">
                <div className="text-xs font-bold text-sky-700 dark:text-sky-300 flex items-center gap-2">
                  <GitBranch className="h-4 w-4 text-sky-500" />
                  자동 탐지된 설문 분기(Skip-Logic) 무결성 규칙 ({analysis.detected_rules.length}개)
                </div>
                <span className="text-2xs text-sky-600 dark:text-sky-400 font-semibold">
                  합성 시 100% 무결성 사후 보정 적용
                </span>
              </div>
              <div className="grid gap-2 sm:grid-cols-2">
                {analysis.detected_rules.map((rule, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between rounded-lg border border-sky-500/20 bg-white/80 dark:bg-slate-900/60 p-2.5 text-xs"
                  >
                    <div className="flex items-center gap-1.5 truncate text-slate-700 dark:text-slate-300">
                      <span className="font-semibold truncate">{rule.condition_col}</span>
                      <span className="text-sky-500 font-bold">={rule.condition_val}</span>
                      <ArrowRight className="h-3 w-3 text-slate-400 shrink-0" />
                      <span className="font-semibold truncate">{rule.target_col}</span>
                      <span className="text-emerald-500 font-bold">={rule.target_val}</span>
                    </div>
                    <span className="shrink-0 rounded bg-sky-100 dark:bg-sky-900/50 px-1.5 py-0.5 text-2xs font-bold text-sky-600 dark:text-sky-300">
                      신뢰도 {(rule.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Module Grid */}
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {analysis.modules.map((m, idx) => (
              <div
                key={idx}
                className="rounded-xl border border-slate-500/20 bg-slate-50/50 dark:bg-slate-900/40 p-3 text-xs space-y-1"
              >
                <div className="font-bold truncate text-slate-800 dark:text-slate-200 flex items-center gap-1.5">
                  <FileText className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
                  <span className="truncate">{m.file_key}</span>
                </div>
                <div className="text-slate-400 flex items-center justify-between pt-1">
                  <span>{m.row_count.toLocaleString()}행 · 총 {m.column_count}개 문항</span>
                  <span className="text-emerald-600 dark:text-emerald-400 font-semibold">
                    고유 {m.unique_columns.length}문항
                  </span>
                </div>
              </div>
            ))}
          </div>

          {/* 3. Synthesis Options & Run */}
          <div className="border-t border-slate-500/20 pt-5 space-y-4">
            <h4 className="text-xs font-bold text-slate-300 flex items-center gap-1.5">
              <SlidersHorizontal className="h-3.5 w-3.5 text-emerald-500" />
              AI 합성 모델 및 무결성 보존 옵션
            </h4>

            {/* Feature Toggles */}
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <label className="flex items-start gap-2.5 rounded-xl border border-emerald-500/20 bg-emerald-50/30 dark:bg-emerald-950/20 p-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={applyLogicRules}
                  onChange={e => setApplyLogicRules(e.target.checked)}
                  className="mt-0.5 rounded text-emerald-500 focus:ring-emerald-400"
                />
                <div>
                  <div className="text-xs font-bold text-emerald-600 dark:text-emerald-400">
                    분기 로직 무결성 보정 (Skip-Logic)
                  </div>
                  <div className="text-2xs text-slate-400 mt-0.5">
                    비논리적 모순 레코드 100% 원천 차단
                  </div>
                </div>
              </label>

              <label className="flex items-start gap-2.5 rounded-xl border border-sky-500/20 bg-sky-50/30 dark:bg-sky-950/20 p-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={preserveLikertOrder}
                  onChange={e => setPreserveLikertOrder(e.target.checked)}
                  className="mt-0.5 rounded text-sky-500 focus:ring-sky-400"
                />
                <div>
                  <div className="text-xs font-bold text-sky-600 dark:text-sky-400">
                    리커트 척도 서열성 보존 ({analysis.likert_columns_count}개)
                  </div>
                  <div className="text-2xs text-slate-400 mt-0.5">
                    5점 척도 순위 및 상관계수 왜곡 방지
                  </div>
                </div>
              </label>

              <label className="flex items-start gap-2.5 rounded-xl border border-indigo-500/20 bg-indigo-50/30 dark:bg-indigo-950/20 p-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={protectKAnonymity}
                  onChange={e => setProtectKAnonymity(e.target.checked)}
                  className="mt-0.5 rounded text-indigo-500 focus:ring-indigo-400"
                />
                <div>
                  <div className="text-xs font-bold text-indigo-600 dark:text-indigo-400">
                    준식별자 k-익명성 보호 (k ≥ 5)
                  </div>
                  <div className="text-2xs text-slate-400 mt-0.5">
                    희귀 계층 특이치 재식별 위험 차단
                  </div>
                </div>
              </label>
            </div>

            {/* Model & Row count parameters */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4 pt-2">
              <div>
                <label className="text-xs font-semibold block text-slate-400 mb-1">AI 합성 모델</label>
                <select
                  value={modelType}
                  onChange={e => setModelType(e.target.value)}
                  className="ui-field w-full text-xs"
                >
                  <option value="ctgan">CTGAN (다차원 범주형 딥러닝 - 권장)</option>
                  <option value="tvae">TVAE (변이형 오토인코더)</option>
                  <option value="gaussian_copula">Gaussian Copula (통계 코퓰라)</option>
                  <option value="statistical">Statistical (고속 빈도 샘플러)</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-semibold block text-slate-400 mb-1">목표 생성 행 수 (증강 규모)</label>
                <input
                  type="number"
                  min={10}
                  max={100000}
                  step={100}
                  value={targetRows}
                  onChange={e => setTargetRows(Number(e.target.value))}
                  className="ui-field w-full text-xs"
                />
              </div>

              {modelType === 'ctgan' || modelType === 'tvae' ? (
                <>
                  <div>
                    <label className="text-xs font-semibold block text-slate-400 mb-1">학습 에포크 (Epochs)</label>
                    <input
                      type="number"
                      min={1}
                      max={300}
                      value={epochs}
                      onChange={e => setEpochs(Number(e.target.value))}
                      className="ui-field w-full text-xs"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-semibold block text-slate-400 mb-1">배치 크기 (Batch Size)</label>
                    <input
                      type="number"
                      min={10}
                      max={512}
                      value={batchSize}
                      onChange={e => setBatchSize(Number(e.target.value))}
                      className="ui-field w-full text-xs"
                    />
                  </div>
                </>
              ) : null}
            </div>

            <div className="flex items-center justify-between pt-2">
              <div className="flex items-center gap-3">
                <label className="flex items-center gap-2 cursor-pointer text-xs font-semibold">
                  <input
                    type="checkbox"
                    checked={dpEnabled}
                    onChange={e => setDpEnabled(e.target.checked)}
                    className="rounded text-emerald-500 focus:ring-emerald-400"
                  />
                  <span>차분 프라이버시 (DP) 노이즈 주입</span>
                </label>
                {dpEnabled && (
                  <div className="flex items-center gap-1.5 text-xs">
                    <span className="text-slate-400">Epsilon (ε):</span>
                    <input
                      type="number"
                      min={0.1}
                      max={10}
                      step={0.1}
                      value={dpEpsilon}
                      onChange={e => setDpEpsilon(Number(e.target.value))}
                      className="ui-field w-20 py-1 text-xs"
                    />
                  </div>
                )}
              </div>

              <button
                disabled={isGenerating}
                onClick={handleStartSynthesis}
                className="ui-button-primary px-6 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold"
              >
                {isGenerating ? (
                  <>
                    <RefreshCw className="mr-2 inline h-4 w-4 animate-spin" />
                    설문 통합 합성 진행 중...
                  </>
                ) : (
                  <>
                    <Sparkles className="mr-2 inline h-4 w-4" />
                    설문 통합 합성 및 무결성 보정 실행
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 4. Generation Progress */}
      {isGenerating && jobStatus && (
        <div className="ui-panel p-6 space-y-4">
          <div className="flex items-center justify-between text-xs font-bold">
            <span className="flex items-center gap-2 text-emerald-500">
              <RefreshCw className="h-4 w-4 animate-spin" />
              {jobStatus.message || '작업 처리 중...'}
            </span>
            <span>{jobStatus.progress}%</span>
          </div>
          <div className="w-full bg-slate-200 dark:bg-slate-800 rounded-full h-2.5 overflow-hidden">
            <div
              className="bg-emerald-500 h-2.5 rounded-full transition-all duration-300"
              style={{ width: `${Math.max(5, jobStatus.progress)}%` }}
            />
          </div>
        </div>
      )}

      {/* 5. Completed Results & Download Card */}
      {jobStatus && jobStatus.status === 'completed' && (
        <div className="ui-panel p-6 space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-500/20 pb-4">
            <div>
              <h3 className="text-base font-bold text-emerald-500 flex items-center gap-2">
                <CheckCircle2 className="h-5 w-5" />
                설문 합성 및 결과 저장 완료
              </h3>
              <p className="text-xs text-slate-400 mt-1">
                생성된 {jobStatus.target_rows?.toLocaleString()}행의 설문 데이터와 평가 결과를 확인하세요.
              </p>
            </div>
            {jobStatus.download_url && (
              <a
                href={jobStatus.download_url}
                className="ui-button-primary px-6 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold flex items-center gap-2 shadow-lg"
              >
                <Download className="h-4 w-4" />
                전체 설문 패키지 (.ZIP) 일괄 다운로드
              </a>
            )}
          </div>

          {/* Quality & Integrity Badges */}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div className="rounded-xl border border-emerald-500/30 bg-emerald-50/40 dark:bg-emerald-950/30 p-3 text-center">
              <div className="text-xs text-slate-400">설문 논리 무결성</div>
              <div className="text-lg font-bold text-emerald-500 mt-0.5 flex items-center justify-center gap-1">
                {jobStatus.logic_integrity?.passed === true && <Check className="h-4 w-4 stroke-[3]" />}
                {jobStatus.logic_integrity?.integrity_score != null
                  ? `${jobStatus.logic_integrity.integrity_score}% ${jobStatus.logic_integrity.passed === true ? 'PASS' : '검토 필요'}`
                  : '미측정'}
              </div>
            </div>
            <div className="rounded-xl border border-slate-500/20 bg-slate-50/50 dark:bg-slate-900/40 p-3 text-center">
              <div className="text-xs text-slate-400">종합 품질 점수</div>
              <div className="text-lg font-bold text-emerald-500 mt-0.5">
                {jobStatus.quality?.overall_quality != null
                  ? `${(jobStatus.quality.overall_quality * 100).toFixed(1)}점` : '미측정'}
              </div>
            </div>
            <div className="rounded-xl border border-slate-500/20 bg-slate-50/50 dark:bg-slate-900/40 p-3 text-center">
              <div className="text-xs text-slate-400">증강 생성 규모</div>
              <div className="text-lg font-bold text-slate-800 dark:text-slate-100 mt-0.5">
                {jobStatus.target_rows?.toLocaleString()}행
              </div>
            </div>
            <div className="rounded-xl border border-slate-500/20 bg-slate-50/50 dark:bg-slate-900/40 p-3 text-center">
              <div className="text-xs text-slate-400">상관관계 보존율</div>
              <div className="text-lg font-bold text-sky-500 mt-0.5">
                {jobStatus.quality?.utility?.correlation?.overall_correlation_score != null
                  ? `${(jobStatus.quality.utility.correlation.overall_correlation_score * 100).toFixed(1)}%` : '미측정'}
              </div>
            </div>
          </div>

          {/* Individual Split Files Table */}
          <div className="space-y-2">
            <h4 className="text-xs font-bold text-slate-400">생성된 개별 설문 모듈 엑셀 파일 목록:</h4>
            <div className="grid gap-2 sm:grid-cols-2">
              {jobStatus.tables?.map((t, idx) => (
                <div
                  key={idx}
                  className={`flex items-center justify-between rounded-xl border p-3 text-xs ${
                    idx === 0
                      ? 'border-emerald-500/40 bg-emerald-500/10'
                      : 'border-slate-500/20 bg-slate-50 dark:bg-slate-900/40'
                  }`}
                >
                  <div className="flex items-center gap-2 min-w-0 pr-2">
                    <FileSpreadsheet className={`h-4 w-4 shrink-0 ${idx === 0 ? 'text-emerald-500' : 'text-slate-400'}`} />
                    <div className="truncate">
                      <div className="font-bold truncate">{t.filename}</div>
                      <div className="text-slate-400 text-2xs">{t.rows.toLocaleString()}행 · {t.columns}열</div>
                    </div>
                  </div>
                  <a
                    href={t.download_url}
                    className="shrink-0 rounded-lg bg-slate-200 dark:bg-slate-800 px-2.5 py-1 text-slate-700 dark:text-slate-200 hover:bg-emerald-500 hover:text-white transition-colors flex items-center gap-1 font-semibold"
                  >
                    <Download className="h-3 w-3" />
                    다운로드
                  </a>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
