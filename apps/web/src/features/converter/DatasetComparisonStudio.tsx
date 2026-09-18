/**
 * 파일명: DatasetComparisonStudio.tsx
 * 경로: apps/web/src/features/converter/DatasetComparisonStudio.tsx
 * 목적: 실제 원본·변환 파일을 독립적으로 읽고 각 형식으로 나란히 표시함
 * 작성자: 개발팀
 * 작성일: 2026-09-12
 * 수정일: 2026-09-17
 */
import React, { useEffect, useMemo, useState } from 'react';
import DOMPurify from 'dompurify';
import { Columns, Copy, Check, Download, Maximize2, X, FileCode, Search } from 'lucide-react';
import { defaultPreviewMode, downloadPreviewBlob, FilePreview, parquetPreview, parseFilePreview, PreviewMode, previewFormat } from './datasetFilePreview';
const EMPTY_COLUMNS: string[] = [];
const EMPTY_ROWS: Record<string, unknown>[] = [];

export interface DatasetComparisonStudioProps {
  originalFile?: File | null;
  originalUrl?: string;
  originalFilename?: string;
  sourceFormat?: string;
  targetFormat: string;
  fileName?: string;
  downloadUrl?: string;
  downloadReady?: boolean;
  rowsCount?: number;
  columnsCount?: number;
  columns?: string[];
  preview?: Record<string, unknown>[];
  structuredPreview?: string;
  markdownPreview?: string | null;
  htmlPreview?: string | null;
  sourceEncoding?: string;
  sourceSheetName?: string;
}

// 날짜·중첩 값을 실제 셀 표현으로 표시함
function displayCell(value: unknown): string {
  if (value == null) return '';
  if (value instanceof Date) return value.toISOString();
  return typeof value === 'object' ? JSON.stringify(value) : String(value);
}

/** 원본 또는 변환 파일 하나를 독립적으로 표시함
 * @param props 패널의 실제 파일·형식·다운로드 경로·바이너리 표 요약
 * @returns 원문 코드, 스프레드시트 표 또는 격리된 HTML 패널
 */
