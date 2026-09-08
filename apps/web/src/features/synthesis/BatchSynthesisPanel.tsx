import React, { useEffect, useRef, useState } from 'react';
import { BatchStatus, BatchUploadItem, JobStatus, ReviewMetadataInput, SynthesisRequest } from '../../types';
import { uploadDatasets, startBatch, getBatch, cancelBatch, cancelSynthesis, getDownloadUrl } from '../../services/api';
import { AdvancedSynthesisSettings, defaultSynthesisOptions, SynthesisOptions } from './AdvancedSynthesisSettings';
import { UnifiedFileUploader } from '../shared/UnifiedFileUploader';

const labels: Record<string, string> = { pending: '대기', processing: '처리 중', completed: '완료',
  completed_with_errors: '일부 실패·취소', failed: '실패', canceled: '취소' };
const isRunning = (batch: BatchStatus | null) => !!batch && ['pending', 'processing'].includes(batch.status);
const reviewFields: Array<[keyof Pick<ReviewMetadataInput, 'dataset_name' | 'special_notes' | 'overview' | 'privacy_plan'>, string]> = [
  ['dataset_name', '데이터명 (기본: 원본 파일명)'], ['special_notes', '특이사항'],
  ['overview', '정보 개요'], ['privacy_plan', '개인정보 처리계획'],
];

export function BatchSynthesisPanel({ initialFiles, initialBatchId, isDarkMode, onClose, onOpenJob }: {
  initialFiles: File[]; initialBatchId?: string | null; isDarkMode: boolean; onClose: () => void; onOpenJob: (job: JobStatus) => void;
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
  const [metadata, setMetadata] = useState<Record<number, ReviewMetadataInput>>({});
  const [options, setOptions] = useState<SynthesisOptions>({});
  const [overrides, setOverrides] = useState<Record<number, SynthesisOptions>>({});
  const initialized = useRef(false);
  const active = isRunning(batch);
  const field = 'ui-field';
  const good = files.filter(file => file.filename && file.profile && !file.error);

  async function upload(selected: File[]) {
    if (!selected.length) return;
    if (selected.length > 20) { setError('한 번에 최대 20개 파일을 선택하세요.'); return; }
    if (selected.some(f => f.size > 100 * 1024 * 1024)) { setError('파일당 최대 100MB까지 업로드할 수 있습니다.'); return; }
    setBusy(true); setError(''); setBatch(null); setFiles([]); setOverrides({}); setMetadata({});
    try { setFiles(await uploadDatasets(selected)); }
    catch (e) { setError(String(e)); }
    finally { setBusy(false); }
  }

  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;
    if (initialFiles.length) { void upload(initialFiles); return; }
    if (initialBatchId) {
      setBusy(true);
      getBatch(initialBatchId).then(setBatch).catch(e => setError(String(e)))
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

  return <section className="ui-panel space-y-5 p-6">
    <div className="flex justify-between items-center"><h2 className="ui-section-title text-base">파일 일괄 처리 · 최대 20개</h2>
      <button type="button" onClick={onClose} className="ui-button-secondary">단일 파일 화면으로</button></div>
    <p className="ui-help-text">파일별로 합성·평가·한글 문서 3종을 순서대로 생성합니다. 한 파일이 실패해도 다음 파일을 계속 처리합니다.</p>
    {error && <p role="alert" className="text-sm text-rose-600 break-words">{error}</p>}
    {!active && (
      <UnifiedFileUploader
        multiple
        maxFiles={20}
        title="일괄 처리 데이터 파일 업로드 (최대 20개)"
        subtitle="CSV, Excel(XLSX/XLS), TSV, JSON, Parquet 등 여러 데이터셋을 드래그하거나 선택하여 일괄 업로드합니다."
        isUploading={busy}
        busyText="파일 업로드·분석 또는 작업 등록 중…"
        onFilesSelected={selectedFiles => void upload(selectedFiles)}
        onError={msg => setError(msg)}
      />
    )}
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
          profile={file.profile || null} isDarkMode={isDarkMode}
          reviewMetadata={metadata[index] || {}}
          onReviewMetadataChange={value => setMetadata(prev => ({ ...prev, [index]: value }))} />
          <details className="p-3 text-xs"><summary className="cursor-pointer font-semibold">이 파일의 심의자료 입력</summary>
            <div className="grid md:grid-cols-2 gap-3 mt-3">{reviewFields.map(([key, label]) => <label key={key} className="grid gap-1">{label}
              <textarea className={field} rows={2} value={metadata[index]?.[key] || ''}
                onChange={e => setMetadata(prev => ({ ...prev, [index]: { ...prev[index], [key]: e.target.value } }))} /></label>)}</div>
          </details></>}
      </div>)}</div>
      <button type="button" disabled={busy || !good.length || (!sameRows && rows < 1)} onClick={() => void start()}
        className="ui-button-primary px-5 py-3">{good.length}개 파일 일괄 실행</button>
      {good.length !== files.length && <p className="text-xs text-rose-600">분석에 실패한 {files.length - good.length}개 파일은 실행에서 제외됩니다.</p>}
    </>}
    {batch && <>
      <div className="flex flex-wrap items-center justify-between gap-3"><strong>{labels[batch.status]} · {batch.finished}/{batch.total}개 처리</strong>
        <span className="text-sm">완료 {batch.completed} · 실패 {batch.failed} · 취소 {batch.canceled}</span>
        {active && <button className="ui-button-danger" onClick={() => void cancel()}>전체 중단</button>}
        {batch.package_zip && <a className="ui-button-primary" href={getDownloadUrl(batch.package_zip)}>전체 결과 ZIP 다운로드</a>}
      </div>
      <progress className="w-full h-3" max={100} value={batch.progress} aria-label="일괄 처리 진행률" />
      {batch.error && <p role="alert" className="text-rose-600 text-sm">{batch.error}</p>}
      <div className="ui-table-shell"><table className="ui-table"><thead><tr>
        <th>파일</th><th>상태</th><th>진행·실패 사유</th><th>결과</th>
      </tr></thead><tbody>{batch.jobs.map(job => <tr key={job.id}>
        <td className="break-all">{job.original_filename}</td><td className="whitespace-nowrap">{labels[job.status]}</td>
        <td className="max-w-lg break-words">{job.progress}% · {job.error || job.message}</td>
        <td className="whitespace-nowrap space-x-3">{job.status === 'completed' ? <>
          <button className="text-sky-600" onClick={() => onOpenJob(job)}>결과 보기</button>
          {job.package_zip && <a className="text-sky-600" href={getDownloadUrl(job.package_zip)}>ZIP</a>}
        </> : ['pending', 'processing'].includes(job.status) && <button className="text-rose-600" onClick={() => void cancel(job)}>취소</button>}</td>
      </tr>)}</tbody></table></div>
      {active && <p className="text-xs text-slate-500">이 창을 닫아도 서버에서 계속 처리합니다. 새로고침하면 최근 일괄 작업을 다시 표시합니다.</p>}
    </>}
  </section>;
}
