/**
 * 파일명: MarkdownPreviewStudio.tsx
 * 경로: apps/web/src/features/converter/MarkdownPreviewStudio.tsx
 * 목적: Markdown 문서 미리보기 및 원본 대조(페이지별/전체 연속 동기화) 화면을 제공함
 * 작성자: 개발팀
 * 작성일: 2026-09-09
 * 수정일: 2026-09-12
 */
import React, { useState, useMemo, useEffect, useRef } from 'react';
import { marked } from 'marked';
import * as pdfjsLib from 'pdfjs-dist';
import pdfWorkerUrl from 'pdfjs-dist/build/pdf.worker.mjs?url';
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
  AlignCenter,
  Image as ImageIcon,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  ExternalLink,
  Layers,
  Globe
} from 'lucide-react';

pdfjsLib.GlobalWorkerOptions.workerSrc = pdfWorkerUrl;

export interface MarkdownPreviewStudioProps {
  markdown?: string;
  fileName?: string;
  downloadUrl?: string;
  originalFile?: File | null;
  originalUrl?: string;
  htmlPreview?: string;
  pagesCount?: number;
  initialRightTab?: 'html' | 'markdown' | 'source';
}

interface PageItem {
  pageNumber: number;
  title: string;
  markdown: string;
  charCount: number;
  linesCount: number;
}

interface PdfCanvasPageProps {
  pdfDocument: any;
  pageNumber: number;
  zoomLevel: number;
}

// PDF 페이지를 Canvas 2D 컨텍스트로 비동기 렌더링하는 컴포넌트임
const PdfCanvasPage: React.FC<PdfCanvasPageProps> = ({ pdfDocument, pageNumber, zoomLevel }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isRendering, setIsRendering] = useState(true);

  useEffect(() => {
    let cancelled = false;
    let renderTask: any = null;

    const renderPage = async () => {
      if (!pdfDocument || !canvasRef.current) return;
      setIsRendering(true);
      try {
        const page = await pdfDocument.getPage(pageNumber);
        if (cancelled || !canvasRef.current) return;
        const scale = Math.max(0.35, zoomLevel / 100);
        const viewport = page.getViewport({ scale });
        const canvas = canvasRef.current;
        const context = canvas.getContext('2d');
        if (!context) return;
        const outputScale = Math.max(1, window.devicePixelRatio || 1);
        canvas.width = Math.floor(viewport.width * outputScale);
        canvas.height = Math.floor(viewport.height * outputScale);
        canvas.style.width = `${Math.floor(viewport.width)}px`;
        canvas.style.height = `${Math.floor(viewport.height)}px`;
        renderTask = page.render({
          canvasContext: context,
          viewport,
          transform: outputScale !== 1 ? [outputScale, 0, 0, outputScale, 0, 0] : undefined,
        });
        await renderTask.promise;
      } catch (error: any) {
        if (error?.name !== 'RenderingCancelledException') {
          console.error('PDF 페이지 렌더링 실패:', error);
        }
      } finally {
        if (!cancelled) setIsRendering(false);
      }
    };

    renderPage();

    return () => {
      cancelled = true;
      try {
        renderTask?.cancel?.();
      } catch {}
    };
  }, [pdfDocument, pageNumber, zoomLevel]);

  return (
    <div className="relative flex justify-center">
      {isRendering && (
        <div className="absolute inset-0 flex items-center justify-center text-2xs text-fg-muted bg-white/70">
          렌더링 중
        </div>
      )}
      <canvas ref={canvasRef} className="max-w-full bg-white shadow-sm" />
    </div>
  );
};

// 파일 포맷과 미리보기 데이터 유무에 따라 우측 탭의 기본 활성 모드를 결정함
function resolveInitialRightTab(
  initialRightTab: MarkdownPreviewStudioProps['initialRightTab'],
  htmlPreview: string | undefined,
  markdown: string,
  fileName: string
): 'html' | 'markdown' | 'source' {
  if (initialRightTab) return initialRightTab;
  if (
    htmlPreview &&
    (!markdown || /\.(html?|docx?|hwpx?|pdf)$/i.test(fileName))
  ) {
    return 'html';
  }
  return 'markdown';
}

/**
 * 마크다운 본문에서 페이지 분할 표식을 감지하여 개별 페이지 항목으로 분할함
 */
