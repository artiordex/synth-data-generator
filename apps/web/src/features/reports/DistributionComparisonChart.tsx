import React, { useState, useEffect } from 'react';
import { 
  BarChart3, Layers, Sliders, CheckCircle2, AlertCircle, 
  HelpCircle, Search, ArrowUpRight, ArrowDownRight, RefreshCw
} from 'lucide-react';
import { ColumnDistribution, DistributionBin, NumericStats, CategoricalStats } from '../../types';
import { getJobDistributions } from '../../services/api';

interface Props {
  jobId: string;
  isDarkMode: boolean;
}

export const DistributionComparisonChart: React.FC<Props> = ({ jobId, isDarkMode }) => {
  const [distributions, setDistributions] = useState<ColumnDistribution[]>([]);
  const [selectedColName, setSelectedColName] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  
  // UI View states
  const [viewMode, setViewMode] = useState<'overlay' | 'grouped' | 'diff'>('overlay');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [hoveredBin, setHoveredBin] = useState<DistributionBin | null>(null);

  useEffect(() => {
    let isMounted = true;
    const loadDistributions = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await getJobDistributions(jobId);
        if (isMounted) {
          setDistributions(res.columns || []);
          if (res.columns && res.columns.length > 0) {
            setSelectedColName(res.columns[0].name);
          }
        }
      } catch (err: any) {
        if (isMounted) {
          setError(err.message || '분포 비교 데이터 로드 실패');
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    if (jobId) {
      loadDistributions();
    }
    return () => { isMounted = false; };
  }, [jobId]);

  const selectedCol = distributions.find(c => c.name === selectedColName) || distributions[0] || null;

  const filteredColumns = distributions.filter(c => 
    c.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (loading) {
    return (
      <div className={`p-8 rounded-2xl border flex flex-col items-center justify-center space-y-3 ${
        isDarkMode ? 'bg-slate-900 border-slate-800 text-slate-300' : 'bg-white border-slate-200 text-slate-600'
      }`}>
        <RefreshCw className="w-6 h-6 animate-spin text-sky-500" />
        <div className="text-xs font-semibold">원본 vs 합성 데이터 분포 및 통계 비교 계산 중...</div>
      </div>
    );
  }

  if (error || !selectedCol) {
    return null; // Gracefully degrade if no distribution data exists
  }

  // Chart layout calculations
  const bins = selectedCol.bins || [];
  const maxPct = Math.max(
    ...bins.map(b => Math.max(b.original_pct || 0, b.synthetic_pct || 0)),
    10
  );
  const chartHeight = 220;
  const chartWidth = 720;
  const paddingLeft = 50;
  const paddingRight = 20;
  const paddingTop = 20;
  const paddingBottom = 45;
  const plotWidth = chartWidth - paddingLeft - paddingRight;
  const plotHeight = chartHeight - paddingTop - paddingBottom;

  const yMax = Math.ceil(maxPct * 1.15);
  const getY = (pct: number) => paddingTop + plotHeight - (pct / (yMax || 1)) * plotHeight;
  const barSlotWidth = plotWidth / Math.max(bins.length, 1);

  return (
    <div className={`p-6 rounded-2xl border space-y-6 shadow-sm transition-all ${
      isDarkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'
    }`}>
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b pb-4 dark:border-slate-800">
        <div>
          <h3 className={`font-bold text-sm flex items-center gap-2 ${isDarkMode ? 'text-white' : 'text-slate-900'}`}>
            <BarChart3 className="w-4 h-4 text-sky-500" />
            원본 vs 합성 데이터 분포 비교 인터랙티브 오버레이 차트
          </h3>
          <p className={`text-xs mt-0.5 ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>
            컬럼별 실제 원본 데이터(Blue)와 AI 합성 데이터(Amber)의 확률 분포 보존율을 시각적으로 교차 검증합니다.
          </p>
        </div>

        {/* View Mode Toggle */}
        <div className="flex items-center gap-2">
          <div className={`flex items-center p-1 rounded-xl border text-xs font-semibold ${
            isDarkMode ? 'bg-slate-950 border-slate-800' : 'bg-slate-100 border-slate-200'
          }`}>
            <button
              onClick={() => setViewMode('overlay')}
              className={`px-3 py-1 rounded-lg transition-all ${
                viewMode === 'overlay'
                  ? isDarkMode ? 'bg-sky-600 text-white' : 'bg-white text-sky-700 shadow-sm'
                  : isDarkMode ? 'text-slate-400 hover:text-slate-200' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              오버레이 겹침
            </button>
            <button
              onClick={() => setViewMode('grouped')}
              className={`px-3 py-1 rounded-lg transition-all ${
                viewMode === 'grouped'
                  ? isDarkMode ? 'bg-sky-600 text-white' : 'bg-white text-sky-700 shadow-sm'
                  : isDarkMode ? 'text-slate-400 hover:text-slate-200' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              나란히 비교
            </button>
            <button
              onClick={() => setViewMode('diff')}
              className={`px-3 py-1 rounded-lg transition-all ${
                viewMode === 'diff'
                  ? isDarkMode ? 'bg-sky-600 text-white' : 'bg-white text-sky-700 shadow-sm'
                  : isDarkMode ? 'text-slate-400 hover:text-slate-200' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              오차(Diff %)
            </button>
          </div>
        </div>
      </div>

      {/* Column Selector Pills */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className={`text-xs font-bold ${isDarkMode ? 'text-slate-300' : 'text-slate-700'}`}>
            비교 대상 컬럼 선택 ({distributions.length}개 변수):
          </span>
          {distributions.length > 5 && (
            <div className="relative w-48">
              <Search className="w-3.5 h-3.5 absolute left-2.5 top-2 text-slate-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                placeholder="컬럼명 검색..."
                className={`w-full pl-8 pr-3 py-1 rounded-lg text-xs border outline-none ${
                  isDarkMode 
                    ? 'bg-slate-950 border-slate-800 text-white placeholder-slate-600 focus:border-sky-500' 
                    : 'bg-slate-50 border-slate-200 text-slate-800 placeholder-slate-400 focus:border-sky-500'
                }`}
              />
            </div>
          )}
        </div>

        <div className="flex flex-wrap gap-2 max-h-32 overflow-y-auto pr-1">
          {filteredColumns.map(col => {
            const isSelected = col.name === selectedCol.name;
            const isHighSim = col.similarity_pct >= 90;
            return (
              <button
                key={col.name}
                onClick={() => {
                  setSelectedColName(col.name);
                  setHoveredBin(null);
                }}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all ${
                  isSelected
                    ? isDarkMode
                      ? 'bg-sky-950/80 border-sky-500 text-sky-300 shadow-sm ring-1 ring-sky-500/50'
                      : 'bg-sky-50 border-sky-500 text-sky-950 shadow-sm ring-1 ring-sky-400'
                    : isDarkMode
                    ? 'bg-slate-950/60 border-slate-800 text-slate-300 hover:border-slate-700'
                    : 'bg-slate-50 border-slate-200 text-slate-700 hover:bg-slate-100'
                }`}
              >
                <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                  col.type === 'numerical'
                    ? isDarkMode ? 'bg-sky-500/20 text-sky-400' : 'bg-sky-100 text-sky-700'
                    : isDarkMode ? 'bg-purple-500/20 text-purple-400' : 'bg-purple-100 text-purple-700'
                }`}>
                  {col.type === 'numerical' ? 'NUM' : 'CAT'}
                </span>
                <span>{col.name}</span>
                <span className={`text-[10px] px-1 rounded font-bold ${
                  isHighSim 
                    ? isDarkMode ? 'text-emerald-400 bg-emerald-500/10' : 'text-emerald-700 bg-emerald-50'
                    : isDarkMode ? 'text-amber-400 bg-amber-500/10' : 'text-amber-700 bg-amber-50'
                }`}>
                  {col.similarity_pct}%
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Active Column Meta Banner */}
      <div className={`p-4 rounded-xl border flex flex-col md:flex-row md:items-center justify-between gap-4 ${
        isDarkMode ? 'bg-slate-950 border-slate-800' : 'bg-slate-50 border-slate-200'
      }`}>
        <div className="flex items-center gap-3">
          <div className={`w-9 h-9 rounded-xl flex items-center justify-center font-bold text-xs ${
            selectedCol.type === 'numerical'
              ? 'bg-sky-500/10 text-sky-500 border border-sky-500/20'
              : 'bg-purple-500/10 text-purple-500 border border-purple-500/20'
          }`}>
            {selectedCol.type === 'numerical' ? '123' : 'ABC'}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className={`font-bold text-sm ${isDarkMode ? 'text-white' : 'text-slate-900'}`}>
                {selectedCol.name}
              </span>
              <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${
                isDarkMode ? 'bg-slate-800 text-slate-300' : 'bg-slate-200 text-slate-700'
              }`}>
                {selectedCol.type === 'numerical' ? '연속/수치형 변수' : '범주/코드형 변수'}
              </span>
            </div>
            <div className={`text-xs mt-0.5 ${isDarkMode ? 'text-slate-400' : 'text-slate-500'}`}>
              JSD 거리: <span className="font-mono font-bold">{selectedCol.jsd.toFixed(4)}</span> | 
              분포 유사도: <span className="font-bold text-emerald-600 dark:text-emerald-400">{selectedCol.similarity_pct}% 보존됨</span>
            </div>
          </div>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-4 text-xs font-semibold">
          <div className="flex items-center gap-1.5">
            <span className="w-3.5 h-3.5 rounded bg-sky-500 inline-block shadow-sm"></span>
            <span className={isDarkMode ? 'text-slate-300' : 'text-slate-700'}>원본 데이터 (Original)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3.5 h-3.5 rounded bg-amber-500 inline-block shadow-sm"></span>
            <span className={isDarkMode ? 'text-slate-300' : 'text-slate-700'}>합성 데이터 (Synthetic)</span>
          </div>
          {viewMode === 'overlay' && (
            <div className="flex items-center gap-1.5">
              <span className="w-3.5 h-3.5 rounded bg-emerald-600 inline-block opacity-80 shadow-sm"></span>
              <span className={isDarkMode ? 'text-slate-400' : 'text-slate-500'}>분포 일치 겹침부</span>
            </div>
          )}
        </div>
      </div>

      {/* SVG Canvas Area */}
      <div className="relative overflow-x-auto">
        <svg 
          viewBox={`0 0 ${chartWidth} ${chartHeight}`} 
          className="w-full h-auto max-h-72 select-none"
        >
          {/* Y-Axis Gridlines */}
          {[0, 0.25, 0.5, 0.75, 1.0].map((ratio, i) => {
            const val = (yMax * ratio);
            const y = getY(val);
            return (
              <g key={i}>
                <line 
                  x1={paddingLeft} 
                  y1={y} 
                  x2={chartWidth - paddingRight} 
                  y2={y} 
                  stroke={isDarkMode ? '#334155' : '#e2e8f0'} 
                  strokeDasharray="3 3"
                  strokeWidth="1"
                />
                <text 
                  x={paddingLeft - 8} 
                  y={y + 3} 
                  fill={isDarkMode ? '#94a3b8' : '#64748b'} 
                  fontSize="10" 
                  textAnchor="end"
                  fontFamily="monospace"
                >
                  {Math.round(val)}%
                </text>
              </g>
            );
          })}

          {/* Bars / Overlay Columns */}
          {bins.map((bin, i) => {
            const xSlot = paddingLeft + i * barSlotWidth;
            const isHovered = hoveredBin?.label === bin.label;

            if (viewMode === 'diff') {
              // Difference mode: center at 0%
              const diff = bin.diff_pct || 0;
              const zeroY = getY(0);
              const diffY = getY(Math.abs(diff));
              const barH = Math.abs(diffY - zeroY);
              const barY = diff >= 0 ? zeroY - barH : zeroY;
              const barColor = diff >= 0 ? '#10b981' : '#ef4444';
              const bWidth = Math.max(barSlotWidth * 0.6, 6);

              return (
                <g 
                  key={i} 
                  className="cursor-pointer transition-all"
                  onMouseEnter={() => setHoveredBin(bin)}
                  onMouseLeave={() => setHoveredBin(null)}
                >
                  <rect
                    x={xSlot + (barSlotWidth - bWidth) / 2}
                    y={barY}
                    width={bWidth}
                    height={barH}
                    fill={barColor}
                    rx="3"
                    opacity={isHovered ? 1.0 : 0.8}
                  />
                  {/* Label */}
                  <text
                    x={xSlot + barSlotWidth / 2}
                    y={chartHeight - 15}
                    fill={isDarkMode ? '#94a3b8' : '#64748b'}
                    fontSize="9"
                    textAnchor="middle"
                    fontWeight={isHovered ? 'bold' : 'normal'}
                  >
                    {bin.label.length > 8 ? `${bin.label.slice(0, 7)}…` : bin.label}
                  </text>
                </g>
              );
            }

            if (viewMode === 'grouped') {
              // Grouped mode: two separate side-by-side bars
              const singleW = Math.max(barSlotWidth * 0.38, 4);
              const origY = getY(bin.original_pct);
              const origH = Math.max(plotHeight - (origY - paddingTop), 2);

              const synthY = getY(bin.synthetic_pct);
              const synthH = Math.max(plotHeight - (synthY - paddingTop), 2);

              const xOrig = xSlot + (barSlotWidth - singleW * 2 - 2) / 2;
              const xSynth = xOrig + singleW + 2;

              return (
                <g 
                  key={i} 
                  className="cursor-pointer transition-all"
                  onMouseEnter={() => setHoveredBin(bin)}
                  onMouseLeave={() => setHoveredBin(null)}
                >
                  {/* Original Bar */}
                  <rect
                    x={xOrig}
                    y={origY}
                    width={singleW}
                    height={origH}
                    fill="#0284c7"
                    rx="2"
                    opacity={isHovered ? 1.0 : 0.85}
                  />
                  {/* Synthetic Bar */}
                  <rect
                    x={xSynth}
                    y={synthY}
                    width={singleW}
                    height={synthH}
                    fill="#f59e0b"
                    rx="2"
                    opacity={isHovered ? 1.0 : 0.85}
                  />
                  {/* Label */}
                  <text
                    x={xSlot + barSlotWidth / 2}
                    y={chartHeight - 15}
                    fill={isHovered ? (isDarkMode ? '#38bdf8' : '#0284c7') : (isDarkMode ? '#94a3b8' : '#64748b')}
                    fontSize="9"
                    textAnchor="middle"
                    fontWeight={isHovered ? 'bold' : 'normal'}
                  >
                    {bin.label.length > 8 ? `${bin.label.slice(0, 7)}…` : bin.label}
                  </text>
                </g>
              );
            }

            // Default: Overlay Mode (Semi-transparent overlap)
            const bWidth = Math.max(barSlotWidth * 0.72, 6);
            const xBar = xSlot + (barSlotWidth - bWidth) / 2;

            const origY = getY(bin.original_pct);
            const origH = Math.max(plotHeight - (origY - paddingTop), 2);

            const synthY = getY(bin.synthetic_pct);
            const synthH = Math.max(plotHeight - (synthY - paddingTop), 2);

            return (
              <g 
                key={i} 
                className="cursor-pointer transition-all"
                onMouseEnter={() => setHoveredBin(bin)}
                onMouseLeave={() => setHoveredBin(null)}
              >
                {/* Hover Background Track */}
                <rect
                  x={xSlot}
                  y={paddingTop}
                  width={barSlotWidth}
                  height={plotHeight}
                  fill={isHovered ? (isDarkMode ? 'rgba(56, 189, 248, 0.08)' : 'rgba(2, 132, 199, 0.06)') : 'transparent'}
                  rx="4"
                />

                {/* Original (Blue) */}
                <rect
                  x={xBar}
                  y={origY}
                  width={bWidth}
                  height={origH}
                  fill="#0284c7"
                  opacity={isHovered ? 0.85 : 0.60}
                  rx="3"
                />

                {/* Synthetic (Amber) Overlaid */}
                <rect
                  x={xBar}
                  y={synthY}
                  width={bWidth}
                  height={synthH}
                  fill="#f59e0b"
                  opacity={isHovered ? 0.85 : 0.65}
                  rx="3"
                />

                {/* Label */}
                <text
                  x={xSlot + barSlotWidth / 2}
                  y={chartHeight - 15}
                  fill={isHovered ? (isDarkMode ? '#38bdf8' : '#0284c7') : (isDarkMode ? '#94a3b8' : '#64748b')}
                  fontSize="9"
                  textAnchor="middle"
                  fontWeight={isHovered ? 'bold' : 'normal'}
                >
                  {bin.label.length > 8 ? `${bin.label.slice(0, 7)}…` : bin.label}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* Floating or Static Hover Insight Box */}
      <div className={`p-4 rounded-xl border flex flex-col md:flex-row items-center justify-between gap-4 transition-all ${
        hoveredBin
          ? isDarkMode ? 'bg-sky-950/40 border-sky-500/50' : 'bg-sky-50/80 border-sky-300'
          : isDarkMode ? 'bg-slate-950/40 border-slate-800' : 'bg-slate-50 border-slate-200'
      }`}>
        {hoveredBin ? (
          <>
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-sky-500/10 text-sky-500 flex items-center justify-center font-bold text-xs">
                
              </div>
              <div>
                <div className={`text-xs font-bold ${isDarkMode ? 'text-white' : 'text-slate-900'}`}>
                  구간 / 항목: [{hoveredBin.label}]
                </div>
                <div className="text-[11px] text-slate-400">
                  마우스 호버된 구간의 원본 vs 합성 도수 및 비율 상세
                </div>
              </div>
            </div>

            <div className="flex items-center gap-6 text-xs">
              <div>
                <span className="text-slate-400">원본 (Original): </span>
                <span className="font-bold text-sky-600 dark:text-sky-400">
                  {hoveredBin.original_pct}%
                </span>
                <span className="text-[10px] text-slate-400 ml-1">({hoveredBin.original_count.toLocaleString()}건)</span>
              </div>

              <div>
                <span className="text-slate-400">합성 (Synthetic): </span>
                <span className="font-bold text-amber-600 dark:text-amber-400">
                  {hoveredBin.synthetic_pct}%
                </span>
                <span className="text-[10px] text-slate-400 ml-1">({hoveredBin.synthetic_count.toLocaleString()}건)</span>
              </div>

              <div className="flex items-center gap-1 font-bold">
                <span className="text-slate-400">오차: </span>
                {hoveredBin.diff_pct >= 0 ? (
                  <span className="text-emerald-500 flex items-center text-[11px]">
                    <ArrowUpRight className="w-3.5 h-3.5" />
                    +{hoveredBin.diff_pct}%
                  </span>
                ) : (
                  <span className="text-rose-500 flex items-center text-[11px]">
                    <ArrowDownRight className="w-3.5 h-3.5" />
                    {hoveredBin.diff_pct}%
                  </span>
                )}
              </div>
            </div>
          </>
        ) : (
          <div className="flex items-center gap-2 text-xs text-slate-400 mx-auto py-1">
            <HelpCircle className="w-4 h-4 text-sky-500" />
            <span>차트의 막대 구간에 마우스를 올리면 원본과 합성데이터의 세부 도수 및 오차율(Diff %)을 실시간으로 확인할 수 있습니다.</span>
          </div>
        )}
      </div>

      {/* Side-by-Side Statistics Comparison Grid */}
      <div className="pt-1">
        <h4 className={`text-xs font-bold mb-3 ${isDarkMode ? 'text-slate-300' : 'text-slate-700'}`}>
          주요 기초 통계량 보존율 (Summary Statistics)
        </h4>

        {selectedCol.type === 'numerical' ? (
          <div className="grid grid-cols-2 md:grid-cols-6 gap-3 text-xs">
            {/* Metric Cards */}
            {[
              { 
                label: '평균값 (Mean)', 
                orig: (selectedCol.stats.original as NumericStats).mean, 
                synth: (selectedCol.stats.synthetic as NumericStats).mean 
              },
              { 
                label: '표준편차 (Std Dev)', 
                orig: (selectedCol.stats.original as NumericStats).std, 
                synth: (selectedCol.stats.synthetic as NumericStats).std 
              },
              { 
                label: '중앙값 (Median)', 
                orig: (selectedCol.stats.original as NumericStats).median, 
                synth: (selectedCol.stats.synthetic as NumericStats).median 
              },
              { 
                label: '최솟값 (Min)', 
                orig: (selectedCol.stats.original as NumericStats).min, 
                synth: (selectedCol.stats.synthetic as NumericStats).min 
              },
              { 
                label: '최댓값 (Max)', 
                orig: (selectedCol.stats.original as NumericStats).max, 
                synth: (selectedCol.stats.synthetic as NumericStats).max 
              },
              { 
                label: '총 레코드 수', 
                orig: (selectedCol.stats.original as NumericStats).count.toLocaleString(), 
                synth: (selectedCol.stats.synthetic as NumericStats).count.toLocaleString() 
              },
            ].map((m, idx) => (
              <div 
                key={idx} 
                className={`p-3 rounded-xl border ${
                  isDarkMode ? 'bg-slate-950 border-slate-800' : 'bg-slate-50 border-slate-200'
                }`}
              >
                <div className="text-[10px] text-slate-400 font-semibold">{m.label}</div>
                <div className="mt-1.5 flex items-baseline justify-between">
                  <div className="text-sky-600 dark:text-sky-400 font-mono font-bold">
                    {m.orig ?? '값 없음'}
                  </div>
                  <span className="text-[10px] text-slate-400">vs</span>
                  <div className="text-amber-600 dark:text-amber-400 font-mono font-bold">
                    {m.synth ?? '값 없음'}
                  </div>
                </div>
                <div className="flex justify-between text-[9px] text-slate-500 mt-1">
                  <span>원본</span>
                  <span>합성</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
            {[
              { 
                label: '고유 카테고리 수', 
                orig: (selectedCol.stats.original as CategoricalStats).unique, 
                synth: (selectedCol.stats.synthetic as CategoricalStats).unique 
              },
              { 
                label: '최빈값 (Top Mode)', 
                orig: (selectedCol.stats.original as CategoricalStats).top || '-', 
                synth: (selectedCol.stats.synthetic as CategoricalStats).top || '-' 
              },
              { 
                label: '최빈값 점유율 (%)', 
                orig: `${(selectedCol.stats.original as CategoricalStats).top_pct}%`, 
                synth: `${(selectedCol.stats.synthetic as CategoricalStats).top_pct}%` 
              },
              { 
                label: '총 레코드 수', 
                orig: (selectedCol.stats.original as CategoricalStats).count.toLocaleString(), 
                synth: (selectedCol.stats.synthetic as CategoricalStats).count.toLocaleString() 
              },
            ].map((m, idx) => (
              <div 
                key={idx} 
                className={`p-3 rounded-xl border ${
                  isDarkMode ? 'bg-slate-950 border-slate-800' : 'bg-slate-50 border-slate-200'
                }`}
              >
                <div className="text-[10px] text-slate-400 font-semibold">{m.label}</div>
                <div className="mt-1.5 flex items-baseline justify-between">
                  <div className="text-sky-600 dark:text-sky-400 font-mono font-bold truncate max-w-[45%]">
                    {m.orig}
                  </div>
                  <span className="text-[10px] text-slate-400">vs</span>
                  <div className="text-amber-600 dark:text-amber-400 font-mono font-bold truncate max-w-[45%]">
                    {m.synth}
                  </div>
                </div>
                <div className="flex justify-between text-[9px] text-slate-500 mt-1">
                  <span>원본</span>
                  <span>합성</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
