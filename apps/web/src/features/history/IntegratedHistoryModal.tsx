/**
 * 파일명: IntegratedHistoryModal.tsx
 * 경로: apps/web/src/features/history/IntegratedHistoryModal.tsx
 * 목적: 통합 작업 이력 모달을 표시함
 * 작성자: 개발팀
 * 작성일: 2026-09-09
 * 수정일: 2026-09-09
 */
import React, { useState, useEffect, useMemo } from 'react';
import { 
  History, 
  X, 
  Search, 
  RefreshCw, 
  Download, 
  ChevronRight, 
  ShieldCheck, 
  Cpu, 
  Database, 
  Filter, 
  Clock, 
  FileSpreadsheet,
  Trash2,
  ArrowLeftRight,
  Layers,
} from 'lucide-react';
import { JobStatus } from '../../types';
import { clearAllHistory, getPseudonymHistory, getDummyHistory, getJobsList, getBatchesList, getConverterHistory, getDownloadUrl } from '../../services/api';

export type HistoryType = 'all' | 'pseudo' | 'synthetic' | 'dummy' | 'batch' | 'converter';
const statusLabels: Record<string, string> = { pending: '대기', processing: '처리 중', completed: '완료', completed_with_errors: '일부 실패·취소', failed: '실패', canceled: '취소' };
const actionLabels: Record<string, string> = { mask: '마스킹', hash: '해시', faker: '가명 대체', drop: '삭제' };

interface Props {
  isOpen: boolean;
  onClose: () => void;
  isDarkMode: boolean;
  onSelectJob?: (job: JobStatus) => void;
  onSelectBatch?: (id: string) => void;
  initialType?: HistoryType;
}

export interface UnifiedHistoryItem {
  id: string;
  type: Exclude<HistoryType, 'all'>;
  typeName: string;
  targetName: string;
  subName?: string;
  createdAt: string;
  timestamp: number;
  rowsCount: number;
  specSummary: string;
  resultBadge?: {
    text: string;
    variant: 'emerald' | 'sky' | 'amber' | 'rose' | 'slate';
  };
  downloadUrl?: string;
  downloadFilename?: string;
  rawJob?: JobStatus;
  batchId?: string;
}

