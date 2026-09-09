/**
 * 파일명: PseudonymStudio.tsx
 * 경로: apps/web/src/features/pseudonym/PseudonymStudio.tsx
 * 목적: 가명데이터 처리 작업 화면을 제공함
 * 작성자: 개발팀
 * 작성일: 2026-09-09
 * 수정일: 2026-09-09
 */
import React, { useEffect, useRef, useState } from 'react';
import { AlertCircle, Check, ChevronDown, Download, FileSpreadsheet, FileText, Loader2, Search, ShieldCheck, Upload, X } from 'lucide-react';
import { uploadDataset, getDatasetProfile, pseudonymizeDataset, getDownloadUrl } from '../../services/api';
import { DatasetProfile } from '../../types';
import './pseudonym.css';
import { NativeDocumentWorkspace, NativeSession, inspectNativeDocument } from './NativeDocumentWorkspace';

const tableFormats = ['csv', 'xlsx', 'tsv', 'json', 'parquet'];
const documentFormats = ['pdf', 'hwp', 'hwpx', 'docx', 'md'];
const formats = [...tableFormats, ...documentFormats];
const methods = [['mask', '부분 마스킹'], ['faker', '가상값 치환'], ['token', '프로젝트 토큰'], ['hash', 'SHA-256 해시'], ['drop', '항목 삭제'], ['none', '원본 유지']];
const piiLabels: Record<string, string> = { name: '이름', phone_number: '전화번호', email: '이메일', address: '주소', ssn: '주민등록번호', unstructured_text: '텍스트 내 개인정보 후보' };
type Result = Awaited<ReturnType<typeof pseudonymizeDataset>>;

