/**
 * 파일명: AiGuideReadinessPanel.tsx
 * 경로: apps/web/src/features/aiguide/AiGuideReadinessPanel.tsx
 * 목적: AI 가이드 생성 전 필수 입력과 품질 측정 상태를 표시함
 * 작성자: 개발팀
 * 작성일: 2026-09-29
 * 수정일: 2026-09-29
 */
import React from 'react';
import { AlertTriangle, CheckCircle2, Info } from 'lucide-react';
import type { ReadinessCheckItem } from '../../services/api';

type DataCategory = 'file' | 'api';

interface AiGuideReadinessPanelProps {
  documentTitle: string;
  hasSourceData: boolean;
  dataCategory: DataCategory;
  readinessScore: number | null;
  readinessChecklist: ReadinessCheckItem[];
  metadata: Record<string, string>;
  canonicalMetadata: Record<string, unknown> | null;
}

const OPTIONAL_METADATA_FIELDS = [
  { key: 'publisher', label: '제공기관' },
  { key: 'creator', label: '소관부서' },
  { key: 'contact_name', label: '담당자명' },
  { key: 'contact_email', label: '담당 부서 이메일' },
  { key: 'contact_phone', label: '담당 부서 전화' },
  { key: 'theme_label', label: '주제 분류' },
  { key: 'description', label: '데이터 설명' },
  { key: 'purpose', label: '구축·개방 목적' },
  { key: 'keywords', label: '검색 키워드' },
  { key: 'legal_basis', label: '법적 근거' },
  { key: 'update_frequency', label: '갱신주기' },
  { key: 'spatial', label: '공간·대상 범위' },
  { key: 'collection_process', label: '수집 방법' },
  { key: 'limitations', label: '이용 한계·주의사항' },
  { key: 'temporal_start', label: '대상 기간' },
  { key: 'temporal_end', label: '대상 기간 종료일' },
  { key: 'source_datasets', label: '연계 데이터셋' },
  { key: 'transformation', label: '변환·가공 이력' },
  { key: 'imputation', label: '결측값 처리 방법' },
  { key: 'ai_purpose', label: '예상 AI 활용 목적' },
] as const;

const OPTIONAL_API_FIELDS = [
  { key: 'api_base_url', label: 'API 기본 URL' },
  { key: 'operation_id', label: '기능 식별자' },
  { key: 'operation_name', label: 'API 기능명' },
  { key: 'endpoint', label: '세부 경로' },
  { key: 'http_method', label: 'HTTP method' },
  { key: 'authentication_type', label: '인증 유형' },
  { key: 'authentication', label: '인증 방식 설명' },
  { key: 'specification_url', label: 'OpenAPI·계약 명세 URL' },
  { key: 'api_version', label: 'API 버전' },
  { key: 'rate_limit', label: '호출 제한' },
  { key: 'request_parameters', label: '요청 파라미터' },
  { key: 'pagination', label: '페이지네이션·호출 제한' },
  { key: 'error_codes', label: '오류 코드·재시도 기준' },
  { key: 'response_path', label: '업무 레코드 경로' },
] as const;

// 문자열 입력이 비어 있지 않은지 판별함
const hasValue = (value: unknown): boolean =>
  typeof value === 'string' && value.trim().length > 0;

