/**
 * 파일명: WorkspaceNav.tsx
 * 경로: apps/web/src/components/WorkspaceNav.tsx
 * 목적: 주요 작업 영역 탭과 안내를 표시함
 * 작성자: 개발팀
 * 작성일: 2026-09-09
 * 수정일: 2026-09-16
 */
import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { ArrowLeftRight, Cpu, Database, HelpCircle, ShieldCheck, Sparkles, X } from 'lucide-react';

export type WorkbenchTab = 'pseudo' | 'synthetic' | 'dummy' | 'converter' | 'ai-guide';

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
    title: '데이터변환 (데이터 · 문서 · 스캔 이미지 OCR)',
    helpTitle: '데이터변환 설명 보기',
    Icon: ArrowLeftRight,
    description:
      'CSV, Excel, Parquet 등 이기종 데이터 변환, HWP, HWPX, Word(DOCX), PDF 사내 문서 서식 보존 변환 및 PNG, JPG, TIFF 스캔 이미지 고정밀 OCR 문자·표 구조 복원을 통합 지원합니다.',
  },
  {
    value: 'ai-guide',
    label: 'AI 가이드',
    title: 'AI 가이드 (파일 · API 데이터 친화 가이드 생성)',
    helpTitle: 'AI 가이드 설명 보기',
    Icon: Sparkles,
    description:
      'CSV(파일데이터) 및 JSON·XML(API데이터) 데이터를 분석하여 공공 AI 친화도 표준 평가, 대량 데이터 최적화 및 HWPX 공문서 서식 롤(Rule) 가이드를 자동 생성합니다.',
  },
] as const;

type NavItem = (typeof navItems)[number];

interface TooltipState {
  item: NavItem;
  rect: DOMRect;
}

