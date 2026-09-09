/**
 * 파일명: WorkflowSteps.tsx
 * 경로: apps/web/src/components/WorkflowSteps.tsx
 * 목적: 공통 작업 단계 UI를 표시함
 * 작성자: 개발팀
 * 작성일: 2026-09-09
 * 수정일: 2026-09-09
 */
import React from 'react';
import { CheckCircle2, LucideIcon } from 'lucide-react';

export type WorkflowStepItem<T extends string | number = number> = {
  id: T;
  label: string;
  description?: string;
  Icon?: LucideIcon;
};

type WorkflowStepsProps<T extends string | number = number> = {
  steps: WorkflowStepItem<T>[];
  activeStep: T;
  isCompleted?: (step: WorkflowStepItem<T>) => boolean;
  onSelect?: (step: WorkflowStepItem<T>) => void;
  className?: string;
  variant?: 'cards' | 'header';
};

export function WorkflowSteps<T extends string | number = number>({
  steps,
  activeStep,
  isCompleted,
  onSelect,
  className = '',
  variant = 'cards',
}: WorkflowStepsProps<T>) {
  // 현재 단계와 완료 단계를 공통 표현으로 표시함
  if (variant === 'header') {
    return (
      <nav className={`ui-panel overflow-hidden px-3 py-2.5 sm:px-4 ${className}`} aria-label="작업 단계">
        <ol className="flex items-center gap-1 overflow-x-auto scrollbar-none">
          {steps.map((step, index) => {
            const active = step.id === activeStep;
            const completed = isCompleted?.(step) ?? false;
            const disabled = !onSelect;
            const StepTag = disabled ? 'span' : 'button';

            return (
              <li key={String(step.id)} className="flex shrink-0 items-center gap-1.5">
                {index > 0 && (
                  <span
                    aria-hidden="true"
                    className={`h-px w-5 sm:w-8 ${completed || active ? 'bg-accent/70' : 'bg-[var(--ui-border-strong)]'}`}
                  />
                )}
                <StepTag
                  type={disabled ? undefined : 'button'}
                  disabled={disabled ? undefined : false}
                  aria-current={active ? 'step' : undefined}
                  onClick={disabled ? undefined : () => onSelect?.(step)}
                  className={`inline-flex min-h-9 items-center gap-2 rounded-lg border px-2.5 py-1.5 text-xs font-bold transition-colors ${
                    active
                      ? 'border-accent bg-accent text-accent-fg shadow-xs'
                      : completed
                        ? 'border-accent/40 bg-accent-subtle text-fg'
                        : 'border-subtle bg-surface-muted text-fg-muted'
                  } ${onSelect ? 'hover:border-accent hover:bg-accent-subtle hover:text-fg' : ''}`}
                >
                  <span className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-2xs font-bold ${
                    active
                      ? 'bg-accent-fg/20 text-accent-fg'
                      : completed
                        ? 'bg-success text-white'
                        : 'bg-surface text-fg-muted'
                  }`}>
                    {completed ? <CheckCircle2 className="h-3.5 w-3.5" /> : index + 1}
                  </span>
                  <span className="whitespace-nowrap">{step.label}</span>
                </StepTag>
              </li>
            );
          })}
        </ol>
      </nav>
    );
  }

  return (
    <nav className={`grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5 ${className}`} aria-label="작업 단계">
      {steps.map((step, index) => {
        const active = step.id === activeStep;
        const completed = isCompleted?.(step) ?? false;
        const disabled = !onSelect;
        const Icon = step.Icon;

        return (
          <button
            key={String(step.id)}
            type="button"
            disabled={disabled}
            aria-current={active ? 'step' : undefined}
            onClick={() => onSelect?.(step)}
            className={`flex min-h-[76px] min-w-0 items-center gap-3 rounded-xl border p-3.5 text-left transition-all disabled:cursor-default ${
              active
                ? 'border-accent bg-accent-subtle text-fg shadow-sm ring-1 ring-accent/30'
                : completed
                  ? 'border-subtle bg-surface text-fg shadow-sm'
                  : 'border-subtle bg-surface-muted/60 text-fg-muted'
            } ${onSelect ? 'hover:border-accent hover:bg-accent-subtle' : ''}`}
          >
            <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-xs font-bold ${
              active
                ? 'bg-accent text-accent-fg'
                : completed
                  ? 'bg-success text-white'
                  : 'bg-surface border border-subtle text-fg-muted'
            }`}>
              {completed ? <CheckCircle2 className="h-4 w-4" /> : Icon ? <Icon className="h-4 w-4" /> : index + 1}
            </span>
            <span className="min-w-0">
              <span className="block break-keep text-xs font-bold leading-snug">{step.label}</span>
              {step.description && (
                <span className="mt-0.5 block break-keep text-2xs leading-snug text-fg-subtle">
                  {step.description}
                </span>
              )}
            </span>
          </button>
        );
      })}
    </nav>
  );
}
