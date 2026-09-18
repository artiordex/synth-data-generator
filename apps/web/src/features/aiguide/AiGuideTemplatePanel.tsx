/**
 * 파일명: AiGuideTemplatePanel.tsx
 * 경로: apps/web/src/features/aiguide/AiGuideTemplatePanel.tsx
 * 목적: AI-Ready 보고서 템플릿 메타데이터 및 필드 주석 설정을 관리함
 * 작성자: 개발팀
 * 작성일: 2026-09-16
 * 수정일: 2026-09-16
 */
import React from 'react';
import { AiGuideFieldAnnotation } from '../../services/api';
import { TaxonomySelects } from './TaxonomySelects';
import { UPDATE_FREQUENCY_OPTIONS } from './AiRuleGuideStudio';

const INSTITUTION_FIELDS = [
  ['publisher', '제공기관'], ['creator', '소관부서'], ['contact_name', '담당자 연락처 / 이메일'],
] as const;
const AI_SUGGESTED_FIELDS = [
  ['description', '데이터 설명 (대상·범위·구조·주요 내용)'], ['purpose', '구축·개방 목적 (배경·활용·공공적 가치)'], ['keywords', '검색 키워드'],
  ['theme_label', '주제 분류명'], ['language', '언어 코드'], ['media_type', 'MIME 유형'],
  ['update_frequency', '갱신주기'], ['spatial', '공간·대상 범위'],
  ['collection_process', '수집 방법'], ['limitations', '대표성·편향·이용 한계 및 주의사항'],
] as const;
const LONG_FORM_FIELDS = new Set(['description', 'purpose', 'limitations', 'collection_process']);
const OPTIONAL_CONFIRMATION_FIELDS = [
  ['identifier', '공식 데이터셋 식별자'], ['legal_basis', '관련법령·근거'],
  ['landing_page', '대표 공개 페이지 URL'], ['access_url', '파일/API 접근 URL'],
  ['license', '라이선스·이용조건'], ['rights', '저작권·외부 데이터 권리'],
  ['access_rights', '접근 권한·제한'], ['attribution', '출처 표기 문구'],
  ['contains_pii', '개인정보 포함 여부'], ['anonymization_method', '비식별화 방법'],
] as const;
const API_FIELDS = [
  ['endpoint', 'API 기본 URL·경로'], ['http_method', 'HTTP method'], ['authentication_type', '인증 유형'],
  ['authentication', '인증 방식 설명 (실제 키 입력 금지)'], ['specification_url', 'OpenAPI·계약 명세 URL'],
  ['api_version', 'API 버전'], ['rate_limit', '호출 제한'],
  ['request_parameters', '요청 파라미터·필수·기본값'], ['pagination', '페이지네이션·호출 제한'],
  ['error_codes', '오류 코드·재시도'], ['response_path', '업무 레코드 경로'],
] as const;

interface Props {
  canonical: Record<string, unknown> | null;
  metadata: Record<string, string>;
  onMetadataChange: (value: Record<string, string>) => void;
  annotations: Record<string, AiGuideFieldAnnotation>;
  onAnnotationsChange: (value: Record<string, AiGuideFieldAnnotation>) => void;
}

function visibleFieldName(field: {path: string; name?: string}) {
  if (field.name?.trim()) return field.name.trim();
  const pathParts = field.path.split('/').filter(part => part && part !== '*');
  const leaf = pathParts[pathParts.length - 1] || field.path;
  return leaf.replace(/~1/g, '/').replace(/~0/g, '~');
}

