/**
 * 파일명: BatchSynthesisPanel.tsx
 * 경로: apps/web/src/features/synthesis/BatchSynthesisPanel.tsx
 * 목적: 합성 파일 일괄 처리 화면을 제공함 (순서 조정 및 일괄 문서 다운로드 포함)
 * 작성자: 개발팀
 * 작성일: 2026-09-09
 * 수정일: 2026-09-17
 */
import React, { useEffect, useRef, useState } from 'react';
import { Table, Shield, GripVertical, ChevronUp, ChevronDown, ArrowUpAZ, ArrowDownAZ, Download, FolderArchive } from 'lucide-react';
import { BatchStatus, BatchUploadItem, JobStatus, ReviewMetadataInput, SynthesisRequest } from '../../types';
import { uploadDatasets, startBatch, getBatch, cancelBatch, cancelSynthesis, getDownloadUrl } from '../../services/api';
import { AdvancedSynthesisSettings, defaultSynthesisOptions, SynthesisOptions } from './AdvancedSynthesisSettings';
import { TABLE_DATA_FILE_EXTENSIONS, TABLE_DATA_FORMATS_HINT, UnifiedFileUploader } from '../shared/UnifiedFileUploader';
import { SectionHeader } from '../../components/SectionHeader';


const labels: Record<string, string> = { pending: '대기', processing: '처리 중', completed: '완료',
  completed_with_errors: '일부 실패·취소', failed: '실패', canceled: '취소' };
const isRunning = (batch: BatchStatus | null) => !!batch && ['pending', 'processing'].includes(batch.status);
const reviewFields: Array<[keyof Pick<ReviewMetadataInput, 'dataset_name' | 'special_notes' | 'overview' | 'privacy_plan'>, string]> = [
  ['dataset_name', '데이터명 (기본: 원본 파일명)'], ['special_notes', '특이사항'],
  ['overview', '정보 개요'], ['privacy_plan', '개인정보 처리계획'],
];

/** 파일별 확장 상태: filename을 키로 해서 순서 변경과 독립적으로 유지됨 */
interface FileExtraState {
  metadata: ReviewMetadataInput;
  overrides: SynthesisOptions;
}

/** 자연어 숫자 정렬 comparator */
function naturalCompare(a: string, b: string) {
  return a.localeCompare(b, 'ko', { numeric: true, sensitivity: 'base' });
}

