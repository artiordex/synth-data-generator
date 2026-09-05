import React, { useState, useEffect } from 'react';
import {
  Upload, Database, Sliders, Play, CheckCircle2,
  AlertCircle, BookOpen, Layers, Sun, Moon, FileCode, Zap,
  ShieldCheck, Cpu, History, Info, HelpCircle, ArrowLeftRight
} from 'lucide-react';
import { DatasetProfile, JobStatus, SynthesisRequest } from '../types';
import { uploadDataset, getDatasetProfile, startSynthesis, cancelSynthesis, getJobStatus } from '../services/api';
import { DataDictionaryModal } from '../features/dictionary/DataDictionaryModal';
import { IntegratedHistoryModal, HistoryType } from '../features/history/IntegratedHistoryModal';
import { StepUpload } from '../features/dataset/StepUpload';
import { StepProfile } from '../features/dataset/StepProfile';
import { StepConfig } from '../features/synthesis/StepConfig';
import { defaultSynthesisOptions, SynthesisOptions } from '../features/synthesis/AdvancedSynthesisSettings';
import { StepProgress } from '../features/synthesis/StepProgress';
import { BatchSynthesisPanel } from '../features/synthesis/BatchSynthesisPanel';
import { RelationalSynthesisPanel } from '../features/synthesis/RelationalSynthesisPanel';
import { TimeSeriesPanel } from '../features/synthesis/TimeSeriesPanel';
import { SynthesisWorkflowSelector, SyntheticWorkflow } from '../features/synthesis/SynthesisWorkflowSelector';
import { StepReport } from '../features/reports/StepReport';
import { QuickDummyBuilder } from '../features/dummy/QuickDummyBuilder';
import { PseudonymStudio } from '../features/pseudonym/PseudonymStudio';
import { DataConverterStudio } from '../features/converter/DataConverterStudio';