function FilePanel({ title, filename, file, url, format, fallback, encoding, initialSheet, onText }: {
  title: string; filename: string; file?: File | null; url?: string; format: string;
  fallback: FilePreview; encoding?: string; initialSheet?: string; onText?: (text?: string) => void;
}) {
  const normalized = previewFormat(format);
  const [data, setData] = useState<FilePreview>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [mode, setMode] = useState<PreviewMode>(() => defaultPreviewMode(format));
  const [sheet, setSheet] = useState(initialSheet);
  const [query, setQuery] = useState('');
  useEffect(() => { setMode(defaultPreviewMode(format)); setSheet(initialSheet); setQuery(''); }, [file, url, format, initialSheet]);
  useEffect(() => {
    const controller = new AbortController();
    setData(undefined); setError(''); setLoading(true); onText?.(undefined);
    async function load() {
      try {
        let result: FilePreview;
        if (normalized === 'parquet') result = fallback;
        else {
          let blob: Blob;
          if (file) blob = file;
          else if (url) {
            blob = await downloadPreviewBlob(url, normalized, controller.signal);
          } else throw new Error('실제 파일의 미리보기 경로가 없습니다.');
          result = await parseFilePreview(blob, normalized, sheet, encoding);
        }
        if (!controller.signal.aborted) { setData(result); onText?.(result.text); }
      } catch (failure) {
        if (!controller.signal.aborted) setError(failure instanceof Error ? failure.message : '미리보기를 읽지 못했습니다.');
      } finally { if (!controller.signal.aborted) setLoading(false); }
    }
    void load();
    return () => controller.abort();
  }, [file, url, normalized, sheet, encoding, fallback, onText]);
  const rows = useMemo(() => (data?.table?.rows || []).filter(row => !query || row.some(value => displayCell(value).toLowerCase().includes(query.toLowerCase()))), [data, query]);
  const code = data?.text || '';
  const html = useMemo(() => normalized === 'html' && code ?
    '<meta http-equiv="Content-Security-Policy" content="default-src &#39;none&#39;; style-src &#39;unsafe-inline&#39;; img-src data: blob:; base-uri &#39;none&#39;; form-action &#39;none&#39;">' + DOMPurify.sanitize(code) : '', [normalized, code]);
  return (
    <section className="min-w-0 flex flex-col border border-subtle rounded-xl bg-surface overflow-hidden" aria-label={title}>
      <div className="p-3 border-b border-subtle bg-surface-muted flex flex-wrap items-center justify-between gap-2">
        <div className="min-w-0"><h4 className="text-sm font-semibold">{title} ({format.toUpperCase()})</h4><p className="ui-help-text truncate" title={filename}>{filename}</p></div>
        <div className="flex flex-wrap gap-1">
          {data?.text !== undefined && <button type="button" className="ui-button-secondary text-xs" aria-pressed={mode === 'code'} onClick={() => setMode('code')}>원문 코드</button>}
          {data?.table && <button type="button" className="ui-button-secondary text-xs" aria-pressed={mode === 'table'} onClick={() => setMode('table')}>표 보기</button>}
          {normalized === 'html' && <button type="button" className="ui-button-secondary text-xs" aria-pressed={mode === 'html'} onClick={() => setMode('html')}>HTML 보기</button>}
          {url && <a className="ui-button-secondary text-xs" href={url} download={filename}>파일 다운로드</a>}
        </div>
      </div>
      {data?.sheets && data.sheets.length > 1 && <label className="p-3 text-sm">시트 선택 <select className="ui-field" value={data.sheet} onChange={event => setSheet(event.target.value)}>{data.sheets.map(name => <option key={name}>{name}</option>)}</select></label>}
      {data?.notice && <p className="ui-help-text px-3 py-2 border-b border-subtle">{data.notice}</p>}
      {loading ? <p className="p-4 text-sm" role="status">실제 {format.toUpperCase()} 파일을 읽는 중…</p> : error ? <p className="ui-error m-3" role="alert">{error} 다른 패널의 데이터로 원본을 대체하지 않습니다.</p> : mode === 'html' ?
        <iframe title={`${title} HTML`} sandbox="" srcDoc={html} className="w-full flex-1 min-h-[540px] border-0 bg-white" /> : mode === 'code' ?
        <pre className="p-4 text-xs font-mono leading-relaxed whitespace-pre-wrap break-all overflow-auto flex-1 min-h-[540px] max-h-[72vh]" data-format={normalized}><code>{code}</code></pre> :
        <div className="flex-1 overflow-auto min-h-[540px] max-h-[72vh]">
          <label className="flex items-center gap-2 p-3 text-sm"><Search className="w-4 h-4" /><input className="ui-field" placeholder={`${title} 표 검색`} value={query} onChange={event => setQuery(event.target.value)} /></label>
          <div className="ui-table-shell"><table className="ui-table font-mono"><thead><tr><th>#</th>{data?.table?.headers.map((header, index) => <th key={index}>{header}</th>)}</tr></thead><tbody>{rows.map((row, index) => <tr key={index}><td>{index + 1}</td>{row.map((value, column) => <td key={column} className="whitespace-nowrap">{value == null ? <span className="text-fg-muted italic">null</span> : displayCell(value)}</td>)}</tr>)}</tbody></table></div>
          {rows.length === 0 && <p className="p-4 ui-help-text">표시할 데이터가 없습니다.</p>}
        </div>}
    </section>
  );
}

/** 원본·변환 파일을 각 형식으로 나란히 또는 단독 표시함
 * @param props 업로드 원본과 실제 변환 파일 URL 및 형식 정보
 * @returns 패널별 독립 미리보기와 복사·다운로드·전체화면 도구
 */
