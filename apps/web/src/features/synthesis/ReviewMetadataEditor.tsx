/**
 * 파일명: ReviewMetadataEditor.tsx
 * 경로: apps/web/src/features/synthesis/ReviewMetadataEditor.tsx
 * 목적: 심의용 합성 데이터 메타데이터를 편집함
 * 작성자: 개발팀
 * 작성일: 2026-09-29
 * 수정일: 2026-09-29
 */
import React from 'react';
import { ReviewMetadataInput } from '../../types';
import { SectionHeader } from '../../components/SectionHeader';

const reviewFields: Array<[
  keyof Pick<ReviewMetadataInput, 'dataset_name' | 'special_notes' | 'overview' | 'privacy_plan'>,
  string,
  string,
]> = [
  ['dataset_name', '데이터명', '비워두면 파일명 사용'],
  ['special_notes', '특이사항', '희소 항목, 수집상 유의사항 등'],
  ['overview', '정보 개요', '수집 출처, 기간, 배경, 정보 설명'],
  ['privacy_plan', '개인정보 처리계획', '보유기간, 접근권한, 제공범위, 파기절차'],
];

type ReviewMetadataEditorProps = {
  reviewMetadata: ReviewMetadataInput;
  setReviewMetadata: (value: ReviewMetadataInput) => void;
};

/** 심의 문서에 사용할 메타데이터를 입력받음 */
export function ReviewMetadataEditor({ reviewMetadata, setReviewMetadata }: ReviewMetadataEditorProps) {
  return (
    <section className="ui-panel space-y-4 p-6">
      <SectionHeader
        title="심의자료 한글 문서 입력"
        description="데이터 규모·전체 항목·결측 현황·처리방법·측정결과는 자동 입력됩니다. 아래 내용은 문서에 함께 반영되며, 미입력 사항은 자동 분석 또는 담당자 확인 필요로 표시됩니다."
      />
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {reviewFields.map(([key, label, placeholder]) => (
          <label key={key} className="block text-xs font-semibold">
            {label}
            <textarea
              value={reviewMetadata[key] || ''}
              placeholder={placeholder}
              rows={3}
              onChange={(event) => setReviewMetadata({ ...reviewMetadata, [key]: event.target.value })}
              className="ui-field mt-1"
            />
          </label>
        ))}
      </div>
      <p className="text-xs">원본 예시는 값 비공개 상태로 구조와 결측 여부를 표시합니다. HWPX 문서 3종과 HTML 확인본을 ZIP에 포함합니다.</p>
    </section>
  );
}
