import React, { useState } from 'react';
import { Database, Download, Link2, RefreshCw, Upload, X } from 'lucide-react';
import { generateRelational, getDownloadUrl, profileRelational, uploadDatasets } from '../../services/api';
import { UnifiedFileUploader } from '../shared/UnifiedFileUploader';

interface Props { isDarkMode: boolean; onClose: () => void }

export const RelationalSynthesisPanel: React.FC<Props> = ({ isDarkMode, onClose }) => {
  const [files, setFiles] = useState<File[]>([]);
  const [analysis, setAnalysis] = useState<any>(null);
  const [result, setResult] = useState<any>(null);
  const [model, setModel] = useState('turbo');
  const [scale, setScale] = useState(1);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [uploadedNames, setUploadedNames] = useState<string[]>([]);

  const analyze = async () => {
    if (files.length < 2) return;
    setBusy(true); setError(''); setResult(null);
    try {
      const uploaded = await uploadDatasets(files);
      const names = uploaded.flatMap(x => !x.error && x.filename ? [x.filename] : []);
      if (names.length < 2) throw new Error('정상 업로드된 테이블이 2개 미만입니다.');
      setUploadedNames(names);
      setAnalysis(await profileRelational({ file_names: names, model_type: model, scale }));
    } catch (e: any) { setError(e.message || '관계 분석 실패'); }
    finally { setBusy(false); }
  };

  const generate = async () => {
    setBusy(true); setError('');
    try {
      setResult(await generateRelational({ file_names: uploadedNames, model_type: model, scale,
        primary_keys: analysis.primary_keys, relationships: analysis.relationships }));
    } catch (e: any) { setError(e.message || '관계형 합성 실패'); }
    finally { setBusy(false); }
  };

  return <div className="space-y-6">
    <div className="ui-panel p-6">
      <div className="flex items-start justify-between"><div><h2 className="ui-section-title text-base"><Database className="h-5 w-5 text-sky-500"/>관계형 다중 테이블 합성</h2>
        <p className="ui-help-text mt-1">여러 테이블의 PK/FK를 자동 탐지하고 참조 무결성을 유지해 함께 생성합니다.</p></div>
        <button aria-label="단일 테이블 화면으로" onClick={onClose} className="ui-button-secondary px-2"><X className="h-4 w-4"/></button></div>
      <UnifiedFileUploader
        multiple
        maxFiles={20}
        title="관계형 테이블 파일 업로드 (2~20개)"
        subtitle="PK/FK 참조 관계를 가진 복수 테이블(CSV, Excel, TSV, JSON, Parquet)을 드래그하거나 선택하세요."
        onFilesSelected={selectedFiles => setFiles(selectedFiles)}
        className="mt-5"
      />
      {files.length > 0 && <div className="mt-2 text-xs text-slate-400">{files.map(f => f.name).join(' · ')}</div>}
      <button disabled={files.length < 2 || busy} onClick={analyze} className="ui-button-primary mt-4 px-5 py-2.5">
        {busy ? <RefreshCw className="mr-2 inline h-4 w-4 animate-spin"/> : <Link2 className="mr-2 inline h-4 w-4"/>}PK/FK 관계 분석</button>
      {error && <div className="mt-3 rounded-xl bg-rose-500/10 p-3 text-xs text-rose-500">{error}</div>}
    </div>

    {analysis && <div className="ui-panel p-6">
      <h3 className="ui-section-title">탐지 결과</h3>
      <div className="mt-3 grid gap-3 md:grid-cols-2">{analysis.tables.map((t: any) => <div key={t.name} className="rounded-xl border border-slate-500/20 p-3 text-xs"><b>{t.name}</b><div className="text-slate-400">{t.rows.toLocaleString()}행 · {t.columns.length}열 · PK {t.primary_key || '미탐지'}</div></div>)}</div>
      <div className="mt-4 space-y-2">{analysis.relationships.length ? analysis.relationships.map((r: any, i: number) => <div key={i} className="rounded-lg bg-sky-500/10 px-3 py-2 text-xs"><b>{r.parent_table}.{r.parent_key}</b> → {r.child_table}.{r.child_key}</div>) : <div className="text-xs text-amber-500">관계를 자동 탐지하지 못했습니다. 같은 이름의 PK/FK 값을 확인하세요.</div>}</div>
      <div className="mt-5 flex flex-wrap items-end gap-4"><label className="text-xs font-bold">모델<select value={model} onChange={e => setModel(e.target.value)} className="ui-field mt-1 block"><option value="turbo">Turbo 관계형</option><option value="hma">HMA AI 관계형</option></select></label>
        <label className="text-xs font-bold">생성 배율<input type="number" min="0.1" max="20" step="0.1" value={scale} onChange={e => setScale(Number(e.target.value))} className="ui-field mt-1 block w-28"/></label>
        <button disabled={!analysis.relationships.length || busy} onClick={generate} className="ui-button-primary px-6 py-2.5">관계형 합성 실행</button></div>
    </div>}

    {result && <div className="ui-panel p-6"><div className="flex items-center justify-between"><div><h3 className="font-bold text-emerald-500">생성 완료 · 참조 무결성 검사</h3><p className="text-xs text-slate-400">{result.tables.map((t: any) => `${t.name} ${t.rows.toLocaleString()}행`).join(' · ')}</p></div><a href={getDownloadUrl(result.download_url)} className="ui-button-primary px-5 py-2.5"><Download className="h-4 w-4"/>전체 ZIP 다운로드</a></div>
      <div className="mt-3 space-y-1">{result.relationships.map((r: any, i: number) => <div key={i} className="text-xs">{r.parent_table} → {r.child_table}: 고아 FK {r.orphan_count}건 · <b className={r.status === 'PASS' ? 'text-emerald-500' : 'text-rose-500'}>{r.status}</b></div>)}</div></div>}
  </div>;
};
