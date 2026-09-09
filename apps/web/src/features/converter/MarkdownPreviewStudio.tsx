/**
 * 파일명: MarkdownPreviewStudio.tsx
 * 경로: apps/web/src/features/converter/MarkdownPreviewStudio.tsx
 * 목적: Markdown 문서 미리보기 화면을 제공함
 * 작성자: 개발팀
 * 작성일: 2026-09-09
 * 수정일: 2026-09-09
 */
import React, { useState, useMemo, useEffect } from 'react';
import { marked } from 'marked';
import {
  FileText,
  Columns,
  Eye,
  Code2,
  Copy,
  Check,
  Download,
  BookOpen,
  Sparkles,
  Maximize2,
  X,
  AlignLeft,
  AlignCenter
} from 'lucide-react';

interface MarkdownPreviewStudioProps {
  markdown: string;
  fileName?: string;
  downloadUrl?: string;
}

export const MarkdownPreviewStudio: React.FC<MarkdownPreviewStudioProps> = ({
  markdown,
  fileName = 'converted_document.md',
  downloadUrl
}) => {
  const [viewMode, setViewMode] = useState<'preview' | 'split' | 'source'>('preview');
  const [copiedMd, setCopiedMd] = useState(false);
  const [copiedHtml, setCopiedHtml] = useState(false);
  const [isFullScreen, setIsFullScreen] = useState(false);
  const [isFullWidth, setIsFullWidth] = useState(false);

  // Close full screen on ESC key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isFullScreen) {
        setIsFullScreen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isFullScreen]);

  // Lock body scroll when full screen
  useEffect(() => {
    if (isFullScreen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isFullScreen]);

  // Compute rendered HTML using marked
  const renderedHtml = useMemo(() => {
    try {
      return marked.parse(markdown, { gfm: true, breaks: true }) as string;
    } catch (e) {
      return '<p class="text-rose-500 font-bold p-4">마크다운 렌더링 중 오류가 발생했습니다.</p>';
    }
  }, [markdown]);

  // Statistics
  const linesCount = useMemo(() => markdown.split('\n').length, [markdown]);
  const charCount = useMemo(() => markdown.length, [markdown]);
  const wordCount = useMemo(() => markdown.trim().split(/\s+/).filter(Boolean).length, [markdown]);

  const handleCopyMarkdown = async () => {
    try {
      await navigator.clipboard.writeText(markdown);
      setCopiedMd(true);
      setTimeout(() => setCopiedMd(false), 2000);
    } catch (e) {
      console.error(e);
    }
  };

  const handleCopyHtml = async () => {
    try {
      await navigator.clipboard.writeText(renderedHtml);
      setCopiedHtml(true);
      setTimeout(() => setCopiedHtml(false), 2000);
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div
      className={`bg-surface flex flex-col transition-all duration-200 ${
        isFullScreen
          ? 'fixed inset-0 z-[9999] w-screen h-screen rounded-none border-none shadow-2xl bg-surface'
          : 'w-full rounded-2xl border border-subtle shadow-sm overflow-hidden'
      }`}
    >
      {/* VS Code Style Header & Toolbar */}
      <div className="bg-surface-muted/95 border-b border-subtle px-4 py-2.5 flex flex-wrap items-center justify-between gap-3 select-none backdrop-blur-md">
        {/* Tab title like VS Code */}
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 px-3 py-1.5 bg-surface border border-subtle rounded-lg shadow-xs text-xs font-semibold text-fg">
            <FileText className="w-4 h-4 text-accent shrink-0" />
            <span className="font-mono text-xs">{fileName}</span>
            <span className="text-2xs text-fg-muted font-normal px-1 py-0.2 bg-surface-muted rounded">Markdown</span>
          </div>

          <div className="hidden md:flex items-center gap-2 text-xs text-fg-muted font-mono pl-2">
            <span>{linesCount.toLocaleString()} 줄</span>
            <span>·</span>
            <span>{wordCount.toLocaleString()} 단어</span>
            <span>·</span>
            <span>{charCount.toLocaleString()} 자</span>
          </div>
        </div>

        {/* View Mode Switcher & Actions */}
        <div className="flex items-center gap-2 flex-wrap">
          {/* Mode Switcher Buttons */}
          <div className="flex items-center bg-surface p-0.5 rounded-xl border border-subtle shadow-xs">
            <button
              type="button"
              onClick={() => setViewMode('preview')}
              className={`text-xs font-bold px-3 py-1.5 rounded-lg transition-all flex items-center gap-1.5 ${
                viewMode === 'preview'
                  ? 'bg-accent text-white shadow-xs'
                  : 'text-fg-muted hover:text-fg hover:bg-surface-muted'
              }`}
              title="Visual Studio Code 마크다운 미리보기"
            >
              <Eye className="w-3.5 h-3.5" />
              <span>미리보기</span>
            </button>

            <button
              type="button"
              onClick={() => setViewMode('split')}
              className={`text-xs font-bold px-3 py-1.5 rounded-lg transition-all flex items-center gap-1.5 ${
                viewMode === 'split'
                  ? 'bg-accent text-white shadow-xs'
                  : 'text-fg-muted hover:text-fg hover:bg-surface-muted'
              }`}
              title="나란히 보기 (좌측 소스 + 우측 렌더링 분할)"
            >
              <Columns className="w-3.5 h-3.5" />
              <span>나란히 보기</span>
            </button>

            <button
              type="button"
              onClick={() => setViewMode('source')}
              className={`text-xs font-bold px-3 py-1.5 rounded-lg transition-all flex items-center gap-1.5 ${
                viewMode === 'source'
                  ? 'bg-accent text-white shadow-xs'
                  : 'text-fg-muted hover:text-fg hover:bg-surface-muted'
              }`}
              title="마크다운 원본 소스 코드"
            >
              <Code2 className="w-3.5 h-3.5" />
              <span>소스 코드</span>
            </button>
          </div>

          {/* Width Toggle in Preview */}
          {viewMode === 'preview' && (
            <button
              type="button"
              onClick={() => setIsFullWidth(!isFullWidth)}
              className="ui-button-secondary text-xs px-2.5 py-1.5 flex items-center gap-1 text-fg-muted hover:text-fg"
              title={isFullWidth ? "표준 폭으로 전환" : "화면 전체 너비로 전환"}
            >
              {isFullWidth ? <AlignCenter className="w-3.5 h-3.5" /> : <AlignLeft className="w-3.5 h-3.5" />}
              <span className="hidden xl:inline">{isFullWidth ? "표준 폭" : "넓은 폭"}</span>
            </button>
          )}

          {/* Copy Actions */}
          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={handleCopyMarkdown}
              className="ui-button-secondary text-xs px-3 py-1.5 flex items-center gap-1.5"
              title="마크다운 텍스트 복사"
            >
              {copiedMd ? (
                <>
                  <Check className="w-3.5 h-3.5 text-emerald-500" />
                  <span className="text-emerald-500 font-bold">복사됨!</span>
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">마크다운 복사</span>
                </>
              )}
            </button>

            <button
              type="button"
              onClick={handleCopyHtml}
              className="ui-button-secondary text-xs px-3 py-1.5 flex items-center gap-1.5 text-fg-muted hover:text-fg"
              title="렌더링된 HTML 복사"
            >
              {copiedHtml ? (
                <>
                  <Check className="w-3.5 h-3.5 text-emerald-500" />
                  <span className="text-emerald-500 font-bold">HTML 복사됨!</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-3.5 h-3.5 text-indigo-500" />
                  <span className="hidden sm:inline">HTML 복사</span>
                </>
              )}
            </button>

            {downloadUrl && (
              <a
                href={downloadUrl}
                download={fileName}
                className="ui-button-primary text-xs px-3 py-1.5 flex items-center gap-1.5 shadow-xs"
                title="마크다운 파일 다운로드"
              >
                <Download className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">다운로드</span>
              </a>
            )}

            {/* Fullscreen Button */}
            <button
              type="button"
              onClick={() => setIsFullScreen(!isFullScreen)}
              className={`p-1.5 rounded-xl border transition-all flex items-center gap-1.5 ${
                isFullScreen
                  ? 'bg-rose-500 text-white border-rose-600 hover:bg-rose-600 shadow-sm px-3'
                  : 'bg-surface border-subtle text-fg-muted hover:text-fg hover:bg-surface-muted shadow-xs px-2.5'
              }`}
              title={isFullScreen ? "전체화면 닫기 (ESC)" : "전체 화면으로 미리보기"}
            >
              {isFullScreen ? (
                <>
                  <X className="w-4 h-4" />
                  <span className="text-xs font-bold">전체화면 닫기 (ESC)</span>
                </>
              ) : (
                <>
                  <Maximize2 className="w-3.5 h-3.5 text-accent" />
                  <span className="text-xs font-bold text-fg">전체 화면</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Main Body depending on ViewMode */}
      <div
        className={`flex-1 overflow-hidden ${
          isFullScreen ? 'h-[calc(100vh-76px)]' : 'min-h-[460px] max-h-[680px]'
        }`}
      >
        {/* 1. Preview Only */}
        {viewMode === 'preview' && (
          <div className="h-full overflow-y-auto p-6 sm:p-10 md:p-14 bg-surface markdown-preview-body selection:bg-accent/20">
            <div
              className={`mx-auto prose dark:prose-invert prose-slate prose-sm sm:prose-base leading-relaxed ${
                isFullWidth ? 'max-w-none px-4' : 'max-w-4xl'
              }`}
              dangerouslySetInnerHTML={{ __html: renderedHtml }}
            />
          </div>
        )}

        {/* 2. Split View (Side-by-Side: Source Left, Preview Right) */}
        {viewMode === 'split' && (
          <div className="h-full grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-subtle">
            {/* Left: Source Editor */}
            <div className="h-full overflow-y-auto bg-surface-muted/30 p-5 font-mono text-xs text-fg leading-relaxed select-all">
              <div className="flex items-center justify-between pb-2 mb-3 border-b border-subtle text-2xs font-bold text-fg-muted uppercase tracking-wider sticky top-0 bg-surface-muted/90 backdrop-blur-xs py-1">
                <span>Markdown Source Editor</span>
                <span>UTF-8 · {linesCount} Lines</span>
              </div>
              <pre className="font-mono text-xs sm:text-sm leading-relaxed text-fg whitespace-pre-wrap">
                {markdown}
              </pre>
            </div>

            {/* Right: Live Preview */}
            <div className="h-full overflow-y-auto p-6 md:p-8 bg-surface markdown-preview-body selection:bg-accent/20">
              <div className="flex items-center justify-between pb-2 mb-3 border-b border-subtle text-2xs font-bold text-accent uppercase tracking-wider sticky top-0 bg-surface/90 backdrop-blur-xs py-1">
                <span>Live Preview Output</span>
                <span className="text-fg-muted font-normal">GFM Standard</span>
              </div>
              <div
                className="prose dark:prose-invert prose-slate prose-sm sm:prose-base leading-relaxed"
                dangerouslySetInnerHTML={{ __html: renderedHtml }}
              />
            </div>
          </div>
        )}

        {/* 3. Source Code Only */}
        {viewMode === 'source' && (
          <div className="h-full overflow-y-auto bg-surface-muted/40 p-6 md:p-10 font-mono text-xs text-fg leading-relaxed select-all">
            <div className="max-w-5xl mx-auto">
              <div className="flex items-center justify-between pb-3 mb-4 border-b border-subtle text-xs font-bold text-fg-muted">
                <span>{fileName} ({linesCount} lines, {charCount.toLocaleString()} chars)</span>
                <span>Plaintext / Markdown</span>
              </div>
              <pre className="font-mono text-xs sm:text-sm leading-relaxed text-fg whitespace-pre-wrap bg-surface p-6 rounded-2xl border border-subtle shadow-xs">
                {markdown}
              </pre>
            </div>
          </div>
        )}
      </div>

      {/* VS Code Style Status Footer */}
      <div className="bg-surface-muted/90 border-t border-subtle px-4 py-1.5 flex items-center justify-between text-2xs text-fg-muted font-mono select-none">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1 font-semibold text-fg">
            <BookOpen className="w-3.5 h-3.5 text-accent" />
            GitHub Flavored Markdown
          </span>
          <span className="hidden sm:inline">UTF-8</span>
          <span className="hidden sm:inline">Spaces: 2</span>
        </div>
        <div className="flex items-center gap-3">
          <span>Ln {linesCount}, Col 1</span>
          <span>{charCount.toLocaleString()} characters</span>
          {isFullScreen && (
            <span className="px-1.5 py-0.5 rounded bg-accent/10 text-accent font-bold">
              ESC 키로 닫기
            </span>
          )}
        </div>
      </div>
    </div>
  );
};
