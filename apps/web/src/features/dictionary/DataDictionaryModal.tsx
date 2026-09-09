/**
 * 파일명: DataDictionaryModal.tsx
 * 경로: apps/web/src/features/dictionary/DataDictionaryModal.tsx
 * 목적: 데이터 용어사전 모달을 표시함
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

interface Props {
  isOpen: boolean;
  onClose: () => void;
  isDarkMode?: boolean;
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

const CATEGORY_COLOR_MAP: Record<string, { badge: string; border: string }> = {
  '머신러닝 & 딥러닝': {
    badge: 'bg-indigo-50 text-indigo-700 dark:bg-indigo-950/60 dark:text-indigo-300 border-indigo-200 dark:border-indigo-800/60',
    border: 'hover:border-indigo-400 dark:hover:border-indigo-600',
  },
  '자연어 & 멀티모달': {
    badge: 'bg-teal-50 text-teal-700 dark:bg-teal-950/60 dark:text-teal-300 border-teal-200 dark:border-teal-800/60',
    border: 'hover:border-teal-400 dark:hover:border-teal-600',
  },
  'LLM & 생성형 AI': {
    badge: 'bg-sky-50 text-sky-700 dark:bg-sky-950/60 dark:text-sky-300 border-sky-200 dark:border-sky-800/60',
    border: 'hover:border-sky-400 dark:hover:border-sky-600',
  },
  '보안 & 프라이버시': {
    badge: 'bg-rose-50 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300 border-rose-200 dark:border-rose-800/60',
    border: 'hover:border-rose-400 dark:hover:border-rose-600',
  },
  '비즈니스 AI & 자동화': {
    badge: 'bg-amber-50 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300 border-amber-200 dark:border-amber-800/60',
    border: 'hover:border-amber-400 dark:hover:border-amber-600',
  },
  'AI 에이전트 & RAG': {
    badge: 'bg-purple-50 text-purple-700 dark:bg-purple-950/60 dark:text-purple-300 border-purple-200 dark:border-purple-800/60',
    border: 'hover:border-purple-400 dark:hover:border-purple-600',
  },
};

export const DataDictionaryModal: React.FC<Props> = ({ isOpen, onClose, isDarkMode = false }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<GlossaryCategory>('전체');
  const [selectedInitial, setSelectedInitial] = useState<string>('전체');
  const [activeItem, setActiveItem] = useState<GlossaryItem | null>(null);

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

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 dark:bg-black/80 backdrop-blur-sm p-3 sm:p-6 transition-all">
      <div className="ui-panel relative flex h-[92vh] w-full max-w-6xl flex-col overflow-hidden shadow-2xl">
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-subtle flex items-center justify-between bg-surface-muted/40 transition-colors">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent text-accent-fg shadow-xs">
              <BookOpen className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold tracking-tight text-fg">AI·데이터 용어사전</h2>
                <span className="text-2xs font-semibold px-2 py-0.5 rounded-full border border-subtle bg-surface text-fg-muted">
                  총 {GLOSSARY_DATA.length}개 용어
                </span>
                <span className="text-2xs font-medium px-2 py-0.5 rounded border border-subtle bg-surface text-fg-muted hidden sm:inline-block">
                  식약처 사내 데이터 생성 및 비식별화 표준 용어집
                </span>
              </div>
              <p className="text-xs text-fg-muted mt-0.5">
                인공지능, 통계 가설 검정, OCR·문서 복원, 개인정보 비식별화 및 합성데이터 공식 표준 용어집
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="ui-button-secondary px-2"
            title="닫기"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Search & Filter Toolbar */}
        <div className="px-6 py-3.5 border-b border-subtle flex flex-col gap-3 bg-surface transition-colors">
          <div className="flex items-center gap-3">
            {/* Search Input */}
            <div className="relative flex-1">
              <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-fg-muted" />
              <input
                type="text"
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                placeholder="용어명 또는 설명 검색 (예: RAG, 가명화, 프롬프트, CTGAN, 오케스트레이션, Anonymeter...)"
                className="ui-field py-2 pl-10 pr-9 text-sm"
              />
              {searchTerm && (
                <button
                  onClick={() => setSearchTerm('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-fg-muted hover:text-fg"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>

            {/* Total Results Count */}
            <div className="text-xs font-semibold text-fg-muted whitespace-nowrap">
              검색 결과: <span className="text-accent font-bold">{filteredTerms.length}</span>건
            </div>
          </div>

          {/* Category Tabs */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-none text-xs">
            {GLOSSARY_CATEGORIES.map(cat => {
              const isSelected = selectedCategory === cat;
              const count = categoryCounts[cat] || 0;
              const Icon = cat !== '전체' ? CATEGORY_ICON_MAP[cat] : Filter;

              return (
                <button
                  key={cat}
                  onClick={() => setSelectedCategory(cat)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium whitespace-nowrap transition-all border ${
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

          {/* Initial Hangul / Alphabet Navigation */}
          <div className="flex items-center gap-1 overflow-x-auto pb-0.5 text-2xs font-semibold scrollbar-none">
            <span className="text-fg-muted mr-1 text-2xs">색인:</span>
            {INITIAL_GROUPS.map(init => {
              const isSel = selectedInitial === init;
              return (
                <button
                  key={init}
                  onClick={() => setSelectedInitial(init)}
                  className={`px-2 py-0.5 rounded transition-all ${
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

        {/* Content Body: Grid of Terms */}
        <div className="flex-1 overflow-y-auto p-6 bg-surface-muted/20">
          {filteredTerms.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center p-8">
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
                className="ui-button-primary mt-4 px-3.5 py-1.5 text-xs"
              >
                필터 전체 초기화
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
              {filteredTerms.map(item => {
                const Icon = CATEGORY_ICON_MAP[item.category] || BookOpen;

                return (
                  <div
                    key={item.id}
                    onClick={() => setActiveItem(item)}
                    className="group relative flex flex-col justify-between p-4 rounded-xl border border-subtle bg-surface hover:border-accent/40 hover:bg-surface-muted/50 transition-all cursor-pointer shadow-xs hover:shadow-sm"
                  >
                    <div>
                      {/* Top Badges */}
                      <div className="flex items-center justify-between gap-2 mb-2">
                        <span className="inline-flex items-center gap-1 text-2xs font-semibold px-2 py-0.5 rounded-md border border-subtle bg-surface-muted text-fg">
                          <Icon className="w-3 h-3 text-accent" />
                          <span>{item.category}</span>
                        </span>
                        <span className="text-2xs font-bold text-fg-muted">
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
                    <div className="mt-3 pt-2.5 border-t border-subtle flex items-center justify-between text-xs font-medium text-fg-muted group-hover:text-accent transition-colors">
                      <span>상세 설명 열람</span>
                      <ChevronRight className="w-3.5 h-3.5 transform group-hover:translate-x-0.5 transition-transform" />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3 border-t border-subtle flex items-center justify-between text-xs bg-surface-muted/40 text-fg-muted transition-colors">
          <div className="flex items-center gap-2">
            <span>사내 데이터 생성기 v2.1.0 데이터·AI·보안 표준 용어사전 (식약처 가이드라인 준수)</span>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={onClose}
              className="ui-button-secondary px-3.5 py-1.5 text-xs"
            >
              닫기
            </button>
          </div>
        </div>

        {/* Detail Modal Overlay (when activeItem is selected) */}
        {activeItem && (
          <div className="absolute inset-0 z-20 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
            <div className="ui-panel relative w-full max-w-xl p-6 shadow-2xl">
              {/* Close Button */}
              <button
                onClick={() => setActiveItem(null)}
                className="ui-button-secondary absolute top-4 right-4 px-2"
              >
                <X className="w-5 h-5" />
              </button>

              {/* Category Badge */}
              <div className="mb-3">
                <span className="inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-lg border border-subtle bg-surface-muted text-fg">
                  {React.createElement(CATEGORY_ICON_MAP[activeItem.category] || BookOpen, { className: 'w-3.5 h-3.5 text-accent' })}
                  <span>{activeItem.category}</span>
                </span>
              </div>

              {/* Term Name */}
              <h3 className="text-xl font-bold tracking-tight text-fg mb-4">
                {activeItem.name}
              </h3>

              {/* Detailed Description */}
              <div className="p-4 rounded-xl border border-subtle bg-surface-muted/50 text-fg text-sm leading-relaxed mb-5">
                {activeItem.description}
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-end pt-2 border-t border-subtle">
                <button
                  onClick={() => setActiveItem(null)}
                  className="ui-button-primary px-4 py-2 text-xs font-semibold cursor-pointer"
                >
                  확인 완료
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
