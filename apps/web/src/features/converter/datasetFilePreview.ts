/**
 * 파일명: datasetFilePreview.ts
 * 경로: apps/web/src/features/converter/datasetFilePreview.ts
 * 목적: 실제 원본·변환 파일의 코드·표 미리보기를 제공함
 * 작성자: 개발팀
 * 작성일: 2026-09-17
 * 수정일: 2026-09-17
 */
import Papa from 'papaparse';
import * as XLSX from 'xlsx';

export type PreviewMode = 'code' | 'table' | 'html';
export interface PreviewTable { headers: string[]; rows: unknown[][] }
export interface FilePreview { format: string; text?: string; table?: PreviewTable; sheets?: string[]; sheet?: string; notice?: string }
const TEXT_LIMIT = 2 * 1024 * 1024;
const WORKBOOK_LIMIT = 20 * 1024 * 1024;
const ROW_LIMIT = 200;

// 확장자 별칭을 같은 미리보기 형식으로 정규화함
export function previewFormat(format: string): string {
  const value = format.replace(/^\./, '').toLowerCase();
  return ({ pq: 'parquet', markdown: 'md', htm: 'html' } as Record<string, string>)[value] || value;
}

// 텍스트는 코드, 표 파일은 표, HTML은 격리된 렌더링을 기본 표시함
export function defaultPreviewMode(format: string): PreviewMode {
  const normalized = previewFormat(format);
  return normalized === 'html' ? 'html' : ['csv', 'tsv', 'xlsx', 'xls', 'parquet'].includes(normalized) ? 'table' : 'code';
}

// 숫자 정밀도·키 순서·이스케이프를 변경하지 않고 JSON 공백만 정리함
export function formatJsonText(text: string): string {
  let quoted = false, escaped = false, depth = 0;
  const output: string[] = [];
  for (let i = 0; i < text.length; i++) {
    const char = text[i];
    if (quoted) {
      output.push(char);
      if (escaped) escaped = false;
      else if (char === '\\') escaped = true;
      else if (char === '"') quoted = false;
      continue;
    }
    if (char === '"') { quoted = true; output.push(char); }
    else if (/\s/.test(char)) continue;
    else if (char === '{' || char === '[') {
      output.push(char); depth++;
      if (depth > 128) return text;
      if (!/^\s*[}\]]/.test(text.slice(i + 1, i + 40))) output.push('\n' + '  '.repeat(depth));
    } else if (char === '}' || char === ']') {
      depth = Math.max(0, depth - 1);
      if (!/[{\[]\s*$/.test(output.slice(-2).join(''))) output.push('\n' + '  '.repeat(depth));
      output.push(char);
    } else if (char === ',') output.push(',\n' + '  '.repeat(depth));
    else if (char === ':') output.push(': ');
    else output.push(char);
  }
  return output.join('');
}

// BOM·지정 인코딩·XML 선언을 읽고 UTF-8 실패 시 CP949 계열로 해석함
function decodeText(bytes: ArrayBuffer, encoding?: string): string {
  const raw = new Uint8Array(bytes);
  let label = encoding === 'cp949' ? 'euc-kr' : encoding;
  if (raw[0] === 0xff && raw[1] === 0xfe) label = 'utf-16le';
  else if (raw[0] === 0xfe && raw[1] === 0xff) label = 'utf-16be';
  if (!label) label = new TextDecoder('latin1').decode(raw.slice(0, 256)).match(/^\s*<\?xml[^>]*encoding=["']([^"']+)["']/i)?.[1];
  if (label) return new TextDecoder(label).decode(raw);
  try { return new TextDecoder('utf-8', { fatal: true }).decode(raw, { stream: true }); }
  catch { return new TextDecoder('euc-kr').decode(raw); }
}

/** 대용량 결과 전체를 내려받지 않고 미리보기 한도까지만 읽음
 * @param url 실제 결과 파일 다운로드 URL
 * @param format 결과 파일 형식
 * @param signal 오래된 요청 취소 신호
 * @returns 한도 내 바이트, 한도 초과 시 표시 제한을 판별할 1바이트 포함
 */
