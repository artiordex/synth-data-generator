/**
 * 파일명: NativeDocumentWorkspace.tsx
 * 경로: apps/web/src/features/pseudonym/NativeDocumentWorkspace.tsx
 * 목적: 원본 문서 가명화 작업 화면을 제공함
 * 작성자: 개발팀
 * 작성일: 2026-09-09
 * 수정일: 2026-09-09
 */
import React, { useState } from 'react';
import { AlertCircle, ChevronLeft, ChevronRight, Download, FileText, Loader2, Plus, ShieldCheck, Trash2, Upload } from 'lucide-react';

export type NativeSession = { id: string; page_count: number; format: string; candidates: { original: string; replacement: string; kind: string; count: number }[] };
type NativeResult = { attempt: string; download_url: string; report: { page_count: number; changed_regions: number; scope: string } };

async function post<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`/api/v1/document-privacy/${path}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : '입력값을 확인하세요.');
  return data;
}
export const inspectNativeDocument = (file_name: string) => post<NativeSession>('inspect', { file_name });

export function NativeDocumentWorkspace({ session, filename, onReplace }: { session: NativeSession; filename: string; onReplace: () => void }) {
  const [items, setItems] = useState(session.candidates);
  const [page, setPage] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<NativeResult | null>(null);
  const [showOriginal, setShowOriginal] = useState(false);
  const update = (next: typeof items) => { setItems(next); setResult(null); setError(''); };
  const process = async () => {
    setBusy(true); setResult(null); setError('');
    try { setResult(await post<NativeResult>(`${session.id}/process`, { replacements: items.map(({ original, replacement }) => ({ original, replacement })) })); }
    catch (e) { setError(e instanceof Error ? e.message : '문서 처리에 실패했습니다.'); }
    finally { setBusy(false); }
  };
  const valid = items.length > 0 && items.every(i => i.original.trim() && i.replacement.trim() && i.original !== i.replacement && i.original.length === i.replacement.length);
  const pageUrl = `/api/v1/document-privacy/${session.id}/pages/${page}`;
  return <div aria-busy={busy}>
    <div className="ps-filebar"><FileText size={24} /><div className="ps-filename"><strong>{filename}</strong><span>{session.format} · {session.page_count}페이지 · 원본 서식 유지</span></div><button className="ps-button" disabled={busy} onClick={onReplace}><Upload size={14} />다른 파일</button></div>
    {error && <div className="ps-error" role="alert"><AlertCircle size={18} /><span>{error}</span></div>}
    <div className="ps-native-warning">검토 필요 · 자동 탐지는 이메일·전화번호·주민등록번호·표기된 이름 후보입니다. 주소·이미지·미탐지 개인정보는 별도 검토 대상입니다.</div>
    <fieldset disabled={busy} className="ps-fieldset">
      <section className="ps-native-targets"><div className="ps-section-title"><h3>개인정보 치환 항목</h3><button className="ps-button" onClick={() => update([...items, { original: '', replacement: '', kind: '직접 지정', count: 0 }])}><Plus size={14} />항목 추가</button></div>
        <div className="ps-native-list">{items.map((item, index) => <div className="ps-native-item" key={index}>
          <span>{item.kind}{item.count ? ` · ${item.count}곳` : ''}</span>
          <label>원문<input aria-label={`원문 ${index + 1}`} maxLength={200} value={item.original} onChange={e => update(items.map((v, i) => i === index ? { ...v, original: e.target.value } : v))} /></label>
          <label>대체값<input aria-label={`대체값 ${index + 1}`} maxLength={200} value={item.replacement} onChange={e => update(items.map((v, i) => i === index ? { ...v, replacement: e.target.value } : v))} /><small>{item.replacement.length} / {item.original.length}자</small></label>
          <button className="ps-button" title="치환 항목 삭제" aria-label={`항목 ${index + 1} 삭제`} onClick={() => update(items.filter((_, i) => i !== index))}><Trash2 size={15} /></button>
        </div>)}</div>{!items.length && <p className="ps-muted">선택된 치환 항목 없음</p>}
      </section>
      <div className="ps-footer"><span className="ps-muted">{session.format} → {session.format} · 동일 글자 수 · 원본 영역 내 치환</span><button className="ps-primary" disabled={!valid || busy} onClick={process}>{busy ? <Loader2 className="ps-spin" size={16} /> : <ShieldCheck size={16} />}{busy ? '치환 및 검증 중' : '치환 및 검증'}</button></div>
    </fieldset>
    <div className="ps-review-toolbar"><h3>페이지 비교</h3><div className="ps-native-pagination"><button className="ps-button" title="이전 페이지" aria-label="이전 페이지" disabled={page === 0} onClick={() => setPage(page - 1)}><ChevronLeft size={16} /></button><span>{page + 1} / {session.page_count}</span><button className="ps-button" title="다음 페이지" aria-label="다음 페이지" disabled={page + 1 === session.page_count} onClick={() => setPage(page + 1)}><ChevronRight size={16} /></button></div></div>
    <div className="ps-previews compare"><div className="ps-preview"><div className="ps-preview-title">원본 페이지</div>{showOriginal ? <img className="ps-native-page" src={pageUrl} alt={`원본 ${page + 1}페이지`} /> : <div className="ps-empty"><button className="ps-button" onClick={() => setShowOriginal(true)}>원본 페이지 열기</button></div>}</div><div className="ps-preview"><div className="ps-preview-title">처리 페이지</div>{result ? <img className="ps-native-page" src={`${pageUrl}?attempt=${result.attempt}`} alt={`처리본 ${page + 1}페이지`} /> : <div className="ps-empty">검증 완료 결과 대기</div>}</div></div>
    {result && <div className="ps-result" role="status"><ShieldCheck size={20} /><div><strong>{result.report.changed_regions}곳 치환 · {result.report.page_count}페이지 동일</strong><span>변경 영역 밖 픽셀 일치 · 선택 원문 잔존 검사 통과</span><span>{result.report.scope}</span></div><a className="ps-primary" href={result.download_url}><Download size={16} />{session.format} 다운로드</a></div>}
  </div>;
}
