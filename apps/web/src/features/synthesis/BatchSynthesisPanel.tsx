import React, { useEffect, useRef, useState } from 'react';
import { BatchStatus, BatchUploadItem, JobStatus, SynthesisRequest } from '../../types';
import { uploadDatasets, startBatch, getBatch, cancelBatch, cancelSynthesis, getDownloadUrl } from '../../services/api';
import { AdvancedSynthesisSettings, defaultSynthesisOptions, SynthesisOptions } from './AdvancedSynthesisSettings';

export const ACTIVE_BATCH_KEY = 'synth.activeBatchId';
const labels: Record<string, string> = { pending: '대기', processing: '처리 중', completed: '완료',
  completed_with_errors: '일부 실패·취소', failed: '실패', canceled: '취소' };
const isRunning = (batch: BatchStatus | null) => !!batch && ['pending', 'processing'].includes(batch.status);

export function BatchSynthesisPanel({ initialFiles, isDarkMode, onClose, onOpenJob }: {
  initialFiles: File[]; isDarkMode: boolean; onClose: () => void; onOpenJob: (job: JobStatus) => void;
}) {
  const [files, setFiles] = useState<BatchUploadItem[]>([]);
  const [batch, setBatch] = useState<BatchStatus | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [model, setModel] = useState<SynthesisRequest['model_type']>('ctgan');
  const [rows, setRows] = useState(1000);
  const [sameRows, setSameRows] = useState(true);
  const [department, setDepartment] = useState('범용 데이터분석팀');
  const [purpose, setPurpose] = useState('합성데이터 생성 및 분석');
  const [dpEnabled, setDpEnabled] = useState(false);
  const [epsilon, setEpsilon] = useState(1);
  const [metadata, setMetadata] = useState<Record<number, Record<string, string>>>({});
  const [options, setOptions] = useState<SynthesisOptions>({});
  const [overrides, setOverrides] = useState<Record<number, SynthesisOptions>>({});
  const initialized = useRef(false);
  const active = isRunning(batch);
  const field = `border rounded-lg px-3 py-2 ${isDarkMode ? 'bg-slate-950 border-slate-700' : 'bg-white border-slate-300'}`;
  const good = files.filter(file => file.filename && file.profile && !file.error);

  async function upload(selected: File[]) {
    if (!selected.length) return;
    if (selected.length > 20) { setError('한 번에 최대 20개 파일을 선택하세요.'); return; }
    if (selected.some(f => f.size > 100 * 1024 * 1024)) { setError('파일당 최대 100MB까지 업로드할 수 있습니다.'); return; }
    setBusy(true); setError(''); setBatch(null); setFiles([]); setOverrides({}); setMetadata({});
    localStorage.removeItem(ACTIVE_BATCH_KEY);
    try { setFiles(await uploadDatasets(selected)); }
    catch (e) { setError(String(e)); }
    finally { setBusy(false); }
  }

  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;
    if (initialFiles.length) { void upload(initialFiles); return; }
    const stored = localStorage.getItem(ACTIVE_BATCH_KEY);
    if (stored) {
      setBusy(true);
      getBatch(stored).then(setBatch).catch(e => { setError(String(e)); localStorage.removeItem(ACTIVE_BATCH_KEY); })
        .finally(() => setBusy(false));
    }
  }, []);

  useEffect(() => {
    if (!batch || !isRunning(batch)) return;
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      try { const next = await getBatch(batch.id); if (!stopped) { setBatch(next); setError(''); } }
      catch (e) { if (!stopped) setError(String(e)); }
      finally { if (!stopped) timer = setTimeout(poll, 2000); }
    };
    timer = setTimeout(poll, 1000);
    return () => { stopped = true; clearTimeout(timer); };
  }, [batch?.id, active]);

  async function start() {
    setBusy(true); setError('');
    try {
      const requests: SynthesisRequest[] = files.flatMap((file, index) => file.filename && file.profile && !file.error ? [{
        ...defaultSynthesisOptions, ...file.profile.notebook_preset?.options, ...options, ...overrides[index], file_name: file.filename, original_filename: file.original_filename,
        model_type: model, target_rows: sameRows ? Math.max(file.profile.row_count, 1) : rows,
        department_name: department, project_purpose: purpose,
        dp_enabled: dpEnabled, eps: epsilon, quality_threshold: 0.8, review_metadata: metadata[index],
      }] : []);
      const result = await startBatch(requests);
      localStorage.setItem(ACTIVE_BATCH_KEY, result.id);
      setBatch(result);
    } catch (e) { setError(String(e)); }
    finally { setBusy(false); }
  }

  async function cancel(job?: JobStatus) {
    if (!batch) return;
    try {
      if (job) { await cancelSynthesis(job.id); setBatch(await getBatch(batch.id)); }
      else setBatch(await cancelBatch(batch.id));
    } catch (e) { setError(String(e)); }
  }

  return <section className={`space-y-5 p-6 rounded-2xl border ${isDarkMode ? 'bg-slate-900 border-slate-800 text-slate-100' : 'bg-white border-slate-200 text-slate-900'}`}>
    <div className="flex justify-between items-center"><h2 className="text-lg font-bold">파일 일괄 처리 · 최대 20개</h2>
      <button type="button" onClick={onClose} className="text-sm text-sky-600">단일 파일 화면으로</button></div>
    <p className="text-sm text-slate-500">파일별로 합성·평가·한글 문서 3종을 순서대로 생성합니다. 한 파일이 실패해도 다음 파일을 계속 처리합니다.</p>
    {error && <p role="alert" className="text-sm text-rose-600 break-words">{error}</p>}
    {!active && <label className={`block border-2 border-dashed rounded-xl p-6 text-center ${busy ? 'opacity-50' : 'cursor-pointer'}`}
      onDragOver={e => e.preventDefault()} onDrop={e => { e.preventDefault(); if (!busy) void upload(Array.from(e.dataTransfer.files)); }}>
      <span>{busy ? '파일 업로드·분석 또는 작업 등록 중…' : '파일 선택 또는 드래그 앤 드롭 (최대 20개, 파일당 100MB)'}</span>
      <input aria-label="일괄 처리 파일 선택" className="block mx-auto mt-3 text-xs" type="file" multiple disabled={busy}
        accept=".csv,.xlsx,.xls,.tsv,.txt" onChange={e => { void upload(Array.from(e.target.files || [])); e.target.value = ''; }} />
    </label>}
    {!batch && files.length > 0 && <>
      <div className="grid md:grid-cols-2 gap-3 text-sm">
        <label className="grid gap-1">생성 모델<select className={field} value={model} onChange={e => setModel(e.target.value as typeof model)}>
          <option value="statistical">통계 샘플러</option><option value="gaussian_copula">가우시안 코퓰라</option>
          <option value="ctgan">CTGAN</option><option value="tvae">TVAE</option></select></label>
        <label className="grid gap-1">파일당 생성 행 수<input className={field} type="number" min={1} disabled={sameRows} value={rows} onChange={e => setRows(Number(e.target.value))} /></label>
        <label className="grid gap-1">담당 부서<input className={field} value={department} onChange={e => setDepartment(e.target.value)} /></label>
        <label className="grid gap-1">활용 목적<input className={field} value={purpose} onChange={e => setPurpose(e.target.value)} /></label>
      </div>
      <label className="flex gap-2 text-sm"><input type="checkbox" checked={sameRows} onChange={e => setSameRows(e.target.checked)} />각 원본 파일과 같은 행 수 생성</label>
      <label className="flex gap-2 items-center text-sm"><input type="checkbox" checked={dpEnabled} onChange={e => setDpEnabled(e.target.checked)} />수치형 노이즈 처리 적용
        {dpEnabled && <input className={field} aria-label="노이즈 Epsilon" type="number" min={0.1} step={0.1} value={epsilon} onChange={e => setEpsilon(Number(e.target.value))} />}</label>
      <AdvancedSynthesisSettings options={options} onChange={setOptions} profile={null} isDarkMode={isDarkMode} />
      <p className="text-xs text-slate-500">공통 학습 설정을 적용하며, 아래 파일별 상세 설정에서 변경한 값이 우선합니다.</p>
      <div className="space-y-2">{files.map((file, index) => <div key={index} className="rounded-xl border border-slate-300/40 p-3">
        <div className="flex justify-between gap-3 text-sm"><strong className="break-all">{index + 1}. {file.original_filename}</strong>
          <span>{file.error ? '분석 실패' : `${file.profile?.row_count.toLocaleString()}행 · ${file.profile?.column_count}개 컬럼`}</span></div>
        {file.error ? <p className="text-xs text-rose-600 mt-2">{file.error}</p> : <><AdvancedSynthesisSettings
          options={{ ...defaultSynthesisOptions, ...file.profile?.notebook_preset?.options, ...options, ...overrides[index] }} onChange={value => setOverrides(prev => ({ ...prev, [index]: value }))}
          profile={file.profile || null} isDarkMode={isDarkMode} />
          <details className="p-3 text-xs"><summary className="cursor-pointer font-semibold">이 파일의 심의자료 입력</summary>
            <div className="grid md:grid-cols-2 gap-3 mt-3">{[
              ['dataset_name', '데이터명 (기본: 원본 파일명)'], ['special_notes', '특이사항'],
              ['overview', '정보 개요'], ['privacy_plan', '개인정보 처리계획'],
            ].map(([key, label]) => <label key={key} className="grid gap-1">{label}
              <textarea className={field} rows={2} value={metadata[index]?.[key] || ''}
                onChange={e => setMetadata(prev => ({ ...prev, [index]: { ...prev[index], [key]: e.target.value } }))} /></label>)}</div>
          </details></>}
      </div>)}</div>
      <button type="button" disabled={busy || !good.length || (!sameRows && rows < 1)} onClick={() => void start()}
        className="rounded-xl bg-sky-600 px-5 py-3 text-white font-bold disabled:opacity-50">{good.length}개 파일 일괄 실행</button>
      {good.length !== files.length && <p className="text-xs text-rose-600">분석에 실패한 {files.length - good.length}개 파일은 실행에서 제외됩니다.</p>}
    </>}
    {batch && <>
      <div className="flex flex-wrap items-center justify-between gap-3"><strong>{labels[batch.status]} · {batch.finished}/{batch.total}개 처리</strong>
        <span className="text-sm">완료 {batch.completed} · 실패 {batch.failed} · 취소 {batch.canceled}</span>
        {active && <button className="text-rose-600 text-sm" onClick={() => void cancel()}>전체 중단</button>}
        {batch.package_zip && <a className="bg-sky-600 text-white rounded-lg px-4 py-2 text-sm" href={getDownloadUrl(batch.package_zip)}>전체 결과 ZIP 다운로드</a>}
      </div>
      <progress className="w-full h-3" max={100} value={batch.progress} aria-label="일괄 처리 진행률" />
      {batch.error && <p role="alert" className="text-rose-600 text-sm">{batch.error}</p>}
      <div className="overflow-auto"><table className="w-full text-sm text-left"><thead><tr>
        <th className="p-2">파일</th><th>상태</th><th>진행·실패 사유</th><th>결과</th>
      </tr></thead><tbody>{batch.jobs.map(job => <tr key={job.id} className="border-t border-slate-300/40">
        <td className="p-2 break-all">{job.original_filename}</td><td className="whitespace-nowrap p-2">{labels[job.status]}</td>
        <td className="p-2 max-w-lg break-words">{job.progress}% · {job.error || job.message}</td>
        <td className="p-2 whitespace-nowrap space-x-3">{job.status === 'completed' ? <>
          <button className="text-sky-600" onClick={() => onOpenJob(job)}>결과 보기</button>
          {job.package_zip && <a className="text-sky-600" href={getDownloadUrl(job.package_zip)}>ZIP</a>}
        </> : ['pending', 'processing'].includes(job.status) && <button className="text-rose-600" onClick={() => void cancel(job)}>취소</button>}</td>
      </tr>)}</tbody></table></div>
      {active && <p className="text-xs text-slate-500">이 창을 닫아도 서버에서 계속 처리합니다. 새로고침하면 최근 일괄 작업을 다시 표시합니다.</p>}
    </>}
  </section>;
}
