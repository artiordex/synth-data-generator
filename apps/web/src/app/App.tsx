import React, { useState, useEffect } from 'react';
import { 
  Upload, Database, Sliders, Play, CheckCircle2, 
  AlertCircle, BookOpen, Layers, Sun, Moon, FileCode, Zap,
  ShieldCheck, Cpu, History
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
import { BatchSynthesisPanel, ACTIVE_BATCH_KEY } from '../features/synthesis/BatchSynthesisPanel';
import { StepReport } from '../features/reports/StepReport';
import { QuickDummyBuilder } from '../features/dummy/QuickDummyBuilder';
import { PseudonymStudio } from '../features/pseudonym/PseudonymStudio';

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
  const [batchFiles, setBatchFiles] = useState<File[] | null>(() => localStorage.getItem(ACTIVE_BATCH_KEY) ? [] : null);
  const [activeTab, setActiveTab] = useState<'pseudo' | 'synthetic' | 'dummy'>('synthetic');
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
    <div className={`min-h-screen flex flex-col transition-colors duration-200 ${
      isDarkMode ? 'bg-slate-950 text-slate-100' : 'bg-slate-50 text-slate-800'
    }`}>
      {/* Header */}
      <header className={`sticky top-0 z-40 px-6 py-3.5 flex items-center justify-between border-b backdrop-blur transition-colors ${
        isDarkMode ? 'border-slate-800/80 bg-slate-900/80' : 'border-slate-200 bg-white/90 shadow-sm'
      }`}>
        <button
          onClick={() => {
            setActiveTab('synthetic');
            setStep(1);
            setProfile(null);
            setActiveJob(null);
            setErrorMsg(null);
          }}
          className="flex items-center gap-3 text-left group focus:outline-none cursor-pointer"
          title="메인 화면으로 이동"
        >
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-sky-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-sky-500/20 group-hover:scale-105 transition-transform">
            <Layers className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className={`font-bold text-base tracking-tight flex items-center gap-2 transition-colors ${
              isDarkMode ? 'text-white group-hover:text-sky-400' : 'text-slate-900 group-hover:text-sky-600'
            }`}>
              범용 AI 합성데이터 생성 플랫폼
            </h1>
          </div>
        </button>

        {/* 3 Main Tracks Navigation Tabs (No emojis) */}
        <div className={`flex items-center p-1 rounded-xl border ${
          isDarkMode ? 'bg-slate-800/90 border-slate-700/80' : 'bg-slate-100 border-slate-200'
        }`}>
          <button
            onClick={() => setActiveTab('pseudo')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'pseudo'
                ? isDarkMode 
                  ? 'bg-emerald-600 text-white shadow-sm' 
                  : 'bg-white text-emerald-700 shadow-sm'
                : isDarkMode 
                  ? 'text-slate-400 hover:text-slate-200' 
                  : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>가명데이터 (Pseudonymized)</span>
          </button>

          <button
            onClick={() => setActiveTab('synthetic')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'synthetic'
                ? isDarkMode 
                  ? 'bg-sky-600 text-white shadow-sm' 
                  : 'bg-white text-sky-700 shadow-sm'
                : isDarkMode 
                  ? 'text-slate-400 hover:text-slate-200' 
                  : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Cpu className="w-3.5 h-3.5" />
            <span>AI 합성데이터 (Synthetic)</span>
          </button>

          <button
            onClick={() => setActiveTab('dummy')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'dummy'
                ? isDarkMode 
                  ? 'bg-amber-500 text-slate-950 font-bold shadow-sm' 
                  : 'bg-white text-amber-700 shadow-sm font-bold'
                : isDarkMode 
                  ? 'text-slate-400 hover:text-slate-200' 
                  : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Database className="w-3.5 h-3.5" />
            <span>더미데이터 (Mock Dummy)</span>
          </button>
        </div>

        <div className="flex items-center gap-3">
          {/* Light / Dark Mode Toggle Button */}
          <button
            onClick={() => setIsDarkMode(!isDarkMode)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold transition-all border ${
              isDarkMode 
                ? 'bg-slate-800 hover:bg-slate-700 text-amber-300 border-slate-700 shadow-sm' 
                : 'bg-white hover:bg-slate-100 text-slate-700 border-slate-200 shadow-sm'
            }`}
            title={isDarkMode ? "밝은 화면(라이트 모드)으로 전환" : "어두운 화면(다크 모드)으로 전환"}
          >
            {isDarkMode ? (
              <>
                <Sun className="w-4 h-4 text-amber-400 fill-amber-400/20" />
                <span>라이트 모드</span>
              </>
            ) : (
              <>
                <Moon className="w-4 h-4 text-slate-600 fill-slate-600/20" />
                <span>다크 모드</span>
              </>
            )}
          </button>

          {/* AI & Data Glossary Button */}
          <button
            onClick={() => setIsDictionaryOpen(true)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold transition-all border ${
              isDarkMode 
                ? 'bg-slate-800/90 hover:bg-slate-700 text-slate-200 border-slate-700' 
                : 'bg-white hover:bg-slate-100 text-slate-700 border-slate-200 shadow-sm'
            }`}
            title="FlowHunt 350여 종 표준 AI·데이터 전문 용어사전 열기"
          >
            <BookOpen className="w-4 h-4 text-sky-500" />
            <span>AI·데이터 용어사전</span>
          </button>

          {/* Unified History Modal Button */}
          <button
            onClick={() => { setHistoryType('all'); setIsHistoryOpen(true); }}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold transition-all border ${
              isDarkMode 
                ? 'bg-slate-800/90 hover:bg-slate-700 text-slate-200 border-slate-700' 
                : 'bg-white hover:bg-slate-100 text-slate-700 border-slate-200 shadow-sm'
            }`}
            title="가명·합성·더미 3대 데이터 통합 작업 이력 및 감사 로그 열람"
          >
            <History className="w-4 h-4 text-emerald-500" />
            <span>통합 작업 이력</span>
          </button>

          {/* API Docs Button */}
          <a
            href="/docs"
            target="_blank"
            rel="noopener noreferrer"
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold transition-all border ${
              isDarkMode 
                ? 'bg-slate-800/90 hover:bg-slate-700 text-slate-200 border-slate-700' 
                : 'bg-white hover:bg-slate-100 text-slate-700 border-slate-200 shadow-sm'
            }`}
            title="Swagger 대화형 API 문서 열기"
          >
            <FileCode className="w-4 h-4 text-emerald-500" />
            <span>API 문서 (Swagger)</span>
          </a>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-6 space-y-6">
        {activeTab === 'pseudo' && (
          <PseudonymStudio isDarkMode={isDarkMode} onOpenHistory={() => { setHistoryType('pseudo'); setIsHistoryOpen(true); }} />
        )}
        {activeTab === 'dummy' && (
          <QuickDummyBuilder isDarkMode={isDarkMode} onOpenHistory={() => { setHistoryType('dummy'); setIsHistoryOpen(true); }} />
        )}
        {activeTab === 'synthetic' && (batchFiles !== null ? <BatchSynthesisPanel key={batchViewKey} initialFiles={batchFiles}
          isDarkMode={isDarkMode} onClose={() => setBatchFiles(null)} onOpenJob={job => {
            setBatchFiles(null); setActiveJob(job); setStep(5);
          }} /> : (
          <>
            {/* Step Indicator */}
            <div className="grid grid-cols-5 gap-3">
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
                    className={`flex items-center gap-3 p-3.5 rounded-2xl border text-left transition-all ${
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
                        : 'bg-slate-100/50 border-slate-200 text-slate-400 opacity-60'
                    }`}
                  >
                    <div className={`w-7 h-7 rounded-xl flex items-center justify-center text-xs font-bold ${
                      isActive ? 'bg-sky-500 text-white' : isCompleted ? 'bg-emerald-500 text-white' : isDarkMode ? 'bg-slate-800 text-slate-400' : 'bg-slate-200 text-slate-500'
                    }`}>
                      {isCompleted ? <CheckCircle2 className="w-4 h-4" /> : s.num}
                    </div>
                    <div>
                      <div className="text-xs font-bold">{s.label}</div>
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
                  handleBatchFiles={setBatchFiles}
                />

                <button className="text-sky-600 text-sm font-bold" onClick={() => setBatchFiles([])}>파일 일괄 처리</button>
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
        ))}
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
          localStorage.setItem(ACTIVE_BATCH_KEY, id);
          setBatchViewKey(value => value + 1);
          setBatchFiles([]);
          setActiveTab('synthetic');
          setIsHistoryOpen(false);
        }}
        isOpen={isHistoryOpen}
        onClose={() => setIsHistoryOpen(false)}
        isDarkMode={isDarkMode}
        onSelectJob={(job) => {
          setBatchFiles(null);
          setActiveJob(job);
          setActiveTab('synthetic');
          setStep(5);
          setIsHistoryOpen(false);
        }}
      />
    </div>
  );
}
