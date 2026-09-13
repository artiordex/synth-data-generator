/**
 * 파일명: NativeDocumentWorkspace.tsx
 * 경로: apps/web/src/features/pseudonym/NativeDocumentWorkspace.tsx
 * 목적: 원본 문서 가명화 작업 화면을 제공함
 * 작성자: 개발팀
 * 작성일: 2026-09-09
 * 수정일: 2026-09-09
 */
import React, { useRef, useState } from 'react';
import { AlertCircle, ChevronLeft, ChevronRight, Download, FileText, Loader2, Plus, RotateCcw, ShieldCheck, Trash2, Upload } from 'lucide-react';

export type NativeSession = { id: string; page_count: number; preview_available?: boolean; format: string; ignored?: string[]; candidates: { original: string; replacement: string; kind: string; count: number }[] };
type NativeResult = { attempt: string; download_url: string; verified: boolean; report: { page_count: number; changed_regions: number; layout: string; selected_text_residual: string; similarity_percent?: number | null; scope: string } };
const PROCESS_STAGES = ['원본 문서 분석', '개인정보 영역 치환', '처리 페이지 렌더링', '레이아웃·원문 잔존 검증', '검증 결과 준비'];

async function post<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`/api/v1/document-privacy/${path}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : '입력값을 확인하세요.');
  return data;
}
export const inspectNativeDocument = (file_name: string) => post<NativeSession>('inspect', { file_name });

export function NativeDocumentWorkspace({ session, filename, onReplace }: { session: NativeSession; filename: string; onReplace: () => void }) {
  const [items, setItems] = useState(session.candidates);
  const [ignored, setIgnored] = useState(session.ignored || []);
  const [page, setPage] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<NativeResult | null>(null);
  const [showOriginal, setShowOriginal] = useState(false);
  const [notice, setNotice] = useState('');
  const [processStage, setProcessStage] = useState(0);
  const actionLock = useRef(false);
  const processTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  const update = (next: typeof items) => { setItems(next); setResult(null); setError(''); setNotice(''); };
  const rescan = async () => {
    if (actionLock.current) return;
    actionLock.current = true;
    setBusy(true); setError(''); setResult(null); setNotice('');
    try {
      const response = await fetch(`/api/v1/document-privacy/${session.id}/candidates`);
      if (!response.ok) throw new Error('재검사에 실패했습니다.');
      const data: { candidates: typeof items; ignored: string[] } = await response.json();
      setItems(data.candidates.map(item => {
        const existing = items.find(v => v.original === item.original);
        return existing ? { ...item, replacement: existing.replacement } : item;
      }));
      setIgnored(data.ignored);
    } catch (e) { setError(e instanceof Error ? e.message : '재검사 실패'); }
    finally { actionLock.current = false; setBusy(false); }
  };
  const exclude = async (word: string, action: 'add' | 'remove', index?: number) => {
    if (actionLock.current) return;
    if (!word.trim()) { update(items.filter((_, i) => i !== index)); return; }
    actionLock.current = true;
    const previousItems = items;
    const previousIgnored = ignored;
    if (action === 'add') {
      // Reflect the user's click immediately; restore the row if persistence fails.
      setItems(items.filter(v => v.original !== word));
      setIgnored([...ignored, word].filter((v, i, all) => all.indexOf(v) === i));
    } else {
      setIgnored(ignored.filter(v => v !== word));
    }
    setBusy(true); setError(''); setResult(null); setNotice(action === 'add' ? '제외 목록에 저장하는 중...' : '제외 해제 중...');
    try {
      const data = await post<{ ignored: string[] }>(`${session.id}/ignored`, { word, action });
      setIgnored(data.ignored);
      setNotice(action === 'add' ? `'${word}' 항목을 제외 목록에 반영했습니다.` : `'${word}' 항목을 다시 검사 대상으로 복원했습니다.`);
    }
    catch (e) {
      setItems(previousItems); setIgnored(previousIgnored);
      setNotice(''); setError(e instanceof Error ? e.message : '제외 목록 저장 실패');
    }
    finally { actionLock.current = false; setBusy(false); }
  };
  const process = async () => {
    if (actionLock.current) return;
    actionLock.current = true;
    setBusy(true); setResult(null); setError(''); setNotice(''); setProcessStage(1);
    processTimer.current = setInterval(() => setProcessStage(stage => Math.min(stage + 1, PROCESS_STAGES.length - 1)), 900);
    try { setResult(await post<NativeResult>(`${session.id}/process`, { replacements: items.map(({ original, replacement }) => ({ original, replacement })) })); setShowOriginal(true); setProcessStage(PROCESS_STAGES.length); setNotice('치환과 검증을 모두 통과했습니다.'); }
    catch (e) { setProcessStage(0); setError(e instanceof Error ? e.message : '문서 처리에 실패했습니다.'); }
    finally { if (processTimer.current) clearInterval(processTimer.current); processTimer.current = null; actionLock.current = false; setBusy(false); }
  };
  const valid = items.every(i => i.original.trim() && i.replacement.trim() && i.original !== i.replacement && i.original.length === i.replacement.length);
  const pageUrl = `/api/v1/document-privacy/${session.id}/pages/${page}`;
  return <div aria-busy={busy}>
    <div className="ps-filebar"><FileText size={24} /><div className="ps-filename"><strong>{filename}</strong><span>{session.format} · {session.page_count}페이지 · 원본 서식 유지</span></div><button className="ps-button" disabled={busy} onClick={onReplace}><Upload size={14} />다른 파일</button></div>
    {error && <div className="ps-error" role="alert"><AlertCircle size={18} /><span>{error}</span></div>}
    <div className="ps-native-warning">검토 필요 · 자동 탐지는 이메일·전화번호·주민등록번호·표기된 이름 후보입니다. 주소·이미지·미탐지 개인정보는 별도 검토 대상입니다.</div>
    {busy && processStage > 0 && <section className="ps-processing" role="status" aria-label="문서 처리 진행 상태"><div className="ps-processing-heading"><strong>문서 가명처리 및 검증 진행 중</strong><span>{Math.min(100, Math.round((processStage / PROCESS_STAGES.length) * 100))}%</span></div><progress max={PROCESS_STAGES.length} value={processStage} aria-label="문서 처리 진행률" /><ol>{PROCESS_STAGES.map((stage, index) => <li className={index + 1 < processStage ? 'done' : index + 1 === processStage ? 'active' : ''} key={stage}><span>{index + 1}</span>{stage}</li>)}</ol></section>}
    <fieldset disabled={busy} className="ps-fieldset">
      <section className="ps-native-targets"><div className="ps-section-title"><h3>개인정보 치환 항목</h3><button type="button" className="ps-button" onClick={rescan}><RotateCcw size={14} />재검사</button><button type="button" className="ps-button" onClick={() => update([...items, { original: '', replacement: '', kind: '직접 지정', count: 0 }])}><Plus size={14} />항목 추가</button></div>
        <div className="ps-native-list">{items.map((item, index) => <div className="ps-native-item" key={index}>
          <span>{item.kind}{item.count ? ` · ${item.count}곳` : ''}</span>
          <label>원문<input aria-label={`원문 ${index + 1}`} maxLength={200} value={item.original} onChange={e => update(items.map((v, i) => i === index ? { ...v, original: e.target.value } : v))} /></label>
          <label>대체값<input aria-label={`대체값 ${index + 1}`} maxLength={200} value={item.replacement} onChange={e => update(items.map((v, i) => i === index ? { ...v, replacement: e.target.value } : v))} /><small>{item.replacement.length} / {item.original.length}자</small></label>
          <button type="button" className="ps-button" title="이 문서에서 제외" aria-label={`항목 ${index + 1} 제외`} onClick={() => void exclude(item.original, 'add', index)}><Trash2 size={15} /></button>
        </div>)}</div>{!items.length && <p className="ps-muted">선택된 치환 항목 없음</p>}
      </section>
      {ignored.length > 0 && <details className="ps-advanced"><summary>이 문서 제외 목록 · {ignored.length}개</summary><ul className="ps-ignored-list">{ignored.map(word => <li key={word}><span>{word}</span><button type="button" className="ps-button" title="제외 해제" aria-label={`${word} 제외 해제`} onClick={() => void exclude(word, 'remove')}><RotateCcw size={14} /></button></li>)}</ul></details>}
      {notice && <p className="ps-native-notice" role="status"><ShieldCheck size={15} />{notice}</p>}
      <div className="ps-footer"><span className="ps-muted">{items.length ? `${session.format} → ${session.format} · 동일 글자 수 · 원본 영역 내 치환` : '개인정보 후보 없음 · 원본 형식 보존 검증 후 복제'}</span>{result?.verified && result.report.layout === 'PASS' && result.report.selected_text_residual === 'PASS' ? <a className="ps-primary ps-download-action" href={result.download_url}><Download size={16} />검증 완료 · 다운로드</a> : <button type="button" className="ps-primary" disabled={!valid || busy} onClick={() => void process()}>{busy ? <Loader2 className="ps-spin" size={16} /> : <ShieldCheck size={16} />}{busy ? '치환 및 검증 중' : items.length ? '치환 및 검증' : '원본 형식 검증 및 다운로드'}</button>}</div>
    </fieldset>
    {session.preview_available !== false && session.page_count > 0 ? <><div className="ps-review-toolbar"><h3>페이지 비교</h3><div className="ps-native-pagination"><button className="ps-button" title="이전 페이지" aria-label="이전 페이지" disabled={page === 0} onClick={() => setPage(page - 1)}><ChevronLeft size={16} /></button><span>{page + 1} / {session.page_count}</span><button className="ps-button" title="다음 페이지" aria-label="다음 페이지" disabled={page + 1 === session.page_count} onClick={() => setPage(page + 1)}><ChevronRight size={16} /></button></div></div><div className="ps-previews compare"><div className="ps-preview"><div className="ps-preview-title">원본 페이지</div>{showOriginal ? <img className="ps-native-page" src={pageUrl} alt={`원본 ${page + 1}페이지`} /> : <div className="ps-empty"><button className="ps-button" onClick={() => setShowOriginal(true)}>원본 페이지 열기</button></div>}</div><div className="ps-preview"><div className="ps-preview-title">처리 페이지</div>{result ? <img className="ps-native-page" src={`${pageUrl}?attempt=${result.attempt}`} alt={`처리본 ${page + 1}페이지`} /> : <div className="ps-empty">검증 완료 결과 대기</div>}</div></div></> : <div className="ps-native-no-preview" role="status"><ShieldCheck size={18} />문서에서 자동 탐지된 개인정보가 없어 원본 파일을 그대로 보존합니다. 다운로드 전 파일 무결성을 검증합니다.</div>}
    {result?.verified && result.report.layout === 'PASS' && result.report.selected_text_residual === 'PASS' && <div className="ps-result" role="status"><ShieldCheck size={20} /><div><strong>검증 통과 · {result.report.changed_regions ? `${result.report.changed_regions}곳 치환` : '개인정보 미검출'} · {result.report.page_count}페이지 동일</strong><span>원본 페이지와 처리 페이지 비교 완료 · 변경 영역 밖 픽셀 일치 · 선택 원문 잔존 검사 통과{result.report.similarity_percent != null ? ` · 유사도 ${result.report.similarity_percent.toFixed(1)}%` : ''}</span><span>{result.report.scope}</span></div></div>}
  </div>;
}
