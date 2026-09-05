import React from 'react';
import type { LucideIcon } from 'lucide-react';

type Accent = 'emerald' | 'sky' | 'amber';

const accentStyles: Record<Accent, {
  badge: string;
  icon: string;
  metric: string;
}> = {
  emerald: {
    badge: 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-500/20 dark:bg-emerald-500/10 dark:text-emerald-400',
    icon: 'bg-emerald-100 text-emerald-600 dark:bg-emerald-500/10 dark:text-emerald-400',
    metric: 'text-emerald-600 dark:text-emerald-400',
  },
  sky: {
    badge: 'border-sky-200 bg-sky-50 text-sky-700 dark:border-sky-500/20 dark:bg-sky-500/10 dark:text-sky-400',
    icon: 'bg-sky-100 text-sky-600 dark:bg-sky-500/10 dark:text-sky-400',
    metric: 'text-sky-600 dark:text-sky-400',
  },
  amber: {
    badge: 'border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-500/20 dark:bg-amber-500/10 dark:text-amber-400',
    icon: 'bg-amber-100 text-amber-600 dark:bg-amber-500/10 dark:text-amber-400',
    metric: 'text-amber-600 dark:text-amber-400',
  },
};

export interface WorkspaceMetric {
  label: string;
  value: string;
}

export function DataWorkspaceHeader({
  icon: Icon,
  accent,
  badge,
  context,
  title,
  description,
  metrics,
  isDarkMode,
}: {
  icon: LucideIcon;
  accent: Accent;
  badge: string;
  context: string;
  title: string;
  description: string;
  metrics: WorkspaceMetric[];
  isDarkMode: boolean;
}) {
  const styles = accentStyles[accent];

  return (
    <section className="ui-panel p-5 sm:p-6">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex min-w-0 items-start gap-4">
          <span className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl ${styles.icon}`}>
            <Icon className="h-6 w-6" />
          </span>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className={`rounded-full border px-2.5 py-0.5 text-[11px] font-bold ${styles.badge}`}>
                {badge}
              </span>
              <span className={`text-xs ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>
                {context}
              </span>
            </div>
            <h2 className={`mt-2 text-xl font-bold tracking-tight ${isDarkMode ? 'text-white' : 'text-slate-900'}`}>
              {title}
            </h2>
            <p className={`mt-1 max-w-3xl break-keep text-xs leading-relaxed ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>
              {description}
            </p>
          </div>
        </div>

        <div className="grid shrink-0 grid-cols-2 gap-3">
          {metrics.map(metric => (
            <div key={metric.label} className={`min-w-[132px] rounded-xl border px-4 py-3 text-center ${
              isDarkMode ? 'border-slate-800 bg-slate-950/60' : 'border-slate-200 bg-slate-50'
            }`}>
              <div className={`text-[10px] font-medium ${isDarkMode ? 'text-slate-500' : 'text-slate-400'}`}>{metric.label}</div>
              <div className={`mt-0.5 text-sm font-bold ${styles.metric}`}>{metric.value}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
