/**
 * 파일명: SystemDocsView.tsx
 * 경로: apps/web/src/features/system/SystemDocsView.tsx
 * 목적: 시스템 문서와 라이브러리 정보를 표시함
 * 작성자: 개발팀
 * 작성일: 2026-09-09
 * 수정일: 2026-09-09
 */
import React, { useState, useEffect, useMemo } from 'react';
import {
  BookOpen,
  FileText,
  Search,
  Copy,
  Check,
  RefreshCw,
  ChevronRight,
  Eye,
  Code,
  Download,
  Sparkles
} from 'lucide-react';

export interface DocItem {
  id: string;
  path: string;
  name: string;
  title: string;
  category: string;
  size_bytes: number;
  updated_at: string;
}

interface SystemDocsViewProps {
  initialDoc?: 'changelog' | 'libraries' | string;
  onBack: () => void;
  isDarkMode: boolean;
  onDocChange?: (doc: string) => void;
  onStepChange?: (step: number) => void;
}

export const SystemDocsView: React.FC<SystemDocsViewProps> = ({
  initialDoc = 'changelog',
  onDocChange,
  onStepChange,
}) => {
  const [docs, setDocs] = useState<DocItem[]>([]);
  const [selectedDocPath, setSelectedDocPath] = useState<string>('');
  const [activeDocMetadata, setActiveDocMetadata] = useState<DocItem | null>(null);
  const [content, setContent] = useState<string>('');
  const [isLoadingList, setIsLoadingList] = useState<boolean>(true);
  const [isLoadingContent, setIsLoadingContent] = useState<boolean>(false);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [viewMode, setViewMode] = useState<'rendered' | 'raw'>('rendered');
  const [copied, setCopied] = useState<boolean>(false);

  const [isSyncingLibs, setIsSyncingLibs] = useState<boolean>(false);
  const [syncMessage, setSyncMessage] = useState<string>('');

  // Fallback docs list in case API is loading or offline
  const FALLBACK_DOCS: DocItem[] = [
    { id: '개발이력.md', path: '개발이력.md', name: '시스템 개발 이력', title: '시스템 개발 이력', category: '시스템 문서', size_bytes: 2048, updated_at: '2026-09-09' },
    { id: '라이브러리목록.md', path: '라이브러리목록.md', name: '프로젝트 사용 라이브러리 및 오픈소스 목록', title: '프로젝트 사용 라이브러리 및 오픈소스 목록', category: '시스템 문서', size_bytes: 3072, updated_at: '2026-09-09' },
    { id: '프로젝트안내.md', path: '프로젝트안내.md', name: '플랫폼 안내', title: '범용 AI 합성데이터 생성 및 심의 패키지 플랫폼 안내', category: '시스템 문서', size_bytes: 2560, updated_at: '2026-09-09' },
    { id: '저장소작업지침.md', path: '저장소작업지침.md', name: '저장소 작업 지침', title: '저장소 작업 지침', category: '시스템 문서', size_bytes: 1800, updated_at: '2026-09-09' },
    { id: 'docs/화면설계지침.md', path: 'docs/화면설계지침.md', name: '화면 설계 지침', title: '화면 설계 지침', category: '기술 가이드', size_bytes: 4200, updated_at: '2026-09-09' },
    { id: 'docs/코드주석작성지침.md', path: 'docs/코드주석작성지침.md', name: '코드 주석 작성 지침', title: '코드 주석 작성 지침', category: '기술 가이드', size_bytes: 3200, updated_at: '2026-09-09' },
    { id: 'docs/일괄처리.md', path: 'docs/일괄처리.md', name: '최대 20개 파일 일괄 처리', title: '최대 20개 파일 일괄 처리', category: '기술 가이드', size_bytes: 3500, updated_at: '2026-09-09' },
    { id: 'docs/사내망Nginx운영.md', path: 'docs/사내망Nginx운영.md', name: '사내망 Nginx 운영', title: '사내망 Nginx 운영', category: '기술 가이드', size_bytes: 2900, updated_at: '2026-09-09' },
    { id: 'docs/노트북연동.md', path: 'docs/노트북연동.md', name: '노트북 기능 반영', title: '노트북 기능 반영', category: '기술 가이드', size_bytes: 3100, updated_at: '2026-09-09' },
    { id: 'docs/심의자료생성및배포.md', path: 'docs/심의자료생성및배포.md', name: '심의자료 자동 생성과 모노레포 운영', title: '심의자료 자동 생성과 모노레포 운영', category: '기술 가이드', size_bytes: 4800, updated_at: '2026-09-09' },
    { id: 'docs/세종교육데이터명세.md', path: 'docs/세종교육데이터명세.md', name: '세종 교육데이터 합성 데이터 명세서', title: '세종 교육데이터 합성 데이터 명세서', category: '기술 가이드', size_bytes: 3600, updated_at: '2026-09-09' },
    { id: 'docs/architecture/아키텍처.md', path: 'docs/architecture/아키텍처.md', name: '프로젝트 아키텍처', title: '프로젝트 아키텍처', category: '기술 가이드', size_bytes: 3600, updated_at: '2026-09-09' },
    { id: 'docs/architecture/공통모듈화계획.md', path: 'docs/architecture/공통모듈화계획.md', name: '공통 모듈화 및 도메인 분리 계획', title: '공통 모듈화 및 도메인 분리 계획', category: '기술 가이드', size_bytes: 5200, updated_at: '2026-09-09' },
    { id: 'docs/architecture/개선작업목록.md', path: 'docs/architecture/개선작업목록.md', name: '기능 개선 작업 목록', title: '기능 개선 작업 목록', category: '기술 가이드', size_bytes: 4100, updated_at: '2026-09-09' },
    { id: 'docs/문서목록.md', path: 'docs/문서목록.md', name: '프로젝트 Markdown 문서 목록', title: '프로젝트 Markdown 문서 목록', category: '기술 가이드', size_bytes: 3600, updated_at: '2026-09-09' },
    { id: 'docs/설문_합성데이터_최종산출물/설문_전국3대지역_합성결과_요약보고서.md', path: 'docs/설문_합성데이터_최종산출물/설문_전국3대지역_합성결과_요약보고서.md', name: '설문 전국 3대 지역 합성 결과 요약보고서', title: '설문 전국 3대 지역 합성 결과 요약보고서', category: '기술 가이드', size_bytes: 6200, updated_at: '2026-09-09' },
    { id: 'apps/api/백엔드API안내.md', path: 'apps/api/백엔드API안내.md', name: '백엔드 API 패키지 안내', title: '백엔드 API 패키지 안내', category: '패키지 문서', size_bytes: 1800, updated_at: '2026-09-09' },
    { id: 'packages/synthetic_engine/합성엔진안내.md', path: 'packages/synthetic_engine/합성엔진안내.md', name: '합성 엔진 패키지 안내', title: '합성 엔진 패키지 안내', category: '패키지 문서', size_bytes: 2100, updated_at: '2026-09-09' },
  ];

  // 1. Fetch available markdown documents
  const loadDocsList = async () => {
    setIsLoadingList(true);
    try {
      const res = await fetch('/api/v1/system/docs');
      if (!res.ok) throw new Error('문서 목록 조회 실패');
      const data = await res.json();
      const list: DocItem[] = (data.docs && data.docs.length > 0) ? data.docs : FALLBACK_DOCS;
      setDocs(list);

      // Determine initial selection
      let defaultPath = '개발이력.md';
      if (initialDoc === 'libraries' || initialDoc === '라이브러리목록.md') {
        defaultPath = '라이브러리목록.md';
      } else if (initialDoc && initialDoc !== 'changelog') {
        const found = list.find(d => d.id === initialDoc || d.path === initialDoc || d.name === initialDoc);
        if (found) defaultPath = found.path;
      }

      const match = list.find(d => d.path === defaultPath || d.id === defaultPath) || list[0];
      if (match) {
        setSelectedDocPath(match.path);
        setActiveDocMetadata(match);
      }
    } catch (err) {
      console.warn('API fallback used:', err);
      setDocs(FALLBACK_DOCS);
      const match = FALLBACK_DOCS.find(d => d.id === initialDoc || d.path === initialDoc) || FALLBACK_DOCS[0];
      setSelectedDocPath(match.path);
      setActiveDocMetadata(match);
    } finally {
      setIsLoadingList(false);
    }
  };

  useEffect(() => {
    loadDocsList();
  }, []);

  // Sync libraries handler
  const handleSyncLibraries = async () => {
    setIsSyncingLibs(true);
    setSyncMessage('');
    try {
      const res = await fetch('/api/v1/system/sync-libraries', { method: 'POST' });
      if (!res.ok) throw new Error('라이브러리 동기화 실패');
      const data = await res.json();
      setContent(data.content || '');
      setSyncMessage('package-lock.json 및 pyproject.toml 의존성 동기화 완료!');
      setTimeout(() => setSyncMessage(''), 3000);
      loadDocsList();
    } catch (err: any) {
      setSyncMessage(`동기화 오류: ${err.message}`);
      setTimeout(() => setSyncMessage(''), 3000);
    } finally {
      setIsSyncingLibs(false);
    }
  };

  // Handle external initialDoc change
  useEffect(() => {
    if (!docs.length) return;
    let targetPath = '개발이력.md';
    if (initialDoc === 'libraries' || initialDoc === '라이브러리목록.md') {
      targetPath = '라이브러리목록.md';
    } else if (initialDoc && initialDoc !== 'changelog') {
      const found = docs.find(d => d.id === initialDoc || d.path === initialDoc || d.name === initialDoc);
      if (found) targetPath = found.path;
    }
    const match = docs.find(d => d.path === targetPath || d.id === targetPath);
    if (match && match.path !== selectedDocPath) {
      setSelectedDocPath(match.path);
      setActiveDocMetadata(match);
    }
  }, [initialDoc, docs]);

  // 2. Fetch selected document content
  useEffect(() => {
    if (!selectedDocPath) return;
    setIsLoadingContent(true);
    onStepChange?.(2);

    fetch(`/api/v1/system/doc?path=${encodeURIComponent(selectedDocPath)}`)
      .then(res => {
        if (!res.ok) throw new Error('문서를 불러올 수 없습니다.');
        return res.json();
      })
      .then(data => {
        setContent(data.content || '');
        if (!activeDocMetadata) {
          setActiveDocMetadata({
            id: data.id,
            path: data.path,
            name: data.name,
            title: data.title,
            category: '시스템 문서',
            size_bytes: data.size_bytes,
            updated_at: data.updated_at
          });
        }
        onStepChange?.(3);
      })
      .catch(err => {
        setContent(`# ${selectedDocPath}\n\n문서를 불러오는 중 오류가 발생했습니다: ${err.message}`);
        onStepChange?.(3);
      })
      .finally(() => setIsLoadingContent(false));
  }, [selectedDocPath]);

  // Filtered documents - Search by name, path, or title
  const filteredDocs = useMemo(() => {
    const term = searchTerm.trim().toLowerCase();
    if (!term) return docs;
    return docs.filter(doc =>
      doc.name.toLowerCase().includes(term) ||
      doc.path.toLowerCase().includes(term) ||
      doc.title.toLowerCase().includes(term)
    );
  }, [docs, searchTerm]);

  // Copy markdown handler
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (e) {
      console.error(e);
    }
  };

  // Select a doc
  const handleSelectDoc = (doc: DocItem) => {
    setSelectedDocPath(doc.path);
    setActiveDocMetadata(doc);
    if (doc.path === '개발이력.md') {
      onDocChange?.('changelog');
    } else if (doc.path === '라이브러리목록.md') {
      onDocChange?.('libraries');
    } else {
      onDocChange?.(doc.path);
    }
  };

  // Plain developer-style markdown renderer with Consolas typography
  const renderMarkdown = (md: string) => {
    const lines = md.split('\n');
    const elements: React.ReactNode[] = [];
    let inTable = false;
    let tableRows: string[][] = [];

    const flushTable = (key: number) => {
      if (tableRows.length === 0) return null;
      const [header, divider, ...body] = tableRows;
      const hasHeader = divider && divider.some(cell => cell.includes('-'));
      const renderHeaders = hasHeader ? header : [];
      const renderBody = hasHeader ? body : tableRows;

      const tbl = (
        <div key={`table-${key}`} className="my-4 overflow-x-auto rounded-xl border border-subtle bg-surface">
          <table className="w-full text-left text-xs font-mono">
            {renderHeaders.length > 0 && (
              <thead className="bg-surface-muted border-b border-subtle text-fg font-bold">
                <tr>
                  {renderHeaders.map((h, hIdx) => (
                    <th key={hIdx} className="px-3.5 py-2.5 border-r border-subtle last:border-r-0">
                      {h.trim()}
                    </th>
                  ))}
                </tr>
              </thead>
            )}
            <tbody className="divide-y divide-subtle">
              {renderBody.map((row, rIdx) => (
                <tr key={rIdx} className="hover:bg-surface-muted/40 transition-colors">
                  {row.map((cell, cIdx) => (
                    <td key={cIdx} className="px-3.5 py-2 border-r border-subtle last:border-r-0 text-fg/90">
                      {cell.trim()}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
      tableRows = [];
      inTable = false;
      return tbl;
    };

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const trimmed = line.trim();

      // Table line detection
      if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
        inTable = true;
        const cells = trimmed
          .slice(1, -1)
          .split('|')
          .map(c => c.trim());
        tableRows.push(cells);
        continue;
      } else if (inTable) {
        const tbl = flushTable(i);
        if (tbl) elements.push(tbl);
      }

      if (!trimmed) {
        elements.push(<div key={`space-${i}`} className="h-2" />);
        continue;
      }

      if (trimmed.startsWith('# ')) {
        elements.push(
          <h1 key={`h1-${i}`} className="text-xl font-bold text-fg pb-2 border-b border-subtle mb-4 mt-2 font-mono">
            {trimmed.replace(/^#\s+/, '')}
          </h1>
        );
        continue;
      }

      if (trimmed.startsWith('## ')) {
        elements.push(
          <h2 key={`h2-${i}`} className="text-base font-bold text-fg mt-6 mb-2 font-mono pb-1 border-b border-subtle/50">
            {trimmed.replace(/^##\s+/, '')}
          </h2>
        );
        continue;
      }

      if (trimmed.startsWith('### ')) {
        elements.push(
          <h3 key={`h3-${i}`} className="text-sm font-semibold text-fg mt-4 mb-1 font-mono">
            {trimmed.replace(/^###\s+/, '')}
          </h3>
        );
        continue;
      }

      if (trimmed.startsWith('#### ')) {
        elements.push(
          <h4 key={`h4-${i}`} className="text-xs font-bold text-fg-muted mt-3 mb-1 font-mono uppercase tracking-wider">
            {trimmed.replace(/^####\s+/, '')}
          </h4>
        );
        continue;
      }

      if (trimmed.startsWith('---') || trimmed.startsWith('***')) {
        elements.push(<hr key={`hr-${i}`} className="border-subtle my-4" />);
        continue;
      }

      if (trimmed.startsWith('> ')) {
        elements.push(
          <blockquote key={`quote-${i}`} className="border-l-4 border-accent pl-3 py-1 my-2 text-xs text-fg-muted bg-accent-subtle/30 rounded-r-md font-mono">
            {trimmed.replace(/^>\s+/, '')}
          </blockquote>
        );
        continue;
      }

      if (trimmed.startsWith('- ') || trimmed.startsWith('* ') || /^\d+\.\s/.test(trimmed)) {
        const isNumbered = /^\d+\.\s/.test(trimmed);
        const bulletText = isNumbered ? trimmed.replace(/^\d+\.\s+/, '') : trimmed.replace(/^[-*]\s+/, '');
        const parts = bulletText.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);

        elements.push(
          <div key={`bullet-${i}`} className="flex items-start gap-2 pl-2 py-0.5">
            <span className="text-fg-muted select-none font-mono text-xs mt-0.5 shrink-0">
              {isNumbered ? `${trimmed.match(/^\d+/)?.[0]}.` : '•'}
            </span>
            <span className="text-fg/85 font-mono text-xs leading-relaxed">
              {parts.map((p, pIdx) => {
                if (p.startsWith('**') && p.endsWith('**')) {
                  return (
                    <strong key={pIdx} className="text-fg font-semibold font-mono text-xs">
                      {p.slice(2, -2)}
                    </strong>
                  );
                }
                if (p.startsWith('`') && p.endsWith('`')) {
                  return (
                    <code key={pIdx} className="px-1.5 py-0.5 rounded bg-surface-muted border border-subtle text-accent font-mono text-xs mx-0.5">
                      {p.slice(1, -1)}
                    </code>
                  );
                }
                return p;
              })}
            </span>
          </div>
        );
        continue;
      }

      // Regular paragraph
      const parts = line.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
      elements.push(
        <p key={`p-${i}`} className="text-fg/80 font-mono text-xs leading-relaxed">
          {parts.map((p, pIdx) => {
            if (p.startsWith('**') && p.endsWith('**')) {
              return (
                <strong key={pIdx} className="text-fg font-semibold font-mono">
                  {p.slice(2, -2)}
                </strong>
              );
            }
            if (p.startsWith('`') && p.endsWith('`')) {
              return (
                <code key={pIdx} className="px-1.5 py-0.5 rounded bg-surface-muted border border-subtle text-accent font-mono text-xs mx-0.5">
                  {p.slice(1, -1)}
                </code>
              );
            }
            return p;
          })}
        </p>
      );
    }

    if (inTable) {
      const tbl = flushTable(lines.length);
      if (tbl) elements.push(tbl);
    }

    return <div className="space-y-1.5 text-xs leading-relaxed text-fg/90 font-mono">{elements}</div>;
  };

  return (
    <div className="space-y-4 animate-fade-in font-mono">
      {/* 2-Column Documentation Explorer Layout (Ratio 2:8) */}
      <div className="grid grid-cols-1 lg:grid-cols-10 gap-5 items-start">
        
        {/* Left: Document List Sidebar (2 Cols = 20%) */}
        <div className="lg:col-span-2 flex flex-col gap-3">
          <div className="p-3.5 rounded-2xl border border-subtle bg-surface shadow-xs space-y-3">
            {/* Header & Total Count */}
            <div className="flex items-center justify-between px-1">
              <div className="flex items-center gap-2">
                <BookOpen className="w-4 h-4 text-accent" />
                <span className="font-bold text-xs text-fg">Markdown 문서 목록</span>
              </div>
              <span className="text-2xs font-bold px-2 py-0.5 rounded-full bg-surface-muted border border-subtle text-fg-muted font-mono">
                {filteredDocs.length}개
              </span>
            </div>

            {/* Search Bar */}
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-fg-muted" />
              <input
                type="text"
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                placeholder="문서명 검색..."
                className="ui-field w-full py-1.5 pl-8 pr-3 text-xs font-mono"
              />
            </div>

            {/* Document List Items - Concise single-line .md names */}
            <div className="space-y-1 max-h-[620px] overflow-y-auto pr-1">
              {isLoadingList ? (
                <div className="py-8 text-center text-xs text-fg-muted">
                  <RefreshCw className="w-4 h-4 animate-spin mx-auto mb-2 text-accent" />
                  문서 목록 로딩 중...
                </div>
              ) : filteredDocs.length === 0 ? (
                <div className="py-8 text-center text-xs text-fg-muted">
                  일치하는 Markdown 문서가 없습니다.
                </div>
              ) : (
                filteredDocs.map(doc => {
                  const isSelected = selectedDocPath === doc.path;

                  return (
                    <button
                      key={doc.id}
                      onClick={() => handleSelectDoc(doc)}
                      title={doc.path}
                      className={`w-full text-left px-3 py-2 rounded-xl border transition-all flex items-center gap-2.5 cursor-pointer text-xs font-mono group ${
                        isSelected
                          ? 'bg-accent-subtle/50 border-accent text-accent font-bold shadow-xs ring-1 ring-accent/30'
                          : 'bg-surface-muted/30 border-subtle text-fg-muted hover:bg-surface-muted hover:text-fg hover:border-accent/40'
                      }`}
                    >
                      <FileText className={`w-3.5 h-3.5 shrink-0 ${isSelected ? 'text-accent' : 'text-fg-muted group-hover:text-accent'}`} />
                      <span className={`truncate flex-1 font-mono text-xs ${isSelected ? 'text-accent font-bold' : 'text-fg group-hover:text-accent'}`}>
                        {doc.name}
                      </span>
                      <ChevronRight className={`w-3 h-3 shrink-0 opacity-40 transition-transform group-hover:translate-x-0.5 ${isSelected ? 'opacity-100 text-accent' : ''}`} />
                    </button>
                  );
                })
              )}
            </div>
          </div>
        </div>

        {/* Right: Main Document Reader (8 Cols = 80%) */}
        <div className="lg:col-span-8 flex flex-col gap-3 min-w-0">
          <div className="rounded-2xl border border-subtle bg-surface shadow-xs overflow-hidden">
            
            {/* Top Toolbar of Viewer */}
            <div className="p-4 border-b border-subtle bg-surface-muted/40 flex flex-wrap items-center justify-between gap-3">
              <div className="space-y-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-bold text-fg font-mono">
                    {activeDocMetadata?.name || selectedDocPath}
                  </span>
                </div>

                <div className="flex items-center gap-3 text-xs text-fg-muted flex-wrap">
                  <span className="font-mono bg-surface px-1.5 py-0.5 rounded border border-subtle text-fg">
                    {selectedDocPath}
                  </span>
                  {activeDocMetadata?.size_bytes ? (
                    <span>크기: {(activeDocMetadata.size_bytes / 1024).toFixed(1)} KB</span>
                  ) : null}
                  {activeDocMetadata?.updated_at ? (
                    <span>수정: {activeDocMetadata.updated_at}</span>
                  ) : null}
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-2 flex-wrap">
                {/* 라이브러리 목록 동기화 */}
                {(selectedDocPath === '라이브러리목록.md' || activeDocMetadata?.path === '라이브러리목록.md') && (
                  <button
                    onClick={handleSyncLibraries}
                    disabled={isSyncingLibs}
                    className="ui-button-primary px-2.5 py-1.5 text-xs cursor-pointer flex items-center gap-1.5 shadow-xs"
                    title="package-lock.json 및 pyproject.toml 의존성을 읽어 라이브러리목록.md 자동 갱신"
                  >
                    <Sparkles className={`w-3.5 h-3.5 ${isSyncingLibs ? 'animate-spin' : ''}`} />
                    <span>{isSyncingLibs ? '동기화 중...' : '라이브러리 동기화'}</span>
                  </button>
                )}
                {/* View Mode Toggle */}
                <div className="inline-flex rounded-lg border border-subtle p-0.5 bg-surface text-xs">
                  <button
                    onClick={() => setViewMode('rendered')}
                    className={`flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium cursor-pointer transition-colors ${
                      viewMode === 'rendered'
                        ? 'bg-accent text-accent-fg font-semibold shadow-xs'
                        : 'text-fg-muted hover:text-fg'
                    }`}
                    title="스타일 적용된 문서 보기"
                  >
                    <Eye className="w-3.5 h-3.5" />
                    <span>문서 뷰</span>
                  </button>
                  <button
                    onClick={() => setViewMode('raw')}
                    className={`flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium cursor-pointer transition-colors ${
                      viewMode === 'raw'
                        ? 'bg-accent text-accent-fg font-semibold shadow-xs'
                        : 'text-fg-muted hover:text-fg'
                    }`}
                    title="마크다운 원문 소스 보기"
                  >
                    <Code className="w-3.5 h-3.5" />
                    <span>원문 소스</span>
                  </button>
                </div>

                <button
                  onClick={handleCopy}
                  className="ui-button-secondary px-2.5 py-1.5 text-xs cursor-pointer flex items-center gap-1.5"
                  title="마크다운 텍스트 복사"
                >
                  {copied ? (
                    <>
                      <Check className="w-3.5 h-3.5 text-emerald-500" />
                      <span className="text-emerald-500 font-bold">복사됨!</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5" />
                      <span className="hidden sm:inline">복사</span>
                    </>
                  )}
                </button>

                <button
                  onClick={() => {
                    const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = activeDocMetadata?.name || 'document.md';
                    a.click();
                    URL.revokeObjectURL(url);
                  }}
                  className="ui-button-secondary px-2.5 py-1.5 text-xs cursor-pointer flex items-center gap-1.5"
                  title="마크다운 파일 다운로드"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">다운로드</span>
                </button>

                <button
                  onClick={() => {
                    setSelectedDocPath(prev => prev);
                  }}
                  disabled={isLoadingContent}
                  className="ui-button-secondary px-2 py-1.5 text-xs cursor-pointer flex items-center"
                  title="문서 새로고침"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${isLoadingContent ? 'animate-spin' : ''}`} />
                </button>
              </div>
            </div>

            {/* Document Body */}
            {syncMessage && (
              <div className="mx-6 mt-4 p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-600 dark:text-emerald-400 text-xs font-semibold flex items-center gap-2 animate-fade-in">
                <Check className="w-4 h-4 text-emerald-500 shrink-0" />
                <span>{syncMessage}</span>
              </div>
            )}

            <div className="p-6 sm:p-8 min-h-[520px] max-h-[720px] overflow-y-auto selection:bg-accent/20">
              {isLoadingContent ? (
                <div className="py-20 text-center text-xs text-fg-muted font-mono">
                  <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-3 text-accent" />
                  문서를 불러오는 중입니다...
                </div>
              ) : viewMode === 'raw' ? (
                <div className="bg-surface-muted/50 p-4 rounded-xl border border-subtle overflow-x-auto select-all">
                  <pre className="font-mono text-xs leading-relaxed text-fg whitespace-pre-wrap">
                    {content}
                  </pre>
                </div>
              ) : (
                renderMarkdown(content)
              )}
            </div>

          </div>
        </div>

      </div>
    </div>
  );
};
