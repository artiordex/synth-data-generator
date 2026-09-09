/**
 * 파일명: DataDictionaryView.tsx
 * 경로: apps/web/src/features/dictionary/DataDictionaryView.tsx
 * 목적: 데이터 용어사전 화면을 표시함
 * 작성자: 개발팀
 * 작성일: 2026-09-09
 * 수정일: 2026-09-09
 */
import React, { useState, useMemo } from 'react';
import { 
  BookOpen, 
  Search, 
  X, 
  Cpu, 
  Shield, 
  BrainCircuit, 
  Layers, 
  Briefcase, 
  Bot,
  Filter,
  ChevronRight
} from 'lucide-react';
import { 
  GLOSSARY_DATA, 
  GLOSSARY_CATEGORIES, 
  GlossaryItem, 
  GlossaryCategory 
} from './flowhuntGlossaryData';
import { WorkspaceHeader } from '../../components/WorkspaceHeader';

interface Props {
  onBack: () => void;
  isDarkMode?: boolean;
  onStepChange?: (step: number) => void;
}

const INITIAL_GROUPS = [
  '전체',
  'ㄱ', 'ㄴ', 'ㄷ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅅ', 'ㅇ', 'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ',
  'A-Z', '0-9'
] as const;

const CATEGORY_ICON_MAP: Record<string, React.ElementType> = {
  '머신러닝 & 딥러닝': Cpu,
  '자연어 & 멀티모달': BrainCircuit,
  'LLM & 생성형 AI': Layers,
  '보안 & 프라이버시': Shield,
  '비즈니스 AI & 자동화': Briefcase,
  'AI 에이전트 & RAG': Bot,
};