export async function downloadPreviewBlob(url: string, format: string, signal?: AbortSignal): Promise<Blob> {
  const response = await fetch(url, { signal });
  if (!response.ok) throw new Error(`실제 파일을 읽지 못했습니다 (HTTP ${response.status}).`);
  const limit = ['xlsx', 'xls'].includes(previewFormat(format)) ? WORKBOOK_LIMIT : TEXT_LIMIT;
  const reader = response.body?.getReader();
  if (!reader) return new Blob();
  const chunks: BlobPart[] = [];
  let size = 0;
  try {
    while (size <= limit) {
      const { done, value } = await reader.read();
      if (done) break;
      const slice = value.slice(0, limit + 1 - size);
      chunks.push(slice);
      size += slice.length;
      if (size > limit) { await reader.cancel(); break; }
    }
  } finally { reader.releaseLock(); }
  return new Blob(chunks);
}

/** 실제 파일 바이트를 형식별 미리보기로 읽음
 * @param blob 원본 파일 또는 다운로드한 변환 파일
 * @param format 실제 파일 형식
 * @param sheetName 선택 시트
 * @param encoding 원본 CSV 문자 인코딩
 * @returns 원문·표·시트 목록과 미리보기 제한 안내
 */
export async function parseFilePreview(blob: Blob, format: string, sheetName?: string, encoding?: string): Promise<FilePreview> {
  const normalized = previewFormat(format);
  if (['xlsx', 'xls'].includes(normalized)) {
    if (blob.size > WORKBOOK_LIMIT) throw new Error('엑셀 미리보기는 최대 20 MiB입니다. 다운로드한 파일에서 확인하세요.');
    const buffer = await blob.arrayBuffer();
    const index = XLSX.read(buffer, { type: 'array', bookSheets: true });
    const selected = sheetName && index.SheetNames.includes(sheetName) ? sheetName : index.SheetNames[0];
    if (!selected) throw new Error('엑셀 시트가 없습니다.');
    const book = XLSX.read(buffer, { type: 'array', cellDates: true, sheets: selected, sheetRows: ROW_LIMIT + 1 });
    const sheet = book.Sheets[selected];
    const values: unknown[][] = [];
    if (sheet?.['!ref']) {
      const range = XLSX.utils.decode_range(sheet['!ref']);
      for (let row = range.s.r; row <= Math.min(range.e.r, range.s.r + ROW_LIMIT); row++) {
        const cells: unknown[] = [];
        for (let col = range.s.c; col <= Math.min(range.e.c, range.s.c + 511); col++) {
          const cell = sheet[XLSX.utils.encode_cell({ r: row, c: col })];
          cells.push(cell?.f ? '=' + cell.f : cell?.v ?? null);
        }
        values.push(cells);
      }
    }
    return { format: normalized, table: { headers: (values[0] || []).map(v => String(v ?? '')), rows: values.slice(1) },
      sheets: index.SheetNames, sheet: selected, notice: '실제 시트의 최대 200행·512열을 표시합니다. 수식은 실행하지 않습니다.' };
  }
  const text = decodeText(await blob.slice(0, TEXT_LIMIT).arrayBuffer(), ['csv', 'tsv', 'txt'].includes(normalized) ? encoding : undefined);
  const truncated = blob.size > TEXT_LIMIT;
  const result: FilePreview = { format: normalized, text,
    notice: truncated ? '처음 2 MiB만 표시합니다. 전체 내용은 다운로드 파일에서 확인하세요.' : undefined };
  if (['csv', 'tsv'].includes(normalized)) {
    const parsed = Papa.parse<string[]>(text, { delimiter: normalized === 'tsv' ? '\t' : '', dynamicTyping: false,
      skipEmptyLines: true, preview: ROW_LIMIT + 1 });
    result.table = { headers: parsed.data[0] || [], rows: parsed.data.slice(1) };
    result.notice = [result.notice, '실제 파일의 최대 200개 데이터 행을 표시합니다. CSV/TSV 원문도 확인할 수 있습니다.'].filter(Boolean).join(' ');
  } else if (normalized === 'json' && !truncated) result.text = formatJsonText(text);
  return result;
}

// Parquet 표 요약을 텍스트 원문으로 위장하지 않고 제한을 표시함
export function parquetPreview(headers: string[], rows: Record<string, unknown>[]): FilePreview {
  return { format: 'parquet', table: { headers, rows: rows.map(row => headers.map(key => row[key])) },
    notice: 'Parquet는 바이너리 형식입니다. 서버가 읽은 데이터 행의 표 요약이며 원문 코드는 제공하지 않습니다.' };
}
