/**
 * 파일명: AiGuideSamplePreview.tsx
 * 경로: apps/web/src/features/aiguide/AiGuideSamplePreview.tsx
 * 목적: 업로드 데이터의 표 및 JSON 샘플 미리보기를 제공함
 * 작성자: 개발팀
 * 작성일: 2026-09-29
 * 수정일: 2026-09-29
 */
import React from 'react';
import { Braces, Check, Copy, Table } from 'lucide-react';
import type { SamplePreviewData } from './aiGuidePreviewTypes';

interface AiGuideSamplePreviewProps {
  samplePreview: SamplePreviewData | null;
  previewTab: 'table' | 'json';
  rawText: string;
  jsonSnippetCopied: boolean;
  onPreviewTabChange: (tab: 'table' | 'json') => void;
  onCopyJsonSnippet: () => void;
  renderHighlightedJson: (json: string) => string;
}

/** 파싱된 데이터 표본을 표 또는 JSON으로 표시함 */
export const AiGuideSamplePreview: React.FC<AiGuideSamplePreviewProps> = ({
  samplePreview,
  previewTab,
  rawText,
  jsonSnippetCopied,
  onPreviewTabChange,
  onCopyJsonSnippet,
  renderHighlightedJson,
}) => (
  <>
    {/* 데이터 샘플 미리보기 */}
    {samplePreview ? (
      <div className="space-y-2">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Table className="w-4 h-4 text-accent" />
            <span className="text-xs font-bold text-fg">데이터 샘플 미리보기</span>
            {samplePreview.sheetName && (
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-700 dark:text-emerald-300">
                시트: {samplePreview.sheetName}
              </span>
            )}
            <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-surface-muted text-fg-muted uppercase">
              {samplePreview.format}
            </span>
          </div>

          <div className="flex items-center gap-3">
            {/* 보기 모드 탭 (표 미리보기 vs JSON 구조) */}
            <div className="flex items-center gap-1 bg-surface-muted p-0.5 rounded-lg border border-subtle">
              <button
                type="button"
                onClick={() => onPreviewTabChange('table')}
                className={`flex items-center gap-1.5 px-2.5 py-1 text-2xs font-medium rounded-md transition-colors cursor-pointer ${
                  previewTab === 'table'
                    ? 'bg-surface text-fg shadow-2xs font-bold'
                    : 'text-fg-muted hover:text-fg'
                }`}
              >
                <Table className="w-3.5 h-3.5" />
                <span>표 미리보기</span>
              </button>
              {samplePreview.jsonSnippet && (
                <button
                  type="button"
                  onClick={() => onPreviewTabChange('json')}
                  className={`flex items-center gap-1.5 px-2.5 py-1 text-2xs font-medium rounded-md transition-colors cursor-pointer ${
                    previewTab === 'json'
                      ? 'bg-surface text-accent shadow-2xs font-bold'
                      : 'text-fg-muted hover:text-fg'
                  }`}
                >
                  <Braces className="w-3.5 h-3.5 text-accent" />
                  <span>JSON 구조 (상위 15건)</span>
                </button>
              )}
            </div>

            <span className="text-2xs text-fg-muted font-mono hidden sm:inline">
              {samplePreview.totalCols}개 컬럼 · 상위 {samplePreview.rows.length}건 (전체 {samplePreview.totalRows.toLocaleString()}건)
            </span>
          </div>
        </div>

        {previewTab === 'json' && samplePreview.jsonSnippet ? (
          <div className="rounded-xl border border-slate-200/90 dark:border-subtle overflow-hidden bg-white dark:bg-surface shadow-2xs">
            <div className="flex items-center justify-between px-3.5 py-2.5 bg-slate-50 dark:bg-surface-muted/60 border-b border-slate-200/80 dark:border-subtle">
              <div className="flex items-center gap-2">
                <span className="text-2xs font-bold text-slate-800 dark:text-fg">JSON 구조 미리보기 (상위 15건)</span>
                <span className="text-[10px] text-slate-600 dark:text-fg-muted font-mono bg-white dark:bg-surface px-2 py-0.5 rounded border border-slate-200 dark:border-subtle">
                  전체 {samplePreview.totalRows.toLocaleString()}건 중 상위 {Math.min(15, samplePreview.totalRows)}건
                </span>
              </div>
              <button
                type="button"
                onClick={onCopyJsonSnippet}
                className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-white dark:bg-surface hover:bg-slate-100 dark:hover:bg-surface-muted text-slate-700 dark:text-fg text-2xs border border-slate-300/80 dark:border-subtle transition-colors cursor-pointer font-medium shadow-2xs"
                title="상위 15건 JSON 복사"
              >
                {jsonSnippetCopied ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                    <span className="text-emerald-600 dark:text-emerald-400 font-semibold">복사 완료</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5 text-slate-500 dark:text-fg-muted" />
                    <span>JSON 복사</span>
                  </>
                )}
              </button>
            </div>
            <pre
              className="p-4 font-mono text-xs overflow-x-auto max-h-84 leading-relaxed bg-[#f8fafc] text-slate-800 dark:bg-[#0f172a]/20 dark:text-fg whitespace-pre selection:bg-blue-100 selection:text-blue-900 border-t border-slate-200/40 dark:border-subtle/30"
              dangerouslySetInnerHTML={{ __html: renderHighlightedJson(samplePreview.jsonSnippet) }}
            />
          </div>
        ) : (
          <div className="rounded-xl border border-subtle overflow-hidden bg-surface shadow-2xs">
            <div className="overflow-x-auto max-h-72">
              <table className="w-full text-left text-xs border-collapse font-mono">
                <thead className="sticky top-0 bg-surface-muted border-b border-subtle z-10">
                  <tr>
                    <th className="py-2 px-3 text-2xs font-bold text-fg-muted uppercase w-12 text-center border-r border-subtle/50">
                      #
                    </th>
                    {samplePreview.headers.map((h, i) => (
                      <th key={i} className="py-2 px-3 text-xs font-bold text-fg whitespace-nowrap border-r border-subtle/50 last:border-r-0">
                        {h || `열${i + 1}`}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-subtle/60 text-fg">
                  {samplePreview.rows.map((row, rIdx) => (
                    <tr key={rIdx} className="hover:bg-surface-muted/40 transition-colors">
                      <td className="py-1.5 px-3 text-2xs text-fg-muted text-center bg-surface-muted/30 border-r border-subtle/50">
                        {rIdx + 1}
                      </td>
                      {samplePreview.headers.map((_, cIdx) => (
                        <td
                          key={cIdx}
                          className="py-1.5 px-3 text-xs whitespace-nowrap max-w-[260px] truncate border-r border-subtle/50 last:border-r-0"
                          title={typeof row[cIdx] === 'object' ? JSON.stringify(row[cIdx]) : String(row[cIdx] || '')}
                        >
                          {row[cIdx] !== undefined && row[cIdx] !== '' ? (
                            typeof row[cIdx] === 'object' ? (
                              <span className="font-mono text-fg-muted">{JSON.stringify(row[cIdx])}</span>
                            ) : (
                              row[cIdx]
                            )
                          ) : (
                            <span className="text-fg-muted/40 italic">null</span>
                          )}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    ) : rawText ? (
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-fg">데이터 텍스트 샘플</span>
          <span className="text-2xs text-fg-muted font-mono">{rawText.split('\n').length}</span>
        </div>
        <pre className="p-3.5 rounded-xl bg-surface-muted/60 border border-subtle font-mono text-xs text-fg-muted overflow-x-auto max-h-56 whitespace-pre-wrap">
          {rawText.slice(0, 1200)}
          {rawText.length > 1200 && '\n... (이하 생략)'}
        </pre>
      </div>
    ) : null}
  </>
);