export const DataDictionaryView: React.FC<Props> = ({ onBack, isDarkMode = false, onStepChange }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<GlossaryCategory>('전체');
  const [selectedInitial, setSelectedInitial] = useState<string>('전체');
  const [activeItem, setActiveItem] = useState<GlossaryItem | null>(null);

  React.useEffect(() => {
    const hasFilter = Boolean(searchTerm.trim()) || selectedCategory !== '전체' || selectedInitial !== '전체';
    onStepChange?.(activeItem ? 3 : hasFilter ? 2 : 1);
  }, [activeItem, onStepChange, searchTerm, selectedCategory, selectedInitial]);

  // Filtered terms
  const filteredTerms = useMemo(() => {
    return GLOSSARY_DATA.filter(item => {
      // Search term filter
      if (searchTerm.trim()) {
        const query = searchTerm.toLowerCase();
        const matchName = item.name.toLowerCase().includes(query);
        const matchDesc = item.description.toLowerCase().includes(query);
        if (!matchName && !matchDesc) return false;
      }

      // Category filter
      if (selectedCategory !== '전체' && item.category !== selectedCategory) {
        return false;
      }

      // Initial filter
      if (selectedInitial !== '전체') {
        if (selectedInitial === 'A-Z') {
          const first = item.name.trim().charAt(0).toUpperCase();
          if (first < 'A' || first > 'Z') return false;
        } else if (selectedInitial === '0-9') {
          const first = item.name.trim().charAt(0);
          if (first < '0' || first > '9') return false;
        } else {
          if (item.initial !== selectedInitial) return false;
        }
      }

      return true;
    });
  }, [searchTerm, selectedCategory, selectedInitial]);

  // Counts by category
  const categoryCounts = useMemo(() => {
    const map: Record<string, number> = { '전체': GLOSSARY_DATA.length };
    GLOSSARY_DATA.forEach(t => {
      map[t.category] = (map[t.category] || 0) + 1;
    });
    return map;
  }, []);

  return (
    <div className="space-y-4 sm:space-y-6 animate-fade-in">
      {/* Unified Workspace Header with Actions */}
      <WorkspaceHeader
        eyebrow="DICTIONARY WORKSPACE"
        title="데이터 용어사전"
        description="인공지능, 통계 가설 검정, OCR·문서 복원, 개인정보 비식별화 및 합성데이터 공식 표준 용어집"
        icon={BookOpen}
        badge={
          <span className="text-2xs font-semibold px-2 py-0.5 rounded-full border border-subtle bg-surface-muted text-fg-muted font-mono">
            총 {GLOSSARY_DATA.length}개 용어
          </span>
        }
        actions={
          <div className="flex items-center gap-2 flex-wrap">
            {/* 카테고리 필터 셀렉트 박스 */}
            <div className="flex items-center gap-1.5 bg-surface-muted border border-subtle rounded-lg px-2.5 py-1.5">
              <Filter className="w-3.5 h-3.5 text-accent shrink-0" />
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value as GlossaryCategory)}
                aria-label="용어 카테고리 선택"
                className="bg-transparent text-xs font-bold text-fg focus:outline-none cursor-pointer border-none pr-1"
              >
                {GLOSSARY_CATEGORIES.map(cat => (
                  <option key={cat} value={cat}>
                    {cat} ({categoryCounts[cat] || 0})
                  </option>
                ))}
              </select>
            </div>
          </div>
        }
      />

      {/* Search & Filter Toolbar */}
      <div className="flex flex-col gap-3 rounded-2xl border border-subtle bg-surface p-3.5 sm:p-5 shadow-xs">
        {/* Search Bar & Result Count */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 sm:gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-fg-muted" />
            <input
              type="text"
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              placeholder="용어명 또는 설명 검색 (예: RAG, 가명화, CTGAN, TVAE, 프롬프트, Anonymeter...)"
              className="ui-field w-full py-2 pl-10 pr-9 text-xs sm:text-sm"
            />
            {searchTerm && (
              <button
                onClick={() => setSearchTerm('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-fg-muted hover:text-fg cursor-pointer"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          <div className="text-xs font-semibold text-fg-muted whitespace-nowrap self-end sm:self-center">
            검색 결과: <span className="text-accent font-bold">{filteredTerms.length}</span>건
          </div>
        </div>

        {/* Category Tabs (Horizontally Scrollable on Mobile) */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-none text-xs">
          {GLOSSARY_CATEGORIES.map(cat => {
            const isSelected = selectedCategory === cat;
            const count = categoryCounts[cat] || 0;
            const Icon = cat !== '전체' ? CATEGORY_ICON_MAP[cat] : Filter;

            return (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium whitespace-nowrap transition-all border shrink-0 cursor-pointer ${
                  isSelected
                    ? 'bg-accent text-accent-fg border-accent shadow-xs font-semibold'
                    : 'bg-surface-muted text-fg-muted border-subtle hover:bg-surface hover:text-fg'
                }`}
              >
                {Icon && <Icon className="w-3.5 h-3.5" />}
                <span>{cat}</span>
                <span className={`text-2xs px-1.5 py-0.2 rounded-full font-bold ${
                  isSelected
                    ? 'bg-accent-fg/20 text-accent-fg'
                    : 'bg-surface text-fg-muted'
                }`}>
                  {count}
                </span>
              </button>
            );
          })}
        </div>

        {/* Initial Hangul / Alphabet Index (Horizontally Scrollable) */}
        <div className="flex items-center gap-1 overflow-x-auto pb-0.5 text-2xs font-semibold scrollbar-none">
          <span className="text-fg-muted mr-1 text-2xs shrink-0 select-none">색인:</span>
          {INITIAL_GROUPS.map(init => {
            const isSel = selectedInitial === init;
            return (
              <button
                key={init}
                onClick={() => setSelectedInitial(init)}
                className={`px-2 py-0.5 rounded transition-all shrink-0 cursor-pointer ${
                  isSel
                    ? 'bg-accent text-accent-fg font-bold'
                    : 'text-fg-muted hover:text-fg hover:bg-surface-muted'
                }`}
              >
                {init}
              </button>
            );
          })}
        </div>
      </div>

      {/* Grid of Terms */}
      {filteredTerms.length === 0 ? (
        <div className="rounded-2xl border border-subtle bg-surface p-12 text-center flex flex-col items-center justify-center">
          <div className="w-12 h-12 rounded-2xl bg-surface-muted border border-subtle flex items-center justify-center text-fg-muted mb-3">
            <Search className="w-6 h-6" />
          </div>
          <p className="font-semibold text-sm text-fg">
            검색 조건에 맞는 용어가 없습니다
          </p>
          <p className="text-xs text-fg-muted mt-1 max-w-sm">
            다른 검색어를 입력하시거나 카테고리/초성 필터를 '전체'로 재설정해 보세요.
          </p>
          <button
            onClick={() => {
              setSearchTerm('');
              setSelectedCategory('전체');
              setSelectedInitial('전체');
            }}
            className="ui-button-primary mt-4 px-3.5 py-1.5 text-xs cursor-pointer"
          >
            필터 전체 초기화
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
          {filteredTerms.map(item => {
            const Icon = CATEGORY_ICON_MAP[item.category] || BookOpen;

            return (
              <div
                key={item.id}
                onClick={() => setActiveItem(item)}
                className="group relative flex flex-col justify-between p-4 rounded-xl border border-subtle bg-surface hover:border-accent/40 hover:bg-surface-muted/30 transition-all cursor-pointer shadow-xs hover:shadow-sm"
              >
                <div>
                  {/* Top Badges */}
                  <div className="flex items-center justify-between gap-2 mb-2">
                    <span className="inline-flex items-center gap-1 text-2xs font-semibold px-2 py-0.5 rounded-md border border-subtle bg-surface-muted text-fg">
                      <Icon className="w-3 h-3 text-accent" />
                      <span>{item.category}</span>
                    </span>
                    <span className="text-2xs font-bold text-fg-muted font-mono">
                      {item.initial}
                    </span>
                  </div>

                  {/* Term Title */}
                  <h3 className="font-bold text-sm text-fg group-hover:text-accent transition-colors line-clamp-1 mb-1.5">
                    {item.name}
                  </h3>

                  {/* Term Description Preview */}
                  <p className="text-xs text-fg-muted line-clamp-3 leading-relaxed">
                    {item.description}
                  </p>
                </div>

                {/* Bottom Action Hint */}
                <div className="mt-3 pt-2.5 border-t border-subtle flex items-center justify-between text-2xs font-medium text-fg-muted group-hover:text-accent transition-colors">
                  <span>상세 정의 열람</span>
                  <ChevronRight className="w-3.5 h-3.5 transform group-hover:translate-x-0.5 transition-transform" />
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Detail Overlay View (Modal inside screen) */}
      {activeItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4 animate-fade-in">
          <div className="w-full max-w-xl rounded-2xl border border-subtle bg-surface p-6 shadow-2xl text-fg transition-colors">
            {/* Close Button */}
            <div className="flex items-start justify-between gap-3 mb-3">
              <span className="inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-lg border border-subtle bg-surface-muted text-fg">
                {React.createElement(CATEGORY_ICON_MAP[activeItem.category] || BookOpen, { className: 'w-3.5 h-3.5 text-accent' })}
                <span>{activeItem.category}</span>
              </span>

              <button
                onClick={() => setActiveItem(null)}
                className="ui-button-secondary px-2 py-1 text-xs cursor-pointer"
                title="닫기"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Term Name */}
            <h3 className="text-lg sm:text-xl font-bold tracking-tight text-fg mb-4">
              {activeItem.name}
            </h3>

            {/* Detailed Description */}
            <div className="p-4 rounded-xl border border-subtle bg-surface-muted/40 text-fg text-xs sm:text-sm leading-relaxed mb-5">
              {activeItem.description}
            </div>

            {/* Action Buttons */}
            <div className="flex items-center justify-end pt-2 border-t border-subtle">
              <button
                onClick={() => setActiveItem(null)}
                className="ui-button-primary px-4 py-1.5 text-xs font-semibold cursor-pointer"
              >
                닫기
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
