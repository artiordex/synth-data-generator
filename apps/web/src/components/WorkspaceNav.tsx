/**
 * 파일명: WorkspaceNav.tsx
 * 경로: apps/web/src/components/WorkspaceNav.tsx
 * 목적: 주요 작업 영역 탭과 안내를 표시함
 * 작성자: 개발팀
 * 작성일: 2026-09-09
 * 수정일: 2026-09-09
 */
import React from 'react';
import { ArrowLeftRight, Cpu, Database, HelpCircle, ShieldCheck } from 'lucide-react';

export type WorkbenchTab = 'pseudo' | 'synthetic' | 'dummy' | 'converter';

type WorkspaceNavProps = {
  activeTab: WorkbenchTab;
  isWorkbenchActive: boolean;
  layout: 'desktop' | 'mobile';
  onSelect: (tab: WorkbenchTab) => void;
};

const navItems = [
  {
    value: 'pseudo',
    label: '가명데이터',
    title: '가명데이터 (Pseudonymization)',
    helpTitle: '가명데이터 설명 보기',
    Icon: ShieldCheck,
    description:
      '이름, 전화번호, 주민번호 등 개인식별정보를 한국형 Faker 가명값 및 암호화 기법으로 치환합니다. 원본의 행 구조와 통계적 상관관계를 유지하면서 사내 분석·통계에 안전하게 활용합니다.',
  },
  {
    value: 'synthetic',
    label: '합성데이터',
    title: '합성데이터 (Synthetic Data)',
    helpTitle: '합성데이터 설명 보기',
    Icon: Cpu,
    description:
      'CTGAN, TVAE, Copula 등 AI 딥러닝 모델이 원본의 통계적 패턴과 상관관계만 학습하여 100% 새로 생성한 가상 데이터입니다. 실제 개인정보가 전혀 없어 사외 반출이나 AI 학습에 가장 안전합니다.',
  },
  {
    value: 'dummy',
    label: '더미데이터',
    title: '더미데이터 (Dummy Data)',
    helpTitle: '더미데이터 설명 보기',
    Icon: Database,
    description:
      '원본 데이터 없이도 사전에 정의된 규칙(인적사항, 결제정보, 주소 등)에 따라 시스템 개발, 기능 검증 및 QA 부하 테스트를 위해 즉시 대량으로 생성하는 모의 데이터입니다.',
  },
  {
    value: 'converter',
    label: '데이터변환',
    title: '데이터변환 (Data & Doc Converter)',
    helpTitle: '데이터변환 설명 보기',
    Icon: ArrowLeftRight,
    description:
      'CSV, Excel, Parquet, JSON, SQL 등 이기종 데이터 포맷 상호 변환 및 HWP, HWPX, Word(DOCX) 사내 문서를 원본 서식 그대로 PDF/HWPX로 고속 변환합니다.',
  },
] as const;

const desktopTooltip = ['left-0', 'left-1/2 -translate-x-1/2', 'left-1/2 -translate-x-1/2', 'right-0'];
const desktopArrow = ['left-5', 'left-1/2 -translate-x-1/2', 'left-1/2 -translate-x-1/2', 'right-5'];
const mobileTooltip = [
  'left-0 sm:left-1/2 sm:-translate-x-1/2',
  'left-1/2 -translate-x-1/2',
  'right-0 sm:right-auto sm:left-1/2 sm:-translate-x-1/2',
  'right-0 sm:right-auto sm:left-1/2 sm:-translate-x-1/2',
];
const mobileArrow = [
  'left-5 sm:left-1/2 sm:-translate-x-1/2',
  'left-1/2 -translate-x-1/2',
  'right-5 sm:right-auto sm:left-1/2 sm:-translate-x-1/2',
  'right-5 sm:right-auto sm:left-1/2 sm:-translate-x-1/2',
];

export function WorkspaceNav({ activeTab, isWorkbenchActive, layout, onSelect }: WorkspaceNavProps) {
  const isMobile = layout === 'mobile';
  const wrapperClass = isMobile
    ? 'lg:hidden flex justify-center pt-0.5'
    : 'hidden lg:flex items-center justify-center flex-1 max-w-2xl mx-4';
  const buttonGap = isMobile ? 'gap-2 px-3 py-2' : 'gap-1.5 px-2.5 py-1.5';
  const labelClass = isMobile
    ? 'text-sm sm:text-base font-bold tracking-tight'
    : 'text-xs sm:text-sm font-bold tracking-tight';
  const tooltipWidth = isMobile ? 'w-80 sm:w-96' : 'w-80';
  const tooltipPositions = isMobile ? mobileTooltip : desktopTooltip;
  const arrowPositions = isMobile ? mobileArrow : desktopArrow;

  return (
    <div className={wrapperClass}>
      <div className="grid w-full max-w-3xl grid-cols-2 gap-1 rounded-xl border border-subtle bg-surface-muted p-1 shadow-xs sm:grid-cols-4 lg:max-w-none">
        {navItems.map(({ value, label, title, helpTitle, Icon, description }, index) => {
          const selected = activeTab === value && isWorkbenchActive;
          return (
            <button
              key={value}
              onClick={() => onSelect(value)}
              aria-label={label}
              className={`group relative flex items-center justify-center rounded-lg transition-all cursor-pointer ${buttonGap} ${
                selected
                  ? 'bg-accent text-accent-fg shadow-sm font-bold'
                  : 'text-fg-muted hover:text-fg hover:bg-surface/60 font-medium'
              }`}
            >
              <Icon className="h-4 w-4 shrink-0" />
              <span className={labelClass}>{label}</span>

              <div className="relative group/tooltip ml-0.5 inline-flex items-center">
                <span
                  onClick={(event) => event.stopPropagation()}
                  className={`rounded-full p-0.5 transition-colors cursor-help ${
                    selected ? 'text-accent-fg/80 hover:text-accent-fg' : 'text-fg-muted hover:text-accent'
                  }`}
                  title={helpTitle}
                >
                  <HelpCircle className="h-3.5 w-3.5" />
                </span>

                <div className={`ui-tooltip-bubble pointer-events-none absolute top-full mt-2.5 hidden rounded-xl p-4 shadow-2xl z-50 group-hover/tooltip:block ${tooltipWidth} ${tooltipPositions[index]}`}>
                  <div className={`ui-tooltip-arrow absolute -top-1.5 h-3 w-3 rotate-45 ${arrowPositions[index]}`} />
                  <div className="relative z-10 space-y-2 text-left">
                    <div className="tooltip-title flex items-center gap-2 text-sm font-bold text-white">
                      <Icon className="h-4 w-4 shrink-0 text-sky-400" />
                      <span style={{ color: '#ffffff', fontWeight: 700 }}>{title}</span>
                    </div>
                    <p className="tooltip-desc text-xs leading-relaxed break-keep" style={{ color: '#f8fafc', fontWeight: 400 }}>
                      {description}
                    </p>
                  </div>
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
