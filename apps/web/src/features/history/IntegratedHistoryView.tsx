/**
 * 파일명: IntegratedHistoryView.tsx
 * 경로: apps/web/src/features/history/IntegratedHistoryView.tsx
 * 목적: 통합 작업 이력 화면을 표시함
 * 작성자: 개발팀
 * 작성일: 2026-09-09
 * 수정일: 2026-09-09
 */
import React, { useState, useEffect, useMemo } from 'react';
import { 
  History, 
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
  X
} from 'lucide-react';
import { JobStatus } from '../../types';
import { clearAllHistory, deleteSelectedHistory, getPseudonymHistory, getDummyHistory, getJobsList, getBatchesList, getConverterHistory, getDownloadUrl } from '../../services/api';
import { WorkspaceHeader } from '../../components/WorkspaceHeader';

export type HistoryType = 'all' | 'pseudo' | 'synthetic' | 'dummy' | 'batch' | 'converter';
const statusLabels: Record<string, string> = { pending: '대기', processing: '처리 중', completed: '완료', completed_with_errors: '일부 실패·취소', failed: '실패', canceled: '취소' };
const actionLabels: Record<string, string> = { mask: '마스킹', hash: '해시', faker: '가명 대체', drop: '삭제' };

interface Props {
  onBack: () => void;
  isDarkMode: boolean;
  onSelectJob?: (job: JobStatus) => void;
  onSelectBatch?: (id: string) => void;
  initialType?: HistoryType;
  onStepChange?: (step: number) => void;
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

export const IntegratedHistoryView: React.FC<Props> = ({
  onBack,
  isDarkMode,
  onSelectJob,
  onSelectBatch,
  initialType = 'all',
  onStepChange
}) => {
  const [items, setItems] = useState<UnifiedHistoryItem[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [selectedType, setSelectedType] = useState<HistoryType>(initialType);
  const [loadError, setLoadError] = useState('');
  const [isClearing, setIsClearing] = useState(false);

  useEffect(() => {
    const hasFilter = Boolean(searchTerm.trim()) || selectedType !== 'all';
    onStepChange?.(isLoading ? 1 : hasFilter ? 2 : 3);
  }, [isLoading, onStepChange, searchTerm, selectedType]);

  const handleDeleteSelected = async () => {
    if (selectedIds.size === 0) {
      alert('삭제할 이력 항목의 체크박스(ㅁ)를 선택해 주세요.\n전체 삭제를 원하시면 "전체 선택" 체크박스를 누르신 후 이력 삭제를 클릭하세요.');
      return;
    }
    const count = selectedIds.size;
    if (!window.confirm(`선택한 ${count}개의 작업 이력을 삭제하시겠습니까?\n생성 결과 파일과 템플릿은 안전하게 보존됩니다.`)) {
      return;
    }
    setIsClearing(true);
    setLoadError('');
    try {
      const targetItems = items
        .filter(i => selectedIds.has(i.id))
        .map(i => ({
          type: i.type,
          id: i.id,
          filename: i.downloadFilename || i.subName || i.targetName
        }));

      await deleteSelectedHistory(targetItems);
      setItems(prev => prev.filter(i => !selectedIds.has(i.id)));
      setSelectedIds(new Set());
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : '선택 이력 삭제 실패');
    } finally {
      setIsClearing(false);
    }
  };

  const toggleSelectItem = (id: string, e?: React.MouseEvent) => {
    e?.stopPropagation();
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
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
      (pseudoList || []).forEach((item: any) => {
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
      (jobsList || []).forEach((j: JobStatus) => {
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
      (dummyList || []).forEach((item: any) => {
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

      // 4. Batch items
      (batchesList || []).forEach((batch: any) => unified.push({
        id: batch.id, batchId: batch.id, type: 'batch', typeName: '일괄 처리',
        targetName: `${batch.total}개 파일 일괄 합성`,
        subName: (batch.jobs || []).map((job: JobStatus) => job.original_filename).join(', '),
        createdAt: batch.created_at || '-', timestamp: Date.parse(batch.created_at) || 0,
        rowsCount: (batch.jobs || []).reduce((sum: number, job: JobStatus) => sum + (job.target_rows ?? 0), 0),
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
    loadAllHistory();
  }, []);

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

  const isAllSelected = filteredItems.length > 0 && filteredItems.every(i => selectedIds.has(i.id));
  const isPartiallySelected = filteredItems.some(i => selectedIds.has(i.id)) && !isAllSelected;

  const toggleSelectAll = () => {
    if (isAllSelected) {
      setSelectedIds(prev => {
        const next = new Set(prev);
        filteredItems.forEach(i => next.delete(i.id));
        return next;
      });
    } else {
      setSelectedIds(prev => {
        const next = new Set(prev);
        filteredItems.forEach(i => next.add(i.id));
        return next;
      });
    }
  };

  return (
    <div className="space-y-4 sm:space-y-6 animate-fade-in">
      {/* Unified Workspace Header with Actions */}
      <WorkspaceHeader
        eyebrow="HISTORY WORKSPACE"
        title="통합 작업 이력 관리대장"
        description="가명처리 · AI 합성 · 더미데이터 · 일괄 처리 · 데이터 변환 전체 감사 로그"
        icon={Clock}
        badge={
          <span className="text-2xs font-semibold px-2 py-0.5 rounded-full border border-subtle bg-surface-muted text-fg-muted font-mono">
            총 {items.length}건
          </span>
        }
        actions={
          <div className="flex items-center gap-2 flex-wrap">
            {/* 작업 선택 셀렉트 박스 */}
            <div className="flex items-center gap-1.5 bg-surface-muted border border-subtle rounded-lg px-2.5 py-1.5">
              <Filter className="w-3.5 h-3.5 text-accent shrink-0" />
              <select
                value={selectedType}
                onChange={(e) => setSelectedType(e.target.value as HistoryType)}
                aria-label="작업 유형 선택"
                className="bg-transparent text-xs font-bold text-fg focus:outline-none cursor-pointer border-none pr-1"
              >
                <option value="all">전체 작업 ({counts.all})</option>
                <option value="pseudo">가명데이터 ({counts.pseudo})</option>
                <option value="synthetic">AI 합성 ({counts.synthetic})</option>
                <option value="batch">배치 일괄 ({counts.batch})</option>
                <option value="dummy">더미데이터 ({counts.dummy})</option>
                <option value="converter">데이터 변환 ({counts.converter})</option>
              </select>
            </div>

            <button
              onClick={handleDeleteSelected}
              disabled={isClearing || items.length === 0}
              className={`px-2.5 py-1.5 text-xs cursor-pointer flex items-center gap-1.5 rounded-lg border transition-all ${
                selectedIds.size > 0
                  ? 'bg-rose-600 text-white border-rose-700 hover:bg-rose-700 font-bold shadow-xs'
                  : 'ui-button-danger'
              }`}
              title={selectedIds.size > 0 ? `선택한 ${selectedIds.size}개 이력 삭제` : '체크박스로 선택한 이력을 삭제합니다'}
            >
              <Trash2 className="h-3.5 w-3.5" />
              <span>{selectedIds.size > 0 ? `이력 삭제 (${selectedIds.size})` : '이력 삭제'}</span>
            </button>

            <button
              onClick={handleExportAuditCSV}
              disabled={items.length === 0}
              className="ui-button-secondary px-2.5 py-1.5 text-xs cursor-pointer flex items-center gap-1.5"
              title="관리대장 CSV 파일 다운로드"
            >
              <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-500" />
              <span className="hidden sm:inline">CSV 내보내기</span>
            </button>

            <button
              onClick={loadAllHistory}
              disabled={isLoading}
              className="ui-button-secondary px-2.5 py-1.5 text-xs cursor-pointer flex items-center gap-1.5"
              title="이력 새로고침"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
              <span className="hidden sm:inline">새로고침</span>
            </button>
          </div>
        }
      />

      {/* Toolbar: Track Filters & Search & Selection */}
      <div className="flex flex-col gap-3 rounded-2xl border border-subtle bg-surface p-3.5 sm:p-5 shadow-xs">
        {/* Track Filter Pills (Horizontally Scrollable on Mobile) */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-none text-xs">
          <button
            onClick={() => setSelectedType('all')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium whitespace-nowrap transition-all border shrink-0 cursor-pointer ${
              selectedType === 'all'
                ? 'bg-accent text-accent-fg border-accent shadow-xs font-semibold'
                : 'bg-surface-muted text-fg-muted border-subtle hover:bg-surface hover:text-fg'
            }`}
          >
            <Filter className="w-3.5 h-3.5" />
            <span>전체 이력</span>
            <span className="text-2xs px-1.5 py-0.2 rounded-full font-bold bg-accent-fg/20 text-accent-fg">
              {counts.all}
            </span>
          </button>

          <button
            onClick={() => setSelectedType('pseudo')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium whitespace-nowrap transition-all border shrink-0 cursor-pointer ${
              selectedType === 'pseudo'
                ? 'bg-accent text-accent-fg border-accent shadow-xs font-semibold'
                : 'bg-surface-muted text-fg-muted border-subtle hover:bg-surface hover:text-fg'
            }`}
          >
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>가명데이터</span>
            <span className="text-2xs px-1.5 py-0.2 rounded-full font-bold bg-surface text-fg-muted">
              {counts.pseudo}
            </span>
          </button>

          <button
            onClick={() => setSelectedType('synthetic')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium whitespace-nowrap transition-all border shrink-0 cursor-pointer ${
              selectedType === 'synthetic'
                ? 'bg-accent text-accent-fg border-accent shadow-xs font-semibold'
                : 'bg-surface-muted text-fg-muted border-subtle hover:bg-surface hover:text-fg'
            }`}
          >
            <Cpu className="w-3.5 h-3.5" />
            <span>AI 합성데이터</span>
            <span className="text-2xs px-1.5 py-0.2 rounded-full font-bold bg-surface text-fg-muted">
              {counts.synthetic}
            </span>
          </button>

          <button
            onClick={() => setSelectedType('dummy')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium whitespace-nowrap transition-all border shrink-0 cursor-pointer ${
              selectedType === 'dummy'
                ? 'bg-accent text-accent-fg border-accent shadow-xs font-semibold'
                : 'bg-surface-muted text-fg-muted border-subtle hover:bg-surface hover:text-fg'
            }`}
          >
            <Database className="w-3.5 h-3.5" />
            <span>더미데이터</span>
            <span className="text-2xs px-1.5 py-0.2 rounded-full font-bold bg-surface text-fg-muted">
              {counts.dummy}
            </span>
          </button>

          <button
            onClick={() => setSelectedType('converter')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium whitespace-nowrap transition-all border shrink-0 cursor-pointer ${
              selectedType === 'converter'
                ? 'bg-accent text-accent-fg border-accent shadow-xs font-semibold'
                : 'bg-surface-muted text-fg-muted border-subtle hover:bg-surface hover:text-fg'
            }`}
          >
            <ArrowLeftRight className="w-3.5 h-3.5" />
            <span>데이터 변환</span>
            <span className="text-2xs px-1.5 py-0.2 rounded-full font-bold bg-surface text-fg-muted">
              {counts.converter}
            </span>
          </button>

          <button
            onClick={() => setSelectedType('batch')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium whitespace-nowrap transition-all border shrink-0 cursor-pointer ${
              selectedType === 'batch'
                ? 'bg-accent text-accent-fg border-accent shadow-xs font-semibold'
                : 'bg-surface-muted text-fg-muted border-subtle hover:bg-surface hover:text-fg'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            <span>일괄 처리</span>
            <span className="text-2xs px-1.5 py-0.2 rounded-full font-bold bg-surface text-fg-muted">
              {counts.batch}
            </span>
          </button>
        </div>

        {/* Search Bar */}
        <div className="relative">
          <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-fg-muted" />
          <input
            type="text"
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
            placeholder="대상 파일명, 테이블명, 산출 파일 검색..."
            className="ui-field w-full py-2 pl-10 pr-9 text-xs sm:text-sm"
          />
          {searchTerm && (
            <button
              onClick={() => setSearchTerm('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-fg-muted hover:text-fg cursor-pointer"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {loadError && (
        <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-xs text-rose-600 dark:text-rose-400">
          {loadError} 이력을 불러오는 중 일부 오류가 발생했습니다. 새로고침 시 다시 시도됩니다.
        </div>
      )}

      {/* Content: Desktop Table & Mobile Card List */}
      {filteredItems.length === 0 ? (
        <div className="rounded-2xl border border-subtle bg-surface p-12 text-center flex flex-col items-center justify-center">
          <div className="w-12 h-12 rounded-2xl bg-surface-muted border border-subtle flex items-center justify-center text-fg-muted mb-3">
            <Clock className="w-6 h-6" />
          </div>
          <p className="font-semibold text-sm text-fg">
            {isLoading ? '작업 이력을 불러오는 중입니다...' : '표시할 작업 이력이 없습니다'}
          </p>
          <p className="text-xs text-fg-muted mt-1 max-w-sm">
            가명데이터, AI 합성데이터, 더미데이터, 데이터 변환 작업을 실행하시면 이곳에 자동으로 이력이 통합 기록됩니다.
          </p>
        </div>
      ) : (
        <>
          {/* Desktop Table View (md:block) */}
          <div className="hidden md:block overflow-hidden rounded-2xl border border-subtle bg-surface shadow-xs">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="border-b border-subtle bg-surface-muted/60 text-fg-muted font-semibold">
                  <tr>
                    <th className="py-3 px-3 w-10 text-center">
                      <input
                        type="checkbox"
                        aria-label="전체 이력 선택"
                        checked={isAllSelected}
                        ref={el => {
                          if (el) el.indeterminate = isPartiallySelected;
                        }}
                        onChange={toggleSelectAll}
                        className="rounded border-subtle text-accent focus:ring-accent cursor-pointer w-4 h-4"
                      />
                    </th>
                    <th className="py-3 px-3.5">작업 구분</th>
                    <th className="py-3 px-3.5">처리 일시</th>
                    <th className="py-3 px-3.5">대상명</th>
                    <th className="py-3 px-3.5">산출 파일명</th>
                    <th className="py-3 px-3.5">처리 사양 요약</th>
                    <th className="py-3 px-3.5">건수</th>
                    <th className="py-3 px-3.5">결과 / 상태</th>
                    <th className="py-3 px-3.5 text-right">작업 액션</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-subtle">
                  {filteredItems.map(item => {
                    const isSelected = selectedIds.has(item.id);
                    const isPseudo = item.type === 'pseudo';
                    const isSynth = item.type === 'synthetic';
                    const isDummy = item.type === 'dummy';
                    const isConverter = item.type === 'converter';

                    const TypeIcon = isPseudo ? ShieldCheck : isSynth ? Cpu : isConverter ? ArrowLeftRight : Database;

                    return (
                      <tr 
                        key={item.id} 
                        onClick={() => toggleSelectItem(item.id)}
                        className={`transition-colors cursor-pointer ${
                          isSelected ? 'bg-accent-subtle/30 font-medium' : 'hover:bg-surface-muted/30'
                        }`}
                      >
                        {/* Checkbox */}
                        <td className="py-3 px-3 text-center" onClick={(e) => e.stopPropagation()}>
                          <input
                            type="checkbox"
                            aria-label={`${item.targetName} 선택`}
                            checked={isSelected}
                            onChange={() => toggleSelectItem(item.id)}
                            className="rounded border-subtle text-accent focus:ring-accent cursor-pointer w-4 h-4"
                          />
                        </td>

                        {/* Track Badge */}
                        <td className="py-3 px-3.5 whitespace-nowrap">
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-bold border border-subtle bg-surface-muted text-fg">
                            <TypeIcon className="w-3.5 h-3.5 text-accent" />
                            <span>{item.typeName}</span>
                          </span>
                        </td>

                        {/* Date */}
                        <td className="py-3 px-3.5 font-mono text-fg-muted whitespace-nowrap text-xs">
                          {item.createdAt}
                        </td>

                        {/* Target Name */}
                        <td className="py-3 px-3.5 font-bold text-fg max-w-[160px] truncate text-xs sm:text-sm" title={item.targetName}>
                          {item.targetName}
                        </td>

                        {/* Output File */}
                        <td className="py-3 px-3.5 font-mono text-fg-muted max-w-[170px] truncate text-xs" title={item.subName}>
                          {item.subName || '-'}
                        </td>

                        {/* Spec Summary */}
                        <td className="py-3 px-3.5 text-fg/80 max-w-[200px] truncate text-xs sm:text-sm" title={item.specSummary}>
                          {item.specSummary}
                        </td>

                        {/* Rows Count */}
                        <td className="py-3 px-3.5 font-mono font-medium text-fg whitespace-nowrap text-xs">
                          {item.rowsCount ? `${Number(item.rowsCount).toLocaleString()}건` : '-'}
                        </td>

                        {/* Result / Grade */}
                        <td className="py-3 px-3.5 whitespace-nowrap">
                          {item.resultBadge && (
                            <span className="px-2 py-0.5 rounded-full text-xs font-bold border border-subtle bg-surface-muted text-fg font-mono">
                              {item.resultBadge.text}
                            </span>
                          )}
                        </td>

                        {/* Actions */}
                        <td className="py-3 px-3.5 text-right whitespace-nowrap" onClick={(e) => e.stopPropagation()}>
                          <div className="flex items-center justify-end gap-1.5">
                            {item.batchId && onSelectBatch && (
                              <button
                                onClick={() => onSelectBatch(item.batchId!)}
                                className="ui-button-secondary px-2 py-1 text-xs font-semibold cursor-pointer"
                              >
                                일괄 작업 열기
                              </button>
                            )}

                            {isSynth && item.rawJob && onSelectJob && item.rawJob.status === 'completed' && (
                              <button
                                onClick={() => onSelectJob(item.rawJob!)}
                                className="ui-button-primary px-2.5 py-1 text-xs font-semibold inline-flex items-center gap-1 cursor-pointer"
                                title="합성 결과 리포트 및 분포 차트 열람"
                              >
                                <span>리포트</span>
                                <ChevronRight className="w-3 h-3" />
                              </button>
                            )}

                            {item.downloadUrl && (
                              <a
                                href={getDownloadUrl(item.downloadUrl)}
                                download={item.downloadFilename || 'download'}
                                className="ui-button-secondary px-2.5 py-1 text-xs font-semibold inline-flex items-center gap-1 cursor-pointer"
                                title="산출 파일 다운로드"
                              >
                                <Download className="w-3 h-3" />
                                <span>{isSynth ? 'HWPX' : isConverter ? '다운로드' : '다운로드'}</span>
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
          </div>

          {/* Mobile Card View (md:hidden) */}
          <div className="md:hidden space-y-3">
            {filteredItems.map(item => {
              const isSelected = selectedIds.has(item.id);
              const isPseudo = item.type === 'pseudo';
              const isSynth = item.type === 'synthetic';
              const isConverter = item.type === 'converter';
              const TypeIcon = isPseudo ? ShieldCheck : isSynth ? Cpu : isConverter ? ArrowLeftRight : Database;

              return (
                <div
                  key={item.id}
                  onClick={() => toggleSelectItem(item.id)}
                  className={`rounded-2xl border bg-surface p-4 shadow-xs space-y-3 transition-all cursor-pointer ${
                    isSelected ? 'border-accent ring-2 ring-accent/30 bg-accent-subtle/10' : 'border-subtle'
                  }`}
                >
                  {/* Top Badges & Date */}
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        aria-label={`${item.targetName} 선택`}
                        checked={isSelected}
                        onChange={() => toggleSelectItem(item.id)}
                        className="rounded border-subtle text-accent focus:ring-accent cursor-pointer w-4 h-4"
                      />
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-2xs font-bold border border-subtle bg-surface-muted text-fg">
                        <TypeIcon className="w-3 h-3 text-accent" />
                        <span>{item.typeName}</span>
                      </span>
                    </div>

                    {item.resultBadge && (
                      <span className="px-2 py-0.5 rounded-full text-2xs font-bold border border-subtle bg-surface-muted text-fg font-mono">
                        {item.resultBadge.text}
                      </span>
                    )}
                  </div>

                  {/* Target & Sub Info */}
                  <div>
                    <h3 className="font-bold text-sm text-fg leading-snug">
                      {item.targetName}
                    </h3>
                    {item.subName && (
                      <p className="text-xs text-fg-muted font-mono mt-0.5">
                        {item.subName}
                      </p>
                    )}
                  </div>

                  {/* Metadata Stats */}
                  <div className="pt-2 border-t border-subtle text-xs text-fg-muted space-y-1">
                    <div className="flex justify-between">
                      <span>처리 사양:</span>
                      <span className="font-medium text-fg">{item.specSummary}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>데이터 건수:</span>
                      <span className="font-mono text-fg font-semibold">
                        {item.rowsCount ? `${Number(item.rowsCount).toLocaleString()}건` : '-'}
                      </span>
                    </div>
                    <div className="flex justify-between text-2xs">
                      <span>처리 일시:</span>
                      <span className="font-mono">{item.createdAt}</span>
                    </div>
                  </div>

                  {/* Action Buttons on Mobile */}
                  <div className="pt-2 border-t border-subtle flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                    {item.batchId && onSelectBatch && (
                      <button
                        onClick={() => onSelectBatch(item.batchId!)}
                        className="ui-button-secondary flex-1 py-2 text-xs font-semibold text-center cursor-pointer"
                      >
                        일괄 작업 열기
                      </button>
                    )}

                    {isSynth && item.rawJob && onSelectJob && item.rawJob.status === 'completed' && (
                      <button
                        onClick={() => onSelectJob(item.rawJob!)}
                        className="ui-button-primary flex-1 py-2 text-xs font-semibold inline-flex items-center justify-center gap-1 cursor-pointer"
                      >
                        <span>리포트 열람</span>
                        <ChevronRight className="w-3.5 h-3.5" />
                      </button>
                    )}

                    {item.downloadUrl && (
                      <a
                        href={getDownloadUrl(item.downloadUrl)}
                        download={item.downloadFilename || 'download'}
                        className="ui-button-secondary flex-1 py-2 text-xs font-semibold inline-flex items-center justify-center gap-1 text-center cursor-pointer"
                      >
                        <Download className="w-3.5 h-3.5" />
                        <span>다운로드</span>
                      </a>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
};