export function WorkspaceNav({ activeTab, isWorkbenchActive, layout, onSelect }: WorkspaceNavProps) {
  const isMobile = layout === 'mobile';
  const [tooltipState, setTooltipState] = useState<TooltipState | null>(null);
  const closeTimerRef = React.useRef<number | null>(null);
  const tooltipRef = React.useRef<HTMLDivElement | null>(null);

  const clearCloseTimer = () => {
    if (closeTimerRef.current !== null) {
      window.clearTimeout(closeTimerRef.current);
      closeTimerRef.current = null;
    }
  };

  const scheduleClose = () => {
    clearCloseTimer();
    closeTimerRef.current = window.setTimeout(() => {
      setTooltipState(null);
    }, 120);
  };

  const handleMouseEnter = (item: NavItem, target: HTMLElement) => {
    clearCloseTimer();
    const rect = target.getBoundingClientRect();
    setTooltipState({ item, rect });
  };

  const handleMouseLeave = () => {
    scheduleClose();
  };

  const handleTooltipMouseEnter = () => {
    clearCloseTimer();
  };

  const handleTooltipMouseLeave = () => {
    scheduleClose();
  };

  useEffect(() => {
    if (!tooltipState) return;

    const handlePointerDown = (e: PointerEvent) => {
      if (tooltipRef.current && tooltipRef.current.contains(e.target as Node)) {
        return;
      }
      setTooltipState(null);
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setTooltipState(null);
      }
    };

    const handleScrollOrResize = () => {
      setTooltipState(null);
    };

    window.addEventListener('pointerdown', handlePointerDown);
    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('scroll', handleScrollOrResize, { passive: true });
    window.addEventListener('resize', handleScrollOrResize, { passive: true });

    return () => {
      window.removeEventListener('pointerdown', handlePointerDown);
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('scroll', handleScrollOrResize);
      window.removeEventListener('resize', handleScrollOrResize);
    };
  }, [tooltipState]);

  useEffect(() => {
    return () => {
      clearCloseTimer();
    };
  }, []);

  const wrapperClass = isMobile
    ? 'lg:hidden flex justify-center pt-0.5'
    : 'hidden lg:flex items-center justify-center flex-1 max-w-3xl mx-4';
  const buttonGap = isMobile ? 'gap-2 px-3 py-2' : 'gap-1.5 px-2 py-1.5';
  const labelClass = isMobile
    ? 'text-sm sm:text-base font-bold tracking-tight whitespace-nowrap'
    : 'text-xs sm:text-sm font-bold tracking-tight whitespace-nowrap';

  // 툴팁 위치 및 너비 계산 (화면 밖 삐져나감 100% 방지 클램핑)
  let tooltipLeft = 12;
  let tooltipTop = 0;
  let tooltipWidth = 340;
  let arrowLeft = 20;

  if (tooltipState && typeof window !== 'undefined') {
    const PADDING = 12; // 화면 좌우 최소 안전 여백
    const viewportWidth = window.innerWidth;
    tooltipWidth = Math.min(Math.max(viewportWidth - PADDING * 2, 240), 340);

    const iconCenterX = tooltipState.rect.left + tooltipState.rect.width / 2;
    const idealLeft = iconCenterX - tooltipWidth / 2;
    // 좌우 화면 밖으로 벗어나지 않도록 클램핑
    tooltipLeft = Math.max(PADDING, Math.min(idealLeft, viewportWidth - tooltipWidth - PADDING));
    tooltipTop = tooltipState.rect.bottom + 8;

    // 화살표가 ? 아이콘의 중심을 가리키도록 툴팁 내부 X좌표 계산 후 둥근 모서리 안으로 클램핑
    const rawArrowLeft = iconCenterX - tooltipLeft - 6;
    arrowLeft = Math.max(16, Math.min(rawArrowLeft, tooltipWidth - 28));
  }

  return (
    <div className={wrapperClass}>
      <div className="grid w-full max-w-4xl grid-cols-2 gap-1 rounded-xl border border-subtle bg-surface-muted p-1 shadow-xs sm:grid-cols-3 lg:grid-cols-5 lg:max-w-none">
        {navItems.map((item, index) => {
          const { value, label, Icon, helpTitle } = item;
          const selected = activeTab === value && isWorkbenchActive;
          const isLastItemMobile = isMobile && index === navItems.length - 1;
          const isTooltipActive = tooltipState?.item.value === value;

          return (
            <button
              key={value}
              onClick={() => onSelect(value)}
              aria-label={label}
              className={`group relative flex items-center justify-center rounded-lg transition-all cursor-pointer whitespace-nowrap ${buttonGap} ${
                isLastItemMobile ? 'col-span-2 sm:col-span-1' : ''
              } ${
                selected
                  ? 'bg-accent text-accent-fg shadow-sm font-bold'
                  : 'text-fg-muted hover:text-fg hover:bg-surface/60 font-medium'
              }`}
            >
              <Icon className="h-4 w-4 shrink-0" />
              <span className={labelClass}>{label}</span>

              <div className="relative ml-0.5 inline-flex items-center">
                <span
                  role="button"
                  tabIndex={0}
                  aria-label={helpTitle}
                  onClick={(event) => {
                    event.preventDefault();
                    event.stopPropagation();
                    clearCloseTimer();
                    const rect = event.currentTarget.getBoundingClientRect();
                    setTooltipState((prev) => (prev?.item.value === item.value ? null : { item, rect }));
                  }}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' || event.key === ' ') {
                      event.preventDefault();
                      event.stopPropagation();
                      clearCloseTimer();
                      const rect = event.currentTarget.getBoundingClientRect();
                      setTooltipState((prev) => (prev?.item.value === item.value ? null : { item, rect }));
                    }
                  }}
                  onMouseEnter={(event) => {
                    handleMouseEnter(item, event.currentTarget);
                  }}
                  onMouseLeave={handleMouseLeave}
                  className={`rounded-full p-1 transition-colors cursor-pointer ${
                    selected
                      ? 'text-accent-fg/80 hover:text-accent-fg hover:bg-white/10'
                      : isTooltipActive
                        ? 'text-accent bg-surface-hover'
                        : 'text-fg-muted hover:text-accent hover:bg-surface-hover'
                  }`}
                >
                  <HelpCircle className={isMobile ? 'h-4 w-4' : 'h-3.5 w-3.5'} />
                </span>
              </div>
            </button>
          );
        })}
      </div>

      {/* 포털 기반 화면 클램핑 반응형 툴팁 (데스크톱 및 모바일 전 화면에서 넘침 방지) */}
      {tooltipState &&
        typeof document !== 'undefined' &&
        createPortal(
          <div
            ref={tooltipRef}
            className="fixed z-[9999] transition-opacity animate-in fade-in zoom-in-95 duration-150"
            style={{
              top: `${tooltipTop}px`,
              left: `${tooltipLeft}px`,
              width: `${tooltipWidth}px`,
            }}
            onMouseEnter={handleTooltipMouseEnter}
            onMouseLeave={handleTooltipMouseLeave}
          >
            <div className="ui-tooltip-bubble relative rounded-xl p-4 shadow-2xl whitespace-normal break-keep">
              {/* Tooltip Arrow */}
              <div
                className="ui-tooltip-arrow absolute -top-1.5 h-3 w-3 rotate-45"
                style={{ left: `${arrowLeft}px` }}
              />

              {/* Tooltip Body */}
              <div className="relative z-10 space-y-2 text-left">
                <div className="tooltip-title flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 text-sm font-bold text-white min-w-0">
                    <tooltipState.item.Icon className="h-4 w-4 shrink-0 text-sky-400" />
                    <span className="truncate" style={{ color: '#ffffff', fontWeight: 700 }}>
                      {tooltipState.item.title}
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      setTooltipState(null);
                    }}
                    className="text-slate-400 hover:text-white p-0.5 rounded transition-colors cursor-pointer shrink-0 ml-1"
                    aria-label="툴팁 닫기"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </div>
                <p
                  className="tooltip-desc text-xs leading-relaxed break-keep break-words"
                  style={{ color: '#f8fafc', fontWeight: 400 }}
                >
                  {tooltipState.item.description}
                </p>
              </div>
            </div>
          </div>,
          document.body
        )}
    </div>
  );
}

