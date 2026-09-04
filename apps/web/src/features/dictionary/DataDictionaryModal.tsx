import React, { useState, useMemo } from 'react';
import { 
  BookOpen, 
  Search, 
  X, 
  ExternalLink, 
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
      <div 
        className={`relative w-full max-w-6xl h-[92vh] flex flex-col rounded-2xl shadow-2xl border transition-colors overflow-hidden ${
          isDarkMode 
            ? 'bg-slate-900 border-slate-700/80 text-slate-100' 
            : 'bg-white border-slate-200 text-slate-900'
        }`}
      >
        {/* Modal Header */}
        <div className={`px-6 py-4 border-b flex items-center justify-between transition-colors ${
          isDarkMode ? 'border-slate-800 bg-slate-900/90' : 'border-slate-200 bg-slate-50/80'
        }`}>
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-sky-600 to-indigo-600 flex items-center justify-center shadow-md shadow-sky-500/20 text-white">
              <BookOpen className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold tracking-tight">AI·데이터 용어사전</h2>
                <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full border ${
                  isDarkMode 
                    ? 'bg-sky-950/60 text-sky-300 border-sky-800/60' 
                    : 'bg-sky-50 text-sky-700 border-sky-200'
                }`}>
                  총 {GLOSSARY_DATA.length}개 용어
                </span>
                <span className={`text-[10px] font-medium px-2 py-0.5 rounded border hidden sm:inline-block ${
                  isDarkMode 
                    ? 'bg-slate-800 text-slate-400 border-slate-700' 
                    : 'bg-slate-100 text-slate-600 border-slate-200'
                }`}>
                  FlowHunt Korean Standard & Platform Core
                </span>
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                인공지능, 거대언어모델(LLM), 검색증강생성(RAG), AI 보안 및 합성데이터 관련 표준 전문 용어 정의
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className={`p-2 rounded-xl transition-colors ${
              isDarkMode 
                ? 'text-slate-400 hover:text-slate-200 hover:bg-slate-800' 
                : 'text-slate-500 hover:text-slate-800 hover:bg-slate-100'
            }`}
            title="닫기"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Search & Filter Toolbar */}
        <div className={`px-6 py-3.5 border-b flex flex-col gap-3 transition-colors ${
          isDarkMode ? 'border-slate-800 bg-slate-950/40' : 'border-slate-200/80 bg-white'
        }`}>
          <div className="flex items-center gap-3">
            {/* Search Input */}
            <div className="relative flex-1">
              <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                placeholder="용어명 또는 설명 검색 (예: RAG, 가명화, 프롬프트, CTGAN, 오케스트레이션, Anonymeter...)"
                className={`w-full pl-10 pr-9 py-2 rounded-xl text-xs sm:text-sm border transition-all focus:outline-none focus:ring-2 focus:ring-sky-500/30 ${
                  isDarkMode 
                    ? 'bg-slate-800/80 border-slate-700 text-white placeholder-slate-500 focus:border-sky-500' 
                    : 'bg-slate-50 border-slate-200 text-slate-900 placeholder-slate-400 focus:border-sky-500'
                }`}
              />
              {searchTerm && (
                <button
                  onClick={() => setSearchTerm('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>

            {/* Total Results Count */}
            <div className="text-xs font-semibold text-slate-500 dark:text-slate-400 whitespace-nowrap">
              검색 결과: <span className="text-sky-600 dark:text-sky-400 font-bold">{filteredTerms.length}</span>건
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
                      ? isDarkMode 
                        ? 'bg-sky-600 text-white border-sky-500 shadow-sm font-semibold' 
                        : 'bg-sky-600 text-white border-sky-600 shadow-sm font-semibold'
                      : isDarkMode 
                        ? 'bg-slate-800/80 text-slate-300 border-slate-700/80 hover:bg-slate-700/80' 
                        : 'bg-slate-100 text-slate-600 border-slate-200 hover:bg-slate-200/80'
                  }`}
                >
                  {Icon && <Icon className="w-3.5 h-3.5" />}
                  <span>{cat}</span>
                  <span className={`text-[10px] px-1.5 py-0.2 rounded-full font-bold ${
                    isSelected
                      ? 'bg-white/20 text-white'
                      : isDarkMode ? 'bg-slate-700 text-slate-400' : 'bg-slate-200 text-slate-600'
                  }`}>
                    {count}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Initial Hangul / Alphabet Navigation */}
          <div className="flex items-center gap-1 overflow-x-auto pb-0.5 text-[11px] font-semibold scrollbar-none">
            <span className="text-slate-400 dark:text-slate-500 mr-1 text-[10px]">색인:</span>
            {INITIAL_GROUPS.map(init => {
              const isSel = selectedInitial === init;
              return (
                <button
                  key={init}
                  onClick={() => setSelectedInitial(init)}
                  className={`px-2 py-0.5 rounded transition-all ${
                    isSel
                      ? isDarkMode 
                        ? 'bg-sky-500 text-slate-950 font-bold' 
                        : 'bg-sky-600 text-white font-bold'
                      : isDarkMode 
                        ? 'text-slate-400 hover:text-slate-200 hover:bg-slate-800' 
                        : 'text-slate-500 hover:text-slate-900 hover:bg-slate-100'
                  }`}
                >
                  {init}
                </button>
              );
            })}
          </div>
        </div>

        {/* Content Body: Grid of Terms */}
        <div className="flex-1 overflow-y-auto p-6">
          {filteredTerms.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center p-8">
              <div className="w-12 h-12 rounded-2xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-400 mb-3">
                <Search className="w-6 h-6" />
              </div>
              <p className="font-semibold text-sm text-slate-600 dark:text-slate-300">
                검색 조건에 맞는 용어가 없습니다
              </p>
              <p className="text-xs text-slate-400 dark:text-slate-500 mt-1 max-w-sm">
                다른 검색어를 입력하시거나 카테고리/초성 필터를 '전체'로 재설정해 보세요.
              </p>
              <button
                onClick={() => {
                  setSearchTerm('');
                  setSelectedCategory('전체');
                  setSelectedInitial('전체');
                }}
                className="mt-4 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-sky-600 text-white hover:bg-sky-500"
              >
                필터 전체 초기화
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
              {filteredTerms.map(item => {
                const colorConfig = CATEGORY_COLOR_MAP[item.category] || {
                  badge: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300 border-slate-200',
                  border: 'hover:border-slate-400',
                };
                const Icon = CATEGORY_ICON_MAP[item.category] || BookOpen;

                return (
                  <div
                    key={item.id}
                    onClick={() => setActiveItem(item)}
                    className={`group relative flex flex-col justify-between p-4 rounded-xl border transition-all cursor-pointer ${
                      colorConfig.border
                    } ${
                      isDarkMode 
                        ? 'bg-slate-800/50 border-slate-700/70 hover:bg-slate-800/90 shadow-sm' 
                        : 'bg-white border-slate-200 hover:bg-slate-50/90 shadow-sm hover:shadow-md'
                    }`}
                  >
                    <div>
                      {/* Top Badges */}
                      <div className="flex items-center justify-between gap-2 mb-2">
                        <span className={`inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-md border ${colorConfig.badge}`}>
                          <Icon className="w-3 h-3" />
                          <span>{item.category}</span>
                        </span>
                        <span className="text-[10px] font-bold text-slate-400 dark:text-slate-500">
                          {item.initial}
                        </span>
                      </div>

                      {/* Term Title */}
                      <h3 className="font-bold text-sm text-slate-900 dark:text-white group-hover:text-sky-600 dark:group-hover:text-sky-400 transition-colors line-clamp-1 mb-1.5">
                        {item.name}
                      </h3>

                      {/* Term Description Preview */}
                      <p className="text-xs text-slate-600 dark:text-slate-300 line-clamp-3 leading-relaxed">
                        {item.description}
                      </p>
                    </div>

                    {/* Bottom Action Hint */}
                    <div className="mt-3 pt-2.5 border-t border-slate-100 dark:border-slate-700/60 flex items-center justify-between text-[11px] font-medium text-slate-400 group-hover:text-sky-600 dark:group-hover:text-sky-400 transition-colors">
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
        <div className={`px-6 py-3 border-t flex items-center justify-between text-xs transition-colors ${
          isDarkMode ? 'border-slate-800 bg-slate-900/80 text-slate-400' : 'border-slate-200 bg-slate-50 text-slate-500'
        }`}>
          <div className="flex items-center gap-2">
            <span>출처: FlowHunt Official Glossary & Enterprise Synthetic Engine Core</span>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={onClose}
              className="px-3.5 py-1.5 rounded-lg font-semibold bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-slate-300 dark:hover:bg-slate-700 transition-colors"
            >
              닫기
            </button>
          </div>
        </div>

        {/* Detail Modal Overlay (when activeItem is selected) */}
        {activeItem && (
          <div className="absolute inset-0 z-20 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
            <div className={`relative w-full max-w-xl rounded-2xl p-6 shadow-2xl border transition-all ${
              isDarkMode ? 'bg-slate-900 border-slate-700 text-slate-100' : 'bg-white border-slate-200 text-slate-900'
            }`}>
              {/* Close Button */}
              <button
                onClick={() => setActiveItem(null)}
                className="absolute top-4 right-4 p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800"
              >
                <X className="w-5 h-5" />
              </button>

              {/* Category Badge */}
              <div className="mb-3">
                <span className={`inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-lg border ${
                  CATEGORY_COLOR_MAP[activeItem.category]?.badge || 'bg-slate-100 text-slate-700'
                }`}>
                  {React.createElement(CATEGORY_ICON_MAP[activeItem.category] || BookOpen, { className: 'w-3.5 h-3.5' })}
                  <span>{activeItem.category}</span>
                </span>
              </div>

              {/* Term Name */}
              <h3 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white mb-4">
                {activeItem.name}
              </h3>

              {/* Detailed Description */}
              <div className={`p-4 rounded-xl border text-sm leading-relaxed mb-5 ${
                isDarkMode 
                  ? 'bg-slate-800/60 border-slate-700 text-slate-200' 
                  : 'bg-slate-50 border-slate-200 text-slate-700'
              }`}>
                {activeItem.description}
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-between pt-2">
                {activeItem.url ? (
                  <a
                    href={activeItem.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 text-xs font-semibold text-sky-600 hover:text-sky-700 dark:text-sky-400 dark:hover:text-sky-300 transition-colors"
                  >
                    <span>FlowHunt 공식 원문 기사 확인</span>
                    <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                ) : <span />}

                <button
                  onClick={() => setActiveItem(null)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-sky-600 hover:bg-sky-500 text-white transition-colors"
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
