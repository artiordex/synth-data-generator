import React from 'react';
import { Clock3, FileUp, Files, Network, ClipboardList } from 'lucide-react';

export type SyntheticWorkflow = 'single' | 'batch' | 'relational' | 'timeseries' | 'survey';

const workflows = [
  {
    value: 'single',
    label: '단일 테이블',
    description: '파일 1개를 정밀 분석·합성',
    icon: FileUp,
    accent: 'sky',
  },
  {
    value: 'survey',
    label: '설문 모듈 연계',
    description: '다중 설문 통합 학습 후 원본 분할',
    icon: ClipboardList,
    accent: 'emerald',
  },
  {
    value: 'batch',
    label: '파일 일괄',
    description: '최대 20개 파일을 독립 처리',
    icon: Files,
    accent: 'cyan',
  },
  {
    value: 'relational',
    label: '관계형 테이블',
    description: '여러 테이블의 PK·FK 유지',
    icon: Network,
    accent: 'indigo',
  },
  {
    value: 'timeseries',
    label: '시계열·패널',
    description: '개체별 시간 순서와 흐름 유지',
    icon: Clock3,
    accent: 'violet',
  },
] as const;

const selectedStyles = {
  sky: 'border-sky-500 bg-sky-50 text-sky-950 ring-sky-400/30 dark:border-sky-500 dark:bg-sky-950/60 dark:text-white',
  emerald: 'border-emerald-500 bg-emerald-50 text-emerald-950 ring-emerald-400/30 dark:border-emerald-500 dark:bg-emerald-950/60 dark:text-white',
  cyan: 'border-cyan-500 bg-cyan-50 text-cyan-950 ring-cyan-400/30 dark:border-cyan-500 dark:bg-cyan-950/60 dark:text-white',
  indigo: 'border-indigo-500 bg-indigo-50 text-indigo-950 ring-indigo-400/30 dark:border-indigo-500 dark:bg-indigo-950/60 dark:text-white',
  violet: 'border-violet-500 bg-violet-50 text-violet-950 ring-violet-400/30 dark:border-violet-500 dark:bg-violet-950/60 dark:text-white',
} as const;

const iconStyles = {
  sky: 'bg-sky-100 text-sky-600 dark:bg-sky-500/15 dark:text-sky-300',
  emerald: 'bg-emerald-100 text-emerald-600 dark:bg-emerald-500/15 dark:text-emerald-300',
  cyan: 'bg-cyan-100 text-cyan-600 dark:bg-cyan-500/15 dark:text-cyan-300',
  indigo: 'bg-indigo-100 text-indigo-600 dark:bg-indigo-500/15 dark:text-indigo-300',
  violet: 'bg-violet-100 text-violet-600 dark:bg-violet-500/15 dark:text-violet-300',
} as const;


export function SynthesisWorkflowSelector({ value, onChange, isDarkMode }: {
  value: SyntheticWorkflow;
  onChange: (value: SyntheticWorkflow) => void;
  isDarkMode: boolean;
}) {
  return (
    <section
      aria-labelledby="synthesis-workflow-heading"
      className="ui-panel p-4 sm:p-5"
    >
      <div className="mb-4">
        <h2 id="synthesis-workflow-heading" className={`text-sm font-bold ${isDarkMode ? 'text-white' : 'text-slate-900'}`}>
          합성 방식 선택
        </h2>
        <p className={`mt-1 text-xs ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>
          데이터 구조에 맞는 방식을 고르면 아래 작업 화면이 바로 바뀝니다.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5" role="group" aria-label="합성 방식">
        {workflows.map((workflow) => {
          const Icon = workflow.icon;
          const selected = value === workflow.value;
          return (
            <button
              key={workflow.value}
              type="button"
              aria-pressed={selected}
              onClick={() => onChange(workflow.value)}
              className={`flex min-h-[86px] items-center gap-3 rounded-xl border p-3 text-left transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-500 ${
                selected
                  ? `${selectedStyles[workflow.accent]} shadow-sm ring-1`
                  : isDarkMode
                    ? 'border-slate-700 bg-slate-950/40 text-slate-200 hover:border-slate-500 hover:bg-slate-800/70'
                    : 'border-slate-200 bg-slate-50 text-slate-800 hover:border-slate-300 hover:bg-slate-100'
              }`}
            >
              <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${iconStyles[workflow.accent]}`}>
                <Icon className="h-5 w-5" />
              </span>
              <span className="min-w-0">
                <span className="block text-sm font-bold">{workflow.label}</span>
                <span className={`mt-1 block break-keep text-xs leading-snug ${selected ? 'opacity-75' : isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>
                  {workflow.description}
                </span>
              </span>
            </button>
          );
        })}
      </div>
    </section>
  );
}
