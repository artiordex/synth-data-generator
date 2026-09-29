/**
 * 파일명: AiGuideContextForm.tsx
 * 경로: apps/web/src/features/aiguide/AiGuideContextForm.tsx
 * 목적: AI 가이드 생성에 필요한 기관 맥락을 입력받음
 * 작성자: 개발팀
 * 작성일: 2026-09-29
 * 수정일: 2026-09-29
 */
import React from 'react';

type DataCategory = 'file' | 'api';

interface AiGuideContextFormProps {
  metadata: Record<string, string>;
  metadataProvenance: Record<string, string>;
  dataCategory: DataCategory;
  onMetadataChange: (key: string, value: string) => void;
  onDataCategoryChange: (value: DataCategory) => void;
}

const CONTEXT_FIELDS = [
  { key: 'description', label: '데이터 설명', hint: '무엇을 기록하며, 한 행이 어떤 대상을 뜻하는지 적어 주세요.', multiline: true },
  { key: 'purpose', label: '구축·개방 목적', hint: '수집 배경, 주요 이용자, 업무 활용 목적을 적어 주세요.', multiline: true },
  { key: 'keywords', label: '검색 키워드', hint: '동의어와 약어를 쉼표로 구분해 적어 주세요.' },
  { key: 'temporal_start', label: '대상 기간 시작일', hint: '예: 2022-01-01', type: 'date' },
  { key: 'temporal_end', label: '대상 기간 종료일', hint: '예: 2025-12-31', type: 'date' },
  { key: 'spatial', label: '지역·대상 범위', hint: '예: 전국 17개 시도, 허가된 국내 의약품' },
  { key: 'collection_process', label: '수집·생성 방법', hint: '담당자가 아는 수집 경로와 생성 과정을 적어 주세요.', multiline: true },
  { key: 'limitations', label: '알려진 한계·주의사항', hint: '누락 대상, 집계 기준, 해석상 주의점을 적어 주세요.', multiline: true },
  { key: 'source_datasets', label: '연계 데이터셋', hint: '데이터셋명이나 식별자를 쉼표로 구분해 적어 주세요.' },
] as const;

const PROCESSING_FIELDS = [
  { key: 'version', label: '현재 데이터 버전', hint: '예: 2025.01' },
  { key: 'issued', label: '최초 공개일', hint: '예: 2024-01-15', type: 'date' },
  { key: 'modified', label: '최근 수정일', hint: '예: 2025-01-15', type: 'date' },
  { key: 'version_notes', label: '이번 버전 변경사항', hint: '추가·수정·삭제 및 기준 변경 내역을 적어 주세요.', multiline: true },
  { key: 'transformation', label: '변환·가공 이력', hint: '원본에서 공개본까지 적용한 정제, 결합, 단위 변환 등을 적어 주세요.', multiline: true },
  { key: 'imputation', label: '결측값 처리 방법', hint: '삭제·대체·미처리 여부와 규칙을 적어 주세요.', multiline: true },
  { key: 'ai_purpose', label: '예상 AI 활용 목적', hint: '사용자, 목표, 기대 결과와 사람의 검토 절차를 적어 주세요.', multiline: true },
  { key: 'training_split', label: '학습·평가 분리 기준', hint: '시간·개체 단위 분리 등 이미 정해진 기준이 있을 때 입력하세요.', multiline: true },
] as const;

const API_FIELDS = [
  { key: 'api_base_url', label: 'API 기본 URL', hint: '인증키·토큰이 포함된 주소는 입력하지 마세요.' },
  { key: 'operation_id', label: '기능 식별자', hint: '예: getProductList' },
  { key: 'operation_name', label: 'API 기능명', hint: '예: 의약품 품목 목록 조회' },
  { key: 'endpoint', label: '세부 경로', hint: '예: /getProductList' },
  { key: 'http_method', label: 'HTTP 메서드', hint: '예: GET 또는 POST' },
  { key: 'authentication_type', label: '인증 유형', hint: '예: 인증키, OAuth 2.0, 인증 없음' },
  { key: 'authentication', label: '인증 방식 설명', hint: '헤더·파라미터 위치만 적고 실제 비밀키는 입력하지 마세요.', multiline: true },
  { key: 'specification_url', label: 'OpenAPI·계약 명세 URL', hint: '공식 명세 주소' },
  { key: 'api_version', label: 'API 버전', hint: '예: v1' },
  { key: 'rate_limit', label: '호출 제한', hint: '횟수·기간·적용 단위를 적어 주세요.' },
  { key: 'request_parameters', label: '요청 파라미터', hint: '파라미터마다 한 줄: 이름 | 한글명 | 위치(QUERY/HEADER/PATH/BODY) | 타입 | 필수/선택 | 기본값 | 설명', multiline: true },
  { key: 'pagination', label: '페이지네이션', hint: '페이지 번호·크기·종료 조건을 적어 주세요.' },
  { key: 'error_codes', label: '오류 코드·재시도 기준', hint: '오류마다 한 줄: 코드 | HTTP 상태 | 메시지 | 해결·재시도 조치', multiline: true },
  { key: 'response_path', label: '업무 레코드 경로', hint: '예: response.body.items.item' },
] as const;

