import React, { useState } from 'react';
import { Clock3, Download, RefreshCw, Upload, X } from 'lucide-react';
import { generateTimeSeries, getDatasetProfile, getDownloadUrl, uploadDataset } from '../../services/api';
import { UnifiedFileUploader } from '../shared/UnifiedFileUploader';

export function TimeSeriesPanel({ isDarkMode, onClose }: { isDarkMode: boolean; onClose: () => void }) {
  const [fileName, setFileName] = useState('');
  const [columns, setColumns] = useState<string[]>([]);
  const [entity, setEntity] = useState('');
  const [time, setTime] = useState('');
  const [target, setTarget] = useState(100);
  const [result, setResult] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const upload = async (file: File) => {
    setBusy(true); setError('');
    try { const saved = await uploadDataset(file); const profile = await getDatasetProfile(saved.filename);
      const names = profile.columns.map(c => c.name); setFileName(saved.filename); setColumns(names);
      setEntity(names.find(n => /(^id$|_id$|고객|회원|환자|장비)/i.test(n)) || names[0] || '');
      setTime(names.find(n => /(date|time|일시|일자|날짜|시점)/i.test(n)) || names[1] || names[0] || '');
    } catch (e: any) { setError(e.message); } finally { setBusy(false); }
  };
  const run = async () => { setBusy(true); setError(''); try { setResult(await generateTimeSeries({ file_name: fileName, entity_column: entity, time_column: time, target_entities: target })); } catch (e: any) { setError(e.message); } finally { setBusy(false); } };
  return <div className="space-y-6"><div className="ui-panel p-6">
    <div className="flex justify-between"><div><h2 className="ui-section-title text-base"><Clock3 className="h-5 w-5 text-sky-500"/>시계열·패널 합성</h2><p className="ui-help-text mt-1">개체별 관측 순서와 시간 간격을 유지하면서 새 개체 시계열을 생성합니다.</p></div><button aria-label="단일 테이블 화면으로" onClick={onClose} className="ui-button-secondary px-2"><X className="h-4 w-4"/></button></div>
    {!fileName && (
      <UnifiedFileUploader
        title="시계열 데이터 파일 업로드"
        subtitle="시간 및 개체키 컬럼이 포함된 시계열·패널 데이터(CSV, Excel, TSV, JSON, Parquet)를 업로드하세요."
        isUploading={busy}
        busyText="시계열 데이터 업로드 및 구조 분석 중..."
        onFilesSelected={([selectedFile]) => {
          if (selectedFile) upload(selectedFile);
        }}
        onError={msg => setError(msg)}
        className="mt-5"
      />
    )}
    {columns.length > 0 && <div className="mt-5 grid gap-4 md:grid-cols-3"><label className="text-xs font-bold">개체키<select value={entity} onChange={e => setEntity(e.target.value)} className="ui-field mt-1">{columns.map(c => <option key={c}>{c}</option>)}</select></label><label className="text-xs font-bold">시간 컬럼<select value={time} onChange={e => setTime(e.target.value)} className="ui-field mt-1">{columns.map(c => <option key={c}>{c}</option>)}</select></label><label className="text-xs font-bold">생성 개체 수<input type="number" min="1" value={target} onChange={e => setTarget(Number(e.target.value))} className="ui-field mt-1"/></label></div>}
    {columns.length > 0 && <button disabled={busy} onClick={run} className="ui-button-primary mt-5 px-6 py-2.5">{busy && <RefreshCw className="h-4 w-4 animate-spin"/>}시계열 합성 실행</button>}{error && <p className="ui-error mt-3">{error}</p>}
  </div>{result && <div className="ui-panel p-6"><div className="flex justify-between"><div><b className="text-emerald-500">생성 완료</b><p className="text-xs text-slate-400">{result.entities}개 개체 · {result.rows.toLocaleString()}행 · 개체별 {result.min_observations}~{result.max_observations}회</p></div><a href={getDownloadUrl(result.download_url)} className="ui-button-primary px-5"><Download className="h-4 w-4"/>CSV 다운로드</a></div></div>}</div>;
}