export const DatasetComparisonStudio: React.FC<DatasetComparisonStudioProps> = ({
  originalFile, originalUrl, originalFilename = '원본 파일', sourceFormat = 'CSV', targetFormat,
  fileName = '변환 파일', downloadUrl, downloadReady = true, rowsCount, columnsCount,
  columns = EMPTY_COLUMNS, preview = EMPTY_ROWS, sourceEncoding, sourceSheetName,
}) => {
  const [viewMode, setViewMode] = useState<'split' | 'target' | 'source'>('split');
  const [fullScreen, setFullScreen] = useState(false);
  const [targetText, setTargetText] = useState<string>();
  const [copied, setCopied] = useState(false);
  const fallback = useMemo(() => parquetPreview(columns, preview), [columns, preview]);
  useEffect(() => { setCopied(false); }, [targetText]);
  useEffect(() => {
    if (!fullScreen) return;
    const listener = (event: KeyboardEvent) => { if (event.key === 'Escape') setFullScreen(false); };
    window.addEventListener('keydown', listener);
    return () => window.removeEventListener('keydown', listener);
  }, [fullScreen]);
  // 실제 변환 파일에서 읽은 코드만 복사하고 표 요약을 JSON 원문으로 위장하지 않음
  async function copyTarget() {
    if (targetText === undefined) return;
    try { await navigator.clipboard.writeText(targetText); setCopied(true); }
    catch { setCopied(false); }
  }
  return (
    <div className={`ui-panel flex flex-col gap-3 ${fullScreen ? 'fixed inset-0 z-[9999] rounded-none overflow-auto' : ''}`}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div><h3 className="ui-section-title flex items-center gap-2"><FileCode className="w-4 h-4" />원본·변환 파일 대조</h3><p className="ui-help-text">{sourceFormat.toUpperCase()} → {targetFormat.toUpperCase()} · {rowsCount?.toLocaleString() ?? '—'}행 · {columnsCount ?? columns.length}개 필드</p></div>
        <div className="flex flex-wrap gap-2">
          {(['split', 'source', 'target'] as const).map(mode => <button key={mode} type="button" className="ui-button-secondary text-xs" aria-pressed={viewMode === mode} onClick={() => setViewMode(mode)}>{mode === 'split' ? <Columns className="w-4 h-4" /> : null}{mode === 'split' ? '나란히 대조' : mode === 'source' ? '원본만 보기' : '변환본 단독'}</button>)}
          {targetText !== undefined && <button type="button" className="ui-button-secondary text-xs" onClick={copyTarget}>{copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}{copied ? '복사됨' : '결과 코드 복사'}</button>}
          {downloadUrl && downloadReady && <a className="ui-button-primary text-xs" href={downloadUrl} download={fileName}><Download className="w-4 h-4" />결과 다운로드</a>}
          <button type="button" className="ui-button-secondary text-xs" onClick={() => setFullScreen(value => !value)}>{fullScreen ? <X className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}{fullScreen ? '전체화면 닫기' : '전체화면'}</button>
        </div>
      </div>
      <div className={`grid gap-3 ${viewMode === 'split' ? 'grid-cols-1 lg:grid-cols-2' : 'grid-cols-1'}`}>
        <div className={viewMode === 'target' ? 'hidden' : ''}><FilePanel title="원본 데이터" filename={originalFilename} file={originalFile} url={originalUrl} format={sourceFormat} fallback={fallback} encoding={sourceEncoding} initialSheet={sourceSheetName} /></div>
        <div className={viewMode === 'source' ? 'hidden' : ''}><FilePanel title="변환 결과물" filename={fileName} url={downloadReady ? downloadUrl : undefined} format={targetFormat} fallback={fallback} onText={setTargetText} /></div>
      </div>
      <p className="ui-help-text">왼쪽은 원본 파일, 오른쪽은 실제 생성된 파일을 표시합니다. 표시용 JSON 공백 정리는 파일 내용과 변환 데이터를 바꾸지 않습니다.</p>
    </div>
  );
};