export default function App() {
  // Theme state (Default: Light mode, saved in localStorage)
  const [isDarkMode, setIsDarkMode] = useState<boolean>(() => {
    const saved = localStorage.getItem('theme');
    return saved === 'dark';
  });

  useEffect(() => {
    localStorage.setItem('theme', isDarkMode ? 'dark' : 'light');
    if (isDarkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [isDarkMode]);

  const [step, setStep] = useState<number>(1);
  const [syntheticWorkflow, setSyntheticWorkflow] = useState<SyntheticWorkflow>('single');
  const [batchFiles] = useState<File[]>([]);
  const [selectedBatchId, setSelectedBatchId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'pseudo' | 'synthetic' | 'dummy' | 'converter'>('synthetic');
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadedFilename, setUploadedFilename] = useState<string>('');
  const [profile, setProfile] = useState<DatasetProfile | null>(null);
  const [reviewMetadata, setReviewMetadata] = useState<Record<string, string>>({});
  const [isDictionaryOpen, setIsDictionaryOpen] = useState<boolean>(false);
  const [isHistoryOpen, setIsHistoryOpen] = useState<boolean>(false);
  const [historyType, setHistoryType] = useState<HistoryType>('all');
  const [batchViewKey, setBatchViewKey] = useState(0);

  // Form Config
  const [departmentName, setDepartmentName] = useState<string>('범용 데이터분석팀');
  const [projectPurpose, setProjectPurpose] = useState<string>('AI 모델 학습 및 가명정보 분석 연구');
  const [modelType, setModelType] = useState<'statistical' | 'gaussian_copula' | 'ctgan' | 'tvae'>('ctgan');
  const [targetRows, setTargetRows] = useState<number>(1000);
  const [synthesisOptions, setSynthesisOptions] = useState<SynthesisOptions>({ ...defaultSynthesisOptions });
  const [dpEnabled, setDpEnabled] = useState<boolean>(false);
  const [dpEpsilon, setDpEpsilon] = useState<number>(1.0);
  const [qualityThreshold, setQualityThreshold] = useState<number>(0.8);

  // Active Job
  const [activeJob, setActiveJob] = useState<JobStatus | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Poll active job
  useEffect(() => {
    if (!activeJob || activeJob.status === 'completed' || activeJob.status === 'failed' || activeJob.status === 'canceled') {
      return;
    }

    const interval = setInterval(async () => {
      try {
        const updated = await getJobStatus(activeJob.id);
        setActiveJob(updated);
        if (updated.status === 'completed') {
          setStep(5);
        } else if (updated.status === 'failed') {
          setErrorMsg(updated.message || '합성 작업 실패');
        }
      } catch (e) {
        console.error(e);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [activeJob]);

  const handleFileUpload = async (file: File) => {
    setIsUploading(true);
    setErrorMsg(null);
    try {
      const uploadRes = await uploadDataset(file);
      setUploadedFilename(uploadRes.filename);
      const prof = await getDatasetProfile(uploadRes.filename);
      setProfile(prof);
      setSynthesisOptions({ ...defaultSynthesisOptions, ...prof.notebook_preset?.options });
      setTargetRows(prof.row_count);
      setStep(2);
    } catch (err: any) {
      setErrorMsg(err.message || '파일 업로드 실패');
    } finally {
      setIsUploading(false);
    }
  };

  const handleStartSynthesis = async () => {
    if (!uploadedFilename) return;
    setErrorMsg(null);
    try {
      const req: SynthesisRequest = {
        file_name: uploadedFilename,
        department_name: departmentName,
        project_purpose: projectPurpose,
        model_type: modelType,
        target_rows: Number(targetRows),
        ...synthesisOptions,
        dp_enabled: dpEnabled,
        eps: Number(dpEpsilon),
        quality_threshold: Number(qualityThreshold),
      };
      const job = await startSynthesis(req);
      setActiveJob(job);
      setStep(4);
    } catch (err: any) {
      setErrorMsg(err.message || '합성 작업 시작 실패');
    }
  };

  const handleCancelJob = async () => {
    if (!activeJob) return;
    try {
      await cancelSynthesis(activeJob.id);
      setActiveJob({ ...activeJob, status: 'canceled', message: '작업 취소됨' });
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="app-shell min-h-screen flex flex-col bg-[var(--ui-canvas)] text-[var(--ui-text)] transition-colors duration-200">
      {/* Header */}
      <header className="sticky top-0 z-40 border-b border-[var(--ui-border)] bg-[color:var(--ui-surface)]/95 px-4 py-3 shadow-sm backdrop-blur transition-colors sm:px-6">
        <div className="mx-auto flex w-full max-w-[1440px] flex-col gap-3">
          <div className="flex min-w-0 items-center justify-between gap-3">
            <button
              onClick={() => {
                setActiveTab('synthetic');
                setSyntheticWorkflow('single');
                setStep(1);
                setProfile(null);
                setActiveJob(null);
                setErrorMsg(null);
              }}
              className="group flex min-w-0 shrink-0 sm:flex-1 items-center gap-3 text-left focus:outline-none cursor-pointer"
              title="메인 화면으로 이동"
            >
              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-accent text-accent-fg shadow-xs transition-transform group-hover:scale-105">
                <Layers className="h-6 w-6" />
              </div>
              <div className="hidden sm:flex min-w-0 items-center gap-2.5 sm:gap-3">
                <h1 className="truncate text-xl sm:text-2xl font-black tracking-tight text-fg transition-colors group-hover:text-accent leading-none">
                  사내 데이터 생성기
                </h1>
                <span className="hidden md:inline-block rounded-md border border-subtle bg-surface-muted px-2 py-0.5 text-[10px] font-medium text-fg-muted whitespace-nowrap">
                  가명 · 합성 · 더미 · 변환
                </span>
              </div>
            </button>

            <div className="flex shrink-0 items-center gap-2 overflow-x-auto scrollbar-none">
              {/* Light / Dark Mode Toggle Button */}
              <button
                onClick={() => setIsDarkMode(!isDarkMode)}
                className="ui-button-secondary shrink-0 whitespace-nowrap px-3"
                title={isDarkMode ? "밝은 화면(라이트 모드)으로 전환" : "어두운 화면(다크 모드)으로 전환"}
              >
                {isDarkMode ? (
                  <>
                    <Sun className="w-4 h-4 text-amber-400 fill-amber-400/20" />
                    <span className="hidden sm:inline">라이트 모드</span>
                  </>
                ) : (
                  <>
                    <Moon className="w-4 h-4 text-slate-600 fill-slate-600/20" />
                    <span className="hidden sm:inline">다크 모드</span>
                  </>
                )}
              </button>

              {/* AI & Data Glossary Button */}
              <button
                onClick={() => setIsDictionaryOpen(true)}
                className="ui-button-secondary shrink-0 whitespace-nowrap px-3"
                title="FlowHunt 350여 종 표준 AI·데이터 전문 용어사전 열기"
              >
                <BookOpen className="w-4 h-4 text-sky-500" />
                <span className="hidden md:inline">AI·데이터 용어사전</span>
                <span className="md:hidden">용어사전</span>
              </button>

              {/* Unified History Modal Button */}
              <button
                onClick={() => { setHistoryType('all'); setIsHistoryOpen(true); }}
                className="ui-button-secondary shrink-0 whitespace-nowrap px-3"
                title="가명·합성·더미 3대 데이터 통합 작업 이력 및 감사 로그 열람"
              >
                <History className="w-4 h-4 text-emerald-500" />
                <span className="hidden sm:inline">통합 작업 이력</span>
                <span className="sm:hidden">이력</span>
              </button>

              {/* API Docs Button */}
              <a
                href="/docs"
                target="_blank"
                rel="noopener noreferrer"
                className="ui-button-secondary shrink-0 whitespace-nowrap px-3"
                title="Swagger 대화형 API 문서 열기"
              >
                <FileCode className="w-4 h-4 text-emerald-500" />
                <span className="hidden md:inline">API 문서</span>
                <span className="md:hidden">API</span>
              </a>
            </div>
          </div>

          {/* 4 Main Tracks Navigation Tabs with Black Tooltip Speech Bubbles */}
          <div className="flex justify-center pt-0.5">
            <div className="grid w-full max-w-3xl grid-cols-2 sm:grid-cols-4 gap-1 rounded-xl border border-subtle bg-surface-muted p-1 shadow-xs">
              {/* Tab 1: 가명데이터 */}
              <button
                onClick={() => setActiveTab('pseudo')}
                aria-label="가명데이터"
                className={`group relative flex items-center justify-center gap-2 rounded-lg px-3 py-2 transition-all ${
                  activeTab === 'pseudo'
                    ? 'bg-accent text-accent-fg shadow-sm font-bold'
                    : 'text-fg-muted hover:text-fg hover:bg-surface/60 font-medium'
                }`}
              >
                <ShieldCheck className="h-4 w-4 shrink-0" />
                <span className="text-sm sm:text-base font-bold tracking-tight">가명데이터</span>

                {/* Circle Help Icon with High Contrast Black Speech Bubble */}
                <div className="relative group/tooltip inline-flex items-center ml-0.5">
                  <span
                    onClick={(e) => e.stopPropagation()}
                    className={`p-0.5 rounded-full transition-colors cursor-help ${
                      activeTab === 'pseudo' ? 'text-accent-fg/80 hover:text-accent-fg' : 'text-fg-muted hover:text-accent'
                    }`}
                    title="가명데이터 설명 보기"
                  >
                    <HelpCircle className="w-3.5 h-3.5" />
                  </span>

                  {/* 검은 말풍선 (Black Speech Bubble) - 최고대비 순백색 텍스트 */}
                  <div className="ui-tooltip-bubble pointer-events-none absolute top-full left-0 sm:left-1/2 sm:-translate-x-1/2 mt-2.5 hidden group-hover/tooltip:block w-80 sm:w-96 rounded-xl p-4 shadow-2xl z-50">
                    <div className="ui-tooltip-arrow absolute -top-1.5 left-5 sm:left-1/2 sm:-translate-x-1/2 w-3 h-3 rotate-45" />
                    <div className="relative z-10 space-y-2 text-left">
                      <div className="tooltip-title flex items-center gap-2 text-sm font-bold text-white">
                        <ShieldCheck className="w-4 h-4 text-sky-400 shrink-0" />
                        <span style={{ color: '#ffffff', fontWeight: 700 }}>가명데이터 (Pseudonymization)</span>
                      </div>
                      <p className="tooltip-desc text-[13px] leading-relaxed break-keep" style={{ color: '#f8fafc', fontWeight: 400 }}>
                        이름, 전화번호, 주민번호 등 개인식별정보를 한국형 Faker 가명값 및 암호화 기법으로 치환합니다. 원본의 행 구조와 통계적 상관관계를 유지하면서 사내 분석·통계에 안전하게 활용합니다.
                      </p>
                    </div>
                  </div>
                </div>
              </button>

              {/* Tab 2: 합성데이터 */}
              <button
                onClick={() => setActiveTab('synthetic')}
                aria-label="합성데이터"
                className={`group relative flex items-center justify-center gap-2 rounded-lg px-3 py-2 transition-all ${
                  activeTab === 'synthetic'
                    ? 'bg-accent text-accent-fg shadow-sm font-bold'
                    : 'text-fg-muted hover:text-fg hover:bg-surface/60 font-medium'
                }`}
              >
                <Cpu className="h-4 w-4 shrink-0" />
                <span className="text-sm sm:text-base font-bold tracking-tight">합성데이터</span>

                {/* Circle Help Icon with High Contrast Black Speech Bubble */}
                <div className="relative group/tooltip inline-flex items-center ml-0.5">
                  <span
                    onClick={(e) => e.stopPropagation()}
                    className={`p-0.5 rounded-full transition-colors cursor-help ${
                      activeTab === 'synthetic' ? 'text-accent-fg/80 hover:text-accent-fg' : 'text-fg-muted hover:text-accent'
                    }`}
                    title="합성데이터 설명 보기"
                  >
                    <HelpCircle className="w-3.5 h-3.5" />
                  </span>

                  {/* 검은 말풍선 (Black Speech Bubble) - 최고대비 순백색 텍스트 */}
                  <div className="ui-tooltip-bubble pointer-events-none absolute top-full left-1/2 -translate-x-1/2 mt-2.5 hidden group-hover/tooltip:block w-80 sm:w-96 rounded-xl p-4 shadow-2xl z-50">
                    <div className="ui-tooltip-arrow absolute -top-1.5 left-1/2 -translate-x-1/2 w-3 h-3 rotate-45" />
                    <div className="relative z-10 space-y-2 text-left">
                      <div className="tooltip-title flex items-center gap-2 text-sm font-bold text-white">
                        <Cpu className="w-4 h-4 text-sky-400 shrink-0" />
                        <span style={{ color: '#ffffff', fontWeight: 700 }}>합성데이터 (Synthetic Data)</span>
                      </div>
                      <p className="tooltip-desc text-[13px] leading-relaxed break-keep" style={{ color: '#f8fafc', fontWeight: 400 }}>
                        CTGAN, TVAE, Copula 등 AI 딥러닝 모델이 원본의 통계적 패턴과 상관관계만 학습하여 100% 새로 생성한 가상 데이터입니다. 실제 개인정보가 전혀 없어 사외 반출이나 AI 학습에 가장 안전합니다.
                      </p>
                    </div>
                  </div>
                </div>
              </button>

              {/* Tab 3: 더미데이터 */}
              <button
                onClick={() => setActiveTab('dummy')}
                aria-label="더미데이터"
                className={`group relative flex items-center justify-center gap-2 rounded-lg px-3 py-2 transition-all ${
                  activeTab === 'dummy'
                    ? 'bg-accent text-accent-fg shadow-sm font-bold'
                    : 'text-fg-muted hover:text-fg hover:bg-surface/60 font-medium'
                }`}
              >
                <Database className="h-4 w-4 shrink-0" />
                <span className="text-sm sm:text-base font-bold tracking-tight">더미데이터</span>

                {/* Circle Help Icon with High Contrast Black Speech Bubble */}
                <div className="relative group/tooltip inline-flex items-center ml-0.5">
                  <span
                    onClick={(e) => e.stopPropagation()}
                    className={`p-0.5 rounded-full transition-colors cursor-help ${
                      activeTab === 'dummy' ? 'text-accent-fg/80 hover:text-accent-fg' : 'text-fg-muted hover:text-accent'
                    }`}
                    title="더미데이터 설명 보기"
                  >
                    <HelpCircle className="w-3.5 h-3.5" />
                  </span>

                  {/* 검은 말풍선 (Black Speech Bubble) - 최고대비 순백색 텍스트 */}
                  <div className="ui-tooltip-bubble pointer-events-none absolute top-full right-0 sm:right-auto sm:left-1/2 sm:-translate-x-1/2 mt-2.5 hidden group-hover/tooltip:block w-80 sm:w-96 rounded-xl p-4 shadow-2xl z-50">
                    <div className="ui-tooltip-arrow absolute -top-1.5 right-5 sm:right-auto sm:left-1/2 sm:-translate-x-1/2 w-3 h-3 rotate-45" />
                    <div className="relative z-10 space-y-2 text-left">
                      <div className="tooltip-title flex items-center gap-2 text-sm font-bold text-white">
                        <Database className="w-4 h-4 text-sky-400 shrink-0" />
                        <span style={{ color: '#ffffff', fontWeight: 700 }}>더미데이터 (Dummy Data)</span>
                      </div>
                      <p className="tooltip-desc text-[13px] leading-relaxed break-keep" style={{ color: '#f8fafc', fontWeight: 400 }}>
                        원본 데이터 없이도 사전에 정의된 규칙(인적사항, 결제정보, 주소 등)에 따라 시스템 개발, 기능 검증 및 QA 부하 테스트를 위해 즉시 대량으로 생성하는 모의 데이터입니다.
                      </p>
                    </div>
                  </div>
                </div>
              </button>

              {/* Tab 4: 데이터변환 */}
              <button
                onClick={() => setActiveTab('converter')}
                aria-label="데이터변환"
                className={`group relative flex items-center justify-center gap-2 rounded-lg px-3 py-2 transition-all ${
                  activeTab === 'converter'
                    ? 'bg-accent text-accent-fg shadow-sm font-bold'
                    : 'text-fg-muted hover:text-fg hover:bg-surface/60 font-medium'
                }`}
              >
                <ArrowLeftRight className="h-4 w-4 shrink-0" />
                <span className="text-sm sm:text-base font-bold tracking-tight">데이터변환</span>

                {/* Circle Help Icon with High Contrast Black Speech Bubble */}
                <div className="relative group/tooltip inline-flex items-center ml-0.5">
                  <span
                    onClick={(e) => e.stopPropagation()}
                    className={`p-0.5 rounded-full transition-colors cursor-help ${
                      activeTab === 'converter' ? 'text-accent-fg/80 hover:text-accent-fg' : 'text-fg-muted hover:text-accent'
                    }`}
                    title="데이터변환 설명 보기"
                  >
                    <HelpCircle className="w-3.5 h-3.5" />
                  </span>

                  {/* 검은 말풍선 (Black Speech Bubble) - 최고대비 순백색 텍스트 */}
                  <div className="ui-tooltip-bubble pointer-events-none absolute top-full right-0 sm:right-auto sm:left-1/2 sm:-translate-x-1/2 mt-2.5 hidden group-hover/tooltip:block w-80 sm:w-96 rounded-xl p-4 shadow-2xl z-50">
                    <div className="ui-tooltip-arrow absolute -top-1.5 right-5 sm:right-auto sm:left-1/2 sm:-translate-x-1/2 w-3 h-3 rotate-45" />
                    <div className="relative z-10 space-y-2 text-left">
                      <div className="tooltip-title flex items-center gap-2 text-sm font-bold text-white">
                        <ArrowLeftRight className="w-4 h-4 text-sky-400 shrink-0" />
                        <span style={{ color: '#ffffff', fontWeight: 700 }}>데이터변환 (Data & Doc Converter)</span>
                      </div>
                      <p className="tooltip-desc text-[13px] leading-relaxed break-keep" style={{ color: '#f8fafc', fontWeight: 400 }}>
                        CSV, Excel, Parquet, JSON, SQL 등 이기종 데이터 포맷 상호 변환 및 HWP, HWPX, Word(DOCX) 사내 문서를 원본 서식 그대로 PDF/HWPX로 고속 변환합니다.
                      </p>
                    </div>
                  </div>
                </div>
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="mx-auto w-full max-w-[1440px] flex-1 space-y-6 p-4 sm:p-6 lg:p-8">
        {activeTab === 'pseudo' && (
          <PseudonymStudio isDarkMode={isDarkMode} />
        )}
        {activeTab === 'dummy' && (
          <QuickDummyBuilder isDarkMode={isDarkMode} />
        )}
        {activeTab === 'converter' && (
          <DataConverterStudio isDarkMode={isDarkMode} />
        )}
        {activeTab === 'synthetic' && (
          <>
            <SynthesisWorkflowSelector
              value={syntheticWorkflow}
              onChange={workflow => {
                setSyntheticWorkflow(workflow);
                if (workflow === 'batch') setSelectedBatchId(null);
              }}
              isDarkMode={isDarkMode}
            />

            {syntheticWorkflow === 'timeseries' ? (
              <TimeSeriesPanel isDarkMode={isDarkMode} onClose={() => setSyntheticWorkflow('single')} />
            ) : syntheticWorkflow === 'relational' ? (
              <RelationalSynthesisPanel isDarkMode={isDarkMode} onClose={() => setSyntheticWorkflow('single')} />
            ) : syntheticWorkflow === 'batch' ? (
              <BatchSynthesisPanel
                key={batchViewKey}
                initialFiles={batchFiles}
                initialBatchId={selectedBatchId}
                isDarkMode={isDarkMode}
                onClose={() => {
                  setSelectedBatchId(null);
                  setSyntheticWorkflow('single');
                }}
                onOpenJob={job => {
                  setSyntheticWorkflow('single');
                  setActiveJob(job);
                  setStep(5);
                }}
              />
            ) : (
              <>
            {/* Step Indicator */}
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
              {[
                { num: 1, label: "데이터 업로드 & 무결성", icon: Upload },
                { num: 2, label: "프로파일링 & PII 가명화", icon: Database },
                { num: 3, label: "AI 모델 & DP 파라미터", icon: Sliders },
                { num: 4, label: "실시간 파이프라인 모니터링", icon: Play },
                { num: 5, label: "3대 평가 & HWP 패키지", icon: CheckCircle2 },
              ].map((s) => {
                const isActive = step === s.num;
                const isCompleted = step > s.num;
                return (
                  <button
                    key={s.num}
                    onClick={() => {
                      if (profile && s.num <= 3) setStep(s.num);
                      if (activeJob?.status === 'completed' && s.num === 5) setStep(5);
                    }}
                    className={`flex min-h-[76px] min-w-0 items-center gap-3 rounded-2xl border p-3.5 text-left transition-all ${
                      isActive
                        ? isDarkMode
                          ? 'bg-sky-950/60 border-sky-500/80 text-white shadow-lg shadow-sky-950/50 ring-1 ring-sky-500/40'
                          : 'bg-sky-50 border-sky-500 text-sky-950 shadow-md shadow-sky-100 ring-1 ring-sky-400'
                        : isCompleted
                        ? isDarkMode
                          ? 'bg-slate-900/60 border-slate-800 text-slate-300'
                          : 'bg-white border-slate-200 text-slate-700 shadow-sm'
                        : isDarkMode
                        ? 'bg-slate-900/20 border-slate-800/40 text-slate-600 opacity-60'
                        : 'bg-slate-100/70 border-slate-200 text-slate-600 opacity-80'
                    }`}
                  >
                    <div className={`w-7 h-7 rounded-xl flex items-center justify-center text-xs font-bold ${
                      isActive ? 'bg-sky-500 text-white' : isCompleted ? 'bg-emerald-500 text-white' : isDarkMode ? 'bg-slate-800 text-slate-400' : 'bg-slate-200 text-slate-500'
                    }`}>
                      {isCompleted ? <CheckCircle2 className="w-4 h-4" /> : s.num}
                    </div>
                    <div className="min-w-0">
                      <div className="break-keep text-xs font-bold leading-snug">{s.label}</div>
                      <div className={`text-[10px] ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>Step 0{s.num}</div>
                    </div>
                  </button>
                );
              })}
            </div>

            {/* Error Alert */}
            {errorMsg && (
              <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-rose-700 dark:text-rose-300 text-xs flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 text-rose-500" />
                  <span>{errorMsg}</span>
                </div>
                <button onClick={() => setErrorMsg(null)} className="text-rose-500 hover:text-rose-700"></button>
              </div>
            )}

            {/* Step 1: Upload */}
            {step === 1 && (
              <div className="space-y-6">
                <StepUpload
                  isDarkMode={isDarkMode}
                  isUploading={isUploading}
                  setIsUploading={setIsUploading}
                  setUploadedFilename={setUploadedFilename}
                  setProfile={setProfile}
                  setTargetRows={setTargetRows}
                  setStep={setStep}
                  setErrorMsg={setErrorMsg}
                  handleFileUpload={handleFileUpload}
                />
              </div>
            )}

            {/* Step 2: Profiling & PII */}
            {step === 2 && profile && (
              <StepProfile
                isDarkMode={isDarkMode}
                profile={profile}
                setStep={setStep}
              />
            )}

            {/* Step 3: Synthesis Config */}
            {step === 3 && (
              <StepConfig
                synthesisOptions={synthesisOptions}
                setSynthesisOptions={setSynthesisOptions}
                profile={profile}
                fileName={uploadedFilename}
                isDarkMode={isDarkMode}
                departmentName={departmentName}
                setDepartmentName={setDepartmentName}
                projectPurpose={projectPurpose}
                setProjectPurpose={setProjectPurpose}
                reviewMetadata={reviewMetadata}
                setReviewMetadata={setReviewMetadata}
                targetRows={targetRows}
                setTargetRows={setTargetRows}
                qualityThreshold={qualityThreshold}
                setQualityThreshold={setQualityThreshold}
                modelType={modelType}
                setModelType={setModelType}
                dpEnabled={dpEnabled}
                setDpEnabled={setDpEnabled}
                dpEpsilon={dpEpsilon}
                setDpEpsilon={setDpEpsilon}
                setStep={setStep}
                handleStartSynthesis={handleStartSynthesis}
              />
            )}

            {/* Step 4: Live Pipeline Progress */}
            {step === 4 && activeJob && (
              <StepProgress
                isDarkMode={isDarkMode}
                activeJob={activeJob}
                handleCancelJob={handleCancelJob}
              />
            )}

            {/* Step 5: Dashboard & HWP Package */}
            {step === 5 && activeJob && (
              <StepReport
                isDarkMode={isDarkMode}
                activeJob={activeJob}
                setStep={setStep}
                setProfile={setProfile}
                setActiveJob={setActiveJob}
              />
            )}
              </>
            )}
          </>
        )}
      </main>

      {/* Data Dictionary Modal */}
      <DataDictionaryModal
        isOpen={isDictionaryOpen}
        onClose={() => setIsDictionaryOpen(false)}
        isDarkMode={isDarkMode}
      />

      {/* Integrated History Modal */}
      <IntegratedHistoryModal
        initialType={historyType}
        onSelectBatch={(id) => {
          setSelectedBatchId(id);
          setBatchViewKey(value => value + 1);
          setSyntheticWorkflow('batch');
          setActiveTab('synthetic');
          setIsHistoryOpen(false);
        }}
        isOpen={isHistoryOpen}
        onClose={() => setIsHistoryOpen(false)}
        isDarkMode={isDarkMode}
        onSelectJob={(job) => {
          setSyntheticWorkflow('single');
          setActiveJob(job);
          setActiveTab('synthetic');
          setStep(5);
          setIsHistoryOpen(false);
        }}
      />
    </div>
  );
}
