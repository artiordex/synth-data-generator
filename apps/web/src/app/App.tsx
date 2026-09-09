/**
 * 파일명: App.tsx
 * 경로: apps/web/src/app/App.tsx
 * 목적: 애플리케이션 화면과 전역 워크플로 상태를 조정함
 * 작성자: 개발팀
 * 작성일: 2026-09-09
 * 수정일: 2026-09-09
 */
import React, { useState, useEffect } from 'react';
import {
  Upload, Database, Sliders, Play, CheckCircle2,
  AlertCircle, Layers, Sun, Moon, ShieldCheck,
  ArrowLeftRight, BookOpen, Clock, FileCode, Code2
} from 'lucide-react';
import { DatasetProfile, JobStatus, ReviewMetadataInput, SynthesisRequest } from '../types';
import { uploadDataset, getDatasetProfile, startSynthesis, cancelSynthesis, getJobStatus } from '../services/api';
import { DataDictionaryView } from '../features/dictionary/DataDictionaryView';
import { IntegratedHistoryView } from '../features/history/IntegratedHistoryView';
import { StepUpload } from '../features/dataset/StepUpload';
import { StepProfile } from '../features/dataset/StepProfile';
import { StepConfig } from '../features/synthesis/StepConfig';
import { defaultSynthesisOptions, SynthesisOptions } from '../features/synthesis/AdvancedSynthesisSettings';
import { StepProgress } from '../features/synthesis/StepProgress';
import { BatchSynthesisPanel } from '../features/synthesis/BatchSynthesisPanel';
import { RelationalSynthesisPanel } from '../features/synthesis/RelationalSynthesisPanel';
import { TimeSeriesPanel } from '../features/synthesis/TimeSeriesPanel';
import { SurveySynthesisPanel } from '../features/synthesis/SurveySynthesisPanel';
import { SynthesisWorkflowSelector, SyntheticWorkflow } from '../features/synthesis/SynthesisWorkflowSelector';
import { StepReport } from '../features/reports/StepReport';
import { QuickDummyBuilder } from '../features/dummy/QuickDummyBuilder';
import { PseudonymStudio } from '../features/pseudonym/PseudonymStudio';
import { DataConverterStudio } from '../features/converter/DataConverterStudio';
import { SystemDocsView } from '../features/system/SystemDocsView';
import { ApiDocsView } from '../features/system/ApiDocsView';
import { Footer } from '../components/Footer';
import { WorkspaceNav, WorkbenchTab } from '../components/WorkspaceNav';
import { WorkflowStepItem } from '../components/WorkflowSteps';
import { WorkspaceHeader, WorkspaceHeaderProps } from '../components/WorkspaceHeader';

export type MainView = 'workbench' | 'dictionary' | 'history' | 'changelog' | 'libraries' | 'apidocs';

const singleSynthesisSteps: WorkflowStepItem<number>[] = [
  { id: 1, label: '데이터 업로드', description: '파일 및 무결성 확인', Icon: Upload },
  { id: 2, label: '프로파일링', description: '스키마·PII 분석', Icon: Database },
  { id: 3, label: '합성 설정', description: '모델·DP 파라미터', Icon: Sliders },
  { id: 4, label: '생성 진행', description: '파이프라인 모니터링', Icon: Play },
  { id: 5, label: '결과 검토', description: '평가·HWP 패키지', Icon: CheckCircle2 },
];

const pseudoSteps: WorkflowStepItem<number>[] = [
  { id: 1, label: '파일 분석' },
  { id: 2, label: '처리 규칙' },
  { id: 3, label: '결과 검토' },
];

const dummySteps: WorkflowStepItem<number>[] = [
  { id: 1, label: '스키마 구성' },
  { id: 2, label: '생성 옵션' },
  { id: 3, label: '데이터 생성' },
  { id: 4, label: '결과 검토' },
];

const converterSteps: WorkflowStepItem<number>[] = [
  { id: 1, label: '파일 업로드' },
  { id: 2, label: '변환 설정' },
  { id: 3, label: '변환 실행' },
  { id: 4, label: '결과 검토' },
];

