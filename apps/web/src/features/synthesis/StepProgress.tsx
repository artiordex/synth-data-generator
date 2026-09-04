import React from 'react';
import { RefreshCw } from 'lucide-react';
import { JobStatus } from '../../types';

interface StepProgressProps {
  isDarkMode: boolean;
  activeJob: JobStatus;
  handleCancelJob: () => Promise<void>;
}

export const StepProgress: React.FC<StepProgressProps> = ({
  isDarkMode,
  activeJob,
  handleCancelJob,
}) => {
  return (
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
  );
};