function parseMarkdownPages(markdown: string, expectedPages?: number): PageItem[] {
  if (!markdown || !markdown.trim()) {
    return [
      {
        pageNumber: 1,
        title: '1 페이지',
        markdown: '',
        charCount: 0,
        linesCount: 0,
      }
    ];
  }

  // 페이지 구분자 패턴 정규식: "## Page 1", "## 페이지 1", "### Page 1", "<!-- Page 1 -->" 등 감지함
  const pageHeaderRegex = /(?:^|\n)(?:#{1,3}\s+(?:Page|페이지|PAGE)\s*(\d+)|<!--\s*(?:Page|PAGE|페이지)\s*(\d+)\s*-->|(?:^|\n)##\s+(\d+)\s*(?:p|페이지|Page)?(?:\s|$))/gi;
  const matches: { index: number; pageNumber: number; rawHeader: string }[] = [];
  let match: RegExpExecArray | null;

  while ((match = pageHeaderRegex.exec(markdown)) !== null) {
    const rawNo = match[1] || match[2] || match[3];
    const pNo = parseInt(rawNo, 10);
    const startIndex = match[0].startsWith('\n') ? match.index + 1 : match.index;
    matches.push({
      index: startIndex,
      pageNumber: pNo,
      rawHeader: match[0].trim(),
    });
  }

  // 페이지 구분자가 없을 경우: expectedPages가 주어지면 라인 단위로 균등 분할하여 개별 페이지 식별자 생성함
  if (matches.length === 0) {
    if (expectedPages && expectedPages > 1) {
      const allLines = markdown.split('\n');
      const linesPerPage = Math.max(1, Math.ceil(allLines.length / expectedPages));
      const pages: PageItem[] = [];
      for (let pIdx = 0; pIdx < expectedPages; pIdx++) {
        const start = pIdx * linesPerPage;
        const end = Math.min(allLines.length, start + linesPerPage);
        const pageLines = allLines.slice(start, end);
        const pageMd = pageLines.join('\n').trim();
        pages.push({
          pageNumber: pIdx + 1,
          title: `${pIdx + 1} 페이지`,
          markdown: pageMd,
          charCount: pageMd.length,
          linesCount: pageLines.length,
        });
      }
      return pages;
    }

    return [
      {
        pageNumber: 1,
        title: '전체 문서',
        markdown: markdown,
        charCount: markdown.length,
        linesCount: markdown.split('\n').length,
      }
    ];
  }

  const pages: PageItem[] = [];
  for (let i = 0; i < matches.length; i++) {
    const current = matches[i];
    const next = matches[i + 1];
    const rawContent = next
      ? markdown.slice(current.index, next.index)
      : markdown.slice(current.index);

    let finalContent = rawContent.trim();
    // 첫 번째 페이지 앞에 서문(타이틀 등)이 존재할 경우 1페이지 상단에 병합함
    if (i === 0 && current.index > 0) {
      const intro = markdown.slice(0, current.index).trim();
      if (intro) {
        finalContent = `${intro}\n\n${finalContent}`;
      }
    }

    pages.push({
      pageNumber: current.pageNumber,
      title: `${current.pageNumber} 페이지`,
      markdown: finalContent,
      charCount: finalContent.length,
      linesCount: finalContent.split('\n').length,
    });
  }

  return pages;
}

// 문서 변환 결과 미리보기, 원본 대조 뷰 및 동기화 스크롤 네비게이션을 제공하는 스튜디오 컴포넌트임
export const MarkdownPreviewStudio: React.FC<MarkdownPreviewStudioProps> = ({
  markdown = '',
  fileName = 'converted_document.md',
  downloadUrl,
  originalFile,
  originalUrl,
  htmlPreview,
  pagesCount,
  initialRightTab,
}) => {
  const hasOriginal = Boolean(originalFile || originalUrl);
  const [viewMode, setViewMode] = useState<'preview' | 'split' | 'source'>(() => {
    return hasOriginal ? 'split' : 'preview';
  });
  const [leftPaneMode, setLeftPaneMode] = useState<'original' | 'source'>(() => {
    return hasOriginal ? 'original' : 'source';
  });
  const [rightFormatTab, setRightFormatTab] = useState<'html' | 'markdown' | 'source'>(() => {
    return resolveInitialRightTab(initialRightTab, htmlPreview, markdown, fileName);
  });
  const [zoomLevel, setZoomLevel] = useState<number>(100);
  const [objectUrl, setObjectUrl] = useState<string | null>(null);
  const [copiedMd, setCopiedMd] = useState(false);
  const [copiedHtml, setCopiedHtml] = useState(false);
  const [isFullScreen, setIsFullScreen] = useState(false);
  const [isFullWidth, setIsFullWidth] = useState(false);

  // 페이지 선택 없이 전체 문서를 연속 스크롤로 비교함
  const [compareScope] = useState<'all' | 'page'>('all');
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [syncScroll, setSyncScroll] = useState<boolean>(true);
  const [visiblePageInAllMode, setVisiblePageInAllMode] = useState<number>(1);
  const [pdfViewerSrc, setPdfViewerSrc] = useState<string>('');
  const [pdfDocument, setPdfDocument] = useState<any>(null);
  const [pdfDetectedPages, setPdfDetectedPages] = useState<number | undefined>(undefined);
  const [pdfLoadError, setPdfLoadError] = useState<string | null>(null);
  const [commonScrollRatio, setCommonScrollRatio] = useState<number>(0);

  // 스크롤 동기화 컨테이너 및 상태 Ref 정의함
  const previewScrollRef = useRef<HTMLDivElement>(null);
  const leftScrollRef = useRef<HTMLDivElement>(null);
  const rightScrollRef = useRef<HTMLDivElement>(null);
  const commonTrackRef = useRef<HTMLDivElement>(null);
  const sourceScrollRef = useRef<HTMLDivElement>(null);
  const htmlIframeRef = useRef<HTMLIFrameElement>(null);
  const isSyncingRef = useRef<boolean>(false);
  const activePdfPageRef = useRef<number>(1);
  const lastWheelTransitionRef = useRef<number>(0);
  const isJumpingRef = useRef<boolean>(false);
  const jumpTimerRef = useRef<any>(null);

  useEffect(() => {
    setRightFormatTab(resolveInitialRightTab(initialRightTab, htmlPreview, markdown, fileName));
  }, [fileName, htmlPreview, initialRightTab, markdown]);

  // 마크다운 페이지 분할 계산함 (페이지 표식 누락 시에도 pagesCount 기반 동적 파티셔닝 지원)
  const parsedPages = useMemo(() => parseMarkdownPages(markdown, pagesCount), [markdown, pagesCount]);
  const totalPages = Math.max(parsedPages.length, pagesCount || pdfDetectedPages || 1);

  // 총 페이지 수 변경 시 유효 범위 보정함
  useEffect(() => {
    if (currentPage > totalPages && totalPages > 0) {
      setCurrentPage(1);
    }
  }, [totalPages, currentPage]);

  const currentPageItem = useMemo(() => {
    const found = parsedPages.find(p => p.pageNumber === currentPage);
    return (
      found ||
      parsedPages[0] || {
        pageNumber: 1,
        title: '1 페이지',
        markdown: markdown,
        charCount: markdown.length,
        linesCount: markdown.split('\n').length,
      }
    );
  }, [parsedPages, currentPage, markdown]);

  // 원본 파일(이미지 또는 PDF)에 대한 임시 ObjectURL 생성 및 해제함
  useEffect(() => {
    if (originalFile) {
      const isImg =
        originalFile.type.startsWith('image/') ||
        /\.(png|jpe?g|gif|webp|bmp|tiff?|heic)$/i.test(originalFile.name);
      const isPdf =
        originalFile.type === 'application/pdf' ||
        /\.pdf$/i.test(originalFile.name);

      if (isImg || isPdf) {
        const url = URL.createObjectURL(originalFile);
        setObjectUrl(url);
        return () => {
          URL.revokeObjectURL(url);
        };
      }
    }
    setObjectUrl(null);
  }, [originalFile]);

  // 앱 내부 PDF 렌더링은 CORS 영향을 피하기 위해 업로드 Blob URL을 우선 사용함
  const effectiveOriginalUrl = objectUrl || originalUrl;

  const isPdfOriginal = useMemo(() => {
    if (originalFile) {
      return (
        originalFile.type === 'application/pdf' ||
        /\.pdf$/i.test(originalFile.name)
      );
    }
    if (originalUrl) {
      return /\.pdf/i.test(originalUrl) || originalUrl.toLowerCase().includes('.pdf');
    }
    return false;
  }, [originalFile, originalUrl]);

  const buildPdfViewerSrc = (page?: number) => {
    if (!effectiveOriginalUrl) return '';
    const base = effectiveOriginalUrl.split('#')[0];
    return page && page > 1
      ? `${base}#page=${page}&zoom=page-width`
      : `${base}#view=FitH&zoom=page-width`;
  };

  useEffect(() => {
    if (!isPdfOriginal || !effectiveOriginalUrl) {
      setPdfViewerSrc('');
      setPdfDocument(null);
      setPdfDetectedPages(undefined);
      setPdfLoadError(null);
      return;
    }
    let cancelled = false;
    activePdfPageRef.current = 1;
    setPdfViewerSrc(buildPdfViewerSrc(1));
    setPdfDocument(null);
    setPdfDetectedPages(undefined);
    setPdfLoadError(null);
    const loadingTask = pdfjsLib.getDocument({ url: effectiveOriginalUrl });
    loadingTask.promise
      .then((pdf: any) => {
        if (cancelled) return;
        setPdfDocument(pdf);
        setPdfDetectedPages(pdf.numPages || undefined);
      })
      .catch((error: any) => {
        if (cancelled) return;
        console.error('PDF 원본 로딩 실패:', error);
        setPdfLoadError('PDF 원본을 앱 내부 뷰어로 불러오지 못했습니다. 새 탭에서 원본을 확인해 주세요.');
      });

    return () => {
      cancelled = true;
      try {
        loadingTask.destroy?.();
      } catch {}
    };
  }, [isPdfOriginal, effectiveOriginalUrl]);

  const isImageOriginal = useMemo(() => {
    if (originalFile) {
      return (
        originalFile.type.startsWith('image/') ||
        /\.(png|jpe?g|gif|webp|bmp|tiff?|heic)$/i.test(originalFile.name)
      );
    }
    if (originalUrl) {
      return /\.(png|jpe?g|gif|webp|bmp|tiff?|heic)/i.test(originalUrl);
    }
    return false;
  }, [originalFile, originalUrl]);

  // 컨테이너 내부 특정 대상 요소로 정확한 픽셀 단위 신속 스크롤 이동 함수 정의함
  const scrollToTargetInContainer = (container: HTMLElement, target: HTMLElement) => {
    const containerRect = container.getBoundingClientRect();
    const targetRect = target.getBoundingClientRect();
    const targetScrollTop = container.scrollTop + (targetRect.top - containerRect.top) - 16;
    container.scrollTo({ top: Math.max(0, targetScrollTop), behavior: 'auto' });
  };

  const scrollRatioOf = (el: HTMLElement | null): number => {
    if (!el) return 0;
    const maxScroll = el.scrollHeight - el.clientHeight;
    return maxScroll > 0 ? el.scrollTop / maxScroll : 0;
  };

  const applyRatioTo = (el: HTMLElement | null, ratio: number) => {
    if (!el) return;
    const maxScroll = el.scrollHeight - el.clientHeight;
    el.scrollTop = Math.max(0, maxScroll * Math.max(0, Math.min(1, ratio)));
  };

  const clampRatio = (ratio: number) => Math.max(0, Math.min(1, Number.isFinite(ratio) ? ratio : 0));

  const ratioFromTrackPointer = (clientY: number) => {
    const track = commonTrackRef.current;
    if (!track) return 0;
    const rect = track.getBoundingClientRect();
    if (rect.height <= 0) return 0;
    return clampRatio((clientY - rect.top) / rect.height);
  };

  const pageFromRatio = (ratio: number) =>
    Math.max(1, Math.min(totalPages, Math.round(clampRatio(ratio) * (totalPages - 1)) + 1));

  const ratioFromPage = (page: number) =>
    totalPages > 1 ? (Math.max(1, Math.min(totalPages, page)) - 1) / (totalPages - 1) : 0;

  const updatePdfPositionByRatio = (ratio: number) => {
    if (!isPdfOriginal || !effectiveOriginalUrl || totalPages <= 1) return;
    const page = pageFromRatio(ratio);
    if (page === activePdfPageRef.current && pdfViewerSrc) return;
    activePdfPageRef.current = page;
    setCurrentPage(page);
    setVisiblePageInAllMode(page);
    setPdfViewerSrc(buildPdfViewerSrc(page));
  };

  const updateHtmlPositionByRatio = (ratio: number) => {
    if (totalPages <= 1) return;
    const page = pageFromRatio(ratio);
    setCurrentPage(page);
    setVisiblePageInAllMode(page);
    if (!htmlIframeRef.current) return;
    try {
      htmlIframeRef.current.contentWindow?.postMessage({ type: 'scrollToRatio', ratio }, '*');
      htmlIframeRef.current.contentWindow?.postMessage({ type: 'scrollToPage', page }, '*');
    } catch {}
  };

  const moveSyncedViewToRatio = (ratio: number) => {
    const clampedRatio = clampRatio(ratio);
    isSyncingRef.current = true;
    applyRatioTo(leftScrollRef.current, clampedRatio);
    applyRatioTo(rightScrollRef.current, clampedRatio);
    updatePdfPositionByRatio(clampedRatio);
    updateHtmlPositionByRatio(clampedRatio);
    updateCommonScrollbarFromRatio(clampedRatio);
    requestAnimationFrame(() => {
      isSyncingRef.current = false;
    });
  };

  const updateCommonScrollbarFromRatio = (ratio: number) => {
    setCommonScrollRatio(clampRatio(ratio));
  };

  // 특정 페이지 번호로 이동 처리함 (연속 스크롤 및 요소 위치 기반 정확한 페이지 탐색)
  const handleJumpToPage = (targetPage: number, options?: { updatePdf?: boolean }) => {
    const validPage = Math.max(1, Math.min(totalPages, targetPage));
    setCurrentPage(validPage);
    setVisiblePageInAllMode(validPage);

    // 프로그래밍 방식 점프 중에는 스크롤 리스너가 currentPage를 덮어쓰지 않도록 일시 잠금함
    isJumpingRef.current = true;
    if (jumpTimerRef.current) clearTimeout(jumpTimerRef.current);
    jumpTimerRef.current = setTimeout(() => {
      isJumpingRef.current = false;
    }, 500);

    // 1. 단독 미리보기 뷰 스크롤 이동함
    if (viewMode === 'preview' && previewScrollRef.current) {
      const container = previewScrollRef.current;
      const targetEl = container.querySelector<HTMLElement>(`#preview-page-${validPage}`);
      if (targetEl) {
        scrollToTargetInContainer(container, targetEl);
      } else {
        const maxScroll = container.scrollHeight - container.clientHeight;
        if (maxScroll > 0 && totalPages > 1) {
          container.scrollTo({ top: ((validPage - 1) / (totalPages - 1)) * maxScroll, behavior: 'auto' });
        }
      }
    }

    // 2. 분할 뷰 우측 변환 결과 스크롤 이동함
    if (viewMode === 'split' && rightScrollRef.current) {
      const container = rightScrollRef.current;
      if (compareScope === 'page') {
        container.scrollTop = 0;
      } else {
        const targetRightEl = container.querySelector<HTMLElement>(
          rightFormatTab === 'source' ? `#source-page-${validPage}` : `#preview-page-${validPage}`
        );
        if (targetRightEl) {
          scrollToTargetInContainer(container, targetRightEl);
        } else {
          const maxScroll = container.scrollHeight - container.clientHeight;
          if (maxScroll > 0 && totalPages > 1) {
            container.scrollTo({ top: ((validPage - 1) / (totalPages - 1)) * maxScroll, behavior: 'auto' });
          }
        }
      }
    }

    // 3. 분할 뷰 좌측 마크다운 소스 스크롤 이동함
    if (viewMode === 'split' && leftPaneMode === 'source' && leftScrollRef.current) {
      const container = leftScrollRef.current;
      if (compareScope === 'page') {
        container.scrollTop = 0;
      } else {
        const targetLeftEl = container.querySelector<HTMLElement>(`#source-page-${validPage}`);
        if (targetLeftEl) {
          scrollToTargetInContainer(container, targetLeftEl);
        } else {
          const maxScroll = container.scrollHeight - container.clientHeight;
          if (maxScroll > 0 && totalPages > 1) {
            container.scrollTo({ top: ((validPage - 1) / (totalPages - 1)) * maxScroll, behavior: 'auto' });
          }
        }
      }
    }

    // 4. 소스 코드 단독 뷰 스크롤 이동함
    if (viewMode === 'source' && sourceScrollRef.current) {
      const container = sourceScrollRef.current;
      const targetEl = container.querySelector<HTMLElement>(`#source-standalone-page-${validPage}`);
      if (targetEl) {
        scrollToTargetInContainer(container, targetEl);
      } else {
        const maxScroll = container.scrollHeight - container.clientHeight;
        if (maxScroll > 0 && totalPages > 1) {
          container.scrollTo({ top: ((validPage - 1) / (totalPages - 1)) * maxScroll, behavior: 'auto' });
        }
      }
    }

    // 5. 좌측 PDF/이미지 원본 스크롤 연동함
    if (viewMode === 'split' && leftPaneMode === 'original' && leftScrollRef.current && totalPages > 1) {
      const originalContainer = leftScrollRef.current;
      const targetOriginalEl = isPdfOriginal
        ? originalContainer.querySelector<HTMLElement>(`#original-pdf-page-${validPage}`)
        : null;
      if (targetOriginalEl) {
        scrollToTargetInContainer(originalContainer, targetOriginalEl);
      } else {
        const maxScroll = originalContainer.scrollHeight - originalContainer.clientHeight;
        if (maxScroll > 0) {
          originalContainer.scrollTo({ top: ((validPage - 1) / (totalPages - 1)) * maxScroll, behavior: 'auto' });
        }
      }
    }

    // 6. 좌측 PDF 대조 뷰어 이동함
    if (options?.updatePdf !== false && isPdfOriginal && effectiveOriginalUrl && totalPages > 1) {
      activePdfPageRef.current = validPage;
      setPdfViewerSrc(buildPdfViewerSrc(validPage));
    }

    // 7. 우측 및 단독 뷰의 고충실도 HTML 뷰어 내부 페이지 위치로 신속 이동함
    if (htmlIframeRef.current) {
      try {
        htmlIframeRef.current.contentWindow?.postMessage({ type: 'scrollToPage', page: validPage }, '*');
      } catch {}
      try {
        const doc = htmlIframeRef.current.contentDocument;
        if (doc) {
          const pageEl = doc.getElementById(`page-${validPage}`);
          if (pageEl) {
            pageEl.scrollIntoView({ behavior: 'auto', block: 'start' });
            const win = doc.defaultView;
            const top = pageEl.getBoundingClientRect().top + (win?.scrollY || doc.documentElement.scrollTop || 0) - 20;
            if (win) win.scrollTo({ top, behavior: 'auto' });
            doc.documentElement.scrollTop = top;
            doc.body.scrollTop = top;
          }
        }
      } catch {}
    }
  };

  // 우측 포맷 탭 전환 핸들러 정의함 (탭 전환 후 즉시 현재 페이지 위치로 동기화 스크롤)
  const handleFormatTabChange = (tab: 'html' | 'markdown' | 'source') => {
    setRightFormatTab(tab);
    setTimeout(() => {
      handleJumpToPage(currentPage, { updatePdf: false });
    }, 60);
  };

  // HTML 미리보기 iframe으로부터 실시간 스크롤 페이지 감지 수신함
  useEffect(() => {
    const handleMessage = (e: MessageEvent) => {
      if (isJumpingRef.current) return;
      if (e.data?.type === 'pageScrolled' && typeof e.data.page === 'number') {
        const p = e.data.page;
        if (p >= 1 && p <= totalPages && p !== currentPage) {
          setCurrentPage(p);
          setVisiblePageInAllMode(p);
          if (viewMode === 'split' && rightFormatTab === 'html') {
            const ratio = totalPages > 1 ? (p - 1) / (totalPages - 1) : 0;
            updateCommonScrollbarFromRatio(ratio);
            if (syncScroll && !isSyncingRef.current) {
              isSyncingRef.current = true;
              applyRatioTo(leftScrollRef.current, ratio);
              updatePdfPositionByRatio(ratio);
              requestAnimationFrame(() => {
                isSyncingRef.current = false;
              });
            }
          }
        }
      }
    };
    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, [totalPages, currentPage, viewMode, rightFormatTab, syncScroll]);

  // ESC 키 및 키보드 상하/좌우 페이지 탐색 핸들러 등록함
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isFullScreen) {
        setIsFullScreen(false);
        return;
      }
      const activeTag = document.activeElement?.tagName.toLowerCase();
      if (activeTag === 'input' || activeTag === 'textarea' || activeTag === 'select') {
        return;
      }
      if (totalPages <= 1) return;

      if (e.key === 'ArrowUp' || e.key === 'PageUp') {
        e.preventDefault();
        handleJumpToPage(currentPage - 1, { updatePdf: true });
      } else if (e.key === 'ArrowDown' || e.key === 'PageDown') {
        e.preventDefault();
        handleJumpToPage(currentPage + 1, { updatePdf: true });
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault();
        handleJumpToPage(currentPage - 1, { updatePdf: true });
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        handleJumpToPage(currentPage + 1, { updatePdf: true });
      } else if (e.key === 'Home') {
        e.preventDefault();
        handleJumpToPage(1, { updatePdf: true });
      } else if (e.key === 'End') {
        e.preventDefault();
        handleJumpToPage(totalPages, { updatePdf: true });
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isFullScreen, currentPage, totalPages, viewMode, leftPaneMode]);

  // 전체화면 시 스크롤 잠금 처리함
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

  // 단일 페이지 렌더링 HTML 생성함
  const renderedCurrentPageHtml = useMemo(() => {
    try {
      return marked.parse(currentPageItem.markdown, { gfm: true, breaks: true }) as string;
    } catch {
      return '<p class="text-rose-500 font-bold p-4">마크다운 렌더링 중 오류가 발생했습니다.</p>';
    }
  }, [currentPageItem.markdown]);

  // 전체 페이지 렌더링 HTML 맵 생성함 (전체 연속 모드용)
  const parsedPagesHtmlMap = useMemo(() => {
    const map = new Map<number, string>();
    for (const p of parsedPages) {
      try {
        map.set(p.pageNumber, marked.parse(p.markdown, { gfm: true, breaks: true }) as string);
      } catch {
        map.set(
          p.pageNumber,
          '<p class="text-rose-500 font-bold p-4">페이지 마크다운 렌더링 중 오류가 발생했습니다.</p>'
        );
      }
    }
    return map;
  }, [parsedPages]);

  // 전체 문서 HTML 생성함
  const renderedFullHtml = useMemo(() => {
    try {
      return marked.parse(markdown, { gfm: true, breaks: true }) as string;
    } catch {
      return '<p class="text-rose-500 font-bold p-4">마크다운 렌더링 중 오류가 발생했습니다.</p>';
    }
  }, [markdown]);

  // HTML 미리보기 iframe 내부와 부모 창 간 양방향 스크롤/페이지 이동 통신 스크립트 주입함
  const effectiveHtmlPreview = useMemo(() => {
    if (!htmlPreview) return '';
    const styleTag = `
<style>
html, body {
  scrollbar-width: none;
  -ms-overflow-style: none;
}
html::-webkit-scrollbar,
body::-webkit-scrollbar {
  width: 0;
  height: 0;
}
</style>
`;
    const scriptTag = `
<script>
(function() {
  window.addEventListener('message', function(e) {
    if (e.data && e.data.type === 'scrollToRatio' && typeof e.data.ratio === 'number') {
      var maxScroll = Math.max(
        0,
        (document.documentElement.scrollHeight || document.body.scrollHeight || 0) - window.innerHeight
      );
      window.scrollTo({ top: maxScroll * Math.max(0, Math.min(1, e.data.ratio)), behavior: 'auto' });
      return;
    }
    if (e.data && e.data.type === 'scrollToPage' && typeof e.data.page === 'number') {
      var p = e.data.page;
      var el = document.getElementById('page-' + p) || 
               document.querySelector('[data-page-number="' + p + '"]') || 
               document.querySelectorAll('.pdf-page-card')[p - 1];
      if (el) {
        var top = el.getBoundingClientRect().top + (window.scrollY || document.documentElement.scrollTop || 0) - 16;
        window.scrollTo({ top: Math.max(0, top), behavior: 'auto' });
      }
    }
  });

  var scrollTimer = null;
  window.addEventListener('scroll', function() {
    if (scrollTimer) return;
    scrollTimer = setTimeout(function() {
      scrollTimer = null;
      var cards = document.querySelectorAll('.pdf-page-card, [id^="page-"]');
      if (!cards || cards.length === 0) return;
      var detected = 1;
      for (var i = 0; i < cards.length; i++) {
        var r = cards[i].getBoundingClientRect();
        if (r.top <= 220) {
          var idMatch = cards[i].id ? cards[i].id.match(/page-(\\d+)/) : null;
          detected = idMatch ? parseInt(idMatch[1], 10) : (i + 1);
        } else {
          break;
        }
      }
      try {
        window.parent.postMessage({ type: 'pageScrolled', page: detected }, '*');
      } catch (err) {}
    }, 60);
  }, { passive: true });
})();
</script>
`;
    const styledHtml = htmlPreview.includes('</head>')
      ? htmlPreview.replace('</head>', `${styleTag}</head>`)
      : `${styleTag}${htmlPreview}`;

    if (styledHtml.includes('</body>')) {
      return styledHtml.replace('</body>', `${scriptTag}</body>`);
    }
    return `${styledHtml}${scriptTag}`;
  }, [htmlPreview]);

  // 스크롤 위치 기반 실시간 가시 페이지 감지 처리함
  const updateVisiblePageFromScroll = (container: HTMLElement) => {
    if (totalPages <= 1 || isJumpingRef.current) return;
    const pageNodes = container.querySelectorAll<HTMLElement>('[data-page-number]');
    if (!pageNodes || pageNodes.length === 0) return;

    const containerRect = container.getBoundingClientRect();
    let detectedPage = 1;

    for (let i = 0; i < pageNodes.length; i++) {
      const el = pageNodes[i];
      const rect = el.getBoundingClientRect();
      const relativeTop = rect.top - containerRect.top;
      if (relativeTop <= 180) {
        detectedPage = Number(el.dataset.pageNumber) || (i + 1);
      } else {
        break;
      }
    }

    if (detectedPage >= 1 && detectedPage <= totalPages) {
      if (detectedPage !== currentPage) {
        setCurrentPage(detectedPage);
        setVisiblePageInAllMode(detectedPage);
      }
    }
  };

  // 단독 미리보기 스크롤 핸들러 정의함
  const handlePreviewScroll = () => {
    if (isJumpingRef.current) return;
    const previewEl = previewScrollRef.current;
    if (!previewEl) return;
    updateVisiblePageFromScroll(previewEl);
  };

  // 소스 코드 단독 뷰 스크롤 핸들러 정의함
  const handleSourceScroll = () => {
    if (isJumpingRef.current) return;
    const sourceEl = sourceScrollRef.current;
    if (!sourceEl) return;
    updateVisiblePageFromScroll(sourceEl);
  };

  const handleLeftScroll = () => {
    if (isJumpingRef.current) return;
    const leftEl = leftScrollRef.current;
    if (!leftEl) return;

    // 좌측 스크롤 위치에서도 가시 페이지 감지함
    updateVisiblePageFromScroll(leftEl);
    updateCommonScrollbarFromRatio(scrollRatioOf(leftEl));

    if (!syncScroll || isSyncingRef.current) return;
    isSyncingRef.current = true;
    const ratio = scrollRatioOf(leftEl);
    applyRatioTo(rightScrollRef.current, ratio);
    updatePdfPositionByRatio(ratio);
    updateHtmlPositionByRatio(ratio);
    requestAnimationFrame(() => {
      isSyncingRef.current = false;
    });
  };

  const handleRightScroll = () => {
    if (isJumpingRef.current) return;
    const rightEl = rightScrollRef.current;
    if (!rightEl) return;

    // 현재 스크롤 위치 기반 실시간 가시 페이지 감지함
    updateVisiblePageFromScroll(rightEl);
    updateCommonScrollbarFromRatio(scrollRatioOf(rightEl));

    if (!syncScroll || isSyncingRef.current) return;
    const leftEl = leftScrollRef.current;

    isSyncingRef.current = true;
    const ratio = scrollRatioOf(rightEl);
    applyRatioTo(leftEl, ratio);
    updatePdfPositionByRatio(ratio);
    updateHtmlPositionByRatio(ratio);
    requestAnimationFrame(() => {
      isSyncingRef.current = false;
    });
  };

  const handleCommonPointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.currentTarget.setPointerCapture(e.pointerId);
    moveSyncedViewToRatio(ratioFromTrackPointer(e.clientY));
  };

  const handleCommonPointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    if ((e.buttons & 1) !== 1) return;
    e.preventDefault();
    moveSyncedViewToRatio(ratioFromTrackPointer(e.clientY));
  };

  const handleCommonWheel = (e: React.WheelEvent<HTMLDivElement>) => {
    if (totalPages <= 1 || Math.abs(e.deltaY) < 8) return;
    e.preventDefault();
    const direction = e.deltaY > 0 ? 1 : -1;
    const nextPage = Math.max(1, Math.min(totalPages, currentPage + direction));
    moveSyncedViewToRatio(ratioFromPage(nextPage));
  };

  const handleCommonKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (totalPages <= 1) return;
    const pageStep = totalPages > 1 ? 1 / (totalPages - 1) : 1;
    if (e.key === 'ArrowDown' || e.key === 'PageDown') {
      e.preventDefault();
      moveSyncedViewToRatio(commonScrollRatio + pageStep);
    } else if (e.key === 'ArrowUp' || e.key === 'PageUp') {
      e.preventDefault();
      moveSyncedViewToRatio(commonScrollRatio - pageStep);
    } else if (e.key === 'Home') {
      e.preventDefault();
      moveSyncedViewToRatio(0);
    } else if (e.key === 'End') {
      e.preventDefault();
      moveSyncedViewToRatio(1);
    }
  };

  // 페이지 고정 뷰에서 상/하단 스크롤 경계 도달 시 마우스 휠로 페이지 연속 전환 처리함
  const handleWheelOnPageMode = (e: React.WheelEvent<HTMLDivElement>) => {
    if (compareScope !== 'page' || totalPages <= 1) return;
    const el = e.currentTarget;
    const isAtBottom = el.scrollTop + el.clientHeight >= el.scrollHeight - 6;
    const isAtTop = el.scrollTop <= 6;
    const now = Date.now();

    if (e.deltaY > 25 && isAtBottom && currentPage < totalPages) {
      if (now - lastWheelTransitionRef.current > 350) {
        lastWheelTransitionRef.current = now;
        handleJumpToPage(currentPage + 1, { updatePdf: true });
      }
    } else if (e.deltaY < -25 && isAtTop && currentPage > 1) {
      if (now - lastWheelTransitionRef.current > 350) {
        lastWheelTransitionRef.current = now;
        handleJumpToPage(currentPage - 1, { updatePdf: true });
      }
    }
  };

  // 문서 전체 메트릭 계산함
  const linesCount = useMemo(() => markdown.split('\n').length, [markdown]);
  const charCount = useMemo(() => markdown.length, [markdown]);
  const wordCount = useMemo(() => markdown.trim().split(/\s+/).filter(Boolean).length, [markdown]);

  const handleCopyMarkdown = async () => {
    try {
      const contentToCopy = compareScope === 'page' && totalPages > 1 ? currentPageItem.markdown : markdown;
      await navigator.clipboard.writeText(contentToCopy);
      setCopiedMd(true);
      setTimeout(() => setCopiedMd(false), 2000);
    } catch (e) {
      console.error(e);
    }
  };

  const handleCopyHtml = async () => {
    try {
      const contentToCopy =
        htmlPreview ||
        (compareScope === 'page' && totalPages > 1 ? renderedCurrentPageHtml : renderedFullHtml);
      await navigator.clipboard.writeText(contentToCopy);
      setCopiedHtml(true);
      setTimeout(() => setCopiedHtml(false), 2000);
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div
      className={`bg-surface flex flex-col min-h-0 transition-all duration-200 ${
        isFullScreen
          ? 'fixed inset-0 z-[9999] w-screen h-screen rounded-none border-none shadow-2xl bg-surface'
          : 'w-full h-full rounded-2xl border border-subtle shadow-sm overflow-hidden'
      }`}
    >
      {/* 1. 최상단 헤더 툴바 */}
      <div className={`bg-surface-muted/95 border-b border-subtle flex flex-wrap items-center justify-between select-none backdrop-blur-md ${
        viewMode === 'split' ? 'px-3 py-1.5 gap-2' : 'px-4 py-2.5 gap-3'
      }`}>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 px-3 py-1.5 bg-surface border border-subtle rounded-lg shadow-xs text-xs font-semibold text-fg">
            <FileText className="w-4 h-4 text-accent shrink-0" />
            <span className="font-mono text-xs max-w-[180px] sm:max-w-xs truncate">{fileName}</span>
            <span className="text-2xs font-bold px-1.5 py-0.5 rounded bg-accent/10 text-accent">
              {htmlPreview && rightFormatTab === 'html' ? 'HTML' : 'Markdown'}
            </span>
          </div>

          <div className="hidden md:flex items-center gap-2 text-xs text-fg-muted font-mono pl-2">
            <span>{totalPages > 1 ? `총 ${totalPages} 페이지` : `${linesCount.toLocaleString()} 줄`}</span>
            <span>·</span>
            <span>{wordCount.toLocaleString()} 단어</span>
            <span>·</span>
            <span>{charCount.toLocaleString()} 자</span>
          </div>
        </div>

        {/* 뷰 모드 전환 버튼군 */}
        <div className="flex items-center gap-2 flex-wrap">
          <div className="flex items-center bg-surface p-0.5 rounded-xl border border-subtle shadow-xs">
            <button
              type="button"
              onClick={() => setViewMode('split')}
              className={`text-xs font-bold px-3 py-1.5 rounded-lg transition-all flex items-center gap-1.5 ${
                viewMode === 'split'
                  ? 'bg-accent text-white shadow-xs'
                  : 'text-fg-muted hover:text-fg hover:bg-surface-muted'
              }`}
              title="원본 문서와 변환 마크다운 나란히 대조 보기"
            >
              <Columns className="w-3.5 h-3.5" />
              <span>{hasOriginal ? '나란히 대조' : '나란히 보기'}</span>
              {hasOriginal && (
                <span className="text-2xs px-1.5 py-0.2 rounded-full bg-emerald-500/20 text-emerald-600 dark:text-emerald-300 font-normal">
                  대조
                </span>
              )}
            </button>

            <button
              type="button"
              onClick={() => setViewMode('preview')}
              className={`text-xs font-bold px-3 py-1.5 rounded-lg transition-all flex items-center gap-1.5 ${
                viewMode === 'preview'
                  ? 'bg-accent text-white shadow-xs'
                  : 'text-fg-muted hover:text-fg hover:bg-surface-muted'
              }`}
              title="마크다운 렌더링 화면만 단독 미리보기"
            >
              <Eye className="w-3.5 h-3.5" />
              <span>미리보기</span>
            </button>

            <button
              type="button"
              onClick={() => setViewMode('source')}
              className={`text-xs font-bold px-3 py-1.5 rounded-lg transition-all flex items-center gap-1.5 ${
                viewMode === 'source'
                  ? 'bg-accent text-white shadow-xs'
                  : 'text-fg-muted hover:text-fg hover:bg-surface-muted'
              }`}
              title="마크다운 소스 코드만 단독 표시"
            >
              <Code2 className="w-3.5 h-3.5" />
              <span>소스 코드</span>
            </button>
          </div>

          {/* 폭 조절 토글 */}
          {viewMode === 'preview' && (
            <button
              type="button"
              onClick={() => setIsFullWidth(!isFullWidth)}
              className="ui-button-secondary text-xs px-2.5 py-1.5 flex items-center gap-1 text-fg-muted hover:text-fg"
              title={isFullWidth ? '표준 폭으로 전환' : '화면 전체 너비로 전환'}
            >
              {isFullWidth ? <AlignCenter className="w-3.5 h-3.5" /> : <AlignLeft className="w-3.5 h-3.5" />}
              <span className="hidden xl:inline">{isFullWidth ? '표준 폭' : '넓은 폭'}</span>
            </button>
          )}

          {/* 복사 및 다운로드 액션 */}
          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={handleCopyMarkdown}
              className="ui-button-secondary text-xs px-3 py-1.5 flex items-center gap-1.5"
              title={compareScope === 'page' && totalPages > 1 ? `${currentPage}페이지 마크다운 복사` : '전체 마크다운 복사'}
            >
              {copiedMd ? (
                <>
                  <Check className="w-3.5 h-3.5 text-emerald-500" />
                  <span className="text-emerald-500 font-bold">복사됨!</span>
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">
                    {compareScope === 'page' && totalPages > 1 ? `${currentPage}p 복사` : '마크다운 복사'}
                  </span>
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

            {/* 전체화면 토글 */}
            <button
              type="button"
              onClick={() => setIsFullScreen(!isFullScreen)}
              className={`p-1.5 rounded-xl border transition-all flex items-center gap-1.5 ${
                isFullScreen
                  ? 'bg-rose-500 text-white border-rose-600 hover:bg-rose-600 shadow-sm px-3'
                  : 'bg-surface border-subtle text-fg-muted hover:text-fg hover:bg-surface-muted shadow-xs px-2.5'
              }`}
              title={isFullScreen ? '전체화면 닫기 (ESC)' : '전체 화면으로 미리보기'}
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

      {/* 2. 멀티페이지 안내 바: 페이지 선택 없이 연속 스크롤로 비교 */}
      {totalPages > 1 && (
        <div className="bg-surface border-b border-subtle px-3 py-1.5 flex flex-wrap items-center justify-between gap-2 select-none text-xs">
          <div className="flex items-center gap-2 text-accent font-bold">
            <Layers className="w-3.5 h-3.5" />
            <span>전체 {totalPages}페이지 연속 스크롤 대조</span>
            <span className="text-2xs px-1.5 py-0.5 rounded-full bg-accent/15 text-accent font-normal">
              페이지 선택 없이 아래로 내려 비교
            </span>
          </div>

          <button
            type="button"
            onClick={() => setSyncScroll(!syncScroll)}
            className={`text-2xs font-semibold px-2 py-1 rounded-lg border flex items-center gap-1.5 transition-all ${
              syncScroll
                ? 'border-accent/40 bg-accent/10 text-accent font-bold'
                : 'border-subtle bg-surface text-fg-muted hover:text-fg'
            }`}
            title="좌우 패널 동기화 스크롤 설정"
          >
            <span>동기화 스크롤 {syncScroll ? 'ON' : 'OFF'}</span>
          </button>
        </div>
      )}

      {/* 3. 메인 본문 영역 */}
      <div
        className={`flex-1 min-h-0 overflow-hidden relative ${
          isFullScreen ? 'h-[calc(100vh-130px)]' : ''
        }`}
      >
        {/* 1. 미리보기 단독 모드 */}
        {viewMode === 'preview' && (
          htmlPreview && rightFormatTab === 'html' ? (
            <div className="w-full h-full flex flex-col bg-white">
              <iframe
                ref={htmlIframeRef}
                srcDoc={effectiveHtmlPreview}
                title="고충실도 웹(HTML) 전체 문서 미리보기"
                className="w-full flex-1 border-0 bg-white min-h-0 h-full overflow-y-auto"
              />
            </div>
          ) : (
            <div
              ref={previewScrollRef}
              onScroll={handlePreviewScroll}
              className="h-full overflow-y-auto p-4 sm:p-8 md:p-12 bg-surface-muted/20 markdown-preview-body selection:bg-accent/20"
            >
              <div
                className={`mx-auto ${
                  isFullWidth ? 'max-w-none px-4' : 'max-w-4xl'
                } space-y-8`}
              >
                {totalPages > 1 ? (
                  parsedPages.map((p) => {
                    const html = parsedPagesHtmlMap.get(p.pageNumber) || '';
                    return (
                      <div
                        key={p.pageNumber}
                        id={`preview-page-${p.pageNumber}`}
                        data-page-number={p.pageNumber}
                        className="bg-surface rounded-2xl border border-subtle shadow-xs p-6 sm:p-10 md:p-12 transition-all hover:shadow-md"
                      >
                        {/* 페이지 구분 헤더 */}
                        <div className="flex items-center justify-between pb-3 mb-6 border-b border-subtle text-xs font-semibold text-fg-muted">
                          <span className="flex items-center gap-2 text-accent font-bold">
                            <span className="w-2 h-2 rounded-full bg-accent" />
                            <span>{p.pageNumber} / {totalPages} 페이지</span>
                          </span>
                          <span className="text-2xs font-mono">{p.linesCount}줄 · {p.charCount.toLocaleString()}자</span>
                        </div>
                        <div
                          className="prose dark:prose-invert prose-slate prose-sm sm:prose-base leading-relaxed max-w-none"
                          dangerouslySetInnerHTML={{ __html: html }}
                        />
                      </div>
                    );
                  })
                ) : (
                  <div className="bg-surface rounded-2xl border border-subtle shadow-xs p-6 sm:p-10 md:p-12">
                    <div
                      className="prose dark:prose-invert prose-slate prose-sm sm:prose-base leading-relaxed max-w-none"
                      dangerouslySetInnerHTML={{ __html: renderedFullHtml }}
                    />
                  </div>
                )}
              </div>
            </div>
          )
        )}

        {/* 2. 나란히 대조 분할 뷰 */}
        {viewMode === 'split' && (
          <div className="h-full grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)_14px] divide-x divide-subtle overflow-hidden">
            {/* 좌측 패널: 원본 문서(PDF/이미지) 대조 또는 마크다운 소스 뷰 */}
            <div className="h-full min-w-0 min-h-0 flex flex-col bg-surface-muted/20 overflow-hidden">
              <div className="flex items-center justify-between px-3 py-2 border-b border-subtle bg-surface-muted/90 backdrop-blur-xs text-2xs font-semibold text-fg-muted">
                <div className="flex items-center gap-1 bg-surface p-0.5 rounded-lg border border-subtle">
                  {effectiveOriginalUrl && (
                    <button
                      type="button"
                      onClick={() => setLeftPaneMode('original')}
                      className={`px-2.5 py-1 rounded-md transition-all flex items-center gap-1.5 ${
                        leftPaneMode === 'original'
                          ? 'bg-accent text-white font-bold shadow-xs'
                          : 'text-fg-muted hover:text-fg'
                      }`}
                    >
                      <ImageIcon className="w-3 h-3" />
                      <span>{isPdfOriginal ? '원본 PDF 대조' : '원본 문서 대조'}</span>
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => setLeftPaneMode('source')}
                    className={`px-2.5 py-1 rounded-md transition-all flex items-center gap-1.5 ${
                      leftPaneMode === 'source' || !effectiveOriginalUrl
                        ? 'bg-accent text-white font-bold shadow-xs'
                        : 'text-fg-muted hover:text-fg'
                    }`}
                  >
                    <Code2 className="w-3 h-3" />
                    <span>마크다운 소스</span>
                  </button>
                </div>

                {leftPaneMode === 'original' && (isImageOriginal || isPdfOriginal) && (
                  <div className="flex items-center gap-1 text-2xs">
                    <button
                      type="button"
                      onClick={() => setZoomLevel(prev => Math.max(25, prev - 25))}
                      className="p-1 rounded hover:bg-surface border border-subtle text-fg-muted hover:text-fg"
                      title="축소"
                    >
                      <ZoomOut className="w-3.5 h-3.5" />
                    </button>
                    <span className="font-mono px-1 min-w-[42px] text-center font-bold text-fg">{zoomLevel}%</span>
                    <button
                      type="button"
                      onClick={() => setZoomLevel(prev => Math.min(300, prev + 25))}
                      className="p-1 rounded hover:bg-surface border border-subtle text-fg-muted hover:text-fg"
                      title="확대"
                    >
                      <ZoomIn className="w-3.5 h-3.5" />
                    </button>
                    <button
                      type="button"
                      onClick={() => setZoomLevel(100)}
                      className="px-1.5 py-0.5 rounded hover:bg-surface border border-subtle text-2xs font-mono text-fg-muted hover:text-fg"
                      title="100% 원본 크기"
                    >
                      1:1
                    </button>
                    <button
                      type="button"
                      onClick={() => setZoomLevel(100)}
                      className="p-1 rounded hover:bg-surface border border-subtle text-fg-muted hover:text-fg"
                      title="초기화"
                    >
                      <RotateCcw className="w-3 h-3" />
                    </button>
                  </div>
                )}

                {leftPaneMode === 'original' && isPdfOriginal && effectiveOriginalUrl && (
                  <div className="flex items-center gap-2">
                    <span className="text-2xs font-mono text-accent font-semibold">
                      PDF {currentPage}p 연동 뷰
                    </span>
                    <a
                      href={effectiveOriginalUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 text-fg-muted hover:text-accent"
                      title="새 탭에서 전체 PDF 열기"
                    >
                      <ExternalLink className="w-3 h-3" />
                      <span className="hidden sm:inline">새 탭 열기</span>
                    </a>
                  </div>
                )}

                {leftPaneMode === 'source' && (
                  <span className="font-mono text-2xs">
                    UTF-8 · {compareScope === 'page' && totalPages > 1 ? `${currentPageItem.linesCount} 줄 (${currentPage}p)` : `${linesCount} 줄 (전체)`}
                  </span>
                )}
              </div>

              {/* 좌측 패널 본문 */}
              {leftPaneMode === 'original' && effectiveOriginalUrl ? (
                <div className="flex-1 overflow-hidden relative flex flex-col bg-slate-900/5 dark:bg-slate-950/40 min-h-0">
                  {isPdfOriginal ? (
                    <div
                      ref={leftScrollRef}
                      onScroll={handleLeftScroll}
                      className="w-full h-full overflow-y-auto overflow-x-hidden p-4 bg-slate-200/70 dark:bg-slate-950/60 [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden"
                    >
                      {totalPages > 1 && (
                        <div className="sticky top-0 z-10 ml-auto mb-3 w-fit bg-slate-900/80 dark:bg-slate-800/85 backdrop-blur-xs text-white text-2xs px-2.5 py-1 rounded-md shadow-xs border border-white/20 font-mono flex items-center gap-1.5 pointer-events-none">
                          <Layers className="w-3 h-3 text-accent" />
                          <span>원본 {currentPage} / {totalPages} 페이지</span>
                        </div>
                      )}
                      {pdfLoadError ? (
                        <div className="h-full flex flex-col items-center justify-center text-center p-6 text-fg-muted">
                          <FileText className="w-12 h-12 mb-3 text-accent/60" />
                          <div className="text-sm font-bold text-fg mb-1">PDF 원본 미리보기 실패</div>
                          <p className="text-xs max-w-sm mb-4">{pdfLoadError}</p>
                          <a
                            href={effectiveOriginalUrl}
                            target="_blank"
                            rel="noreferrer"
                            className="ui-button-secondary text-xs px-3 py-1.5 inline-flex items-center gap-1.5"
                          >
                            <ExternalLink className="w-3.5 h-3.5" />
                            <span>새 탭에서 원본 열기</span>
                          </a>
                        </div>
                      ) : !pdfDocument ? (
                        <div className="h-full flex items-center justify-center text-xs font-semibold text-fg-muted">
                          PDF 원본을 불러오는 중입니다...
                        </div>
                      ) : (
                        <div className="space-y-5">
                          {Array.from({ length: totalPages }, (_, idx) => {
                            const pageNumber = idx + 1;
                            return (
                              <div
                                key={`original-pdf-page-${pageNumber}`}
                                id={`original-pdf-page-${pageNumber}`}
                                data-page-number={pageNumber}
                                className="mx-auto max-w-full rounded-lg border border-subtle bg-white p-3 shadow-sm"
                              >
                                <div className="mb-2 flex items-center justify-between border-b border-subtle pb-1.5 text-2xs font-bold text-accent">
                                  <span>원본 PDF {pageNumber} 페이지</span>
                                  <span className="font-mono text-fg-muted">{pageNumber} / {totalPages}</span>
                                </div>
                                <PdfCanvasPage
                                  pdfDocument={pdfDocument}
                                  pageNumber={pageNumber}
                                  zoomLevel={zoomLevel}
                                />
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  ) : isImageOriginal ? (
                    <div
                      ref={leftScrollRef}
                      onScroll={handleLeftScroll}
                      className="w-full h-full overflow-auto p-4 flex items-start justify-center [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden"
                    >
                      <div className="transition-transform duration-150 inline-block shadow-lg rounded-lg overflow-hidden border border-subtle bg-white">
                        <img
                          src={effectiveOriginalUrl}
                          alt="원본 문서 이미지"
                          style={{ width: `${zoomLevel}%`, maxWidth: 'none', display: 'block' }}
                          className="object-contain"
                        />
                      </div>
                    </div>
                  ) : (
                    <div className="w-full h-full flex flex-col items-center justify-center text-center p-6 text-fg-muted">
                      <FileText className="w-12 h-12 mb-3 text-accent/60" />
                      <div className="text-sm font-bold text-fg mb-1">
                        {originalFile?.name || '원본 문서'}
                      </div>
                      <p className="text-xs max-w-sm mb-4">
                        이미지 또는 PDF 형식이 아닌 문서는 브라우저 외부 뷰어 또는 새 탭에서 열어 확인할 수 있습니다.
                      </p>
                      {effectiveOriginalUrl && (
                        <a
                          href={effectiveOriginalUrl}
                          target="_blank"
                          rel="noreferrer"
                          className="ui-button-secondary text-xs px-3 py-1.5 inline-flex items-center gap-1.5"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                          <span>새 탭에서 원본 열기</span>
                        </a>
                      )}
                    </div>
                  )}
                </div>
              ) : (
                /* 마크다운 소스 뷰 */
                <div
                  ref={leftScrollRef}
                  onScroll={handleLeftScroll}
                  onWheel={compareScope === 'page' ? handleWheelOnPageMode : undefined}
                  className="flex-1 min-h-0 overflow-y-auto p-5 font-mono text-xs text-fg leading-relaxed select-all [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden"
                >
                  {compareScope === 'page' && totalPages > 1 ? (
                    <div>
                      <div className="pb-2 mb-3 border-b border-subtle text-2xs font-bold text-accent flex items-center justify-between">
                        <span>{currentPage} 페이지 마크다운 소스</span>
                        <span className="font-normal text-fg-muted">{currentPageItem.linesCount}줄</span>
                      </div>
                      <pre className="font-mono text-xs sm:text-sm leading-relaxed text-fg whitespace-pre-wrap">
                        {currentPageItem.markdown}
                      </pre>
                    </div>
                  ) : (
                    <div className="space-y-6">
                      {totalPages > 1
                        ? parsedPages.map((p) => (
                            <div
                              key={p.pageNumber}
                              id={`source-page-${p.pageNumber}`}
                              data-page-number={p.pageNumber}
                              className="space-y-2 border-b border-subtle/50 pb-6 last:border-b-0"
                            >
                              <div className="flex items-center justify-between pb-1 border-b border-subtle text-2xs font-bold text-accent">
                                <span className="flex items-center gap-1.5">
                                  <Layers className="w-3 h-3" />
                                  <span>{p.pageNumber} 페이지 소스</span>
                                </span>
                                <span className="text-fg-muted font-normal">{p.linesCount}줄</span>
                              </div>
                              <pre className="font-mono text-xs sm:text-sm leading-relaxed text-fg whitespace-pre-wrap">
                                {p.markdown}
                              </pre>
                            </div>
                          ))
                        : (
                            <pre className="font-mono text-xs sm:text-sm leading-relaxed text-fg whitespace-pre-wrap">
                              {markdown}
                            </pre>
                          )}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* 우측 패널: 실시간 마크다운 / HTML / 소스 렌더링 미리보기 */}
            <div className="h-full min-w-0 min-h-0 flex flex-col overflow-hidden bg-surface">
              <div className="flex items-center justify-between px-3 py-2 border-b border-subtle bg-surface/90 backdrop-blur-xs text-2xs font-semibold text-fg">
                {/* 탭 전환 버튼 */}
                <div className="flex items-center gap-1 bg-surface p-0.5 rounded-lg border border-subtle">
                  {htmlPreview && (
                    <button
                      type="button"
                      onClick={() => handleFormatTabChange('html')}
                      className={`px-2.5 py-1 rounded-md transition-all flex items-center gap-1.5 ${
                        rightFormatTab === 'html'
                          ? 'bg-accent text-white font-bold shadow-xs'
                          : 'text-fg-muted hover:text-fg'
                      }`}
                    >
                      <Globe className="w-3 h-3" />
                      <span>고충실도 웹(HTML)</span>
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => handleFormatTabChange('markdown')}
                    className={`px-2.5 py-1 rounded-md transition-all flex items-center gap-1.5 ${
                      rightFormatTab === 'markdown'
                        ? 'bg-accent text-white font-bold shadow-xs'
                        : 'text-fg-muted hover:text-fg'
                    }`}
                  >
                    <FileText className="w-3 h-3" />
                    <span>마크다운(GFM)</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleFormatTabChange('source')}
                    className={`px-2.5 py-1 rounded-md transition-all flex items-center gap-1.5 ${
                      rightFormatTab === 'source'
                        ? 'bg-accent text-white font-bold shadow-xs'
                        : 'text-fg-muted hover:text-fg'
                    }`}
                  >
                    <Code2 className="w-3 h-3" />
                    <span>소스 코드</span>
                  </button>
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-fg-muted font-mono">
                    {compareScope === 'page' && totalPages > 1
                      ? `${currentPage} / ${totalPages}p`
                      : `연속 스크롤 (${totalPages}p 전체)`}
                  </span>
                  {htmlPreview && rightFormatTab === 'html' && downloadUrl && (
                    <a
                      href={downloadUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 text-fg-muted hover:text-accent font-normal"
                      title="새 탭에서 전체 HTML 열기"
                    >
                      <ExternalLink className="w-3 h-3" />
                      <span className="hidden sm:inline">새 탭 열기</span>
                    </a>
                  )}
                </div>
              </div>

              {rightFormatTab === 'html' && htmlPreview ? (
                <div className="flex-1 w-full h-full min-h-0 relative flex flex-col bg-white overflow-hidden">
                  <iframe
                    ref={htmlIframeRef}
                    srcDoc={effectiveHtmlPreview}
                    title="고충실도 HTML 변환 결과 대조"
                    className="w-full flex-1 border-0 bg-white min-h-0 h-full overflow-y-auto"
                  />
                </div>
              ) : rightFormatTab === 'source' ? (
                <div
                  ref={rightScrollRef}
                  onScroll={handleRightScroll}
                  className="flex-1 min-h-0 overflow-y-auto p-5 font-mono text-xs text-fg leading-relaxed select-all [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden"
                >
                  <pre className="font-mono text-xs sm:text-sm leading-relaxed text-fg whitespace-pre-wrap">
                    {markdown}
                  </pre>
                </div>
              ) : (
                <div
                  ref={rightScrollRef}
                  onScroll={handleRightScroll}
                  onWheel={compareScope === 'page' ? handleWheelOnPageMode : undefined}
                  className="flex-1 min-h-0 overflow-y-auto p-6 md:p-8 markdown-preview-body selection:bg-accent/20 [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden"
                >
                  {compareScope === 'page' && totalPages > 1 ? (
                    <div
                      className="prose dark:prose-invert prose-slate prose-sm sm:prose-base leading-relaxed max-w-none"
                      dangerouslySetInnerHTML={{ __html: renderedCurrentPageHtml }}
                    />
                  ) : (
                    <div className="space-y-10">
                      {totalPages > 1
                        ? parsedPages.map((p) => {
                            const html = parsedPagesHtmlMap.get(p.pageNumber) || '';
                            return (
                              <div
                                key={p.pageNumber}
                                id={`preview-page-${p.pageNumber}`}
                                data-page-number={p.pageNumber}
                                className="space-y-3 border-b border-subtle/80 pb-10 last:border-b-0"
                              >
                                <div className="flex items-center justify-between pb-1.5 mb-2 border-b border-subtle text-xs font-bold text-accent">
                                  <span className="flex items-center gap-1.5">
                                    <Layers className="w-3.5 h-3.5" />
                                    <span>{p.pageNumber} 페이지 변환 결과</span>
                                  </span>
                                  <span className="text-2xs text-fg-muted font-normal">{p.linesCount}줄</span>
                                </div>
                                <div
                                  className="prose dark:prose-invert prose-slate prose-sm sm:prose-base leading-relaxed max-w-none"
                                  dangerouslySetInnerHTML={{ __html: html }}
                                />
                              </div>
                            );
                          })
                        : (
                            <div
                              className="prose dark:prose-invert prose-slate prose-sm sm:prose-base leading-relaxed max-w-none"
                              dangerouslySetInnerHTML={{ __html: renderedFullHtml }}
                            />
                          )}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* 우측 공통 스크롤: 원본과 변환 결과를 비율 기반으로 함께 이동 */}
            <div
              className="h-full min-h-0 bg-surface-muted/80 flex flex-col items-center border-l border-subtle"
              title="원본과 변환 결과를 동시에 스크롤합니다"
            >
              <div className="h-7 w-full flex items-center justify-center border-b border-subtle text-[10px] leading-none text-fg-muted select-none bg-surface-muted">
                ⇅
              </div>
              <div
                ref={commonTrackRef}
                role="scrollbar"
                tabIndex={0}
                aria-label="원본과 변환 결과 공통 스크롤"
                aria-orientation="vertical"
                aria-valuemin={1}
                aria-valuemax={totalPages}
                aria-valuenow={currentPage}
                onPointerDown={handleCommonPointerDown}
                onPointerMove={handleCommonPointerMove}
                onWheel={handleCommonWheel}
                onKeyDown={handleCommonKeyDown}
                className="relative w-full flex-1 min-h-0 cursor-pointer select-none bg-surface-muted/70 outline-none focus-visible:ring-2 focus-visible:ring-accent/50"
              >
                <div className="absolute inset-y-2 left-1/2 w-1.5 -translate-x-1/2 rounded-full bg-slate-300/70 dark:bg-slate-700/80" />
                <div
                  className="absolute left-1/2 h-11 w-2.5 -translate-x-1/2 rounded-full bg-slate-500 shadow-sm ring-1 ring-slate-700/20 transition-colors hover:bg-slate-600 dark:bg-slate-400 dark:hover:bg-slate-300"
                  style={{
                    top: `${commonScrollRatio * 100}%`,
                    transform: `translate(-50%, -${commonScrollRatio * 100}%)`,
                  }}
                />
              </div>
            </div>
          </div>
        )}

        {/* 3. 소스 코드 단독 모드 */}
        {viewMode === 'source' && (
          <div
            ref={sourceScrollRef}
            onScroll={handleSourceScroll}
            className="h-full overflow-y-auto bg-surface-muted/20 p-4 sm:p-8 md:p-10 font-mono text-xs text-fg leading-relaxed select-all"
          >
            <div className="max-w-5xl mx-auto space-y-6">
              <div className="flex items-center justify-between pb-3 mb-4 border-b border-subtle text-xs font-bold text-fg-muted">
                <span>
                  {fileName} (
                  {compareScope === 'page' && totalPages > 1
                    ? `${currentPage}페이지, ${currentPageItem.linesCount}줄`
                    : `전체 ${linesCount}줄, ${charCount.toLocaleString()}자`}
                  )
                </span>
                <span>Plaintext / Markdown</span>
              </div>
              {totalPages > 1 ? (
                parsedPages.map((p) => (
                  <div
                    key={p.pageNumber}
                    id={`source-standalone-page-${p.pageNumber}`}
                    data-page-number={p.pageNumber}
                    className="bg-surface rounded-2xl border border-subtle shadow-xs p-6 space-y-3"
                  >
                    <div className="flex items-center justify-between pb-2 border-b border-subtle text-2xs font-bold text-accent">
                      <span className="flex items-center gap-1.5">
                        <Layers className="w-3.5 h-3.5" />
                        <span>{p.pageNumber} / {totalPages} 페이지 소스</span>
                      </span>
                      <span className="text-fg-muted font-normal">{p.linesCount}줄</span>
                    </div>
                    <pre className="font-mono text-xs sm:text-sm leading-relaxed text-fg whitespace-pre-wrap">
                      {p.markdown}
                    </pre>
                  </div>
                ))
              ) : (
                <pre className="font-mono text-xs sm:text-sm leading-relaxed text-fg whitespace-pre-wrap bg-surface p-6 rounded-2xl border border-subtle shadow-xs">
                  {markdown}
                </pre>
              )}
            </div>
          </div>
        )}

        {/* 전체 연속 모드일 때 현재 스크롤 위치 플로팅 뱃지 */}
        {totalPages > 1 && (
          <div className="absolute bottom-4 right-6 z-20 bg-slate-900/85 dark:bg-slate-800/90 backdrop-blur-md text-white px-3.5 py-1.5 rounded-full shadow-lg border border-white/20 text-xs font-mono flex items-center gap-2 pointer-events-none transition-all">
            <Layers className="w-3.5 h-3.5 text-accent animate-pulse" />
            <span>현재 {currentPage} / {totalPages} 페이지 (내리면서 확인 중)</span>
          </div>
        )}
      </div>

      {/* 4. 하단 연속 스크롤 상태 바 */}
      {totalPages > 1 && viewMode !== 'split' && (
        <div className="bg-surface border-t border-subtle px-4 py-2 flex flex-wrap items-center justify-between gap-3 select-none shrink-0 shadow-2xs text-xs">
          <div className="flex items-center gap-2 shrink-0">
            <span className="flex items-center gap-1.5 px-3 py-1 rounded-xl bg-accent/10 text-accent font-bold text-xs font-mono border border-accent/20 shadow-2xs">
              <Layers className="w-3.5 h-3.5" />
              <span>{currentPage} / {totalPages} 페이지</span>
              <span className="text-2xs text-fg-muted font-normal">
                ({Math.round((currentPage / totalPages) * 100)}%)
              </span>
            </span>
          </div>

          <span className="text-fg-muted">
            원본과 변환 결과를 각 패널 안에서 스크롤해 연속 비교합니다.
          </span>
        </div>
      )}

      {/* 5. 최하단 푸터 */}
      <div className={`bg-surface-muted/90 border-t border-subtle px-4 py-1.5 items-center justify-between text-2xs text-fg-muted font-mono select-none ${
        viewMode === 'split' ? 'hidden' : 'flex'
      }`}>
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1 font-semibold text-fg">
            <BookOpen className="w-3.5 h-3.5 text-accent" />
            GitHub Flavored Markdown
          </span>
          <span className="hidden sm:inline">UTF-8</span>
          {totalPages > 1 && (
            <span className="text-accent font-semibold">
              {compareScope === 'page' ? `1:1 대조 (${currentPage}/${totalPages}p)` : `전체 연속 대조 (${totalPages}p)`}
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          {compareScope === 'page' && totalPages > 1 ? (
            <span>
              선택 페이지 {currentPageItem.linesCount}줄 · {currentPageItem.charCount.toLocaleString()}자
            </span>
          ) : (
            <span>
              총 {linesCount.toLocaleString()}줄 · {charCount.toLocaleString()}자
            </span>
          )}
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