const workflowStepSets: Record<SyntheticWorkflow, WorkflowStepItem<number>[]> = {
  single: singleSynthesisSteps,
  batch: [
    { id: 1, label: '파일 업로드' },
    { id: 2, label: '일괄 설정' },
    { id: 3, label: '생성 진행' },
    { id: 4, label: '결과 검토' },
  ],
  relational: [
    { id: 1, label: '테이블 업로드' },
    { id: 2, label: '관계 분석' },
    { id: 3, label: '합성 실행' },
    { id: 4, label: '무결성 검토' },
  ],
  timeseries: [
    { id: 1, label: '파일 업로드' },
    { id: 2, label: '시계열 설정' },
    { id: 3, label: '합성 실행' },
    { id: 4, label: '결과 검토' },
  ],
  survey: [
    { id: 1, label: '모듈 업로드' },
    { id: 2, label: '구조 분석' },
    { id: 3, label: '합성 진행' },
    { id: 4, label: '결과 검토' },
  ],
};

const dictionarySteps: WorkflowStepItem<number>[] = [
  { id: 1, label: '검색 조건' },
  { id: 2, label: '용어 탐색' },
  { id: 3, label: '상세 검토' },
];

const historySteps: WorkflowStepItem<number>[] = [
  { id: 1, label: '이력 수집' },
  { id: 2, label: '필터·검색' },
  { id: 3, label: '작업 검토' },
];

const changelogSteps: WorkflowStepItem<number>[] = [
  { id: 1, label: '문서 선택' },
  { id: 2, label: '변경내역 로드' },
  { id: 3, label: '내용 검토' },
];

