/**
 * 파일명: SynthesisProjectSettings.tsx
 * 경로: apps/web/src/features/synthesis/SynthesisProjectSettings.tsx
 * 목적: 합성 프로젝트의 기관 및 작업 목적을 입력받음
 * 작성자: 개발팀
 * 작성일: 2026-09-29
 * 수정일: 2026-09-29
 */
import React from 'react';
import { Sliders } from 'lucide-react';
import { SectionHeader } from '../../components/SectionHeader';

type SynthesisProjectSettingsProps = {
  departmentName: string;
  setDepartmentName: (value: string) => void;
  projectPurpose: string;
  setProjectPurpose: (value: string) => void;
  targetRows: number;
  setTargetRows: (value: number) => void;
  qualityThreshold: number;
  setQualityThreshold: (value: number) => void;
};

/** 합성 작업에 필요한 프로젝트 정보를 편집함 */
export function SynthesisProjectSettings({
  departmentName,
  setDepartmentName,
  projectPurpose,
  setProjectPurpose,
  targetRows,
  setTargetRows,
  qualityThreshold,
  setQualityThreshold,
}: SynthesisProjectSettingsProps) {
  return (
    <section className="ui-panel space-y-4 p-6">
      <SectionHeader title="프로젝트 및 합성 대상 정보" Icon={Sliders} />
      <div className="space-y-3">
        <div>
          <label className="ui-label">담당 부서명</label>
          <input
            type="text"
            value={departmentName}
            onChange={(event) => setDepartmentName(event.target.value)}
            className="ui-field"
          />
        </div>
        <div>
          <label className="ui-label">연구 및 심의 목적</label>
          <input
            type="text"
            value={projectPurpose}
            onChange={(event) => setProjectPurpose(event.target.value)}
            className="ui-field"
          />
        </div>
        <div>
          <label className="ui-label">합성 생성 행 수 (Target Rows)</label>
          <input
            type="number"
            value={targetRows}
            onChange={(event) => setTargetRows(Number(event.target.value))}
            className="ui-field"
          />
        </div>
        <div>
          <label className="ui-label">심의 통과 품질 임계점 (기준 80점)</label>
          <input
            type="number"
            step="0.05"
            min="0.5"
            max="0.99"
            value={qualityThreshold}
            onChange={(event) => setQualityThreshold(Number(event.target.value))}
            className="ui-field"
          />
        </div>
      </div>
    </section>
  );
}
