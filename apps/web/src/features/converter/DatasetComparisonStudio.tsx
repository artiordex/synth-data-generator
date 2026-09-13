/**
 * 파일명: DatasetComparisonStudio.tsx
 * 경로: apps/web/src/features/converter/DatasetComparisonStudio.tsx
 * 목적: 정형 데이터셋 변환 시 원본 데이터셋과 변환 결과(SQL, Parquet, JSON, CSV, XML)를 양쪽으로 나란히 대조하고 연속 스크롤로 검토하는 전문 스튜디오를 제공함
 * 작성자: 개발팀
 * 작성일: 2026-09-12
 */
import React, { useState, useMemo } from 'react';
import {
  Table as TableIcon,
  Columns,
  Code2,
  Copy,
  Check,
  Download,
  Maximize2,
  X,
  Search,
  ArrowRight,
  Database,
  FileSpreadsheet,
  FileCode,
  Sparkles,
  ExternalLink,
  Layers,
  Split,
  Eye,
} from 'lucide-react';

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
  preview?: Record<string, any>[];
  markdownPreview?: string | null;
  htmlPreview?: string | null;
}

// 원본 데이터셋과 변환 결과물을 양방향 분할 또는 단독 뷰로 대조하고 페이징 탐색을 제공하는 컴포넌트임
export const DatasetComparisonStudio: React.FC<DatasetComparisonStudioProps> = ({
  originalFile,
  originalUrl,
  originalFilename = 'source_dataset.csv',
  sourceFormat = 'CSV',
  targetFormat,
  fileName = 'converted_dataset',
  downloadUrl,
  downloadReady = true,
  rowsCount,
  columnsCount,
  columns = [],
  preview = [],
  markdownPreview,
  htmlPreview,
}) => {
  const [viewMode, setViewMode] = useState<'split' | 'target' | 'source'>('split');
  const [isFullScreen, setIsFullScreen] = useState(false);
  const [searchFilter, setSearchFilter] = useState('');
  const [copiedResult, setCopiedResult] = useState(false);
  const [targetDisplayMode, setTargetDisplayMode] = useState<'visual' | 'code'>('visual');

  const normalizedTarget = targetFormat.toLowerCase();
  const isSql = normalizedTarget === 'sql';
  const isJson = ['json', 'jsonl'].includes(normalizedTarget);
  const isXml = normalizedTarget === 'xml';
  const isCodeOutput = isSql || isJson || isXml;

  // 원본 데이터셋 필터링 (행 검색)
  const filteredRows = useMemo(() => {
    if (!preview || preview.length === 0) return [];
    if (!searchFilter.trim()) return preview;
    const query = searchFilter.toLowerCase();
    return preview.filter(row =>
      Object.values(row).some(val =>
        String(val ?? '').toLowerCase().includes(query)
      )
    );
  }, [preview, searchFilter]);

  // 원본과 변환본은 페이지를 나누지 않고 같은 행 집합을 하나의 스크롤로 내려가며 비교함
  const displayedRows = filteredRows;

  // 변환 결과 코드/텍스트 내용 산출함
  const resultContentText = useMemo(() => {
    if (markdownPreview) {
      // 마크다운 코드 블록(```sql ... ``` 등)에서 순수 내용 분리
      const codeBlockMatch = markdownPreview.match(/```(?:\w+)?\n([\s\S]*?)```/);
      if (codeBlockMatch) return codeBlockMatch[1];
      return markdownPreview;
    }
    if (htmlPreview) return htmlPreview;
    if (preview && preview.length > 0) {
      if (isJson) return JSON.stringify(preview, null, 2);
      return JSON.stringify(preview.slice(0, 10), null, 2);
    }
    return '';
  }, [markdownPreview, htmlPreview, preview, isJson]);

  const handleCopyResult = async () => {
    try {
      if (resultContentText) {
        await navigator.clipboard.writeText(resultContentText);
      } else if (preview && preview.length > 0) {
        await navigator.clipboard.writeText(JSON.stringify(preview, null, 2));
      }
      setCopiedResult(true);
      setTimeout(() => setCopiedResult(false), 2000);
    } catch (e) {
      console.error(e);
    }
  };

  // 테이블 하단 상태 바 렌더링 함수 정의함
  const renderScrollStatusBar = () => {
    if (filteredRows.length === 0) return null;
    return (
      <div className="flex flex-wrap items-center justify-between gap-2 px-3 py-1.5 border-t border-subtle bg-surface-muted/60 text-xs select-none">
        <div className="flex items-center gap-2 text-fg-muted font-mono text-2xs">
          <span>표시 중 {filteredRows.length.toLocaleString()}행</span>
          <span>·</span>
          <span>단일 스크롤 대조</span>
        </div>

        <div className="flex items-center gap-2 text-2xs font-semibold text-accent">
          <ArrowRight className="w-3.5 h-3.5" />
          <span>원본과 변환본을 좌우 고정한 채 아래로 내려 비교합니다</span>
        </div>
      </div>
    );
  };

  return (
    <div
      className={`bg-surface flex flex-col transition-all duration-200 ${
        isFullScreen
          ? 'fixed inset-0 z-[9999] w-screen h-screen rounded-none border-none shadow-2xl bg-surface'
          : 'w-full rounded-2xl border border-subtle shadow-sm overflow-hidden'
      }`}
    >
      {/* 1. 최상단 헤더 툴바 */}
      <div className="bg-surface-muted/95 border-b border-subtle px-4 py-2.5 flex flex-wrap items-center justify-between gap-3 select-none backdrop-blur-md">
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 px-3 py-1.5 bg-surface border border-subtle rounded-lg shadow-xs text-xs font-semibold text-fg">
            <Database className="w-4 h-4 text-accent shrink-0" />
            <span className="font-mono text-xs max-w-[160px] sm:max-w-xs truncate">{fileName}</span>
            <span className="text-2xs text-fg-muted font-normal px-1.5 py-0.5 bg-accent/10 text-accent rounded font-bold">
              {targetFormat.toUpperCase()}
            </span>
          </div>

          <div className="hidden md:flex items-center gap-2 text-xs text-fg-muted font-mono pl-2">
            <span>{rowsCount ? `총 ${rowsCount.toLocaleString()} 행` : `${preview.length}행 로드`}</span>
            <span>·</span>
            <span>{columnsCount || columns.length}개 컬럼</span>
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
              title="원본 데이터와 변환 결과물을 나란히 비교함"
            >
              <Columns className="w-3.5 h-3.5" />
              <span>나란히 대조</span>
              <span className="text-2xs px-1.5 py-0.2 rounded-full bg-emerald-500/20 text-emerald-600 dark:text-emerald-300 font-normal">
                대조
              </span>
            </button>

            <button
              type="button"
              onClick={() => setViewMode('target')}
              className={`text-xs font-bold px-3 py-1.5 rounded-lg transition-all flex items-center gap-1.5 ${
                viewMode === 'target'
                  ? 'bg-accent text-white shadow-xs'
                  : 'text-fg-muted hover:text-fg hover:bg-surface-muted'
              }`}
              title="변환된 결과물만 단독으로 넓게 봄"
            >
              <Eye className="w-3.5 h-3.5" />
              <span>변환본 단독</span>
            </button>

            <button
              type="button"
              onClick={() => setViewMode('source')}
              className={`text-xs font-bold px-3 py-1.5 rounded-lg transition-all flex items-center gap-1.5 ${
                viewMode === 'source'
                  ? 'bg-accent text-white shadow-xs'
                  : 'text-fg-muted hover:text-fg hover:bg-surface-muted'
              }`}
              title="업로드된 원본 데이터 테이블만 봄"
            >
              <TableIcon className="w-3.5 h-3.5" />
              <span>원본만 보기</span>
            </button>
          </div>

          {/* 액션 버튼들 */}
          <div className="flex items-center gap-1.5">
            {resultContentText && (
              <button
                type="button"
                onClick={handleCopyResult}
                className="ui-button-secondary text-xs px-3 py-1.5 flex items-center gap-1.5"
                title="변환 결과 복사"
              >
                {copiedResult ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-emerald-500" />
                    <span className="text-emerald-500 font-bold">복사됨!</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5" />
                    <span className="hidden sm:inline">결과 복사</span>
                  </>
                )}
              </button>
            )}

            {downloadUrl && downloadReady && (
              <a
                href={downloadUrl}
                download={fileName}
                className="ui-button-primary text-xs px-3 py-1.5 flex items-center gap-1.5 shadow-xs"
                title="변환 완료된 파일 다운로드"
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
              title={isFullScreen ? '전체화면 닫기 (ESC)' : '전체 화면으로 대조'}
            >
              {isFullScreen ? (
                <>
                  <X className="w-4 h-4" />
                  <span className="text-xs font-bold">전체화면 닫기</span>
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

      {/* 2. 메인 대조 영역 */}
      <div className="flex-1 relative overflow-hidden min-h-[580px] h-[72vh]">
        {/* 분할 뷰 모드 */}
        {viewMode === 'split' && (
          <div className="h-full overflow-auto">
            <div className="grid min-w-[980px] grid-cols-2 divide-x divide-subtle">
            {/* 좌측 패널: 원본 데이터셋 테이블 */}
            <div className="min-h-full bg-surface-muted/15">
              <div className="sticky top-0 z-30 flex items-center justify-between px-4 py-2 border-b border-subtle bg-surface-muted/95 backdrop-blur-xs text-xs font-semibold text-fg">
                <div className="flex items-center gap-2">
                  <FileSpreadsheet className="w-4 h-4 text-accent shrink-0" />
                  <span className="font-bold">원본 데이터 ({sourceFormat})</span>
                  <span className="text-2xs font-mono px-2 py-0.5 rounded-full bg-surface border border-subtle text-fg-muted">
                    {preview.length}행 표시 (총 {rowsCount?.toLocaleString() ?? preview.length}행)
                  </span>
                </div>

                {/* 실시간 필터 검색창 */}
                <div className="relative w-40 sm:w-52">
                  <Search className="w-3.5 h-3.5 text-fg-muted absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                  <input
                    type="text"
                    value={searchFilter}
                    onChange={(e) => setSearchFilter(e.target.value)}
                    placeholder="원본 데이터 검색..."
                    className="w-full text-xs pl-8 pr-3 py-1 rounded-lg border border-subtle bg-surface text-fg focus:outline-none focus:border-accent"
                  />
                  {searchFilter && (
                    <button
                      type="button"
                      onClick={() => setSearchFilter('')}
                      className="absolute right-2 top-1/2 -translate-y-1/2 text-fg-muted hover:text-fg"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  )}
                </div>
              </div>

              {/* 좌측 테이블 스크롤 본문 */}
              <div className="p-2">
                {columns.length > 0 && displayedRows.length > 0 ? (
                  <table className="w-full text-left text-xs border-collapse font-mono">
                    <thead className="sticky top-[41px] z-20 shadow-2xs">
                      <tr className="border-b border-subtle bg-surface-muted text-fg-muted">
                        <th className="p-2 w-12 text-center text-2xs font-bold uppercase tracking-wider bg-surface-muted">
                          #
                        </th>
                        {columns.map((col, idx) => (
                          <th
                            key={idx}
                            className="p-2.5 font-bold whitespace-nowrap text-fg border-l border-subtle/50 first:border-l-0 bg-surface-muted"
                          >
                            {col}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-subtle bg-surface">
                      {displayedRows.map((row, rIdx) => (
                        <tr key={rIdx} className="hover:bg-accent/5 transition-colors">
                          <td className="p-2 text-center text-2xs text-fg-muted/70 select-none bg-surface-muted/20">
                            {rIdx + 1}
                          </td>
                          {columns.map((col, cIdx) => (
                            <td
                              key={cIdx}
                              className="p-2.5 whitespace-nowrap text-fg border-l border-subtle/30 first:border-l-0 text-xs"
                            >
                              {row[col] != null ? String(row[col]) : (
                                <span className="text-fg-muted/40 italic">null</span>
                              )}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <div className="h-full flex flex-col items-center justify-center text-center p-8 text-fg-muted">
                    <TableIcon className="w-10 h-10 mb-2 opacity-40" />
                    <p className="text-xs">
                      {searchFilter ? '검색 결과와 일치하는 데이터가 없습니다.' : '표시할 원본 데이터가 없습니다.'}
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* 우측 패널: 변환 결과물 (SQL, Parquet, JSON, CSV 등) */}
            <div className="min-h-full bg-surface">
              <div className="sticky top-0 z-30 flex items-center justify-between px-4 py-2 border-b border-subtle bg-surface/95 backdrop-blur-xs text-xs font-semibold text-fg">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-accent shrink-0" />
                  <span className="font-bold">변환 결과물 ({targetFormat.toUpperCase()})</span>
                  <span className="text-2xs font-mono px-2 py-0.5 rounded-full bg-accent/10 text-accent font-bold">
                    {isCodeOutput ? '구조화 쿼리/코드' : '변환 데이터셋'}
                  </span>
                </div>

                {isCodeOutput && (
                  <div className="flex items-center bg-surface-muted p-0.5 rounded-lg border border-subtle text-2xs">
                    <button
                      type="button"
                      onClick={() => setTargetDisplayMode('code')}
                      className={`px-2 py-0.5 rounded font-bold transition-all ${
                        targetDisplayMode === 'code' ? 'bg-surface text-accent shadow-xs' : 'text-fg-muted hover:text-fg'
                      }`}
                    >
                      <Code2 className="w-3 h-3 inline mr-1" />
                      코드 뷰
                    </button>
                    <button
                      type="button"
                      onClick={() => setTargetDisplayMode('visual')}
                      className={`px-2 py-0.5 rounded font-bold transition-all ${
                        targetDisplayMode === 'visual' ? 'bg-surface text-accent shadow-xs' : 'text-fg-muted hover:text-fg'
                      }`}
                    >
                      <TableIcon className="w-3 h-3 inline mr-1" />
                      테이블 뷰
                    </button>
                  </div>
                )}
              </div>

              {/* 우측 본문 스크롤 */}
              <div className="p-4">
                {isCodeOutput && targetDisplayMode === 'code' ? (
                  <div className="font-mono text-xs text-fg leading-relaxed bg-surface-muted/30 p-4 rounded-xl border border-subtle whitespace-pre-wrap select-all">
                    {resultContentText}
                  </div>
                ) : htmlPreview ? (
                  <div
                    className="prose dark:prose-invert max-w-none text-xs"
                    dangerouslySetInnerHTML={{ __html: htmlPreview }}
                  />
                ) : (
                  /* 테이블 변환 결과 (Parquet, CSV, Excel 등 컬럼 미리보기) */
                  <table className="w-full text-left text-xs border-collapse font-mono">
                    <thead className="sticky top-[41px] z-20 shadow-2xs">
                      <tr className="border-b border-subtle bg-surface-muted text-fg-muted">
                        <th className="p-2 w-12 text-center text-2xs font-bold uppercase tracking-wider bg-surface-muted">
                          #
                        </th>
                        {columns.map((col, idx) => (
                          <th
                            key={idx}
                            className="p-2.5 font-bold whitespace-nowrap text-fg border-l border-subtle/50 first:border-l-0 bg-surface-muted"
                          >
                            {col}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-subtle bg-surface">
                      {displayedRows.map((row, rIdx) => (
                        <tr key={rIdx} className="hover:bg-accent/5 transition-colors">
                          <td className="p-2 text-center text-2xs text-fg-muted/70 select-none bg-surface-muted/20">
                            {rIdx + 1}
                          </td>
                          {columns.map((col, cIdx) => (
                            <td
                              key={cIdx}
                              className="p-2.5 whitespace-nowrap text-fg border-l border-subtle/30 first:border-l-0 text-xs"
                            >
                              {row[col] != null ? String(row[col]) : (
                                <span className="text-fg-muted/40 italic">null</span>
                              )}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>
            </div>
            {renderScrollStatusBar()}
          </div>
        )}

        {/* 변환본 단독 뷰 모드 */}
        {viewMode === 'target' && (
          <div className="h-full flex flex-col p-4 overflow-auto">
            {isCodeOutput ? (
              <div className="font-mono text-xs text-fg leading-relaxed bg-surface-muted/30 p-6 rounded-2xl border border-subtle overflow-auto whitespace-pre-wrap select-all max-w-6xl mx-auto w-full">
                {resultContentText}
              </div>
            ) : (
              <div className="overflow-auto border border-subtle rounded-2xl bg-surface flex flex-col">
                <table className="w-full text-left text-xs border-collapse font-mono">
                  <thead className="sticky top-0 z-10 shadow-2xs">
                    <tr className="border-b border-subtle bg-surface-muted text-fg-muted">
                      <th className="p-2.5 w-12 text-center text-2xs font-bold bg-surface-muted">#</th>
                      {columns.map((col, idx) => (
                        <th key={idx} className="p-2.5 font-bold whitespace-nowrap text-fg bg-surface-muted">
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-subtle bg-surface">
                    {displayedRows.map((row, rIdx) => (
                      <tr key={rIdx} className="hover:bg-accent/5 transition-colors">
                        <td className="p-2.5 text-center text-2xs text-fg-muted select-none">
                          {rIdx + 1}
                        </td>
                        {columns.map((col, cIdx) => (
                          <td key={cIdx} className="p-2.5 whitespace-nowrap text-fg font-mono text-xs">
                            {row[col] != null ? String(row[col]) : ''}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
                {renderScrollStatusBar()}
              </div>
            )}
          </div>
        )}

        {/* 원본만 보기 뷰 모드 */}
        {viewMode === 'source' && (
          <div className="h-full flex flex-col p-4 overflow-auto">
            <div className="overflow-auto border border-subtle rounded-2xl bg-surface flex flex-col">
              <table className="w-full text-left text-xs border-collapse font-mono">
                <thead className="sticky top-0 z-10 shadow-2xs">
                  <tr className="border-b border-subtle bg-surface-muted text-fg-muted">
                    <th className="p-2.5 w-12 text-center text-2xs font-bold bg-surface-muted">#</th>
                    {columns.map((col, idx) => (
                      <th key={idx} className="p-2.5 font-bold whitespace-nowrap text-fg bg-surface-muted">
                        {col}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-subtle bg-surface">
                  {displayedRows.map((row, rIdx) => (
                    <tr key={rIdx} className="hover:bg-accent/5 transition-colors">
                    <td className="p-2.5 text-center text-2xs text-fg-muted select-none">
                        {rIdx + 1}
                      </td>
                      {columns.map((col, cIdx) => (
                        <td key={cIdx} className="p-2.5 whitespace-nowrap text-fg font-mono text-xs">
                          {row[col] != null ? String(row[col]) : ''}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
              {renderScrollStatusBar()}
            </div>
          </div>
        )}
      </div>

      {/* 3. 최하단 푸터 바 */}
      <div className="bg-surface-muted/90 border-t border-subtle px-4 py-2 flex items-center justify-between text-2xs text-fg-muted font-mono select-none">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1 font-semibold text-fg">
            <TableIcon className="w-3.5 h-3.5 text-accent" />
            <span>정형 데이터셋 양쪽 대조 스튜디오</span>
          </span>
          <span>·</span>
          <span>{columns.length}개 필드</span>
          <span>·</span>
          <span>상위 {preview.length}행 검토 중 (전체 {rowsCount?.toLocaleString() ?? preview.length}행)</span>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-accent font-semibold">
            {viewMode === 'split' ? '양쪽 나란히 대조 활성' : viewMode === 'target' ? '변환본 단독 뷰' : '원본 단독 뷰'}
          </span>
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
