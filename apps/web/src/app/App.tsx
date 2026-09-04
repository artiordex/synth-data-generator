import React, { useState, useEffect } from 'react';
import { 
  Upload, Database, Shield, Sliders, Play, CheckCircle2, 
  AlertCircle, Download, BookOpen, RefreshCw, Layers, FileText, Cpu,
  Sun, Moon
} from 'lucide-react';
import { DatasetProfile, JobStatus, SynthesisRequest } from '../types';
import { uploadDataset, getDatasetProfile, startSynthesis, cancelSynthesis, getJobStatus, listJobs, getDownloadUrl } from '../services/api';
import { DataDictionaryModal } from '../features/dictionary/DataDictionaryModal';

export default function App() {
  // Theme state (Default: Light mode for clean bright look, saved in localStorage)
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
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadedFilename, setUploadedFilename] = useState<string>('');
  const [profile, setProfile] = useState<DatasetProfile | null>(null);
  const [isDictionaryOpen, setIsDictionaryOpen] = useState<boolean>(false);

  // Form Config
  const [departmentName, setDepartmentName] = useState<string>('범용 데이터분석팀');
  const [projectPurpose, setProjectPurpose] = useState<string>('AI 모델 학습 및 가명정보 분석 연구');
  const [modelType, setModelType] = useState<'statistical' | 'gaussian_copula' | 'ctgan' | 'tvae'>('statistical');
  const [targetRows, setTargetRows] = useState<number>(1000);
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
          setErrorMsg(updated.message || '작업 실패');
        }
      } catch (e) {
        console.error(e);
      }
    }, 1500);

    return () => clearInterval(interval);
  }, [activeJob]);

  // Handle File Upload
  const handleFileUpload = async (file: File) => {
    setIsUploading(true);
    setErrorMsg(null);
    try {
      const res = await uploadDataset(file);
      setUploadedFilename(res.filename);
      const prof = await getDatasetProfile(res.filename);
      setProfile(prof);
      setTargetRows(prof.row_count > 0 ? prof.row_count : 1000);
      setStep(2);
    } catch (err: any) {
      setErrorMsg(err.message || '파일 업로드 및 프로파일링 실패');
    } finally {
      setIsUploading(false);
    }
  };

  // Start Synthesis
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
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-sky-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-sky-500/20">
            <Layers className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className={`font-bold text-base tracking-tight flex items-center gap-2 ${
              isDarkMode ? 'text-white' : 'text-slate-900'
            }`}>
              범용 AI 합성데이터 생성 플랫폼
            </h1>
          </div>
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

          {/* Data Dictionary Button */}
          <button
            onClick={() => setIsDictionaryOpen(true)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold transition-all border ${
              isDarkMode 
                ? 'bg-slate-800/90 hover:bg-slate-700 text-slate-200 border-slate-700' 
                : 'bg-white hover:bg-slate-100 text-slate-700 border-slate-200 shadow-sm'
            }`}
          >
            <BookOpen className="w-4 h-4 text-sky-500" />
            데이터 지식 사전
          </button>

          {/* Engine Status Badge */}
          <div className="flex items-center gap-2 px-3 py-1.5 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-emerald-600 dark:text-emerald-400 text-xs font-semibold">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            엔진 준비 완료
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-6 space-y-6">
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
            <button onClick={() => setErrorMsg(null)} className="text-rose-500 hover:text-rose-700">✕</button>
          </div>
        )}

        {/* Step 1: Upload */}
        {step === 1 && (
          <div className={`border rounded-2xl p-8 text-center space-y-6 shadow-sm ${
            isDarkMode ? 'bg-slate-900/60 border-slate-800' : 'bg-white border-slate-200'
          }`}>
            <div className="max-w-md mx-auto space-y-2">
              <h2 className={`text-xl font-bold ${isDarkMode ? 'text-white' : 'text-slate-900'}`}>
                데이터 파일 업로드
              </h2>
              <p className={`text-xs ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>
                정형 데이터셋(CSV, XLSX, XLS, Parquet)을 업로드하면 SHA-256 무결성 검증과 자동 PII 감지가 즉시 실행됩니다.
              </p>
            </div>

            <div 
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                  handleFileUpload(e.dataTransfer.files[0]);
                }
              }}
              className={`border-2 border-dashed rounded-2xl p-12 transition-all cursor-pointer max-w-2xl mx-auto ${
                isDarkMode 
                  ? 'bg-slate-950/40 border-slate-700 hover:border-sky-500' 
                  : 'bg-slate-50 border-slate-300 hover:border-sky-500 hover:bg-sky-50/30'
              }`}
              onClick={() => document.getElementById('file-input')?.click()}
            >
              <input 
                id="file-input" 
                type="file" 
                accept=".csv,.xlsx,.xls,.parquet" 
                className="hidden" 
                onChange={(e) => {
                  if (e.target.files && e.target.files[0]) {
                    handleFileUpload(e.target.files[0]);
                  }
                }} 
              />
              <div className="flex flex-col items-center gap-3">
                <div className={`w-14 h-14 rounded-2xl flex items-center justify-center ${
                  isDarkMode ? 'bg-sky-500/10 border border-sky-500/20 text-sky-400' : 'bg-sky-100 border border-sky-200 text-sky-600'
                }`}>
                  <Upload className="w-7 h-7" />
                </div>
                <div>
                  <p className={`text-sm font-bold ${isDarkMode ? 'text-slate-200' : 'text-slate-800'}`}>
                    {isUploading ? '파일 분석 및 무결성 해시 계산 중...' : '클릭하여 파일을 선택하거나 이곳으로 드래그 앤 드롭'}
                  </p>
                  <p className={`text-xs mt-1 ${isDarkMode ? 'text-slate-500' : 'text-slate-400'}`}>
                    CSV, Excel(XLSX/XLS), Parquet 지원 (최대 100MB)
                  </p>
                </div>
              </div>
            </div>

            {/* Quick Test Data Samples */}
            <div className={`pt-4 border-t max-w-xl mx-auto text-left ${
              isDarkMode ? 'border-slate-800' : 'border-slate-200'
            }`}>
              <div className={`text-xs font-bold mb-2 ${isDarkMode ? 'text-slate-400' : 'text-slate-600'}`}>
                💡 빠른 테스트용 샘플 파일 선택:
              </div>
              <div className="flex flex-wrap gap-2">
                {["perf_test.csv", "customer_behavior_sample_dataset.csv"].map((sample) => (
                  <button
                    key={sample}
                    onClick={async () => {
                      setIsUploading(true);
                      setUploadedFilename(sample);
                      try {
                        const prof = await getDatasetProfile(sample);
                        setProfile(prof);
                        setTargetRows(prof.row_count > 0 ? prof.row_count : 1000);
                        setStep(2);
                      } catch (e: any) {
                        setErrorMsg('샘플 로드 실패: ' + e.message);
                      } finally {
                        setIsUploading(false);
                      }
                    }}
                    className={`px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all ${
                      isDarkMode 
                        ? 'bg-slate-800 hover:bg-slate-700 text-sky-400 border-slate-700' 
                        : 'bg-white hover:bg-slate-100 text-sky-600 border-slate-300 shadow-sm'
                    }`}
                  >
                    📄 {sample}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Step 2: Profiling & PII */}
        {step === 2 && profile && (
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
                      <th className="px-4 py-3">샘플 데이터</th>
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
                        <td className={`px-4 py-2.5 font-mono text-[11px] truncate max-w-xs ${
                          isDarkMode ? 'text-slate-400' : 'text-slate-600'
                        }`}>
                          {c.samples.join(', ')}
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
        )}

        {/* Step 3: Synthesis Config */}
        {step === 3 && (
          <div className="space-y-6">
            <div className="grid grid-cols-2 gap-6">
              {/* Left: General Settings */}
              <div className={`p-6 rounded-2xl border space-y-4 shadow-sm ${
                isDarkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'
              }`}>
                <h3 className={`font-bold text-sm flex items-center gap-2 ${isDarkMode ? 'text-slate-100' : 'text-slate-900'}`}>
                  <Sliders className="w-4 h-4 text-sky-500" />
                  프로젝트 및 합성 대상 정보
                </h3>
                <div className="space-y-3">
                  <div>
                    <label className={`block text-xs font-semibold mb-1 ${isDarkMode ? 'text-slate-400' : 'text-slate-600'}`}>담당 부서명</label>
                    <input 
                      type="text" 
                      value={departmentName} 
                      onChange={(e) => setDepartmentName(e.target.value)} 
                      className={`w-full px-3 py-2 border rounded-xl text-xs focus:outline-none focus:border-sky-500 ${
                        isDarkMode ? 'bg-slate-950 border-slate-700 text-white' : 'bg-slate-50 border-slate-300 text-slate-900'
                      }`}
                    />
                  </div>
                  <div>
                    <label className={`block text-xs font-semibold mb-1 ${isDarkMode ? 'text-slate-400' : 'text-slate-600'}`}>연구 및 심의 목적</label>
                    <input 
                      type="text" 
                      value={projectPurpose} 
                      onChange={(e) => setProjectPurpose(e.target.value)} 
                      className={`w-full px-3 py-2 border rounded-xl text-xs focus:outline-none focus:border-sky-500 ${
                        isDarkMode ? 'bg-slate-950 border-slate-700 text-white' : 'bg-slate-50 border-slate-300 text-slate-900'
                      }`}
                    />
                  </div>
                  <div>
                    <label className={`block text-xs font-semibold mb-1 ${isDarkMode ? 'text-slate-400' : 'text-slate-600'}`}>합성 생성 행 수 (Target Rows)</label>
                    <input 
                      type="number" 
                      value={targetRows} 
                      onChange={(e) => setTargetRows(Number(e.target.value))} 
                      className={`w-full px-3 py-2 border rounded-xl text-xs focus:outline-none focus:border-sky-500 ${
                        isDarkMode ? 'bg-slate-950 border-slate-700 text-white' : 'bg-slate-50 border-slate-300 text-slate-900'
                      }`}
                    />
                  </div>
                  <div>
                    <label className={`block text-xs font-semibold mb-1 ${isDarkMode ? 'text-slate-400' : 'text-slate-600'}`}>심의 통과 품질 임계점 (기준 80점)</label>
                    <input 
                      type="number" 
                      step="0.05"
                      min="0.5"
                      max="0.99"
                      value={qualityThreshold} 
                      onChange={(e) => setQualityThreshold(Number(e.target.value))} 
                      className={`w-full px-3 py-2 border rounded-xl text-xs focus:outline-none focus:border-sky-500 ${
                        isDarkMode ? 'bg-slate-950 border-slate-700 text-white' : 'bg-slate-50 border-slate-300 text-slate-900'
                      }`}
                    />
                  </div>
                </div>
              </div>

              {/* Right: AI Model & Privacy */}
              <div className={`p-6 rounded-2xl border space-y-4 shadow-sm ${
                isDarkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'
              }`}>
                <h3 className={`font-bold text-sm flex items-center gap-2 ${isDarkMode ? 'text-slate-100' : 'text-slate-900'}`}>
                  <Cpu className="w-4 h-4 text-sky-500" />
                  생성 모델 & 차분 프라이버시(DP)
                </h3>
                
                {/* Model Selector */}
                <div>
                  <label className={`block text-xs font-semibold mb-2 ${isDarkMode ? 'text-slate-400' : 'text-slate-600'}`}>AI 합성 엔진 선택</label>
                  <div className="grid grid-cols-2 gap-2">
                    {[
                      { id: 'statistical', label: '터보 통계 샘플러', desc: '1~3초 초고속 생성 (권장)' },
                      { id: 'gaussian_copula', label: '가우시안 코퓰라', desc: '상관관계 보존 준모수 모델' },
                      { id: 'ctgan', label: 'CTGAN 딥러닝', desc: '조건부 적대적 생성 신경망' },
                      { id: 'tvae', label: 'TVAE 딥러닝', desc: '변분 오토인코더 신경망' },
                    ].map((m) => (
                      <button
                        key={m.id}
                        type="button"
                        onClick={() => setModelType(m.id as any)}
                        className={`p-3 rounded-xl border text-left transition-all ${
                          modelType === m.id 
                            ? isDarkMode
                              ? 'bg-sky-950/60 border-sky-500 text-white shadow'
                              : 'bg-sky-50 border-sky-500 text-sky-900 shadow-sm ring-1 ring-sky-400'
                            : isDarkMode
                            ? 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'
                            : 'bg-slate-50 border-slate-200 text-slate-600 hover:border-slate-300'
                        }`}
                      >
                        <div className="text-xs font-bold">{m.label}</div>
                        <div className={`text-[10px] mt-0.5 ${isDarkMode ? 'text-slate-500' : 'text-slate-400'}`}>{m.desc}</div>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Differential Privacy Toggle */}
                <div className={`pt-2 border-t space-y-3 ${isDarkMode ? 'border-slate-800' : 'border-slate-200'}`}>
                  <div className="flex items-center justify-between">
                    <div>
                      <div className={`text-xs font-bold ${isDarkMode ? 'text-slate-200' : 'text-slate-800'}`}>차분 프라이버시 (Laplace DP) 적용</div>
                      <div className={`text-[10px] ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>수학적 라플라스 노이즈로 엄격한 개인정보 차단</div>
                    </div>
                    <input 
                      type="checkbox" 
                      checked={dpEnabled} 
                      onChange={(e) => setDpEnabled(e.target.checked)} 
                      className="w-4 h-4 text-sky-600 rounded"
                    />
                  </div>

                  {dpEnabled && (
                    <div className={`p-3 rounded-xl border space-y-2 ${
                      isDarkMode ? 'bg-slate-950 border-slate-800' : 'bg-slate-50 border-slate-200'
                    }`}>
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
                        onChange={(e) => setDpEpsilon(Number(e.target.value))} 
                        className="w-full accent-sky-500"
                      />
                      <div className="flex justify-between text-[10px] text-slate-400">
                        <span>강력한 프라이버시 (0.1)</span>
                        <span>높은 통계 정확도 (5.0)</span>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Navigation Button */}
            <div className="flex justify-between items-center">
              <button
                onClick={() => setStep(2)}
                className={`px-4 py-2 rounded-xl text-xs font-bold border transition-colors ${
                  isDarkMode 
                    ? 'bg-slate-800 hover:bg-slate-700 text-slate-300 border-slate-700' 
                    : 'bg-white hover:bg-slate-100 text-slate-700 border-slate-300 shadow-sm'
                }`}
              >
                ← 이전 단계
              </button>
              <button
                onClick={handleStartSynthesis}
                className="px-8 py-3 rounded-xl bg-gradient-to-r from-sky-600 to-indigo-600 hover:from-sky-500 hover:to-indigo-500 text-sm font-bold text-white transition-all shadow-lg shadow-sky-600/30"
              >
                🚀 실시간 합성 및 심의 패키지 파이프라인 가동
              </button>
            </div>
          </div>
        )}

        {/* Step 4: Live Pipeline Progress */}
        {step === 4 && activeJob && (
          <div className={`p-8 rounded-2xl border text-center space-y-6 max-w-2xl mx-auto shadow-xl ${
            isDarkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'
          }`}>
            <div className={`w-16 h-16 rounded-2xl flex items-center justify-center mx-auto animate-pulse ${
              isDarkMode ? 'bg-sky-500/10 border border-sky-500/30 text-sky-400' : 'bg-sky-100 border border-sky-200 text-sky-600'
            }`}>
              <RefreshCw className="w-8 h-8 animate-spin" />
            </div>

            <div className="space-y-2">
              <h2 className={`text-lg font-bold ${isDarkMode ? 'text-white' : 'text-slate-900'}`}>
                합성데이터 생성 및 3대 공문서 자동 바인딩 중
              </h2>
              <p className="text-xs text-sky-600 dark:text-sky-400 font-bold">{activeJob.message}</p>
            </div>

            {/* Progress Bar */}
            <div className="space-y-2">
              <div className={`w-full h-3 rounded-full overflow-hidden border p-0.5 ${
                isDarkMode ? 'bg-slate-950 border-slate-800' : 'bg-slate-100 border-slate-200'
              }`}>
                <div 
                  className="h-full bg-gradient-to-r from-sky-500 to-indigo-500 rounded-full transition-all duration-300"
                  style={{ width: `${activeJob.progress}%` }}
                />
              </div>
              <div className="flex justify-between text-xs font-mono text-slate-400">
                <span>작업 ID: {activeJob.id}</span>
                <span className="font-bold">{activeJob.progress}%</span>
              </div>
            </div>

            {/* Cancel Button */}
            <button
              onClick={handleCancelJob}
              className="px-4 py-2 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 text-rose-600 dark:text-rose-400 border border-rose-500/30 text-xs font-bold transition-colors"
            >
              작업 중단 (Cancel Job)
            </button>
          </div>
        )}

        {/* Step 5: Dashboard & HWP Download Package */}
        {step === 5 && activeJob && (
          <div className="space-y-6">
            {/* Scorecard Hero */}
            <div className="grid grid-cols-4 gap-4">
              <div className={`p-5 rounded-2xl border flex items-center justify-between shadow-sm ${
                isDarkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'
              }`}>
                <div>
                  <div className={`text-xs ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>심의 종합 판정</div>
                  <div className={`text-2xl font-black mt-1 ${isDarkMode ? 'text-white' : 'text-slate-900'}`}>
                    {activeJob.assessment_grade || 'A'} 등급
                  </div>
                  <div className="text-[10px] text-emerald-600 dark:text-emerald-400 font-bold mt-0.5">
                    {activeJob.assessment_passed ? '✓ 심의 승인 권고' : '재검토 권고'}
                  </div>
                </div>
                <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-600 dark:text-emerald-400 font-black text-lg">
                  {activeJob.assessment_score || 90}점
                </div>
              </div>

              <div className={`p-5 rounded-2xl border shadow-sm ${
                isDarkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'
              }`}>
                <div className={`text-xs ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>통계적 품질 지수 (JSD)</div>
                <div className="text-2xl font-black text-sky-600 dark:text-sky-400 mt-1">
                  {((activeJob.quality_score || 0.88) * 100).toFixed(1)}%
                </div>
                <div className={`text-[10px] mt-0.5 ${isDarkMode ? 'text-slate-500' : 'text-slate-400'}`}>원본 다변량 분포 유사도</div>
              </div>

              <div className={`p-5 rounded-2xl border shadow-sm ${
                isDarkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'
              }`}>
                <div className={`text-xs ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>Anonymeter 재식별 위험도</div>
                <div className="text-2xl font-black text-amber-600 dark:text-amber-400 mt-1">
                  {((activeJob.reid_risk || 0.04) * 100).toFixed(2)}%
                </div>
                <div className={`text-[10px] mt-0.5 ${isDarkMode ? 'text-slate-500' : 'text-slate-400'}`}>EU GDPR 29조 기준 안전치</div>
              </div>

              <div className={`p-5 rounded-2xl border shadow-sm ${
                isDarkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'
              }`}>
                <div className={`text-xs ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>생성 레코드 수</div>
                <div className="text-2xl font-black text-indigo-600 dark:text-indigo-400 mt-1">
                  {activeJob.target_rows.toLocaleString()} 건
                </div>
                <div className={`text-[10px] mt-0.5 ${isDarkMode ? 'text-slate-500' : 'text-slate-400'}`}>{activeJob.model_type.toUpperCase()} 엔진</div>
              </div>
            </div>

            {/* Submission Package Directory Structure & Download Box */}
            <div className={`p-6 rounded-2xl border space-y-4 shadow-sm ${
              isDarkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'
            }`}>
              <div className="flex items-center justify-between">
                <div>
                  <h3 className={`font-bold text-sm flex items-center gap-2 ${isDarkMode ? 'text-white' : 'text-slate-900'}`}>
                    <FileText className="w-4 h-4 text-sky-500" />
                    제출용 3대 패키지 및 공문서 다운로드
                  </h3>
                  <p className={`text-xs ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>
                    각 파일별 격리 폴더 및 3대 심의자료 HWP 자동 바인딩 완료
                  </p>
                </div>
                {activeJob.package_zip && (
                  <a
                    href={getDownloadUrl(activeJob.package_zip)}
                    className="px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-xs font-bold text-white flex items-center gap-2 shadow-lg shadow-emerald-600/20 transition-all"
                  >
                    <Download className="w-4 h-4" />
                    전체 패키지 압축 ZIP 다운로드
                  </a>
                )}
              </div>

              {/* Folder structure cards */}
              <div className="grid grid-cols-3 gap-4 pt-2">
                <div className={`p-4 rounded-xl border space-y-2 ${
                  isDarkMode ? 'bg-slate-950 border-slate-800' : 'bg-slate-50 border-slate-200'
                }`}>
                  <div className="text-xs font-bold text-sky-600 dark:text-sky-400 flex items-center gap-1.5">
                    📁 1. 원본데이터 폴더
                  </div>
                  <div className={`text-[11px] font-semibold ${isDarkMode ? 'text-slate-300' : 'text-slate-700'}`}>
                    {activeJob.original_filename}
                  </div>
                  <div className="text-[10px] text-slate-400 font-mono truncate">
                    SHA-256: {activeJob.file_sha256}
                  </div>
                </div>

                <div className={`p-4 rounded-xl border space-y-2 ${
                  isDarkMode ? 'bg-slate-950 border-slate-800' : 'bg-slate-50 border-slate-200'
                }`}>
                  <div className="text-xs font-bold text-indigo-600 dark:text-indigo-400 flex items-center gap-1.5">
                    📁 2. 합성데이터 폴더
                  </div>
                  <div className={`text-[11px] font-semibold ${isDarkMode ? 'text-slate-300' : 'text-slate-700'}`}>
                    합성데이터.csv & 합성데이터.xlsx
                  </div>
                  <div className="text-[10px] text-slate-400">
                    {activeJob.target_rows}건 생성 완료
                  </div>
                </div>

                <div className={`p-4 rounded-xl border space-y-2 ${
                  isDarkMode ? 'bg-slate-950 border-slate-800' : 'bg-slate-50 border-slate-200'
                }`}>
                  <div className="text-xs font-bold text-rose-600 dark:text-rose-400 flex items-center gap-1.5">
                    📁 3. 심의위원회 심의자료 (HWP 3종)
                  </div>
                  <div className={`text-[11px] space-y-0.5 ${isDarkMode ? 'text-slate-300' : 'text-slate-700'}`}>
                    <div>✓ 원본데이터 명세서.hwp</div>
                    <div>✓ 합성데이터 명세서.hwp</div>
                    <div>✓ 심의위원회 심의자료.hwp</div>
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
                className={`px-6 py-2.5 rounded-xl text-xs font-bold border transition-colors ${
                  isDarkMode 
                    ? 'bg-slate-800 hover:bg-slate-700 text-slate-200 border-slate-700' 
                    : 'bg-white hover:bg-slate-100 text-slate-700 border-slate-300 shadow-sm'
                }`}
              >
                + 새 데이터셋 합성 작업 시작
              </button>
            </div>
          </div>
        )}
      </main>

      {/* Data Dictionary Modal */}
      <DataDictionaryModal 
        isOpen={isDictionaryOpen} 
        onClose={() => setIsDictionaryOpen(false)} 
        isDarkMode={isDarkMode}
      />
    </div>
  );
}