export const IntegratedHistoryModal: React.FC<Props> = ({
  isOpen,
  onClose,
  isDarkMode,
  onSelectJob,
  onSelectBatch,
  initialType = 'all'
}) => {
  const [items, setItems] = useState<UnifiedHistoryItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [selectedType, setSelectedType] = useState<HistoryType>('all');
  const [loadError, setLoadError] = useState('');
  const [isClearing, setIsClearing] = useState(false);

  const handleClearHistory = async () => {
    if (!window.confirm('통합 작업 이력 전체를 삭제할까요? 생성 결과 파일과 템플릿은 유지됩니다.')) return;
    setIsClearing(true);
    setLoadError('');
    try {
      await clearAllHistory();
      setItems([]);
      setSearchTerm('');
      setSelectedType('all');
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : '이력 삭제 실패');
    } finally {
      setIsClearing(false);
    }
  };

  const loadAllHistory = async () => {
    setIsLoading(true);
    try {
      const results = await Promise.allSettled([
        getPseudonymHistory(), getDummyHistory(), getJobsList(), getBatchesList(), getConverterHistory()
      ]);
      const [pseudoList, dummyList, jobsList, batchesList, converterList] = results.map(result => result.status === 'fulfilled' ? result.value : []);
      const names = ['가명처리', '더미데이터', 'AI 합성', '일괄 처리', '데이터 변환'];
      setLoadError(results.flatMap((result, index) => result.status === 'rejected' ? [names[index]] : []).join(', '));

      const unified: UnifiedHistoryItem[] = [];

      // 1. Pseudonymization items
      pseudoList.forEach((item: any) => {
        const d = item.created_at ? new Date(item.created_at) : new Date();
        unified.push({
          id: `pseudo-${item.id || Math.random()}`,
          type: 'pseudo',
          typeName: '가명데이터',
          targetName: item.original_file || item.file_name || '원본 파일',
          subName: item.file_name,
          createdAt: item.created_at || '-',
          timestamp: isNaN(d.getTime()) ? 0 : d.getTime(),
          rowsCount: item.rows_count || 0,
          specSummary: `${item.columns_count ?? 0}개 컬럼 · ${Object.entries(item.pii_summary ?? {}).map(([column, spec]) => `${column}: ${actionLabels[(spec as { action: string }).action] || '처리'}`).join(', ') || '처리 항목 없음'}`,
          resultBadge: {
            text: item.export_format || 'CSV',
            variant: 'emerald'
          },
          downloadUrl: item.download_url,
          downloadFilename: item.file_name
        });
      });

      // 2. Synthetic items
      jobsList.forEach((j: JobStatus) => {
        const d = j.created_at ? new Date(j.created_at) : new Date();
        const grade = j.assessment_grade;
        const variant = grade === 'S' ? 'emerald' : grade === 'A' ? 'sky' : grade === 'B' ? 'amber' : 'rose';
        
        unified.push({
          id: `synth-${j.id}`,
          type: 'synthetic',
          typeName: 'AI 합성데이터',
          targetName: j.original_filename || '합성 데이터셋',
          subName: `${(j.model_type || 'statistical').toUpperCase()} 모델`,
          createdAt: j.created_at ? new Date(j.created_at).toLocaleString('ko-KR', {
            year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit'
          }) : '-',
          timestamp: isNaN(d.getTime()) ? 0 : d.getTime(),
          rowsCount: j.target_rows || 0,
          specSummary: `품질 ${j.quality_score == null ? '-' : (j.quality_score * 100).toFixed(1) + '%'} · 위험도 ${j.reid_risk == null ? '-' : (j.reid_risk * 100).toFixed(2) + '%'}`,
          resultBadge: j.status === 'completed' ? {
            text: j.assessment_passed ? `${grade ?? '-'} 등급 (${j.assessment_score ?? '-'}점)` : '완료 · 검토 필요',
            variant: variant
          } : {
            text: statusLabels[j.status] || j.status,
            variant: 'slate'
          },
          downloadUrl: j.package_zip ? `/api/v1/files/download?path=${encodeURIComponent(j.package_zip)}` : undefined,
          downloadFilename: `${j.id}_review_package.zip`,
          rawJob: j
        });
      });

      // 3. Dummy items
      dummyList.forEach((item: any) => {
        const d = item.created_at ? new Date(item.created_at) : new Date();
        unified.push({
          id: `dummy-${item.id || Math.random()}`,
          type: 'dummy',
          typeName: '더미데이터',
          targetName: item.table_name || '더미 테이블',
          subName: item.file_name,
          createdAt: item.created_at || '-',
          timestamp: isNaN(d.getTime()) ? 0 : d.getTime(),
          rowsCount: item.rows_generated || 0,
          specSummary: `${item.columns_count ?? 0}개 표준 도메인 스키마 기반 생성`,
          resultBadge: {
            text: item.export_format || 'CSV',
            variant: 'amber'
          },
          downloadUrl: item.download_url,
          downloadFilename: item.file_name
        });
      });

      batchesList.forEach(batch => unified.push({
        id: batch.id, batchId: batch.id, type: 'batch', typeName: '일괄 처리',
        targetName: `${batch.total}개 파일 일괄 합성`,
        subName: batch.jobs.map((job: JobStatus) => job.original_filename).join(', '),
        createdAt: batch.created_at || '-', timestamp: Date.parse(batch.created_at) || 0,
        rowsCount: batch.jobs.reduce((sum: number, job: JobStatus) => sum + (job.target_rows ?? 0), 0),
        specSummary: `완료 ${batch.completed} · 실패 ${batch.failed} · 취소 ${batch.canceled} · 진행 ${batch.progress}%`,
        resultBadge: { text: statusLabels[batch.status] || batch.status, variant: batch.status === 'completed' ? 'emerald' : 'slate' },
        downloadUrl: batch.package_zip ? `/api/v1/files/download?path=${encodeURIComponent(batch.package_zip)}` : undefined,
        downloadFilename: `${batch.id}.zip`,
      }));

      // 5. Converter items
      (converterList || []).forEach((item: any) => {
        const d = item.created_at ? new Date(item.created_at) : new Date();
        const sizeStr = item.file_size
          ? (item.file_size < 1024
              ? `${item.file_size} B`
              : item.file_size < 1024 * 1024
              ? `${(item.file_size / 1024).toFixed(1)} KB`
              : `${(item.file_size / (1024 * 1024)).toFixed(2)} MB`)
          : '';

        unified.push({
          id: `conv-${item.id || Math.random()}`,
          type: 'converter',
          typeName: '데이터 변환',
          targetName: item.output_filename || item.original_filename || '변환 파일',
          subName: `${item.source_format} → ${item.target_format} (${item.category === 'document' ? '문서' : '데이터셋'})`,
          createdAt: item.created_at || '-',
          timestamp: isNaN(d.getTime()) ? 0 : d.getTime(),
          rowsCount: item.rows_count || 0,
          specSummary: `${item.category === 'document' ? '문서 서식 변환' : `${item.columns_count || 0}개 컬럼 · `}${sizeStr}`,
          resultBadge: {
            text: `${item.target_format} 완료`,
            variant: 'sky'
          },
          downloadUrl: item.download_url,
          downloadFilename: item.output_filename || item.original_filename
        });
      });

      // Sort newest first
      unified.sort((a, b) => b.timestamp - a.timestamp);
      setItems(unified);
    } catch (e) {
      console.error('통합 이력 로드 실패:', e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      setSelectedType(initialType);
      setSearchTerm('');
      loadAllHistory();
    }
  }, [isOpen, initialType]);

  // Filtered items
  const filteredItems = useMemo(() => {
    return items.filter(item => {
      if (selectedType !== 'all' && item.type !== selectedType) {
        return false;
      }
      if (searchTerm.trim()) {
        const q = searchTerm.toLowerCase();
        const matchTarget = item.targetName.toLowerCase().includes(q);
        const matchSub = (item.subName || '').toLowerCase().includes(q);
        const matchSummary = item.specSummary.toLowerCase().includes(q);
        const matchType = item.typeName.toLowerCase().includes(q);
        if (!matchTarget && !matchSub && !matchSummary && !matchType) {
          return false;
        }
      }
      return true;
    });
  }, [items, selectedType, searchTerm]);

  // Counts by track
  const counts = useMemo(() => {
    return {
      all: items.length,
      pseudo: items.filter(i => i.type === 'pseudo').length,
      synthetic: items.filter(i => i.type === 'synthetic').length,
      dummy: items.filter(i => i.type === 'dummy').length,
      batch: items.filter(i => i.type === 'batch').length,
      converter: items.filter(i => i.type === 'converter').length,
    };
  }, [items]);

  // Export audit log as CSV
  const handleExportAuditCSV = () => {
    if (items.length === 0) return;
    const headers = ['작업유형', '대상명', '산출파일명', '처리일시', '생성건수', '사양요약', '결과상태'];
    const rows = items.map(i => [
      i.typeName,
      `"${i.targetName.replace(/"/g, '""')}"`,
      `"${(i.subName || '').replace(/"/g, '""')}"`,
      `"${i.createdAt}"`,
      i.rowsCount,
      `"${i.specSummary.replace(/"/g, '""')}"`,
      `"${i.resultBadge?.text || ''}"`
    ]);

    const csvContent = '\uFEFF' + [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `통합작업이력_관리대장_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 dark:bg-black/80 backdrop-blur-sm p-3 sm:p-6 transition-all">
      <div className="ui-panel relative flex h-[92vh] w-full max-w-6xl flex-col overflow-hidden shadow-2xl">
        {/* Modal Header */}
        <div className={`px-6 py-4 border-b flex items-center justify-between transition-colors ${
          isDarkMode ? 'border-slate-800 bg-slate-900/90' : 'border-slate-200 bg-slate-50/80'
        }`}>
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-sky-700 text-white shadow-sm dark:bg-sky-600">
              <History className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold tracking-tight">통합 작업 이력 관리대장</h2>
                <span className={`text-2xs font-semibold px-2 py-0.5 rounded-full border ${
                  isDarkMode 
                    ? 'bg-emerald-950/60 text-emerald-300 border-emerald-800/60' 
                    : 'bg-emerald-50 text-emerald-700 border-emerald-200'
                }`}>
                  총 {items.length}건
                </span>
                <span className={`text-2xs font-medium px-2 py-0.5 rounded border hidden sm:inline-block ${
                  isDarkMode 
                    ? 'bg-slate-800 text-slate-400 border-slate-700' 
                    : 'bg-slate-100 text-slate-600 border-slate-200'
                }`}>
                  가명처리 · AI 합성 · 더미데이터 · 일괄 처리 · 데이터 변환
                </span>
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                최근 작업을 유형별로 조회하고 결과 파일과 심의자료를 내려받습니다.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleClearHistory}
              disabled={isClearing || items.length === 0}
              className="ui-button-danger"
              title="통합 작업 이력 전체 삭제"
            >
              <Trash2 className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">이력 전체 삭제</span>
            </button>
            <button
              onClick={handleExportAuditCSV}
              className="ui-button-secondary"
              title="관리대장 CSV 파일 다운로드"
            >
              <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-500" />
              <span>관리대장 내보내기</span>
            </button>

            <button
              onClick={onClose}
              className="ui-button-secondary px-2"
              title="닫기"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Toolbar: Search and Track Filters */}
        <div className={`px-6 py-3.5 border-b flex flex-col sm:flex-row items-center justify-between gap-3 transition-colors ${
          isDarkMode ? 'border-slate-800 bg-slate-950/40' : 'border-slate-200/80 bg-white'
        }`}>
          {/* Tracks Filter Tabs */}
          <div className="flex items-center gap-1.5 overflow-x-auto w-full sm:w-auto pb-1 sm:pb-0 scrollbar-none text-xs">
            <button
              onClick={() => setSelectedType('all')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium whitespace-nowrap transition-all border ${
                selectedType === 'all'
                  ? isDarkMode 
                    ? 'bg-slate-700 text-white border-slate-600 shadow-sm font-semibold' 
                    : 'bg-slate-800 text-white border-slate-800 shadow-sm font-semibold'
                  : isDarkMode 
                    ? 'bg-slate-800/80 text-slate-300 border-slate-700/80 hover:bg-slate-700/80' 
                    : 'bg-slate-100 text-slate-600 border-slate-200 hover:bg-slate-200/80'
              }`}
            >
              <Filter className="w-3.5 h-3.5" />
              <span>전체 이력</span>
              <span className="text-2xs px-1.5 py-0.2 rounded-full font-bold bg-white/20 text-white">
                {counts.all}
              </span>
            </button>

            <button
              onClick={() => setSelectedType('pseudo')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium whitespace-nowrap transition-all border ${
                selectedType === 'pseudo'
                  ? 'bg-emerald-600 text-white border-emerald-600 shadow-sm font-semibold'
                  : isDarkMode 
                    ? 'bg-slate-800/80 text-slate-300 border-slate-700/80 hover:bg-slate-700/80' 
                    : 'bg-slate-100 text-slate-600 border-slate-200 hover:bg-slate-200/80'
              }`}
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>가명데이터</span>
              <span className={`text-2xs px-1.5 py-0.2 rounded-full font-bold ${
                selectedType === 'pseudo' ? 'bg-white/20 text-white' : 'bg-emerald-500/20 text-emerald-600 dark:text-emerald-400'
              }`}>
                {counts.pseudo}
              </span>
            </button>

            <button
              onClick={() => setSelectedType('synthetic')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium whitespace-nowrap transition-all border ${
                selectedType === 'synthetic'
                  ? 'bg-sky-600 text-white border-sky-600 shadow-sm font-semibold'
                  : isDarkMode 
                    ? 'bg-slate-800/80 text-slate-300 border-slate-700/80 hover:bg-slate-700/80' 
                    : 'bg-slate-100 text-slate-600 border-slate-200 hover:bg-slate-200/80'
              }`}
            >
              <Cpu className="w-3.5 h-3.5" />
              <span>AI 합성데이터</span>
              <span className={`text-2xs px-1.5 py-0.2 rounded-full font-bold ${
                selectedType === 'synthetic' ? 'bg-white/20 text-white' : 'bg-sky-500/20 text-sky-600 dark:text-sky-400'
              }`}>
                {counts.synthetic}
              </span>
            </button>

            <button
              onClick={() => setSelectedType('dummy')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium whitespace-nowrap transition-all border ${
                selectedType === 'dummy'
                  ? 'bg-amber-600 text-white border-amber-600 shadow-sm font-semibold'
                  : isDarkMode 
                    ? 'bg-slate-800/80 text-slate-300 border-slate-700/80 hover:bg-slate-700/80' 
                    : 'bg-slate-100 text-slate-600 border-slate-200 hover:bg-slate-200/80'
              }`}
            >
              <Database className="w-3.5 h-3.5" />
              <span>더미데이터</span>
              <span className={`text-2xs px-1.5 py-0.2 rounded-full font-bold ${
                selectedType === 'dummy' ? 'bg-white/20 text-white' : 'bg-amber-500/20 text-amber-600 dark:text-amber-400'
              }`}>
                {counts.dummy}
              </span>
            </button>

            <button
              onClick={() => setSelectedType('converter')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium whitespace-nowrap transition-all border ${
                selectedType === 'converter'
                  ? 'bg-indigo-600 text-white border-indigo-600 shadow-sm font-semibold'
                  : isDarkMode 
                    ? 'bg-slate-800/80 text-slate-300 border-slate-700/80 hover:bg-slate-700/80' 
                    : 'bg-slate-100 text-slate-600 border-slate-200 hover:bg-slate-200/80'
              }`}
            >
              <ArrowLeftRight className="w-3.5 h-3.5" />
              <span>데이터 변환</span>
              <span className={`text-2xs px-1.5 py-0.2 rounded-full font-bold ${
                selectedType === 'converter' ? 'bg-white/20 text-white' : 'bg-indigo-500/20 text-indigo-600 dark:text-indigo-400'
              }`}>
                {counts.converter}
              </span>
            </button>

            <button
              onClick={() => setSelectedType('batch')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium whitespace-nowrap transition-all border ${
                selectedType === 'batch'
                  ? 'bg-sky-700 text-white border-sky-700 shadow-sm font-semibold'
                  : isDarkMode 
                    ? 'bg-slate-800/80 text-slate-300 border-slate-700/80 hover:bg-slate-700/80' 
                    : 'bg-slate-100 text-slate-600 border-slate-200 hover:bg-slate-200/80'
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              <span>일괄 처리</span>
              <span className={`text-2xs px-1.5 py-0.2 rounded-full font-bold ${
                selectedType === 'batch' ? 'bg-white/20 text-white' : 'bg-sky-500/20 text-sky-600 dark:text-sky-400'
              }`}>
                {counts.batch}
              </span>
            </button>
          </div>

          {/* Search Input & Refresh */}
          <div className="flex items-center gap-2 w-full sm:w-auto">
            <div className="relative flex-1 sm:w-64">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                placeholder="대상 파일명, 테이블명 검색..."
                className={`w-full pl-9 pr-7 py-1.5 rounded-xl text-xs border transition-all focus:outline-none focus:ring-2 focus:ring-sky-500/30 ${
                  isDarkMode 
                    ? 'bg-slate-800/80 border-slate-700 text-white placeholder-slate-500' 
                    : 'bg-slate-50 border-slate-200 text-slate-900 placeholder-slate-400'
                }`}
              />
              {searchTerm && (
                <button
                  onClick={() => setSearchTerm('')}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                >
                  <X className="w-3 h-3" />
                </button>
              )}
            </div>

            <button
              onClick={loadAllHistory}
              disabled={isLoading}
              className={`p-2 rounded-xl transition-colors border ${
                isDarkMode 
                  ? 'bg-slate-800 hover:bg-slate-700 text-slate-300 border-slate-700' 
                  : 'bg-white hover:bg-slate-50 text-slate-600 border-slate-200 shadow-sm'
              }`}
              title="이력 새로고침"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        {/* Content Table */}
        <div className="flex-1 overflow-y-auto p-6">
          {loadError && <p role="alert" className="mb-3 text-sm text-rose-600">{loadError} 이력을 불러오지 못했습니다. 새로고침해 주세요. 나머지 이력은 표시됩니다.</p>}
          {filteredItems.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center p-8">
              <div className="w-12 h-12 rounded-2xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-400 mb-3">
                <Clock className="w-6 h-6" />
              </div>
              <p className="font-semibold text-sm text-slate-600 dark:text-slate-300">
                {isLoading ? '작업 이력을 불러오는 중입니다' : '표시할 작업 이력이 없습니다'}
              </p>
              <p className="text-xs text-slate-400 dark:text-slate-500 mt-1 max-w-sm">
                가명데이터, AI 합성데이터, 더미데이터 생성 작업을 실행하시면 이곳에 자동으로 이력이 통합 기록됩니다.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto rounded-xl border dark:border-slate-800 shadow-sm">
              <table className="w-full text-left text-xs">
                <thead className={`border-b ${isDarkMode ? 'bg-slate-950/90 text-slate-300 border-slate-800' : 'bg-slate-50 text-slate-700 border-slate-200'}`}>
                  <tr>
                    <th className="py-3 px-3 font-semibold">작업 구분</th>
                    <th className="py-3 px-3 font-semibold">처리 일시</th>
                    <th className="py-3 px-3 font-semibold">대상명 (원본/테이블)</th>
                    <th className="py-3 px-3 font-semibold">산출 파일명</th>
                    <th className="py-3 px-3 font-semibold">처리 사양 및 요약</th>
                    <th className="py-3 px-3 font-semibold">건수</th>
                    <th className="py-3 px-3 font-semibold">심의/결과</th>
                    <th className="py-3 px-3 font-semibold text-right">작업 액션</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                  {filteredItems.map(item => {
                    const isPseudo = item.type === 'pseudo';
                    const isSynth = item.type === 'synthetic';
                    const isDummy = item.type === 'dummy';
                    const isConverter = item.type === 'converter';

                    const typeBadgeClass = isPseudo
                      ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800/60'
                      : isSynth
                      ? 'bg-sky-50 text-sky-700 dark:bg-sky-950/60 dark:text-sky-300 border-sky-200 dark:border-sky-800/60'
                      : isConverter
                      ? 'bg-indigo-50 text-indigo-700 dark:bg-indigo-950/60 dark:text-indigo-300 border-indigo-200 dark:border-indigo-800/60'
                      : 'bg-amber-50 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300 border-amber-200 dark:border-amber-800/60';

                    const TypeIcon = isPseudo ? ShieldCheck : isSynth ? Cpu : isConverter ? ArrowLeftRight : Database;

                    return (
                      <tr 
                        key={item.id} 
                        className={`transition-colors ${isDarkMode ? 'hover:bg-slate-800/40' : 'hover:bg-slate-50/80'}`}
                      >
                        {/* Track Badge */}
                        <td className="py-3 px-3 whitespace-nowrap">
                          <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-2xs font-bold border ${typeBadgeClass}`}>
                            <TypeIcon className="w-3 h-3" />
                            <span>{item.typeName}</span>
                          </span>
                        </td>

                        {/* Date */}
                        <td className="py-3 px-3 font-mono text-slate-500 dark:text-slate-400 whitespace-nowrap">
                          {item.createdAt}
                        </td>

                        {/* Target Name */}
                        <td className="py-3 px-3 font-semibold text-slate-900 dark:text-white max-w-[150px] truncate" title={item.targetName}>
                          {item.targetName}
                        </td>

                        {/* Output File */}
                        <td className="py-3 px-3 font-mono text-slate-600 dark:text-slate-300 max-w-[170px] truncate" title={item.subName}>
                          {item.subName || '-'}
                        </td>

                        {/* Spec Summary */}
                        <td className="py-3 px-3 text-slate-600 dark:text-slate-300 max-w-[200px] truncate" title={item.specSummary}>
                          {item.specSummary}
                        </td>

                        {/* Rows Count */}
                        <td className="py-3 px-3 font-mono font-medium text-slate-800 dark:text-slate-200 whitespace-nowrap">
                          {item.rowsCount ? `${Number(item.rowsCount).toLocaleString()}건` : '-'}
                        </td>

                        {/* Result / Grade */}
                        <td className="py-3 px-3 whitespace-nowrap">
                          {item.resultBadge && (
                            <span className={`px-2 py-0.5 rounded-full text-2xs font-bold border ${
                              item.resultBadge.variant === 'emerald'
                                ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800/60'
                                : item.resultBadge.variant === 'sky'
                                ? 'bg-sky-50 text-sky-700 dark:bg-sky-950/60 dark:text-sky-300 border-sky-200 dark:border-sky-800/60'
                                : item.resultBadge.variant === 'amber'
                                ? 'bg-amber-50 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300 border-amber-200 dark:border-amber-800/60'
                                : 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300 border-slate-200 dark:border-slate-700'
                            }`}>
                              {item.resultBadge.text}
                            </span>
                          )}
                        </td>

                        {/* Actions */}
                        <td className="py-3 px-3 text-right whitespace-nowrap">
                          <div className="flex items-center justify-end gap-1.5">
                            {item.batchId && onSelectBatch && <button onClick={() => onSelectBatch(item.batchId!)} className="px-2.5 py-1 rounded-lg bg-sky-600 text-white">일괄 작업 열기</button>}
                            {isSynth && item.rawJob && onSelectJob && item.rawJob.status === 'completed' && (
                              <button
                                onClick={() => onSelectJob(item.rawJob!)}
                                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold bg-sky-600 hover:bg-sky-500 text-white transition-colors shadow-sm"
                                title="이 합성 결과 리포트 및 분포 오버레이 차트 즉시 열람"
                              >
                                <span>리포트</span>
                                <ChevronRight className="w-3.5 h-3.5" />
                              </button>
                            )}

                            {item.downloadUrl && (
                              <a
                                href={getDownloadUrl(item.downloadUrl)}
                                download={item.downloadFilename || 'download'}
                                className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold text-white transition-colors shadow-sm ${
                                  isPseudo ? 'bg-emerald-600 hover:bg-emerald-500' :
                                  isSynth ? 'bg-indigo-600 hover:bg-indigo-500' :
                                  isConverter ? 'bg-indigo-600 hover:bg-indigo-500' :
                                  'bg-amber-600 hover:bg-amber-500'
                                }`}
                                title={isSynth ? "HWPX 및 심의패키지 다운로드" : isConverter ? "변환 완료 파일 다운로드" : "산출 데이터 파일 다운로드"}
                              >
                                <Download className="w-3.5 h-3.5" />
                                <span>{isSynth ? 'HWPX' : isConverter ? '변환파일' : '다운로드'}</span>
                              </a>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className={`px-6 py-3 border-t flex items-center justify-between text-xs transition-colors ${
          isDarkMode ? 'border-slate-800 bg-slate-900/80 text-slate-400' : 'border-slate-200 bg-slate-50 text-slate-500'
        }`}>
          <div className="flex items-center gap-2">
            <span>일괄 처리 묶음과 파일별 합성 이력이 함께 표시됩니다.</span>
          </div>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-xl font-semibold bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-slate-300 dark:hover:bg-slate-700 transition-colors"
          >
            닫기
          </button>
        </div>
      </div>
    </div>
  );
};
