import React, { useState } from 'react';
import {
  ShieldCheck, Upload, Download, RefreshCw,
  CheckCircle2, AlertCircle, FileText,
} from 'lucide-react';
import { uploadDataset, getDatasetProfile, pseudonymizeDataset, getDownloadUrl } from '../../services/api';
import { DatasetProfile } from '../../types';
import { UnifiedFileUploader } from '../shared/UnifiedFileUploader';

interface Props {
  isDarkMode: boolean;
}

export const PseudonymStudio: React.FC<Props> = ({ isDarkMode }) => {
  const [file, setFile] = useState<File | null>(null);
  const [uploadedFilename, setUploadedFilename] = useState<string>('');
  const [profile, setProfile] = useState<DatasetProfile | null>(null);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Column PII Actions: { [colName]: "faker" | "mask" | "hash" | "drop" }
  const [piiActions, setPiiActions] = useState<Record<string, string>>({});
  const [exportFormat, setExportFormat] = useState<string>('csv');
  const [projectId, setProjectId] = useState<string>('default-project');
  const [quasiIdentifiers, setQuasiIdentifiers] = useState<string[]>([]);
  const [sensitiveColumns, setSensitiveColumns] = useState<string[]>([]);

  // Result state
  const [result, setResult] = useState<{
    file_name: string;
    download_url: string;
    rows_count: number;
    columns: string[];
    summary: Record<string, any>;
    original_preview: Record<string, any>[];
    pseudonymized_preview: Record<string, any>[];
    privacy_metrics?: Record<string, any>;
  } | null>(null);

  const [previewTab, setPreviewTab] = useState<'after' | 'before'>('after');

  const handleFileUpload = async (selectedFile: File) => {
    setIsUploading(true);
    setErrorMsg(null);
    setResult(null);
    try {
      const uploadRes = await uploadDataset(selectedFile);
      setFile(selectedFile);
      setUploadedFilename(uploadRes.filename);

      const prof = await getDatasetProfile(uploadRes.filename);
      setProfile(prof);

      // Default actions for detected PII
      const defaultActions: Record<string, string> = {};
      prof.columns.forEach(col => {
        if (col.pii_detected) {
          defaultActions[col.name] = 'faker';
        }
      });
      setPiiActions(defaultActions);
    } catch (err: any) {
      setErrorMsg(err.message || '파일 업로드 및 분석에 실패했습니다.');
    } finally {
      setIsUploading(false);
    }
  };

  const handleExecutePseudonymization = async () => {
    if (!uploadedFilename) return;
    setIsProcessing(true);
    setErrorMsg(null);
    try {
      const res = await pseudonymizeDataset({
        file_name: uploadedFilename,
        pii_actions: piiActions,
        export_format: exportFormat,
        project_id: projectId,
        quasi_identifiers: quasiIdentifiers,
        sensitive_columns: sensitiveColumns,
      });
      setResult(res);
    } catch (err: any) {
      setErrorMsg(err.message || '가명화 처리에 실패했습니다.');
    } finally {
      setIsProcessing(false);
    }
  };

  const detectedPiiCols = profile?.columns.filter(c => c.pii_detected) || [];
  const otherCols = profile?.columns.filter(c => !c.pii_detected) || [];

  return (
    <div className="space-y-6">
      {errorMsg && (
        <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-rose-700 dark:text-rose-300 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-500" />
            <span>{errorMsg}</span>
          </div>
          <button onClick={() => setErrorMsg(null)} className="text-rose-500 hover:text-rose-700">닫기</button>
        </div>
      )}

      {/* Step 1: Upload Section */}
      {!profile && (
        <UnifiedFileUploader
          title="가명처리할 데이터 파일 업로드"
          subtitle="CSV, Excel(XLSX/XLS), TSV, JSON, Parquet 등 원본 데이터를 업로드하면 즉시 14종 PII 자동 탐지 및 가명화 계획을 수립합니다."
          isUploading={isUploading}
          busyText="파일 업로드 및 PII 자동 탐지 중..."
          onFilesSelected={([selectedFile]) => {
            if (selectedFile) handleFileUpload(selectedFile);
          }}
          onError={msg => setErrorMsg(msg)}
        />
      )}

      {/* Step 2: Inspection & Action Configuration */}
      {profile && (
        <div className="space-y-6">
          {/* File Meta bar */}
          <div className={`p-4 rounded-xl border flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
            isDarkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'
          }`}>
            <div className="flex items-center gap-3">
              <FileText className="w-5 h-5 text-emerald-500 shrink-0" />
              <div>
                <div className={`text-xs font-bold ${isDarkMode ? 'text-white' : 'text-slate-900'}`}>
                  {profile.filename}
                </div>
                <div className="text-[11px] text-slate-400 font-mono">
                  총 {profile.row_count.toLocaleString()}행 | {profile.column_count}개 컬럼 | 탐지된 식별자 {detectedPiiCols.length}개
                </div>
              </div>
            </div>

            <button
              onClick={() => {
                setProfile(null);
                setFile(null);
                setResult(null);
              }}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all self-start sm:self-auto ${
                isDarkMode ? 'bg-slate-800 border-slate-700 text-slate-300 hover:bg-slate-700' : 'bg-slate-100 border-slate-200 text-slate-700 hover:bg-slate-200'
              }`}
            >
              다른 파일 선택
            </button>
          </div>

          {/* PII Action Rules Card */}
          <div className={`p-4 sm:p-6 rounded-2xl border space-y-4 ${
            isDarkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'
          }`}>
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <h3 className={`font-bold text-sm flex items-center gap-2 ${isDarkMode ? 'text-white' : 'text-slate-900'}`}>
                  <ShieldCheck className="w-4 h-4 text-emerald-500 shrink-0" />
                  개인식별정보(PII) 가명처리 규칙 설정
                </h3>
                <p className={`text-xs mt-0.5 ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>
                  탐지된 민감정보별로 가명치환(Faker), 마스킹, SHA-256 해시, 컬럼 삭제 중 원하는 기법을 지정하세요.
                </p>
              </div>

              {/* Quick Batch Actions */}
              <div className="flex items-center gap-2 flex-wrap">
                <span className={`text-[11px] font-semibold ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>일괄 적용:</span>
                <button
                  onClick={() => {
                    const next: Record<string, string> = {};
                    detectedPiiCols.forEach(c => next[c.name] = 'faker');
                    setPiiActions(next);
                  }}
                  className={`px-2.5 py-1 rounded-lg text-xs font-semibold border transition-all ${
                    isDarkMode ? 'bg-slate-800 border-slate-700 text-slate-300' : 'bg-slate-100 border-slate-200 text-slate-700'
                  }`}
                >
                  가명 치환(Faker)
                </button>
                <button
                  onClick={() => {
                    const next: Record<string, string> = {};
                    detectedPiiCols.forEach(c => next[c.name] = 'mask');
                    setPiiActions(next);
                  }}
                  className={`px-2.5 py-1 rounded-lg text-xs font-semibold border transition-all ${
                    isDarkMode ? 'bg-slate-800 border-slate-700 text-slate-300' : 'bg-slate-100 border-slate-200 text-slate-700'
                  }`}
                >
                  마스킹(***)
                </button>
              </div>
            </div>

            {/* PII Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs min-w-[640px]">
                <thead>
                  <tr className={`border-b text-[11px] font-bold ${
                    isDarkMode ? 'border-slate-800 text-slate-400 bg-slate-950/60' : 'border-slate-200 text-slate-500 bg-slate-50'
                  }`}>
                    <th className="py-2.5 px-3">컬럼명</th>
                    <th className="py-2.5 px-3">탐지된 개인정보 분류</th>
                    <th className="py-2.5 px-3">원본 샘플 예시</th>
                    <th className="py-2.5 px-3">적용할 가명화 기법</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                  {detectedPiiCols.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="py-6 text-center text-slate-400">
                        자동 탐지된 직접 개인식별정보가 없습니다. 안전한 일반 데이터셋입니다.
                      </td>
                    </tr>
                  ) : (
                    detectedPiiCols.map(col => {
                      const currentAction = piiActions[col.name] || 'faker';
                      return (
                        <tr key={col.name} className={isDarkMode ? 'hover:bg-slate-800/40' : 'hover:bg-slate-50'}>
                          <td className="py-3 px-3 font-semibold text-sky-600 dark:text-sky-400">
                            {col.name}
                          </td>
                          <td className="py-3 px-3">
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20">
                              {col.pii_type}
                            </span>
                          </td>
                          <td className="py-3 px-3 font-mono text-slate-400 truncate max-w-xs">
                            {col.samples && col.samples.length > 0 ? col.samples.slice(0, 2).join(', ') : '-'}
                          </td>
                          <td className="py-3 px-3">
                            <select
                              value={currentAction}
                              onChange={e => setPiiActions({ ...piiActions, [col.name]: e.target.value })}
                              className={`px-3 py-1.5 rounded-xl border text-xs font-semibold outline-none transition-all ${
                                isDarkMode ? 'bg-slate-950 border-slate-700 text-white focus:border-emerald-500' : 'bg-white border-slate-200 text-slate-800 focus:border-emerald-500'
                              }`}
                            >
                              <option value="faker">가명 치환 (한국형 Faker 가상값)</option>
                              <option value="token">프로젝트 일관 토큰 (HMAC)</option>
                              <option value="mask">마스킹 (*** 대체)</option>
                              <option value="hash">일방향 암호화 (SHA-256 해시)</option>
                              <option value="drop">컬럼 삭제 (완전 제거)</option>
                            </select>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>

            <div className={`grid gap-4 rounded-xl border p-4 md:grid-cols-3 ${isDarkMode ? 'border-slate-800 bg-slate-950/40' : 'border-slate-200 bg-slate-50'}`}>
              <label className="text-xs font-bold">프로젝트 토큰 영역
                <input value={projectId} onChange={e => setProjectId(e.target.value)}
                  className={`mt-1 w-full rounded-lg border px-3 py-2 font-mono ${isDarkMode ? 'border-slate-700 bg-slate-950' : 'border-slate-300 bg-white'}`} />
                <span className="mt-1 block font-normal text-slate-400">같은 프로젝트·컬럼·원본값은 여러 파일에서도 같은 토큰이 됩니다.</span>
              </label>
              <div className="text-xs"><div className="mb-2 font-bold">준식별자 (k 평가)</div>
                <div className="max-h-28 space-y-1 overflow-auto">{profile.columns.map(col => <label key={col.name} className="flex gap-2">
                  <input type="checkbox" checked={quasiIdentifiers.includes(col.name)} onChange={e => setQuasiIdentifiers(e.target.checked ? [...quasiIdentifiers, col.name] : quasiIdentifiers.filter(x => x !== col.name))} />{col.name}
                </label>)}</div>
              </div>
              <div className="text-xs"><div className="mb-2 font-bold">민감정보 (l/t 평가)</div>
                <div className="max-h-28 space-y-1 overflow-auto">{profile.columns.map(col => <label key={col.name} className="flex gap-2">
                  <input type="checkbox" checked={sensitiveColumns.includes(col.name)} onChange={e => setSensitiveColumns(e.target.checked ? [...sensitiveColumns, col.name] : sensitiveColumns.filter(x => x !== col.name))} />{col.name}
                </label>)}</div>
              </div>
            </div>

            {/* Execution Controls */}
            <div className="pt-4 border-t dark:border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <span className={`text-xs font-bold ${isDarkMode ? 'text-slate-300' : 'text-slate-700'}`}>
                  내보내기 포맷:
                </span>
                <div className="flex items-center gap-2">
                  <label className="flex items-center gap-1.5 text-xs cursor-pointer">
                    <input
                      type="radio"
                      name="pseudo_fmt"
                      value="csv"
                      checked={exportFormat === 'csv'}
                      onChange={() => setExportFormat('csv')}
                      className="text-emerald-600"
                    />
                    <span>CSV (UTF-8 BOM)</span>
                  </label>
                  <label className="flex items-center gap-1.5 text-xs cursor-pointer ml-3">
                    <input
                      type="radio"
                      name="pseudo_fmt"
                      value="xlsx"
                      checked={exportFormat === 'xlsx'}
                      onChange={() => setExportFormat('xlsx')}
                      className="text-emerald-600"
                    />
                    <span>Excel (XLSX)</span>
                  </label>
                </div>
              </div>

              <button
                onClick={handleExecutePseudonymization}
                disabled={isProcessing}
                className="px-6 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-xs font-bold text-white shadow-lg shadow-emerald-600/20 flex items-center justify-center gap-2 transition-all disabled:opacity-50"
              >
                {isProcessing ? <RefreshCw className="w-4 h-4 animate-spin" /> : <ShieldCheck className="w-4 h-4" />}
                <span>{isProcessing ? '가명화 처리 중...' : '가명데이터 생성 및 다운로드 준비'}</span>
              </button>
            </div>
          </div>

          {/* Step 3: Result & Preview Grid */}
              {result && (
            <div className={`p-6 rounded-2xl border space-y-4 ${
              isDarkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'
            }`}>
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b pb-4 dark:border-slate-800">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                      가명화 처리 완료
                    </span>
                    <span className={`text-xs ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>
                      총 {result.rows_count.toLocaleString()}건 1:1 보존
                    </span>
                  </div>
                  <h3 className={`font-bold text-sm mt-1 ${isDarkMode ? 'text-white' : 'text-slate-900'}`}>
                    가명데이터 생성 결과 확인 및 다운로드
                  </h3>
                  {result.privacy_metrics && <div className="mt-2 flex flex-wrap gap-2 text-[11px]">
                    <span className={`rounded-full px-2 py-1 font-bold ${result.privacy_metrics.status === 'PASS' ? 'bg-emerald-500/10 text-emerald-600' : 'bg-amber-500/10 text-amber-600'}`}>{result.privacy_metrics.status === 'PASS' ? 'k/l/t 통과' : 'k/l/t 검토 필요'}</span>
                    {result.privacy_metrics.k != null && <span>k={result.privacy_metrics.k}</span>}
                    {result.privacy_metrics.l != null && <span>l={result.privacy_metrics.l}</span>}
                    {result.privacy_metrics.t != null && <span>t={Number(result.privacy_metrics.t).toFixed(3)}</span>}
                  </div>}
                </div>

                <a
                  href={getDownloadUrl(result.download_url)}
                  className="px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-xs font-bold text-white flex items-center gap-2 shadow-lg shadow-emerald-600/20 transition-all"
                >
                  <Download className="w-4 h-4" />
                  <span>{result.file_name} 다운로드</span>
                </a>
              </div>

              {/* Toggle Preview: Before vs After */}
              <div className="flex items-center justify-between">
                <div className={`flex items-center p-1 rounded-xl border text-xs font-semibold ${
                  isDarkMode ? 'bg-slate-950 border-slate-800' : 'bg-slate-100 border-slate-200'
                }`}>
                  <button
                    onClick={() => setPreviewTab('after')}
                    className={`px-3 py-1 rounded-lg transition-all ${
                      previewTab === 'after'
                        ? isDarkMode ? 'bg-emerald-600 text-white' : 'bg-white text-emerald-700 shadow-sm'
                        : isDarkMode ? 'text-slate-400 hover:text-slate-200' : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    가명처리 후 데이터 (After)
                  </button>
                  <button
                    onClick={() => setPreviewTab('before')}
                    className={`px-3 py-1 rounded-lg transition-all ${
                      previewTab === 'before'
                        ? isDarkMode ? 'bg-emerald-600 text-white' : 'bg-white text-emerald-700 shadow-sm'
                        : isDarkMode ? 'text-slate-400 hover:text-slate-200' : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    가명처리 전 원본 (Before)
                  </button>
                </div>

                <span className="text-[11px] text-slate-400">
                  상위 15건 레코드 샘플 프리뷰
                </span>
              </div>

              {/* Data Grid */}
              <div className="overflow-x-auto max-h-72 border rounded-xl dark:border-slate-800">
                <table className="w-full text-left text-xs min-w-[500px]">
                  <thead className={`sticky top-0 ${isDarkMode ? 'bg-slate-950 text-slate-300' : 'bg-slate-100 text-slate-700'}`}>
                    <tr>
                      {result.columns.map(c => (
                        <th key={c} className="py-2.5 px-3 font-semibold border-b dark:border-slate-800 whitespace-nowrap">
                          {c}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200 dark:divide-slate-800 font-mono">
                    {(previewTab === 'after' ? result.pseudonymized_preview : result.original_preview).map((row, idx) => (
                      <tr key={idx} className={isDarkMode ? 'hover:bg-slate-800/40' : 'hover:bg-slate-50'}>
                        {result.columns.map(c => (
                          <td key={c} className="py-2 px-3 whitespace-nowrap text-slate-300 dark:text-slate-300">
                            {row[c] !== undefined && row[c] !== null ? String(row[c]) : ''}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

    </div>
  );
};