/** 필수 오류와 선택 권고 및 측정된 준비도를 구분해 표시함 */
export const AiGuideReadinessPanel: React.FC<AiGuideReadinessPanelProps> = ({
  documentTitle,
  hasSourceData,
  dataCategory,
  readinessScore,
  readinessChecklist,
  metadata,
  canonicalMetadata,
}) => {
  const requiredChecks = [
    {
      label: '분석할 원본 데이터',
      complete: hasSourceData,
      guidance: '1단계에서 파일을 올리거나 샘플 데이터를 불러오세요.',
    },
    {
      label: '문서 제목',
      complete: hasValue(documentTitle),
      guidance: '1단계에서 문서 제목을 입력하세요.',
    },
  ];
  const requiredIssues = requiredChecks.filter(check => !check.complete);
  const optionalFields = dataCategory === 'api'
    ? [...OPTIONAL_METADATA_FIELDS, ...OPTIONAL_API_FIELDS]
    : OPTIONAL_METADATA_FIELDS;
  const missingOptionalFields = optionalFields.filter(({ key }) => !hasValue(metadata[key]));
  const completedOptionalFields = optionalFields.length - missingOptionalFields.length;
  const score = typeof readinessScore === 'number' && Number.isFinite(readinessScore)
    ? Math.max(0, Math.min(100, Math.round(readinessScore)))
    : null;
  const rawReviewRequired = canonicalMetadata?.reviewRequired ?? canonicalMetadata?.review_required;
  const reviewRequired = Array.isArray(rawReviewRequired)
    ? rawReviewRequired.flatMap((item) => {
      if (typeof item === 'string' && item.trim()) {
        return [{ path: item, category: item.split('/')[1] || '기타' }];
      }
      if (item && typeof item === 'object') {
        const entry = item as { bindingPath?: unknown; label?: unknown; category?: unknown };
        const path = typeof entry.bindingPath === 'string' ? entry.bindingPath
          : typeof entry.label === 'string' ? entry.label : '';
        if (!path) return [];
        return [{ path, category: typeof entry.category === 'string' ? entry.category : path.split('/')[1] || '기타' }];
      }
      return [];
    })
    : [];
  const reviewCategoryCounts = reviewRequired.reduce<Record<string, number>>((counts, item) => {
    counts[item.category] = (counts[item.category] ?? 0) + 1;
    return counts;
  }, {});

  return (
    <section className="ui-panel p-5 space-y-4" aria-labelledby="ai-guide-readiness-title">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <h3 id="ai-guide-readiness-title" className="ui-section-title">산출물 생성 전 준비도 점검</h3>
          <p className="text-xs text-fg-muted">
            필수 입력 오류와 기관 확인 권고를 구분해 표시합니다. 권고 항목은 검토 안내입니다.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-2xs font-semibold">
          <span className={`rounded-full px-2.5 py-1 ${requiredIssues.length
            ? 'bg-rose-500/10 text-rose-700 dark:text-rose-300'
            : 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300'}`}>
            필수 입력 {requiredChecks.length - requiredIssues.length}/{requiredChecks.length}
          </span>
          <span className="rounded-full bg-amber-500/10 text-amber-700 dark:text-amber-300 px-2.5 py-1">
            선택 권고 {missingOptionalFields.length}건
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-3">
        <div className={`rounded-xl border p-4 space-y-2 ${requiredIssues.length
          ? 'border-rose-500/30 bg-rose-500/5'
          : 'border-emerald-500/25 bg-emerald-500/5'}`}>
          <div className="flex items-center gap-2">
            {requiredIssues.length
              ? <AlertTriangle className="h-4 w-4 text-rose-600 dark:text-rose-400" />
              : <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />}
            <h4 className="text-sm font-bold text-fg">필수 입력 오류</h4>
          </div>
          {requiredIssues.length ? (
            <ul className="space-y-1.5 text-xs text-rose-700 dark:text-rose-300">
              {requiredIssues.map(check => (
                <li key={check.label}>
                  <span className="font-semibold">{check.label}:</span> {check.guidance}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-emerald-700 dark:text-emerald-300">원본 데이터와 문서 제목이 준비되었습니다.</p>
          )}
        </div>

        <div className="rounded-xl border border-amber-500/25 bg-amber-500/5 p-4 space-y-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h4 className="text-sm font-bold text-fg">선택 메타데이터 권고</h4>
            <span className="text-2xs text-fg-muted">입력 {completedOptionalFields}/{optionalFields.length}</span>
          </div>
          {missingOptionalFields.length ? (
            <ul className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-1 text-xs text-amber-800 dark:text-amber-200">
              {missingOptionalFields.map(({ key, label }) => <li key={key}>· {label}</li>)}
            </ul>
          ) : (
            <p className="text-xs text-emerald-700 dark:text-emerald-300">선택 메타데이터 항목이 채워져 있습니다.</p>
          )}
          <p className="text-2xs text-fg-muted">
            위 ‘기관 확인 정보 수정’에서 보완할 수 있습니다. 공공누리 이용조건과 개인정보·권리 관계는 별도로 확인해 주세요.
          </p>
        </div>
      </div>

      <div className="rounded-xl border border-subtle bg-surface-muted/50 p-4 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Info className="h-4 w-4 text-accent" />
            <h4 className="text-sm font-bold text-fg">데이터 분석 준비도</h4>
          </div>
          <span className="text-sm font-bold text-accent">관측값 채움률 {score === null ? '미측정' : `${score}%`}</span>
        </div>
        <p className="text-xs text-fg-muted">
          입력 데이터의 관측값 중 null·빈 문자열이 아닌 값의 비율입니다. 구조상 누락된 필수 항목, 정확성·대표성·편향·개인정보 적합성은 별도로 검토해야 합니다.
        </p>
        {readinessChecklist.length > 0 ? (
          <ul className="space-y-1.5 border-t border-subtle pt-3">
            {readinessChecklist.map((item, index) => {
              const isPass = item.status === 'pass';
              const isFail = item.status === 'fail';
              const statusLabel = isPass ? '완료' : isFail ? '오류' : '권고';
              const statusClass = isPass
                ? 'text-emerald-700 dark:text-emerald-300'
                : isFail
                  ? 'text-rose-700 dark:text-rose-300'
                  : 'text-amber-700 dark:text-amber-300';
              return (
                <li key={`${item.item}-${index}`} className="flex flex-wrap items-start gap-x-2 text-xs">
                  <span className={`shrink-0 font-semibold ${statusClass}`}>[{statusLabel}]</span>
                  <span className="font-semibold text-fg">{item.item}</span>
                  <span className="text-fg-muted">{item.message}</span>
                </li>
              );
            })}
          </ul>
        ) : (
          <p className="border-t border-subtle pt-3 text-xs text-fg-muted">분석 체크리스트가 없습니다.</p>
        )}
        {reviewRequired.length > 0 && (
          <details className="border-t border-subtle pt-3">
            <summary className="cursor-pointer text-xs font-semibold text-fg">
              미확정 표준 필드 {reviewRequired.length}건 보기
            </summary>
            <p className="mt-2 text-2xs text-fg-muted">
              AI 초안·관측값·기관 확인값의 상태를 구분한 전체 목록입니다. 빈 표준 항목은 담당자 확인 상태로 남아 있습니다.
            </p>
            <div className="my-2 flex flex-wrap gap-1.5">
              {Object.entries(reviewCategoryCounts).sort((a, b) => b[1] - a[1]).map(([category, count]) => (
                <span key={category} className="rounded-full border border-amber-500/20 bg-amber-500/10 px-2 py-0.5 text-2xs text-amber-800 dark:text-amber-200">
                  {category} {count}건
                </span>
              ))}
            </div>
            <ul className="max-h-64 space-y-1 overflow-auto rounded border border-subtle bg-surface p-2 text-2xs text-fg-muted">
              {reviewRequired.map((item, index) => <li key={`${item.path}-${index}`} className="break-all">{item.path}</li>)}
            </ul>
          </details>
        )}
      </div>
    </section>
  );
};