// 입력값의 작성 출처를 검토 가능한 라벨로 표시함
const provenanceLabel = (source?: string) => source === 'AUTO_INFERRED'
  ? 'AI 초안 · 검토 필요'
  : source === 'SAMPLE_PRESET'
    ? '샘플 예시 · 실제값 확인'
    : source === 'USER_CONFIRMED'
      ? '담당자 입력'
      : '';

/** 데이터 정의와 운영 맥락을 입력받음 */
export const AiGuideContextForm: React.FC<AiGuideContextFormProps> = ({
  metadata,
  metadataProvenance,
  dataCategory,
  onMetadataChange,
  onDataCategoryChange,
}) => {
  const inputClass = 'w-full rounded border border-subtle bg-surface px-2.5 py-2 text-xs text-fg outline-none transition-colors focus:border-accent';

  // 입력 필드 설정을 접근 가능한 폼 요소로 렌더링함
  const renderFields = (fields: ReadonlyArray<{ key: string; label: string; hint: string; multiline?: boolean; type?: string }>) => (
    <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
      {fields.map((field) => (
        <label key={field.key} className={`grid gap-1.5 text-xs ${field.multiline ? 'lg:col-span-2' : ''}`}>
          <span className="flex flex-wrap items-center gap-2 font-semibold text-fg">
            {field.label}
            {provenanceLabel(metadataProvenance[field.key]) && (
              <span className="rounded-full bg-accent/10 px-2 py-0.5 text-2xs font-medium text-accent">
                {provenanceLabel(metadataProvenance[field.key])}
              </span>
            )}
          </span>
          {field.multiline ? (
            <textarea
              className={`${inputClass} resize-y`}
              rows={3}
              maxLength={6000}
              value={metadata[field.key] || ''}
              placeholder={field.hint}
              onChange={(event) => onMetadataChange(field.key, event.target.value)}
            />
          ) : (
            <input
              className={inputClass}
              type={field.type || 'text'}
              maxLength={2000}
              value={metadata[field.key] || ''}
              placeholder={field.hint}
              onChange={(event) => onMetadataChange(field.key, event.target.value)}
            />
          )}
        </label>
      ))}
    </div>
  );

  return (
    <section className="ui-panel space-y-4 p-5" aria-labelledby="ai-guide-context-title">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h4 id="ai-guide-context-title" className="ui-section-title">AI 초안에 사용할 업무 맥락</h4>
          <p className="mt-1 text-xs text-fg-muted">
            파일 구조만으로 알 수 없는 내용을 입력하면 데이터 설명·필드 의미·활용 시나리오 초안에 반영합니다. 모르는 값은 비워 두어도 됩니다.
          </p>
        </div>
        <label className="grid min-w-52 gap-1 text-xs font-semibold text-fg">
          데이터 제공 방식
          <select
            className={inputClass}
            value={dataCategory}
            onChange={(event) => onDataCategoryChange(event.target.value as DataCategory)}
          >
            <option value="file">정적 파일·정기 배포 자료</option>
            <option value="api">API 서비스 응답</option>
          </select>
        </label>
      </div>

      <details open className="rounded-lg border border-subtle p-3">
        <summary className="cursor-pointer text-sm font-semibold text-fg">데이터 정의와 범위</summary>
        <div className="mt-3">{renderFields(CONTEXT_FIELDS)}</div>
      </details>

      <details className="rounded-lg border border-subtle p-3">
        <summary className="cursor-pointer text-sm font-semibold text-fg">버전·가공·AI 활용 정보</summary>
        <div className="mt-3">{renderFields(PROCESSING_FIELDS)}</div>
      </details>

      {dataCategory === 'api' && (
        <details className="rounded-lg border border-subtle p-3">
          <summary className="cursor-pointer text-sm font-semibold text-fg">API 운영·계약 정보</summary>
          <p className="mt-1 text-xs text-fg-muted">API 응답 구조와 공식 서비스 계약을 구분해 입력합니다. 실제 인증키나 토큰은 입력하지 마세요.</p>
          <div className="mt-3">{renderFields(API_FIELDS)}</div>
        </details>
      )}
    </section>
  );
};