// AI 가이드 템플릿 메타데이터 및 필드 주석 편집 패널 컴포넌트임
export function AiGuideTemplatePanel({canonical, metadata, onMetadataChange, annotations, onAnnotationsChange}: Props) {
  const fields = ((canonical?.fields ?? []) as {path: string; name?: string; types?: string[]; data_type?: string}[])
    .map(field => ({...field, types: field.types ?? String(field.data_type ?? '').split(' | ').filter(Boolean)}))
    .filter(field => field.types.some(type => !['object', 'array'].includes(type)));
  const structure = canonical?.structure as {data_category?: string} | undefined;
  const category = canonical?.data_category ?? structure?.data_category;
  const isApi = category === 'api' || category === 'hybrid';

  const baseInputStyle =
    'w-full bg-surface-muted/20 hover:bg-surface-muted/40 focus:bg-surface border border-subtle/60 focus:border-accent rounded px-2.5 py-1.5 text-xs text-fg font-medium outline-none transition-colors';
  const baseSelectStyle =
    'w-full bg-surface-muted/20 hover:bg-surface-muted/40 focus:bg-surface border border-subtle/60 focus:border-accent rounded px-2.5 py-1.5 text-xs text-fg font-medium outline-none transition-colors cursor-pointer';

  const metadataInputs = (items: ReadonlyArray<readonly [string, string]>, placeholder: string) =>
    items.map(([key, label]) => {
      const isLong = LONG_FORM_FIELDS.has(key);

      let control: React.ReactNode;

      if (key === 'theme_label') {
        control = (
          <TaxonomySelects
            value={metadata[key] || ''}
            onChange={val => onMetadataChange({...metadata, [key]: val})}
          />
        );
      } else if (key === 'update_frequency') {
        const currentOption = UPDATE_FREQUENCY_OPTIONS.find(
          opt => opt.value === metadata[key] || opt.label === metadata[key]
        );
        const currentVal = currentOption ? currentOption.value : (metadata[key] ? 'OTHER' : 'DAILY_OR_MORE');
        const isCustom = currentVal === 'OTHER' || (
          metadata[key] && !UPDATE_FREQUENCY_OPTIONS.some(opt => opt.value !== 'OTHER' && (opt.value === metadata[key] || opt.label === metadata[key]))
        );
        control = (
          <div className="flex flex-col gap-1.5">
            <select
              value={currentVal}
              onChange={event => {
                const sel = event.target.value;
                const matched = UPDATE_FREQUENCY_OPTIONS.find(o => o.value === sel);
                if (matched && matched.value !== 'OTHER') {
                  onMetadataChange({ ...metadata, [key]: matched.label });
                } else {
                  onMetadataChange({ ...metadata, [key]: '기타' });
                }
              }}
              className={baseSelectStyle}
            >
              {UPDATE_FREQUENCY_OPTIONS.map(item => (
                <option key={item.value} value={item.value} className="bg-surface text-fg">
                  {item.label}
                </option>
              ))}
            </select>
            {isCustom && (
              <input
                type="text"
                value={metadata[key] === '기타' ? '' : (metadata[key] || '')}
                onChange={event => onMetadataChange({ ...metadata, [key]: event.target.value || '기타' })}
                className={baseInputStyle}
                placeholder="주기를 직접 입력하세요 (예: 1시간 주기 자동 계측 수집)"
              />
            )}
          </div>
        );
      } else if (isLong) {
        control = (
          <textarea
            className={`${baseInputStyle} resize-y`}
            rows={5}
            maxLength={8000}
            value={metadata[key] || ''}
            placeholder={placeholder}
            onChange={event => onMetadataChange({...metadata, [key]: event.target.value})}
          />
        );
      } else {
        control = (
          <input
            type="text"
            className={baseInputStyle}
            maxLength={4000}
            value={metadata[key] || ''}
            placeholder={placeholder}
            onChange={event => onMetadataChange({...metadata, [key]: event.target.value})}
          />
        );
      }

      return (
        <div key={key} className={`grid grid-cols-12 ${isLong ? 'items-start' : 'items-center'} gap-2`}>
          <span className={`col-span-4 font-bold text-fg shrink-0 text-xs break-keep leading-snug ${isLong ? 'pt-1.5' : ''}`}>
            {label}
          </span>
          <div className="col-span-8">
            {control}
          </div>
        </div>
      );
    });

  return <div className="space-y-4 border-t border-subtle pt-4">
    <h4 className="ui-section-title">기관 확인 정보 수정</h4>
    <p className="text-xs text-fg-muted">1단계에서 입력한 기관 정보를 확인하고 필요한 경우 수정하세요.</p>
    <div className="grid grid-cols-1 md:grid-cols-2 items-center gap-x-8 gap-y-3">
      {metadataInputs(INSTITUTION_FIELDS, '기관 확인 필요')}
    </div>
    <details open className="rounded border border-subtle p-3">
      <summary className="cursor-pointer text-sm font-semibold mb-3">가이드 내용 수정</summary>
      <div className="grid grid-cols-1 md:grid-cols-2 items-start gap-x-8 gap-y-3 mt-3">
        {metadataInputs(AI_SUGGESTED_FIELDS, 'AI 추천 없음')}
      </div>
    </details>
    <details open className="rounded border border-subtle p-3">
      <summary className="cursor-pointer text-sm font-semibold">필드명·설명 수정 ({fields.length}개)</summary>
      <div className="mt-3 border border-subtle rounded overflow-hidden bg-surface shadow-xs">
        <div className="max-h-[560px] overflow-auto">
          <table className="w-full text-xs text-left border-collapse">
            <thead className="sticky top-0 z-10 bg-surface-muted border-b border-subtle text-fg-muted font-bold text-2xs">
              <tr>
                <th scope="col" className="py-2.5 px-3 text-center w-12 shrink-0">No</th>
                <th scope="col" className="py-2.5 px-3 w-28 shrink-0">데이터 타입</th>
                <th scope="col" className="py-2.5 px-3 min-w-[130px] w-36">한글 표시명</th>
                <th scope="col" className="py-2.5 px-3 min-w-[140px] w-40">영문 컬럼명 (lowerCamelCase)</th>
                <th scope="col" className="py-2.5 px-3 min-w-[200px]">설명·업무 의미</th>
                <th scope="col" className="py-2.5 px-3 min-w-[80px] w-24 text-center">단위</th>
                <th scope="col" className="py-2.5 px-3 min-w-[130px] w-36">도메인</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-subtle bg-surface">
              {fields.map((field, idx) => {
                const primaryType = (() => {
                  const raw = (field.types[0] ?? 'string').toLowerCase();
                  if (raw.includes('int') || raw === 'long') return 'integer';
                  if (raw.includes('float') || raw.includes('double') || raw === 'decimal') return 'numeric';
                  if (raw.includes('num') || raw === 'number') return 'numeric';
                  if (raw === 'bool' || raw === 'boolean') return 'boolean';
                  if (raw === 'date') return 'date';
                  if (raw.includes('datetime') || raw.includes('timestamp')) return 'datetime';
                  if (raw === 'json' || raw === 'object') return 'json';
                  if (raw === 'text') return 'text';
                  if (raw.includes('char') || raw.includes('varchar')) return 'varchar';
                  return 'varchar';
                })();
                const DATA_TYPES = ['varchar', 'char', 'text', 'integer', 'bigint', 'numeric', 'float', 'boolean', 'date', 'datetime', 'json', '기타'] as const;

                const fieldAnn = annotations[field.path] ?? {english_name: '', label: '', description: '', unit: '', codes: ''};
                const selectedType = (annotations[field.path] as any)?.data_type ?? primaryType;
                const defaultLabel = visibleFieldName(field);

                const handleChange = (key: keyof AiGuideFieldAnnotation | 'data_type', val: string) => {
                  const existing = annotations[field.path] ?? {english_name: '', label: defaultLabel, description: '', unit: '', codes: ''};
                  onAnnotationsChange({
                    ...annotations,
                    [field.path]: { ...existing, [key]: val },
                  });
                };

                return (
                  <tr key={field.path} className="hover:bg-surface-muted/40 transition-colors">
                    {/* 1. No */}
                    <td className="py-2 px-3 text-center text-fg-muted font-mono font-medium">{idx + 1}</td>

                    {/* 2. 데이터 타입 */}
                    <td className="py-1 px-2">
                      <select
                        className="w-full text-xs px-2 py-1.5 rounded bg-surface border border-subtle hover:border-accent/40 focus:border-accent focus:outline-none transition-colors font-mono text-fg"
                        value={selectedType}
                        onChange={e => handleChange('data_type', e.target.value)}
                      >
                        {DATA_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                      </select>
                    </td>

                    {/* 3. 한글 표시명 */}
                    <td className="py-1 px-2">
                      <input
                        type="text"
                        className="w-full text-xs px-2.5 py-1.5 rounded bg-surface border border-subtle hover:border-accent/40 focus:border-accent focus:bg-surface focus:outline-none transition-colors font-medium text-fg"
                        placeholder={defaultLabel}
                        value={fieldAnn.label !== undefined ? fieldAnn.label : defaultLabel}
                        onChange={e => handleChange('label', e.target.value)}
                      />
                    </td>

                    {/* 4. 영문 컬럼명 */}
                    <td className="py-1 px-2">
                      <input
                        type="text"
                        className="w-full text-xs px-2.5 py-1.5 rounded bg-surface border border-subtle hover:border-accent/40 focus:border-accent focus:bg-surface focus:outline-none transition-colors font-mono text-fg"
                        placeholder="lowerCamelCase"
                        maxLength={64}
                        value={fieldAnn.english_name || ''}
                        onChange={e => handleChange('english_name', e.target.value)}
                      />
                    </td>

                    {/* 5. 설명·업무 의미 */}
                    <td className="py-1 px-2">
                      <input
                        type="text"
                        className="w-full text-xs px-2.5 py-1.5 rounded bg-surface border border-subtle hover:border-accent/40 focus:border-accent focus:bg-surface focus:outline-none transition-colors text-fg"
                        placeholder="업무 의미·설명 입력"
                        maxLength={2000}
                        value={fieldAnn.description || ''}
                        onChange={e => handleChange('description', e.target.value)}
                      />
                    </td>

                    {/* 6. 단위 */}
                    <td className="py-1 px-2">
                      <input
                        type="text"
                        className="w-full text-xs px-2.5 py-1.5 rounded bg-surface border border-subtle hover:border-accent/40 focus:border-accent focus:bg-surface focus:outline-none transition-colors text-fg text-center"
                        placeholder="-"
                        maxLength={100}
                        value={fieldAnn.unit || ''}
                        onChange={e => handleChange('unit', e.target.value)}
                      />
                    </td>

                    {/* 7. 도메인 */}
                    <td className="py-1 px-2">
                      <input
                        type="text"
                        className="w-full text-xs px-2.5 py-1.5 rounded bg-surface border border-subtle hover:border-accent/40 focus:border-accent focus:bg-surface focus:outline-none transition-colors text-fg"
                        placeholder="-"
                        maxLength={1000}
                        value={fieldAnn.codes || ''}
                        onChange={e => handleChange('codes', e.target.value)}
                      />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </details>
    <details className="rounded border border-subtle p-3">
      <summary className="cursor-pointer text-sm font-semibold mb-2">추가 기관 확인 정보</summary>
      <p className="text-xs text-fg-muted mb-3">법령·라이선스·URL과 API 계약처럼 데이터만으로 확정할 수 없는 항목이 있을 때만 입력하세요.</p>
      <div className="grid grid-cols-1 md:grid-cols-2 items-center gap-x-8 gap-y-3">
        {metadataInputs(OPTIONAL_CONFIRMATION_FIELDS, '필요한 경우 입력')}
        {isApi && metadataInputs(API_FIELDS, 'API 운영기관 확인 필요')}
      </div>
    </details>
  </div>;
}
