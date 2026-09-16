/**
 * 파일명: AiGuideTemplatePanel.tsx
 * 경로: apps/web/src/features/aiguide/AiGuideTemplatePanel.tsx
 * 목적: AI-Ready 보고서 템플릿 메타데이터 및 필드 주석 설정을 관리함
 * 작성자: 개발팀
 * 작성일: 2026-09-16
 * 수정일: 2026-09-16
 */
import React, { useState } from 'react';
import { AiGuideFieldAnnotation, parseAiGuideTemplate } from '../../services/api';
import { UnifiedFileUploader } from '../shared/UnifiedFileUploader';

const COMMON_FIELDS = [
  ['publisher', '제공기관'], ['description', '데이터 설명'], ['department', '운영부서'],
  ['legal_basis', '관련법령·근거'], ['landing_page', '공개 페이지 URL'], ['contact', '담당부서·연락처'],
  ['license', '라이선스·이용조건'], ['rights', '저작권·외부 데이터 권리'], ['update_frequency', '갱신주기'],
  ['version', '배포 버전'], ['issued', '최초 공개일'], ['modified', '원천 수정일'],
  ['temporal', '시간 범위·시간대'], ['spatial', '공간·대상 범위'], ['source_datasets', '원천·연계 데이터셋'],
  ['transformation', '결합키·파생식·가공 이력'], ['imputation', '결측 보정 방법·플래그 의미'],
  ['training_split', 'AI 목적·학습/검증 분리'], ['limitations', '대표성·편향·개인정보·이용 한계'],
];
const API_FIELDS = [
  ['endpoint', 'API URL'], ['http_method', 'HTTP method'], ['authentication', '인증 방식 (실제 키 입력 금지)'],
  ['request_parameters', '요청 파라미터·필수·기본값'], ['pagination', '페이지네이션·호출 제한'],
  ['error_codes', '오류 코드·재시도'], ['response_path', '업무 레코드 경로'],
];

interface Props {
  canonical: Record<string, unknown> | null;
  metadata: Record<string, string>;
  onMetadataChange: (value: Record<string, string>) => void;
  annotations: Record<string, AiGuideFieldAnnotation>;
  onAnnotationsChange: (value: Record<string, AiGuideFieldAnnotation>) => void;
}

// AI 가이드 템플릿 메타데이터 및 필드 주석 편집 패널 컴포넌트임
export function AiGuideTemplatePanel({canonical, metadata, onMetadataChange, annotations, onAnnotationsChange}: Props) {
  const [verification, setVerification] = useState('');
  const [busy, setBusy] = useState(false);
  const fields = ((canonical?.fields ?? []) as {path: string; types: string[]}[])
    .filter(field => field.types.some(type => !['object', 'array'].includes(type)));
  const metadataFields = canonical?.data_category === 'api' ? [...COMMON_FIELDS, ...API_FIELDS] : COMMON_FIELDS;

  const verify = (file: File) => {
    if (file.size > 32 * 1024 * 1024) { setVerification('32 MiB 이하의 HWPX를 선택하세요.'); return; }
    setBusy(true); setVerification('');
    const reader = new FileReader();
    reader.onerror = () => { setBusy(false); setVerification('파일을 읽지 못했습니다.'); };
    reader.onload = async () => {
      try {
        const result = await parseAiGuideTemplate(String(reader.result).split(',')[1]);
        setVerification(`${result.title}: 본문·메타데이터 일치, ${result.dictionary.length}개 필드, 기관 확인 ${result.review_required.length}건 (${result.document_status})`);
      } catch (error) {
        setVerification(error instanceof Error ? error.message : '검증 실패');
      } finally { setBusy(false); }
    };
    reader.readAsDataURL(file);
  };

  return <div className="space-y-4 border-t border-subtle pt-4">
    <h4 className="ui-section-title">샘플 템플릿에 채울 기관 정보</h4>
    <p className="text-xs text-fg-muted">한국지역난방공사 샘플의 서식을 사용합니다. 기관명·태양광 수치·보간 설명은 자동 복사하지 않습니다. 빈 항목은 기관 확인 필요로 남고, 입력값은 사용자 제공 정보로 표시되며 템플릿 HWPX에 반영됩니다.</p>
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
      {metadataFields.map(([key, label]) => <label key={key} className="space-y-1">
        <span className="ui-label">{label}</span>
        <textarea className="ui-input w-full text-xs" rows={2} maxLength={4000}
          value={metadata[key] || ''} placeholder="기관 확인 필요"
          onChange={event => onMetadataChange({...metadata, [key]: event.target.value})} />
      </label>)}
    </div>
    <details className="rounded-xl border border-subtle p-3">
      <summary className="cursor-pointer text-sm font-semibold">전체 필드 설명·단위·코드 보완 ({fields.length}개)</summary>
      <p className="text-xs text-fg-muted my-2">무차원 항목은 단위에 ‘무차원’, 코드가 없으면 ‘해당 없음’을 명시할 수 있습니다.</p>
      <div className="space-y-3 max-h-[500px] overflow-auto">
        {fields.map(field => <div key={field.path} className="border-t border-subtle pt-2 space-y-2">
          <p className="text-xs font-mono break-all">{field.path} ({field.types.join(' | ')})</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {([['label', '표시명'], ['description', '설명·업무 의미'], ['unit', '단위'], ['codes', '코드·허용값']] as const).map(([key, label]) => <label key={key}>
              <span className="ui-label">{label}</span>
              <input className="ui-input w-full text-xs" maxLength={2000} value={annotations[field.path]?.[key] || ''}
                onChange={event => onAnnotationsChange({...annotations, [field.path]: {
                  ...(annotations[field.path] ?? {label: '', description: '', unit: '', codes: ''}), [key]: event.target.value,
                }})} />
            </label>)}
          </div>
        </div>)}
      </div>
    </details>
    <details className="rounded-xl border border-subtle p-3">
      <summary className="cursor-pointer text-sm font-semibold">생성한 HWPX 재파싱 확인</summary>
      <div className="mt-3">
        <UnifiedFileUploader title="생성한 가이드 HWPX 확인" accept=".hwpx" formatsHint="이 탭에서 생성한 템플릿 HWPX · 최대 32 MiB"
          isUploading={busy} onFilesSelected={files => files[0] && verify(files[0])} onError={setVerification} />
        {verification && <p className="mt-2 text-xs text-fg" role="status">{verification}</p>}
      </div>
    </details>
  </div>;
}
