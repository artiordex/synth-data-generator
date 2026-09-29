/**
 * 파일명: AiGuideArtifactDownloads.tsx
 * 경로: apps/web/src/features/aiguide/AiGuideArtifactDownloads.tsx
 * 목적: AI 가이드 문서와 메타데이터 산출물 다운로드를 제공함
 * 작성자: 개발팀
 * 작성일: 2026-09-29
 * 수정일: 2026-09-30
 */
import React from 'react';
import { Check, Copy, Download } from 'lucide-react';
import type { AiGuideHumanFormat } from '../../services/api';

interface AiGuideArtifactDownloadsProps {
  documentTitle: string;
  humanFormat: AiGuideHumanFormat;
  zipDocumentBase64: string;
  humanDocumentBase64: string;
  allDocumentsBase64: Record<string, string>;
  customMarkdownGuide: string | null;
  generatedMarkdownGuide: string;
  customJsonRule: string | null;
  metadataXml: string;
  serverJsonLd: string;
  generatedJsonLd: string;
  copySuccess: boolean;
  onDownloadBase64: (content: string, filename: string, mimeType: string) => void;
  onDownloadFile: (content: string, filename: string, mimeType: string) => void;
  onCopyClipboard: (text: string) => void;
}

/** 생성된 가이드 파일을 다운로드하고 내용을 복사함 */
export const AiGuideArtifactDownloads: React.FC<AiGuideArtifactDownloadsProps> = ({
  documentTitle,
  humanFormat,
  zipDocumentBase64,
  humanDocumentBase64,
  allDocumentsBase64,
  customMarkdownGuide,
  generatedMarkdownGuide,
  customJsonRule,
  metadataXml,
  serverJsonLd,
  generatedJsonLd,
  copySuccess,
  onDownloadBase64,
  onDownloadFile,
  onCopyClipboard,
}) => (
  <>
    {/* 생성 완료 후 개별 문서와 메타데이터 다운로드 */}
  {(zipDocumentBase64 || humanDocumentBase64) && (
    <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-xl bg-surface-muted/60 border border-subtle">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-2xs font-bold text-fg-muted mr-1">개별 문서 다운로드:</span>
        <button
          type="button"
          className="text-xs px-2.5 py-1.5 rounded-lg border border-subtle bg-surface text-fg hover:bg-surface-muted font-medium flex items-center gap-1 cursor-pointer transition-colors"
          onClick={() => {
            const b64 = allDocumentsBase64['hwpx'] || (humanFormat === 'hwpx' ? humanDocumentBase64 : '');
            if (b64) onDownloadBase64(b64, `${documentTitle}_AI_가이드.hwpx`, 'application/hwp+zip');
          }}
          title="한글 표준 문서 (HWPX)"
        >
          <Download className="w-3 h-3" /> HWPX
        </button>
        <button
          type="button"
          className="text-xs px-2.5 py-1.5 rounded-lg border border-subtle bg-surface text-fg hover:bg-surface-muted font-medium flex items-center gap-1 cursor-pointer transition-colors"
          onClick={() => {
            const b64 = allDocumentsBase64['docx'] || (humanFormat === 'docx' ? humanDocumentBase64 : '');
            if (b64) onDownloadBase64(b64, `${documentTitle}_AI_가이드.docx`, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document');
          }}
          title="Word 문서 (DOCX)"
        >
          <Download className="w-3 h-3" /> DOCX
        </button>
        <button
          type="button"
          className="text-xs px-2.5 py-1.5 rounded-lg border border-subtle bg-surface text-fg hover:bg-surface-muted font-medium flex items-center gap-1 cursor-pointer transition-colors"
          onClick={() => {
            const b64 = allDocumentsBase64['md'] || (humanFormat === 'md' ? humanDocumentBase64 : '');
            if (b64) onDownloadBase64(b64, `${documentTitle}_AI_가이드.md`, 'text/markdown;charset=utf-8');
            else onDownloadFile(customMarkdownGuide || generatedMarkdownGuide, `${documentTitle}_AI_가이드.md`, 'text/markdown;charset=utf-8');
          }}
          title="마크다운 문서 (MD)"
        >
          <Download className="w-3 h-3" /> MD
        </button>

        <button
          type="button"
          className="text-xs px-2.5 py-1.5 rounded-lg border border-subtle bg-surface text-fg hover:bg-surface-muted font-medium flex items-center gap-1 cursor-pointer transition-colors"
          onClick={() => {
            const b64 = allDocumentsBase64['html'] || (humanFormat === 'html' ? humanDocumentBase64 : '');
            if (b64) onDownloadBase64(b64, `${documentTitle}_AI_Guide.html`, 'text/html;charset=utf-8');
          }}
          title="HTML 문서"
        >
          <Download className="w-3 h-3" /> HTML
        </button>

        <span className="text-subtle mx-1">|</span>
        <span className="text-2xs font-bold text-fg-muted mr-1">메타데이터</span>

        <button
          type="button"
          className="text-xs px-2.5 py-1.5 rounded-lg border border-subtle bg-surface text-fg hover:bg-surface-muted font-medium flex items-center gap-1 cursor-pointer transition-colors"
          onClick={() => onDownloadFile(customJsonRule || '{}', `${documentTitle}_메타데이터.json`, 'application/json;charset=utf-8')}
          title="표준 JSON 메타데이터"
        >
          <Download className="w-3 h-3" /> JSON
        </button>
        <button
          type="button"
          className="text-xs px-2.5 py-1.5 rounded-lg border border-subtle bg-surface text-fg hover:bg-surface-muted font-medium flex items-center gap-1 cursor-pointer transition-colors"
          onClick={() => onDownloadFile(metadataXml, `${documentTitle}_메타데이터.xml`, 'application/xml;charset=utf-8')}
          title="표준 XML 메타데이터"
        >
          <Download className="w-3 h-3" /> XML
        </button>
        <button
          type="button"
          className="text-xs px-2.5 py-1.5 rounded-lg border border-subtle bg-surface text-fg hover:bg-surface-muted font-medium flex items-center gap-1 cursor-pointer transition-colors"
          onClick={() => onDownloadFile(serverJsonLd || generatedJsonLd, `${documentTitle}_메타데이터.jsonld`, 'application/ld+json;charset=utf-8')}
          title="W3C DCAT 3.0 JSON-LD"
        >
          <Download className="w-3 h-3" /> JSON-LD
        </button>
        {allDocumentsBase64['ai_knowledge'] && (
          <button
            type="button"
            className="text-xs px-2.5 py-1.5 rounded-lg border border-accent/40 bg-accent/5 text-fg hover:bg-accent/10 font-medium flex items-center gap-1 cursor-pointer transition-colors"
            onClick={() => onDownloadBase64(allDocumentsBase64['ai_knowledge'], `${documentTitle}_AI_지식.jsonl`, 'application/x-ndjson;charset=utf-8')}
            title="검색·문맥 제공용 항목별 JSONL. 미확정 정보와 AI 제안은 상태 및 근거와 함께 표시합니다."
          >
            <Download className="w-3 h-3" /> AI 지식 JSONL
          </button>
        )}
        {allDocumentsBase64['knowledge_manifest'] && (
          <button
            type="button"
            className="text-xs px-2.5 py-1.5 rounded-lg border border-subtle bg-surface text-fg hover:bg-surface-muted font-medium flex items-center gap-1 cursor-pointer transition-colors"
            onClick={() => onDownloadBase64(allDocumentsBase64['knowledge_manifest'], `${documentTitle}_AI_지식_manifest.json`, 'application/json;charset=utf-8')}
            title="JSONL의 해시, 스키마, 검토 상태 정책, 검색 적재 방법"
          >
            <Download className="w-3 h-3" /> 지식 매니페스트
          </button>
        )}
      </div>

      <button
        type="button"
        onClick={() => onCopyClipboard(customMarkdownGuide || generatedMarkdownGuide)}
        className="ui-button-secondary text-xs px-3 py-1.5 flex items-center gap-1.5 cursor-pointer shrink-0"
      >
        {copySuccess ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5 text-fg-muted" />}
        <span>{copySuccess ? '복사 완료' : 'Markdown 가이드 복사'}</span>
      </button>
    </div>
  )}
  </>
);
