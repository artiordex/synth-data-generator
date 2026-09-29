/**
 * 파일명: AdvancedSynthesisColumnTable.tsx
 * 경로: apps/web/src/features/synthesis/AdvancedSynthesisColumnTable.tsx
 * 목적: 합성 데이터 컬럼의 민감도와 입력 규칙을 편집함
 * 작성자: 개발팀
 * 작성일: 2026-09-29
 * 수정일: 2026-09-29
 */
import React from 'react';
import { DatasetProfile, InformationType, ReviewMetadataInput } from '../../types';
import { SynthesisOptions } from './AdvancedSynthesisSettings';

const informationTypes: InformationType[] = ['준식별자', '일반정보'];

type AdvancedSynthesisColumnTableProps = {
  options: SynthesisOptions;
  onChange: (value: SynthesisOptions) => void;
  profile: DatasetProfile | null;
  isDarkMode: boolean;
  reviewMetadata?: ReviewMetadataInput;
  onReviewMetadataChange?: (value: ReviewMetadataInput) => void;
};

/** 컬럼별 합성 설정을 표 형태로 편집함 */
export function AdvancedSynthesisColumnTable({
  options,
  onChange,
  profile,
  isDarkMode,
  reviewMetadata,
  onReviewMetadataChange,
}: AdvancedSynthesisColumnTableProps) {
  const columns = profile?.columns.filter((column) => !column.pii_detected) || [];
  const categoricalColumns = options.categorical_columns ?? profile?.suggested_categorical ?? [];
  const numericalColumns = options.numerical_columns ?? profile?.suggested_numerical ?? [];
  const fieldStyle = `rounded border p-2 ${isDarkMode ? 'bg-slate-950 border-slate-700' : 'bg-white border-slate-300'}`;

  // 컬럼을 지정한 설정 목록에 추가하거나 제거함
  const toggleColumn = (key: 'preserve_null_columns' | 'evaluation_excluded_columns', name: string, selected: boolean) => {
    onChange({
      ...options,
      [key]: selected ? [...(options[key] || []), name] : (options[key] || []).filter((column) => column !== name),
    });
  };

  // 담당자가 확인한 컬럼 정보 유형을 메타데이터에 반영함
  const updateInformationType = (name: string, informationType: InformationType) => {
    if (!onReviewMetadataChange) return;
    const previousColumn = reviewMetadata?.columns?.[name] || {};
    onReviewMetadataChange({
      ...reviewMetadata,
      columns: {
        ...(reviewMetadata?.columns || {}),
        [name]: { ...previousColumn, information_type: informationType },
      },
    });
  };

  return (
    <div className="max-h-96 overflow-auto">
      <table className="w-full min-w-[1120px] text-left text-xs">
        <thead>
          <tr>
            <th className="w-[22%] p-2">항목</th>
            <th className="w-[12%]">학습 유형</th>
            <th className="w-[13%]">정보영역</th>
            <th className="w-[37%]">고유값 미리보기</th>
            <th className="w-[8%] text-center">결측 의미 보존</th>
            <th className="w-[8%] text-center">평가 제외</th>
          </tr>
        </thead>
        <tbody>
          {columns.map((column) => {
            const values = column.samples || [];
            const selectedInformationType = (
              reviewMetadata?.columns?.[column.name]?.information_type
              || column.information_type
              || '일반정보'
            ) as InformationType;

            return (
              <tr key={column.name} className="align-top border-t border-slate-300/30">
                <td className="p-2 font-medium">{column.name}</td>
                <td className="py-2 pr-2">
                  <select
                    aria-label={`${column.name} 학습 유형`}
                    className={fieldStyle}
                    value={numericalColumns.includes(column.name) ? 'numerical' : 'categorical'}
                    onChange={(event) => onChange({
                      ...options,
                      categorical_columns: [
                        ...categoricalColumns.filter((name) => name !== column.name),
                        ...(event.target.value === 'categorical' ? [column.name] : []),
                      ],
                      numerical_columns: [
                        ...numericalColumns.filter((name) => name !== column.name),
                        ...(event.target.value === 'numerical' ? [column.name] : []),
                      ],
                    })}
                  >
                    <option value="categorical">범주형</option>
                    <option value="numerical">수치형</option>
                  </select>
                </td>
                <td className="py-2 pr-2">
                  <select
                    aria-label={`${column.name} 정보영역`}
                    className={fieldStyle}
                    value={informationTypes.includes(selectedInformationType) ? selectedInformationType : '일반정보'}
                    onChange={(event) => updateInformationType(column.name, event.target.value as InformationType)}
                    disabled={!onReviewMetadataChange}
                  >
                    <option value="준식별자">준식별자</option>
                    <option value="일반정보">일반정보</option>
                  </select>
                </td>
                <td className="py-2 pr-3">
                  <div className={`max-h-20 overflow-y-auto rounded border p-2 ${isDarkMode ? 'border-slate-800 bg-slate-950/70' : 'border-slate-200 bg-slate-50'}`}>
                    <div className="mb-1 text-2xs text-slate-500">
                      고유값 {(column.unique_values_total ?? column.unique_count).toLocaleString()}개
                      {column.samples_truncated ? ` · 상위 ${values.length.toLocaleString()}개 표시` : ''}
                    </div>
                    {values.length ? (
                      <div className="flex flex-wrap gap-1">
                        {values.map((value, index) => (
                          <span
                            key={`${column.name}-${value}-${index}`}
                            className={`max-w-full rounded px-1.5 py-0.5 text-2xs leading-5 ${isDarkMode ? 'bg-slate-800 text-slate-200' : 'border border-slate-200 bg-white text-slate-700'}`}
                            title={value}
                          >
                            {value}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="text-2xs text-slate-400">표시할 값 없음</span>
                    )}
                  </div>
                </td>
                <td className="py-3 text-center">
                  <input
                    aria-label={`${column.name} 결측 의미 보존`}
                    type="checkbox"
                    checked={options.preserve_null_columns?.includes(column.name) ?? false}
                    onChange={(event) => toggleColumn('preserve_null_columns', column.name, event.target.checked)}
                  />
                </td>
                <td className="py-3 text-center">
                  <input
                    aria-label={`${column.name} 평가 제외`}
                    type="checkbox"
                    checked={options.evaluation_excluded_columns?.includes(column.name) ?? false}
                    onChange={(event) => toggleColumn('evaluation_excluded_columns', column.name, event.target.checked)}
                  />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