const librarySteps: WorkflowStepItem<number>[] = [
  { id: 1, label: '문서 선택' },
  { id: 2, label: '라이브러리 로드' },
  { id: 3, label: '의존성 검토' },
];



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
  const [pseudoStep, setPseudoStep] = useState<number>(1);
  const [dummyStep, setDummyStep] = useState<number>(1);
  const [converterStep, setConverterStep] = useState<number>(1);
  const [syntheticAuxStep, setSyntheticAuxStep] = useState<number>(1);
  const [dictionaryStep, setDictionaryStep] = useState<number>(1);
  const [historyStep, setHistoryStep] = useState<number>(1);
  const [docsStep, setDocsStep] = useState<number>(1);
  const [apiDocsStep, setApiDocsStep] = useState<number>(1);
  const [syntheticWorkflow, setSyntheticWorkflow] = useState<SyntheticWorkflow>('single');
  const [batchFiles] = useState<File[]>([]);
  const [selectedBatchId, setSelectedBatchId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<WorkbenchTab>('synthetic');
  const [mainView, setMainView] = useState<MainView>('workbench');

  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadedFilename, setUploadedFilename] = useState<string>('');
  const [profile, setProfile] = useState<DatasetProfile | null>(null);
  const [reviewMetadata, setReviewMetadata] = useState<ReviewMetadataInput>({});
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
        review_metadata: reviewMetadata,
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

  const handleSelectWorkbenchTab = (tab: WorkbenchTab) => {
    setActiveTab(tab);
    setMainView('workbench');
  };

  const getWorkspaceHeaderProps = (): WorkspaceHeaderProps<number> | null => {
    if (mainView === 'dictionary' || mainView === 'history') {
      return null;
    }
    if (mainView === 'changelog') {
      return {
        eyebrow: 'SYSTEM DOCS',
        title: '개발이력 (개발이력.md)',
        description: '시스템 버전별 신규 기능 추가 및 아키텍처 변경 이력',
        icon: FileCode,
      };
    }
    if (mainView === 'libraries') {
      return {
        eyebrow: 'SYSTEM DOCS',
        title: '라이브러리 목록 (라이브러리목록.md)',
        description: '엔진 및 웹 프론트엔드 핵심 오픈소스 라이브러리 라이선스 및 의존성',
        icon: Layers,
      };
    }
    if (mainView === 'apidocs') {
      return {
        eyebrow: 'API SPECIFICATION',
        title: '사내 데이터 생성기 API',
        description: 'FastAPI OpenAPI 3.1 명세 기반 엔드포인트 실시간 탐색 및 대화형 호출 테스트',
        icon: Code2,
      };
    }
    if (activeTab === 'pseudo') {
      return {
        eyebrow: 'PRIVACY WORKSPACE',
        title: '가명데이터 처리',
        description: '개인식별정보(PII) 자동 탐지 및 한국형 Faker·마스킹·토큰화 안전 변환',
        icon: ShieldCheck,
        steps: pseudoSteps,
        activeStep: pseudoStep,
      };
    }
    if (activeTab === 'dummy') {
      return {
        eyebrow: 'DUMMY WORKSPACE',
        title: '더미데이터 생성',
        description: '행안부 공통표준 도메인 및 DDL/OpenAPI 스키마 기반 대량 모의 데이터 즉시 생성',
        icon: Database,
        steps: dummySteps,
        activeStep: dummyStep,
      };
    }
    if (activeTab === 'converter') {
      return {
        eyebrow: 'CONVERTER WORKSPACE',
        title: '데이터 포맷 변환',
        description: 'CSV, Excel, Parquet, JSON 및 HWP/HWPX/DOCX/PDF 문서 서식 유지 상호 변환',
        icon: ArrowLeftRight,
        steps: converterSteps,
        activeStep: converterStep,
      };
    }
    if (activeTab === 'synthetic') {
      const titles: Record<SyntheticWorkflow, string> = {
        single: '합성데이터 생성 (단일 테이블)',
        batch: '합성데이터 생성 (대량 일괄 배치)',
        relational: '합성데이터 생성 (관계형 멀티테이블)',
        timeseries: '합성데이터 생성 (시계열 데이터)',
        survey: '합성데이터 생성 (설문·모듈형 데이터)',
      };
      return {
        eyebrow: 'SYNTHESIS WORKSPACE',
        title: titles[syntheticWorkflow],
        description: 'CTGAN · TVAE · Gaussian Copula 및 차분 프라이버시(DP) 적용 AI 가상 데이터 합성',
        icon: Sliders,
        steps: workflowStepSets[syntheticWorkflow],
        activeStep: syntheticWorkflow === 'single' ? step : syntheticAuxStep,
        onSelectStep: syntheticWorkflow === 'single'
          ? (item) => {
              if (profile && item.id <= 3) setStep(item.id);
              if (activeJob?.status === 'completed' && item.id === 5) setStep(5);
            }
          : undefined,
      };
    }
    return null;
  };

  const workspaceHeaderProps = getWorkspaceHeaderProps();

  return (
    <div className="app-shell min-h-screen flex flex-col bg-[var(--ui-canvas)] text-[var(--ui-text)] transition-colors duration-200">
      {/* Header */}
      <header className="sticky top-0 z-40 border-b border-[var(--ui-border)] bg-[color:var(--ui-surface)]/95 px-4 py-3 shadow-sm backdrop-blur transition-colors sm:px-6">
        <div className="mx-auto flex w-full max-w-[1440px] flex-col gap-3">
          <div className="flex min-w-0 items-center justify-between gap-3">
            <button
              onClick={() => {
                setMainView('workbench');
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
                <span className="hidden md:inline-block rounded-md border border-subtle bg-surface-muted px-2 py-0.5 text-2xs font-medium text-fg-muted whitespace-nowrap">
                  가명 · 합성 · 더미 · 변환
                </span>
              </div>
            </button>

            <WorkspaceNav
              activeTab={activeTab}
              isWorkbenchActive={mainView === 'workbench'}
              layout="desktop"
              onSelect={handleSelectWorkbenchTab}
            />

            <div className="flex shrink-0 items-center gap-2 overflow-x-auto scrollbar-none">
              {/* Light / Dark Mode Toggle Button */}
              <button
                onClick={() => setIsDarkMode(!isDarkMode)}
                className="ui-button-secondary shrink-0 whitespace-nowrap px-3 cursor-pointer"
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
            </div>
          </div>

          <WorkspaceNav
            activeTab={activeTab}
            isWorkbenchActive={mainView === 'workbench'}
            layout="mobile"
            onSelect={handleSelectWorkbenchTab}
          />
        </div>
      </header>

      {/* Main Container */}
      <main className="mx-auto w-full max-w-[1440px] flex-1 space-y-6 p-4 sm:p-6 lg:p-8">
        {workspaceHeaderProps && (
          <WorkspaceHeader {...workspaceHeaderProps} />
        )}

        {mainView === 'dictionary' && (
          <DataDictionaryView
            onBack={() => setMainView('workbench')}
            isDarkMode={isDarkMode}
            onStepChange={setDictionaryStep}
          />
        )}

        {mainView === 'history' && (
          <IntegratedHistoryView
            onBack={() => setMainView('workbench')}
            isDarkMode={isDarkMode}
            onStepChange={setHistoryStep}
            onSelectJob={(job) => {
              setSyntheticWorkflow('single');
              setActiveJob(job);
              setActiveTab('synthetic');
              setMainView('workbench');
              setStep(5);
            }}
            onSelectBatch={(id) => {
              setSelectedBatchId(id);
              setBatchViewKey(value => value + 1);
              setSyntheticWorkflow('batch');
              setActiveTab('synthetic');
              setMainView('workbench');
            }}
          />
        )}

        {(mainView === 'changelog' || mainView === 'libraries') && (
          <SystemDocsView
            initialDoc={mainView}
            onBack={() => setMainView('workbench')}
            isDarkMode={isDarkMode}
            onDocChange={(doc) => {
              if (doc === 'changelog' || doc === 'libraries') {
                setMainView(doc);
              }
            }}
            onStepChange={setDocsStep}
          />
        )}

        {mainView === 'apidocs' && (
          <ApiDocsView
            isDarkMode={isDarkMode}
            onStepChange={setApiDocsStep}
          />
        )}

        {mainView === 'workbench' && (
          <>
            {activeTab === 'pseudo' && (
              <PseudonymStudio isDarkMode={isDarkMode} onStepChange={setPseudoStep} />
            )}
            {activeTab === 'dummy' && (
              <QuickDummyBuilder isDarkMode={isDarkMode} onStepChange={setDummyStep} />
            )}
            {activeTab === 'converter' && (
              <DataConverterStudio isDarkMode={isDarkMode} onStepChange={setConverterStep} />
            )}
            {activeTab === 'synthetic' && (
              <>
                <SynthesisWorkflowSelector
                  value={syntheticWorkflow}
                  onChange={workflow => {
                    setSyntheticWorkflow(workflow);
                    setSyntheticAuxStep(1);
                    if (workflow === 'batch') setSelectedBatchId(null);
                  }}
                  isDarkMode={isDarkMode}
                />

                {syntheticWorkflow === 'survey' ? (
                  <SurveySynthesisPanel isDarkMode={isDarkMode} onClose={() => setSyntheticWorkflow('single')} onStepChange={setSyntheticAuxStep} />
                ) : syntheticWorkflow === 'timeseries' ? (
                  <TimeSeriesPanel isDarkMode={isDarkMode} onClose={() => setSyntheticWorkflow('single')} onStepChange={setSyntheticAuxStep} />
                ) : syntheticWorkflow === 'relational' ? (
                  <RelationalSynthesisPanel isDarkMode={isDarkMode} onClose={() => setSyntheticWorkflow('single')} onStepChange={setSyntheticAuxStep} />
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
                    onStepChange={setSyntheticAuxStep}
                    onOpenJob={job => {
                      setSyntheticWorkflow('single');
                      setActiveJob(job);
                      setStep(5);
                    }}
                  />
                ) : (
                  <>
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
          </>
        )}
      </main>

      {/* Clean Text-Only Footer */}
      <Footer
        isDarkMode={isDarkMode}
        onOpenDoc={(doc) => {
          setMainView(doc);
          window.scrollTo({ top: 0, behavior: 'smooth' });
        }}
      />
    </div>
  );
}
