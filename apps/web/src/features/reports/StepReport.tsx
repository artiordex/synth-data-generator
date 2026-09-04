import React from 'react';
import { FileText, Download } from 'lucide-react';
import { JobStatus } from '../../types';
import { getDownloadUrl } from '../../services/api';
import { DistributionComparisonChart } from './DistributionComparisonChart';
import { RecentJobsHistory } from './RecentJobsHistory';

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
  return (
    <div className="space-y-6">
      {/* Scorecard Hero */}
      <div className="grid grid-cols-4 gap-4">
        <div className={`p-5 rounded-2xl border flex items-center justify-between shadow-sm ${
          isDarkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'
        }`}>
          <div>
            <div className={`text-xs ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>심의 종합 판정</div>
            <div className={`text-2xl font-black mt-1 ${isDarkMode ? 'text-white' : 'text-slate-900'}`}>
              {activeJob.assessment_passed ? `${activeJob.assessment_grade ?? '-'} 등급` : '검토 필요'}
            </div>
            <div className="text-[10px] text-emerald-600 dark:text-emerald-400 font-bold mt-0.5">
              {activeJob.assessment_passed ? '자동 점검 통과' : '측정 결과와 누락 항목 확인'}
            </div>
          </div>
          <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-600 dark:text-emerald-400 font-black text-lg">
            {activeJob.assessment_score == null ? '미측정' : `${activeJob.assessment_score}점`}
          </div>
        </div>

        <div className={`p-5 rounded-2xl border shadow-sm ${
          isDarkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'
        }`}>
          <div className={`text-xs ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>분포 품질 지수 (1 − 평균 JSD)</div>
          <div className="text-2xl font-black text-sky-600 dark:text-sky-400 mt-1">
            {activeJob.quality_score == null ? '미측정' : `${(activeJob.quality_score * 100).toFixed(1)}%`}
          </div>
          <div className={`text-[10px] mt-0.5 ${isDarkMode ? 'text-slate-500' : 'text-slate-400'}`}>수치형 공통 20구간·결측 포함</div>
        </div>

        <div className={`p-5 rounded-2xl border shadow-sm ${
          isDarkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'
        }`}>
          <div className={`text-xs ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>Anonymeter 재식별 위험도</div>
          <div className="text-2xl font-black text-amber-600 dark:text-amber-400 mt-1">
            {activeJob.reid_risk == null ? '미측정' : `${(activeJob.reid_risk * 100).toFixed(2)}%`}
          </div>
          <div className={`text-[10px] mt-0.5 ${isDarkMode ? 'text-slate-500' : 'text-slate-400'}`}>독립 대조 데이터를 이용한 단일 식별 위험도</div>
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

      {/* Interactive Distribution Comparison Overlay Chart */}
      <DistributionComparisonChart jobId={activeJob.id} isDarkMode={isDarkMode} />

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
              한글(HWPX) 심의자료 3종과 HTML 확인본 생성 완료
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
              1. 원본데이터 폴더
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
              2. 합성데이터 폴더
            </div>
            <div className={`text-[11px] font-semibold ${isDarkMode ? 'text-slate-300' : 'text-slate-700'}`}>
              합성데이터.csv & 합성데이터.xlsx
            </div>
            <div className="text-[10px] text-slate-400">
              {activeJob.target_rows}건 생성 완료 (체크포인트 저장됨)
            </div>
          </div>

          <div className={`p-4 rounded-xl border space-y-2 ${
            isDarkMode ? 'bg-slate-950 border-slate-800' : 'bg-slate-50 border-slate-200'
          }`}>
            <div className="text-xs font-bold text-rose-600 dark:text-rose-400 flex items-center gap-1.5">
              3. 심의위원회 심의자료 (HWPX 3종)
            </div>
            <div className={`text-[11px] space-y-0.5 ${isDarkMode ? 'text-slate-300' : 'text-slate-700'}`}>
              <div>[제출용] 원본데이터 명세서.hwpx</div>
              <div>[제출용] 합성데이터 명세서.hwpx</div>
              <div>[제출용] 안전성 및 유용성 측정결과서.hwpx</div>
              <div>[확인용] HTML 확인본 / 입력내용 JSON</div>
            </div>
          </div>
        </div>
      </div>

      {/* Recent AI Synthetic Jobs History Section */}
      <RecentJobsHistory 
        isDarkMode={isDarkMode}
        currentJobId={activeJob.id}
        onSelectJob={(job) => {
          setActiveJob(job);
        }}
      />

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
  );
};