export const PseudonymStudio: React.FC<{ isDarkMode: boolean; onStepChange?: (step: number) => void }> = ({ onStepChange }) => {
  const input = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [native, setNative] = useState<NativeSession | null>(null);
  const [profile, setProfile] = useState<DatasetProfile | null>(null);
  const [uploaded, setUploaded] = useState('');
  const [busy, setBusy] = useState<'upload' | 'process' | null>(null);
  const [error, setError] = useState('');
  const [drag, setDrag] = useState(false);
  const [rules, setRules] = useState<Record<string, string>>({});
  const [format, setFormat] = useState('csv');
  const [project, setProject] = useState('default-project');
  const [quasi, setQuasi] = useState<string[]>([]);
  const [sensitive, setSensitive] = useState<string[]>([]);
  const [result, setResult] = useState<Result | null>(null);
  const [search, setSearch] = useState('');
  const [view, setView] = useState<'compare' | 'before' | 'after'>('compare');
  const [showOriginal, setShowOriginal] = useState(false);
  const documentMode = documentFormats.includes(file?.name.split('.').pop()?.toLowerCase() || '');
  const columns = profile?.columns.filter(c => !documentMode || c.name !== '문단번호') || [];
  const selectedCount = columns.filter(c => rules[c.name] && rules[c.name] !== 'none').length;
  const availableMethods = methods.filter(([v]) => !documentMode || ['mask', 'none'].includes(v));
  const updateRules = (next: Record<string, string>) => { setRules(next); setResult(null); };

  useEffect(() => {
    onStepChange?.(result ? 3 : profile || native ? 2 : 1);
  }, [native, onStepChange, profile, result]);

  const upload = async (files: File[]) => {
    if (busy) return;
    if (files.length !== 1) { setError('한 번에 파일 1개를 선택하세요.'); return; }
    const next = files[0], ext = next.name.split('.').pop()?.toLowerCase() || '';
    if (!formats.includes(ext)) { setError('지원하지 않는 파일 형식입니다.'); return; }
    if (!next.size || next.size > 100 * 1024 * 1024) { setError('파일 크기는 0보다 크고 100MB 이하여야 합니다.'); return; }
    setBusy('upload'); setError(''); setResult(null); setProfile(null); setUploaded('');
    setNative(null);
    setFile(next); setQuasi([]); setSensitive([]); setSearch(''); setShowOriginal(false);
    try {
      const saved = await uploadDataset(next);
      if (['pdf', 'hwp', 'hwpx'].includes(ext)) {
        setNative(await inspectNativeDocument(saved.filename));
        return;
      }
      const inspected = await getDatasetProfile(saved.filename, true);
      if (!inspected.row_count) throw new Error('추출 가능한 데이터가 없습니다. 스캔 문서는 OCR 처리가 필요합니다.');
      setUploaded(saved.filename); setProfile(inspected); setFormat(ext === 'hwp' ? 'hwpx' : ext);
      setRules(Object.fromEntries(inspected.columns.map(c => [c.name,
        (documentFormats.includes(ext) && c.name !== '문단번호') || c.pii_detected ? 'mask' : 'none'])));
    } catch (e) { setError(e instanceof Error ? e.message : '파일을 분석하지 못했습니다.'); }
    finally { setBusy(null); }
  };

  const execute = async () => {
    if (!profile || busy || !selectedCount || !project.trim()) return;
    setBusy('process'); setError(''); setResult(null);
    try {
      setResult(await pseudonymizeDataset({ file_name: uploaded,
        pii_actions: Object.fromEntries(Object.entries(rules).filter(([, v]) => v !== 'none')),
        export_format: format, project_id: project.trim(),
        quasi_identifiers: documentMode ? [] : quasi.filter(n => rules[n] !== 'drop'),
        sensitive_columns: documentMode ? [] : sensitive.filter(n => rules[n] !== 'drop') }));
      setView('compare');
    } catch (e) { setError(e instanceof Error ? e.message : '가명처리에 실패했습니다.'); }
    finally { setBusy(null); }
  };

  const preview = (after: boolean) => {
    const rows = after ? result?.pseudonymized_preview || [] : result?.original_preview || profile?.preview || [];
    const names = after ? result?.columns || [] : profile?.columns.map(c => c.name) || [];
    if (after && !result) return <div className="ps-empty"><ShieldCheck size={28} /><strong>처리 결과 대기</strong></div>;
    if (!after && !showOriginal) return <div className="ps-empty"><FileText size={28} /><button className="ps-button" onClick={() => setShowOriginal(true)}>원본 미리보기 열기</button></div>;
    if (documentMode) return <div className="ps-document">{rows.map((row, i) => <div className="ps-paragraph" key={i}><span>{String(i + 1).padStart(2, '0')}</span><p>{names.filter(n => n !== '문단번호').map(n => String(row[n] ?? '')).join('\n') || '(빈 내용)'}</p></div>)}</div>;
    return <div className="ps-grid-scroll"><table className="ps-data"><thead><tr>{names.map(n => <th key={n}>{n}</th>)}</tr></thead><tbody>{rows.map((row, i) => <tr key={i}>{names.map(n => <td key={n} className={after && String(row[n] ?? '') !== String(result?.original_preview[i]?.[n] ?? '') ? 'ps-changed' : ''}>{String(row[n] ?? '')}</td>)}</tr>)}</tbody></table></div>;
  };
  const filtered = columns.filter(c => `${c.name} ${piiLabels[c.pii_type] || ''}`.toLowerCase().includes(search.toLowerCase()));

  return <div className="ps-workspace" aria-busy={!!busy}>
    {error && <div className="ps-error" role="alert"><AlertCircle size={18} /><span>{error}</span><button aria-label="오류 닫기" onClick={() => setError('')}><X size={16} /></button></div>}
    <input ref={input} type="file" aria-label="가명처리 파일 선택" accept={formats.map(f => `.${f}`).join(',')} hidden disabled={!!busy} onChange={e => { if (e.target.files?.length) upload(Array.from(e.target.files)); e.target.value = ''; }} />
    {native ? <NativeDocumentWorkspace key={native.id} session={native} filename={file?.name || ''} onReplace={() => input.current?.click()} /> : !profile ? <section className={`ps-upload ${drag ? 'drag' : ''}`} onDragOver={e => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)} onDrop={e => { e.preventDefault(); setDrag(false); upload(Array.from(e.dataTransfer.files)); }}>
      <div className="ps-upload-icon">{busy ? <Loader2 className="ps-spin" size={30} /> : <Upload size={30} />}</div><h3>{busy ? '파일 업로드 및 분석 중' : '가명처리할 파일 선택'}</h3><p>{busy ? file?.name : '파일을 이곳에 놓거나 직접 선택하세요.'}</p>
      <button className="ps-primary" disabled={!!busy} onClick={() => input.current?.click()}><Upload size={16} />파일 선택</button>
      <div className="ps-formats"><div><FileSpreadsheet size={17} /><span>표 데이터</span><strong>CSV · XLSX · TSV · JSON · PARQUET</strong></div><div><FileText size={17} /><span>문서</span><strong>PDF · HWP · HWPX · DOCX · MD</strong></div></div><span className="ps-muted">파일당 최대 100MB · 스캔·이미지 문서는 OCR 필요</span>
    </section> : <>
      <div className="ps-filebar">{documentMode ? <FileText size={25} /> : <FileSpreadsheet size={25} />}<div className="ps-filename"><strong>{file?.name}</strong><span>{file ? (file.size / 1024 / 1024).toFixed(2) : '0'} MB · {documentMode ? '문서 텍스트' : '표 데이터'} · {profile.row_count.toLocaleString()}{documentMode ? '개 추출 구간' : '행'}{!documentMode && ` · ${profile.column_count}개 컬럼`}</span></div><button className="ps-button" disabled={!!busy} onClick={() => input.current?.click()}><Upload size={14} />다른 파일</button></div>
      <fieldset disabled={!!busy} className="ps-fieldset"><div className="ps-layout"><aside className="ps-rules">
        <div className="ps-section-title"><h3>처리 규칙</h3><span>{selectedCount} / {columns.length} 적용</span></div>
        <label className="ps-search"><Search size={15} /><input aria-label="처리 항목 검색" placeholder="항목 검색" value={search} onChange={e => setSearch(e.target.value)} /></label>
        <label className="ps-bulk">일괄 적용<select aria-label="일괄 처리방법" value="" onChange={e => updateRules(Object.fromEntries(columns.map(c => [c.name, e.target.value])))}><option value="" disabled>처리방법 선택</option>{availableMethods.map(([v, label]) => <option key={v} value={v}>{label}</option>)}</select></label>
        <div className="ps-rule-list">{filtered.map((c, i) => <div className="ps-rule" key={c.name}><div className="ps-rule-name"><span className="ps-number">{i + 1}</span><strong title={c.name}>{documentMode ? '문서 본문' : c.name}</strong></div><span className={`ps-label ${c.pii_detected ? 'detected' : ''}`}>{c.pii_detected ? piiLabels[c.pii_type] || c.pii_type || '개인정보 후보' : '자동 탐지 없음'}</span><select aria-label={`${c.name} 처리방법`} value={rules[c.name] || 'none'} onChange={e => updateRules({ ...rules, [c.name]: e.target.value })}>{availableMethods.map(([v, label]) => <option key={v} value={v}>{label}</option>)}</select></div>)}</div>
        {!filtered.length && <p className="ps-muted">검색 결과 없음</p>}
      </aside><section className="ps-review">
        <div className="ps-section-title"><h3>{documentMode ? '문서 검토' : '데이터 검토'}</h3><span>{documentMode ? '추출 텍스트 · 서식 재구성' : '미리보기'} · 최대 {result ? 15 : 10}{documentMode ? '개 구간' : '행'}</span></div>
        <div className="ps-review-toolbar"><div className="ps-tabs" role="tablist" aria-label="미리보기 보기 방식">{([['compare', '비교'], ['before', '원본'], ['after', '처리 결과']] as const).map(([v, label]) => <button key={v} role="tab" aria-selected={view === v} onClick={() => setView(v)}>{label}</button>)}</div>{showOriginal && <button className="ps-text-button" onClick={() => setShowOriginal(false)}>원본 숨기기</button>}</div>
        <div className={`ps-previews ${view === 'compare' ? 'compare' : ''}`}>{view !== 'after' && <div className="ps-preview"><div className="ps-preview-title"><FileText size={14} />원본</div>{preview(false)}</div>}{view !== 'before' && <div className="ps-preview"><div className="ps-preview-title"><ShieldCheck size={14} />처리 결과 {result && <Check size={14} />}</div>{preview(true)}</div>}</div>
        <details className="ps-advanced"><summary>고급 설정<ChevronDown size={14} /></summary><div className="ps-advanced-content"><label>프로젝트 토큰 영역<input aria-label="프로젝트 토큰 영역" value={project} maxLength={100} onChange={e => { setProject(e.target.value); setResult(null); }} /></label>
          {!documentMode && <div className="ps-evaluation">{([['준식별자 (k 평가)', quasi, setQuasi], ['민감항목 (l/t 평가)', sensitive, setSensitive]] as const).map(([label, selected, set]) => <div key={label}><strong>{label}</strong><div>{columns.filter(c => rules[c.name] !== 'drop').map(c => <label key={c.name}><input type="checkbox" checked={selected.includes(c.name)} onChange={e => { set(e.target.checked ? [...selected, c.name] : selected.filter(n => n !== c.name)); setResult(null); }} />{c.name}</label>)}</div></div>)}</div>}
        </div></details>
      </section></div>
      <footer className="ps-footer"><label>내보내기<select aria-label="내보내기 형식" value={format} onChange={e => { setFormat(e.target.value); setResult(null); }}>{formats.filter(f => f !== 'hwp').map(f => <option value={f} key={f}>{f.toUpperCase()}</option>)}</select></label><span className="ps-muted">{file?.name.toLowerCase().endsWith('.hwp') ? 'HWP 입력 → HWPX 출력 권장' : documentMode ? '본문·표 추출본 기준' : `${selectedCount}개 컬럼 처리`}</span>
        <button className="ps-primary" disabled={!selectedCount || !project.trim() || !!busy || columns.every(c => rules[c.name] === 'drop')} onClick={execute}>{busy === 'process' ? <Loader2 size={16} className="ps-spin" /> : <ShieldCheck size={16} />}{busy === 'process' ? '처리 중' : '가명처리 실행'}</button></footer></fieldset>
      {result && <div className="ps-result" role="status"><Check size={20} /><div><strong>처리 완료 · {result.rows_count.toLocaleString()}{documentMode ? '개 구간' : '행'}</strong><span>결과 검토 필요{!documentMode && result.privacy_metrics?.k != null ? ` · k=${result.privacy_metrics.k}` : ''}</span></div><a className="ps-primary" href={getDownloadUrl(result.download_url)}><Download size={16} />{format.toUpperCase()} 다운로드</a></div>}
    </>}
  </div>;
};