export function BatchSynthesisPanel({ initialFiles, initialBatchId, isDarkMode, onClose, onOpenJob, onStepChange }: {
  initialFiles: File[]; initialBatchId?: string | null; isDarkMode: boolean; onClose: () => void; onOpenJob: (job: JobStatus) => void; onStepChange?: (step: number) => void;
}) {
  const [files, setFiles] = useState<BatchUploadItem[]>([]);
  // 파일별 확장 상태: key = file.filename (서버 고유명)
  const [extras, setExtras] = useState<Record<string, FileExtraState>>({});
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
  const [options, setOptions] = useState<SynthesisOptions>({});
  // 드래그 앤 드롭 상태
  const [dragIndex, setDragIndex] = useState<number | null>(null);
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null);
  const initialized = useRef(false);
  const active = isRunning(batch);
  const field = 'ui-field';
  const good = files.filter(file => file.filename && file.profile && !file.error);

  useEffect(() => {
    onStepChange?.(batch ? (active ? 3 : 4) : files.length > 0 ? 2 : 1);
  }, [active, batch, files.length, onStepChange]);

  async function upload(selected: File[]) {
    if (!selected.length) return;
    if (selected.length > 20) { setError('한 번에 최대 20개 파일을 선택하세요.'); return; }
    if (selected.some(f => f.size > 100 * 1024 * 1024)) { setError('파일당 최대 100MB까지 업로드할 수 있습니다.'); return; }
    setBusy(true); setError(''); setBatch(null); setFiles([]); setExtras({});
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
      const requests: SynthesisRequest[] = files.flatMap((file) => file.filename && file.profile && !file.error ? [{
        ...defaultSynthesisOptions, ...file.profile.notebook_preset?.options, ...options,
        ...(extras[file.filename!]?.overrides || {}),
        file_name: file.filename!, original_filename: file.original_filename,
        model_type: model, target_rows: sameRows ? Math.max(file.profile.row_count, 1) : rows,
        department_name: department, project_purpose: purpose,
        dp_enabled: dpEnabled, eps: epsilon, quality_threshold: 0.8,
        review_metadata: extras[file.filename!]?.metadata,
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

  // 순서 변경 헬퍼
  function moveFile(from: number, to: number) {
    if (to < 0 || to >= files.length) return;
    const next = [...files];
    const [moved] = next.splice(from, 1);
    next.splice(to, 0, moved);
    setFiles(next);
  }

  function sortFiles(asc: boolean) {
    setFiles(prev => [...prev].sort((a, b) =>
      asc ? naturalCompare(a.original_filename, b.original_filename)
           : naturalCompare(b.original_filename, a.original_filename)
    ));
  }

  // Drag & Drop handlers
  function onDragStart(e: React.DragEvent, index: number) {
    setDragIndex(index);
    e.dataTransfer.effectAllowed = 'move';
  }
  function onDragOver(e: React.DragEvent, index: number) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    setDragOverIndex(index);
  }
  function onDrop(e: React.DragEvent, index: number) {
    e.preventDefault();
    if (dragIndex !== null && dragIndex !== index) moveFile(dragIndex, index);
    setDragIndex(null); setDragOverIndex(null);
  }
  function onDragEnd() { setDragIndex(null); setDragOverIndex(null); }

  // 파일별 extra 상태 업데이터
  function updateExtra(filename: string, patch: Partial<FileExtraState>) {
    setExtras(prev => {
      const existing = prev[filename] || { metadata: {} as ReviewMetadataInput, overrides: {} as SynthesisOptions };
      return { ...prev, [filename]: { ...existing, ...patch } };
    });
  }


  // 일괄 문서 다운로드 URL (documents_zip 우선, fallback은 API 엔드포인트)
  const documentsZipUrl = batch
    ? (batch.documents_zip
        ? getDownloadUrl(batch.documents_zip)
        : `/api/v1/batches/${batch.id}/download-documents`)
    : null;


  return <section className="ui-panel space-y-5 p-6">
    <SectionHeader
      title="파일 일괄 처리 · 최대 20개"
      description="파일별로 합성·평가·한글 문서 3종을 순서대로 생성합니다. 한 파일이 실패해도 다음 파일을 계속 처리합니다."
      action={<button type="button" onClick={onClose} className="ui-button-secondary">단일 파일 화면으로</button>}
    />
    {error && <p role="alert" className="text-sm text-rose-600 break-words">{error}</p>}
    {!active && (
      <UnifiedFileUploader
        multiple
        maxFiles={20}
        title="일괄 처리 데이터 파일 업로드 (최대 20개)"
        subtitle="CSV, Excel(XLSX/XLS), TSV, TXT, JSON, JSONL, Parquet 등 여러 표 데이터셋을 드래그하거나 선택하여 일괄 업로드합니다."
        accept={TABLE_DATA_FILE_EXTENSIONS}
        formatsHint={TABLE_DATA_FORMATS_HINT}
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

      {/* 파일 순서 조정 툴바 */}
      <div className="flex flex-wrap items-center gap-2 pb-1 border-b border-subtle">
        <span className="text-xs font-semibold text-fg-muted mr-1">처리 순서 조정</span>
        <button
          type="button"
          onClick={() => sortFiles(true)}
          className="ui-button-secondary flex items-center gap-1 px-2.5 py-1 text-xs"
          title="파일명 오름차순 정렬"
        >
          <ArrowUpAZ className="w-3.5 h-3.5" /> 오름차순
        </button>
        <button
          type="button"
          onClick={() => sortFiles(false)}
          className="ui-button-secondary flex items-center gap-1 px-2.5 py-1 text-xs"
          title="파일명 내림차순 정렬"
        >
          <ArrowDownAZ className="w-3.5 h-3.5" /> 내림차순
        </button>
        <span className="text-xs text-fg-muted ml-1">· 또는 각 항목을 드래그하거나 ▲▼ 버튼으로 순서를 조정하세요.</span>
      </div>

      <div className="space-y-3">{files.map((file, index) => {
        const key = file.filename || file.original_filename;
        const extra = extras[key] || { metadata: {} as ReviewMetadataInput, overrides: {} };
        const piiCount = file.profile ? Object.keys(file.profile.detected_pii || {}).length : 0;
        const rawPreview = file.profile?.preview || [];
        const isDragging = dragIndex === index;
        const isDragOver = dragOverIndex === index && dragIndex !== index;
        return (
          <div
            key={key}
            draggable
            onDragStart={e => onDragStart(e, index)}
            onDragOver={e => onDragOver(e, index)}
            onDrop={e => onDrop(e, index)}
            onDragEnd={onDragEnd}
            className={`rounded-xl border p-3.5 space-y-2.5 transition-all
              ${isDragging ? 'opacity-40 border-accent scale-[0.99]' : 'border-slate-300/40'}
              ${isDragOver ? 'border-accent border-dashed bg-accent/5 shadow-md' : ''}
            `}
          >
            <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
              <div className="flex items-center gap-2 min-w-0">
                {/* 드래그 핸들 */}
                <span
                  className="w-5 h-5 flex items-center justify-center text-fg-muted cursor-grab active:cursor-grabbing shrink-0"
                  title="드래그하여 순서 변경"
                >
                  <GripVertical className="w-4 h-4" />
                </span>
                {/* 순서 번호 배지 */}
                <span className="w-5 h-5 rounded-full bg-accent/15 text-accent text-2xs font-bold flex items-center justify-center shrink-0">
                  {index + 1}
                </span>
                <strong className="break-all font-semibold text-fg">{file.original_filename}</strong>
              </div>
              <div className="flex items-center gap-2 text-xs">
                {/* 위/아래 이동 버튼 */}
                <div className="flex items-center gap-0.5">
                  <button
                    type="button"
                    disabled={index === 0}
                    onClick={() => moveFile(index, index - 1)}
                    className="w-5 h-5 flex items-center justify-center rounded hover:bg-surface-muted disabled:opacity-25"
                    title="위로 이동"
                  ><ChevronUp className="w-3 h-3" /></button>
                  <button
                    type="button"
                    disabled={index === files.length - 1}
                    onClick={() => moveFile(index, index + 1)}
                    className="w-5 h-5 flex items-center justify-center rounded hover:bg-surface-muted disabled:opacity-25"
                    title="아래로 이동"
                  ><ChevronDown className="w-3 h-3" /></button>
                </div>
                {file.error ? (
                  <span className="text-rose-600 font-medium">분석 실패</span>
                ) : (
                  <>
                    <span className="px-2 py-0.5 rounded bg-surface-muted text-fg-muted font-mono text-2xs border border-subtle">
                      {file.profile?.row_count.toLocaleString()}행 · {file.profile?.column_count}개 컬럼
                    </span>
                    {piiCount > 0 ? (
                      <span className="px-2 py-0.5 rounded bg-warning-subtle text-warning font-medium text-2xs border border-warning/20 flex items-center gap-1">
                        <Shield className="w-3 h-3" />
                        PII {piiCount}개
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 rounded bg-success-subtle text-success font-medium text-2xs border border-success/20">
                        안전
                      </span>
                    )}
                  </>
                )}
              </div>
            </div>

            {file.error ? (
              <p className="text-xs text-rose-600 mt-2">{file.error}</p>
            ) : (
              <>
                {/* 원본 데이터 샘플 미리보기 */}
                {rawPreview.length > 0 && file.profile && (
                  <details className="rounded-lg border border-subtle bg-surface-muted/30 overflow-hidden text-xs">
                    <summary className="px-3 py-2 cursor-pointer font-semibold flex items-center justify-between text-fg hover:text-accent transition-colors select-none">
                      <span className="flex items-center gap-1.5">
                        <Table className="w-3.5 h-3.5 text-accent" />
                        <span>원본 데이터 샘플 미리보기 (상위 {rawPreview.length}행)</span>
                      </span>
                      <span className="text-2xs text-fg-muted font-normal">클릭하여 펼치기/접기</span>
                    </summary>
                    <div className="p-2 border-t border-subtle bg-surface overflow-x-auto max-h-[320px] scrollbar-thin">
                      <table className="w-full text-left text-2xs font-mono border-collapse">
                        <thead className="sticky top-0 bg-surface-muted border-b border-subtle text-fg font-bold z-10">
                          <tr>
                            <th className="px-2.5 py-1.5 border-r border-subtle text-center text-fg-muted bg-surface-muted w-10 shrink-0">#</th>
                            {file.profile.columns.map((col) => (
                              <th key={col.name} className="px-2.5 py-1.5 border-r border-subtle last:border-r-0 whitespace-nowrap">
                                <div className="flex items-center gap-1">
                                  <span>{col.name}</span>
                                  <span className={`px-1 py-0.2 rounded text-3xs font-mono font-normal border ${
                                    col.inferred_type === 'numerical'
                                      ? 'bg-accent-subtle text-accent border-accent/20'
                                      : col.inferred_type === 'pii'
                                      ? 'bg-danger-subtle text-danger border-danger/20'
                                      : 'bg-surface text-fg-subtle border-subtle'
                                  }`}>
                                    {col.inferred_type}
                                  </span>
                                </div>
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-subtle">
                          {rawPreview.map((row, rIdx) => (
                            <tr key={rIdx} className="hover:bg-surface-muted/30 transition-colors">
                              <td className="px-2.5 py-1 border-r border-subtle text-center text-fg-muted select-none bg-surface-muted/20">{rIdx + 1}</td>
                              {file.profile!.columns.map((col) => {
                                const val = row[col.name];
                                const isNull = val === null || val === undefined || val === '';
                                return (
                                  <td key={col.name} className="px-2.5 py-1 border-r border-subtle last:border-r-0 whitespace-nowrap text-fg/90">
                                    {isNull ? <span className="italic text-fg-muted/50 text-3xs">null</span> : String(val)}
                                  </td>
                                );
                              })}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </details>
                )}

                <AdvancedSynthesisSettings
                  options={{ ...defaultSynthesisOptions, ...file.profile?.notebook_preset?.options, ...options, ...extra.overrides }}
                  onChange={value => updateExtra(key, { overrides: value })}
                  profile={file.profile || null}
                  isDarkMode={isDarkMode}
                  reviewMetadata={extra.metadata}
                  onReviewMetadataChange={value => updateExtra(key, { metadata: value })}
                />
                <details className="p-3 text-xs border border-subtle rounded-lg bg-surface-muted/20">
                  <summary className="cursor-pointer font-semibold">이 파일의 심의자료 입력</summary>
                  <div className="grid md:grid-cols-2 gap-3 mt-3">
                    {reviewFields.map(([rKey, label]) => (
                      <label key={rKey} className="grid gap-1">
                        {label}
                        <textarea
                          className={field}
                          rows={2}
                          value={extra.metadata?.[rKey] || ''}
                          onChange={e => updateExtra(key, { metadata: { ...extra.metadata, [rKey]: e.target.value } })}
                        />
                      </label>
                    ))}
                  </div>
                </details>
              </>
            )}
          </div>
        );
      })}</div>
      <button type="button" disabled={busy || !good.length || (!sameRows && rows < 1)} onClick={() => void start()}
        className="ui-button-primary px-5 py-3">{good.length}개 파일 일괄 실행</button>
      {good.length !== files.length && <p className="text-xs text-rose-600">분석에 실패한 {files.length - good.length}개 파일은 실행에서 제외됩니다.</p>}
    </>}
    {batch && <>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <strong>{labels[batch.status]} · {batch.finished}/{batch.total}개 처리</strong>
        <span className="text-sm">완료 {batch.completed} · 실패 {batch.failed} · 취소 {batch.canceled}</span>
        {active && <button className="ui-button-danger" onClick={() => void cancel()}>전체 중단</button>}
        {/* 다운로드 버튼 영역 (완료 후 표시) */}
        {!active && (batch.package_zip || batch.documents_zip) && (
          <div className="flex flex-wrap gap-2 items-center">
            {documentsZipUrl && (
              <a
                className="ui-button-primary flex items-center gap-1.5 px-3 py-2 text-sm"
                href={documentsZipUrl}
                title="원천데이터, 합성데이터, 심의자료가 처리 순서(01, 02, …)로 넘버링된 단일 ZIP 파일"
              >
                <Download className="w-4 h-4" />
                일괄 문서 다운로드 (순서 넘버링)
              </a>
            )}
            {batch.package_zip && (
              <a
                className="ui-button-secondary flex items-center gap-1.5 px-3 py-2 text-sm"
                href={getDownloadUrl(batch.package_zip)}
                title="원본 폴더 구조(원천데이터/합성데이터/심의자료 폴더별)로 패키징된 전체 결과 ZIP"
              >
                <FolderArchive className="w-4 h-4" />
                폴더별 결과 ZIP
              </a>
            )}
          </div>
        )}
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
