/**
 * 파일명: WorkspaceHeader.tsx
 * 경로: apps/web/src/components/WorkspaceHeader.tsx
 * 목적: 워크스페이스 제목과 작업 단계를 표시함
 * 작성자: 개발팀
 * 작성일: 2026-09-09
 * 수정일: 2026-09-09
 */
import React from 'react';
import { CheckCircle2, LucideIcon } from 'lucide-react';
import { WorkflowStepItem } from './WorkflowSteps';

export interface WorkspaceHeaderProps<T extends string | number = number> {
  eyebrow: string;
  title: string;
  description?: string;
  icon?: LucideIcon;
  badge?: React.ReactNode;
  steps?: WorkflowStepItem<T>[];
  activeStep?: T;
  isCompleted?: (step: WorkflowStepItem<T>) => boolean;
  onSelectStep?: (step: WorkflowStepItem<T>) => void;
  actions?: React.ReactNode;
  className?: string;
}

export function WorkspaceHeader<T extends string | number = number>({
  eyebrow,
  title,
  description,
  icon: Icon,
  badge,
  steps,
  activeStep,
  isCompleted,
  onSelectStep,
  actions,
  className = '',
}: WorkspaceHeaderProps<T>) {
  return (
    <div
      className={`ui-panel flex flex-col gap-3 px-4 py-3.5 sm:px-5 lg:flex-row lg:items-center lg:justify-between ${className}`}
    >
      {/* Left: Large Icon + Pill Eyebrow + Title + Description */}
      <div className="flex min-w-0 items-center gap-4">
        {Icon && (
          <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-accent text-accent-fg shadow-md">
            <Icon className="h-7 w-7" />
          </div>
        )}
        <div className="min-w-0">
          {/* Eyebrow as pill badge */}
          <div className="mb-1.5 inline-flex items-center gap-1.5">
            <span className="inline-flex items-center rounded-full border border-accent/30 bg-accent-subtle px-2.5 py-0.5 text-2xs font-extrabold tracking-widest text-accent uppercase font-mono">
              {eyebrow}
            </span>
            {badge && <div className="shrink-0">{badge}</div>}
          </div>
          <div className="flex items-baseline gap-2.5 flex-wrap">
            <h2 className="text-xl font-black tracking-tight text-fg leading-snug">
              {title}
            </h2>
          </div>
          {description && (
            <p className="mt-0.5 text-xs text-fg-muted truncate break-keep">
              {description}
            </p>
          )}
        </div>
      </div>

      {/* Right: Actions or Step Bar */}
      {actions ? (
        <div className="shrink-0 self-start lg:self-auto max-w-full">
          {actions}
        </div>
      ) : steps && steps.length > 0 && typeof activeStep !== 'undefined' ? (
        <nav aria-label="작업 단계" className="shrink-0 overflow-x-auto scrollbar-none self-start lg:self-auto max-w-full">
          <ol className="flex items-center gap-1 py-0.5">
            {steps.map((step, index) => {
              const active = step.id === activeStep;
              const completed = isCompleted ? isCompleted(step) : Number(activeStep) > Number(step.id);
              const disabled = !onSelectStep;
              const StepTag = disabled ? 'span' : 'button';

              return (
                <li key={String(step.id)} className="flex shrink-0 items-center gap-1">
                  {index > 0 && (
                    <span
                      aria-hidden="true"
                      className={`h-px w-4 sm:w-7 transition-colors ${
                        completed ? 'bg-success/60' : active ? 'bg-accent/40' : 'bg-[var(--ui-border-strong)]'
                      }`}
                    />
                  )}
                  <StepTag
                    type={disabled ? undefined : 'button'}
                    disabled={disabled ? undefined : false}
                    aria-current={active ? 'step' : undefined}
                    onClick={disabled ? undefined : () => onSelectStep?.(step)}
                    className={`inline-flex min-h-8 items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-bold transition-all ${
                      active
                        ? 'border-accent bg-accent text-accent-fg shadow-sm'
                        : completed
                          ? 'border-success/40 bg-success-subtle text-fg hover:border-success/70'
                          : 'border-subtle bg-surface-muted/70 text-fg-muted'
                    } ${onSelectStep ? 'cursor-pointer hover:border-accent hover:bg-accent-subtle hover:text-fg' : ''}`}
                  >
                    {/* Status indicator: checkmark for done, number for pending */}
                    <span
                      className={`flex h-4 w-4 shrink-0 items-center justify-center rounded-full text-2xs font-black ${
                        active
                          ? 'bg-white/20 text-accent-fg'
                          : completed
                            ? 'bg-success text-white'
                            : 'bg-surface border border-subtle text-fg-muted'
                      }`}
                    >
                      {completed ? <CheckCircle2 className="h-3 w-3" /> : index + 1}
                    </span>
                    <span className="whitespace-nowrap">{step.label}</span>
                  </StepTag>
                </li>
              );
            })}
          </ol>
        </nav>
      ) : null}
    </div>
  );
}
