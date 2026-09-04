import React, { useState, useEffect } from 'react';
import { History, RefreshCw, Clock, Download, ChevronRight, CheckCircle2, AlertCircle } from 'lucide-react';
import { JobStatus } from '../../types';
import { getJobsList, getDownloadUrl } from '../../services/api';

interface Props {
  isDarkMode: boolean;
  onSelectJob?: (job: JobStatus) => void;
  currentJobId?: string;
}

export const RecentJobsHistory: React.FC<Props> = ({
  isDarkMode,
  onSelectJob,
  currentJobId
}) => {
  const [jobs, setJobs] = useState<JobStatus[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const loadJobs = async () => {
    setIsLoading(true);
    try {
      const list = await getJobsList();
      // Sort newest first
      setJobs(list);
    } catch (e) {
      console.error('합성 작업 이력 로드 실패:', e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadJobs();
  }, []);

  const getGradeBadge = (grade?: string) => {
    const g = grade || 'A';
    if (g === 'S') {
      return 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800/60';
    }
    if (g === 'A') {
      return 'bg-sky-50 text-sky-700 dark:bg-sky-950/60 dark:text-sky-300 border-sky-200 dark:border-sky-800/60';
    }
    if (g === 'B') {
      return 'bg-amber-50 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300 border-amber-200 dark:border-amber-800/60';
    }
    return 'bg-rose-50 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300 border-rose-200 dark:border-rose-800/60';
  };

  return (
    <div className={`p-6 rounded-2xl border transition-colors ${
      isDarkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200 shadow-sm'
    }`}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2.5">
          <div className={`p-2 rounded-xl ${
            isDarkMode ? 'bg-sky-950/60 text-sky-400 border border-sky-800/50' : 'bg-sky-50 text-sky-700 border border-sky-200'
          }`}>
            <History className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-bold text-base text-slate-900 dark:text-white flex items-center gap-2">
              최근 AI 합성 작업 이력
              <span className={`text-xs px-2 py-0.5 rounded-full font-semibold ${
                isDarkMode ? 'bg-slate-800 text-slate-300' : 'bg-slate-100 text-slate-700'
              }`}>
                {jobs.length}건
              </span>
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              금융보안원 및 가명정보 결합전문기관 심의 제출용 AI 합성데이터 생성 및 평가 내역
            </p>
          </div>
        </div>

        <button
          onClick={loadJobs}
          disabled={isLoading}
          className={`p-2 rounded-xl transition-colors border ${
            isDarkMode 
              ? 'bg-slate-800 hover:bg-slate-700 text-slate-300 border-slate-700' 
              : 'bg-white hover:bg-slate-50 text-slate-600 border-slate-200 shadow-sm'
          }`}
          title="이력 새로고침"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {jobs.length === 0 ? (
        <div className="text-center py-8 border border-dashed rounded-xl dark:border-slate-800">
          <Clock className="w-8 h-8 mx-auto text-slate-400 mb-2 opacity-60" />
          <p className="text-xs font-semibold text-slate-600 dark:text-slate-400">수행된 AI 합성 작업 이력이 없습니다.</p>
          <p className="text-[11px] text-slate-400 dark:text-slate-500 mt-0.5">상단에서 데이터셋을 업로드하고 파이프라인을 실행하시면 자동으로 이력이 기록됩니다.</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border dark:border-slate-800">
          <table className="w-full text-left text-xs">
            <thead className={`border-b ${isDarkMode ? 'bg-slate-950/80 text-slate-300 border-slate-800' : 'bg-slate-50 text-slate-700 border-slate-200'}`}>
              <tr>
                <th className="py-2.5 px-3 font-semibold">작업 일시</th>
                <th className="py-2.5 px-3 font-semibold">원본 데이터셋</th>
                <th className="py-2.5 px-3 font-semibold">AI 모델</th>
                <th className="py-2.5 px-3 font-semibold">생성 건수</th>
                <th className="py-2.5 px-3 font-semibold">심의 판정</th>
                <th className="py-2.5 px-3 font-semibold">품질 지수</th>
                <th className="py-2.5 px-3 font-semibold">재식별 위험도</th>
                <th className="py-2.5 px-3 font-semibold text-right">상세 및 다운로드</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
              {jobs.map((j) => {
                const isSelected = j.id === currentJobId;
                const dateStr = j.created_at ? new Date(j.created_at).toLocaleString('ko-KR', {
                  year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit'
                }) : '-';

                return (
                  <tr 
                    key={j.id} 
                    className={`transition-colors ${
                      isSelected 
                        ? isDarkMode ? 'bg-sky-950/40 border-l-2 border-l-sky-500' : 'bg-sky-50/70 border-l-2 border-l-sky-500' 
                        : isDarkMode ? 'hover:bg-slate-800/40' : 'hover:bg-slate-50/80'
                    }`}
                  >
                    <td className="py-2.5 px-3 font-mono text-slate-500 dark:text-slate-400 whitespace-nowrap">
                      {dateStr}
                    </td>
                    <td className="py-2.5 px-3 font-medium text-slate-900 dark:text-white max-w-[140px] truncate" title={j.original_filename}>
                      {j.original_filename || '데이터셋'}
                    </td>
                    <td className="py-2.5 px-3">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300 border border-slate-200 dark:border-slate-700 uppercase">
                        {j.model_type || 'STATISTICAL'}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 font-mono text-slate-700 dark:text-slate-300">
                      {j.target_rows ? `${Number(j.target_rows).toLocaleString()}건` : '-'}
                    </td>
                    <td className="py-2.5 px-3">
                      {j.status === 'completed' ? (
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${getGradeBadge(j.assessment_grade)}`}>
                          {j.assessment_passed ? `${j.assessment_grade ?? '-'} 등급 (${j.assessment_score ?? '-'}점)` : '검토 필요'}
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded text-[10px] bg-slate-200 text-slate-600 dark:bg-slate-800 dark:text-slate-400">
                          {j.status}
                        </span>
                      )}
                    </td>
                    <td className="py-2.5 px-3 font-mono text-sky-600 dark:text-sky-400 font-semibold">
                      {j.quality_score ? `${(j.quality_score * 100).toFixed(1)}%` : '-'}
                    </td>
                    <td className="py-2.5 px-3 font-mono text-amber-600 dark:text-amber-400">
                      {j.reid_risk != null ? `${(j.reid_risk * 100).toFixed(2)}%` : '미측정'}
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        {onSelectJob && j.status === 'completed' && (
                          <button
                            onClick={() => onSelectJob(j)}
                            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold bg-sky-600 hover:bg-sky-500 text-white transition-colors shadow-sm"
                            title="이 결과 리포트 및 분포 차트 열람"
                          >
                            <span>리포트</span>
                            <ChevronRight className="w-3.5 h-3.5" />
                          </button>
                        )}
                        {j.package_zip && (
                          <a
                            href={getDownloadUrl(`/api/v1/files/download?path=${j.package_zip}`)}
                            download={`${j.id}_review_package.zip`}
                            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold bg-slate-100 hover:bg-slate-200 text-slate-700 dark:bg-slate-800 dark:hover:bg-slate-700 dark:text-slate-200 transition-colors border border-slate-200 dark:border-slate-700"
                            title="HWPX 서식 및 심의자료 ZIP 다운로드"
                          >
                            <Download className="w-3.5 h-3.5" />
                            <span>HWPX</span>
                          </a>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
