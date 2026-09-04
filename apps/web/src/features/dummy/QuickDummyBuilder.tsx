import React, { useState, useEffect } from 'react';
import { 
  Sparkles, Zap, Plus, Trash2, Download, Table, Layers, 
  CheckCircle2, FileText, Database, RefreshCw, ChevronRight, Search, X,
  History, Clock
} from 'lucide-react';
import { getDummyDomains, getDummyTemplates, inferDummyColumn, generateDummyData, getDummyHistory, getDownloadUrl } from '../../services/api';

interface ColumnItem {
  id: string;
  name: string;
  domain_id: string;
  domain_name: string;
  category: string;
  source: string;
  sample: string;
}

interface Props {
  isDarkMode: boolean;
  onOpenHistory?: () => void;
}

export const QuickDummyBuilder: React.FC<Props> = ({ isDarkMode, onOpenHistory }) => {
  const [templates, setTemplates] = useState<any[]>([]);
  const [allDomains, setAllDomains] = useState<any[]>([]);
  const [groupedDomains, setGroupedDomains] = useState<Record<string, any[]>>({});
  const [categories, setCategories] = useState<string[]>([]);
  
  const [tableName, setTableName] = useState<string>('user_dummy_table');
  const [columns, setColumns] = useState<ColumnItem[]>([
    { id: '1', name: 'user_id', domain_id: 'user_id', domain_name: '회원/사용자 ID', category: '인적 및 계정 정보', source: '행안부_공통표준', sample: 'USR_10001' },
    { id: '2', name: 'user_name', domain_id: 'korean_name', domain_name: '성명 (한국명)', category: '인적 및 계정 정보', source: '행안부_공통표준', sample: '김민수' },
    { id: '3', name: 'mobile_phone', domain_id: 'phone_mobile', domain_name: '휴대전화번호 (010)', category: '연락처 및 주소', source: '행안부_공통표준', sample: '010-4829-1920' },
    { id: '4', name: 'email', domain_id: 'email', domain_name: '이메일 주소', category: '연락처 및 주소', source: '행안부_공통표준', sample: 'user482@gmail.com' },
    { id: '5', name: 'gender', domain_id: 'gender', domain_name: '성별 (남/여)', category: '인적 및 계정 정보', source: '행안부_공통표준', sample: '남' },
    { id: '6', name: 'age', domain_id: 'age', domain_name: '연령/나이 (만 나이)', category: '인적 및 계정 정보', source: '행안부_공통표준', sample: '34' },
    { id: '7', name: 'address', domain_id: 'road_address', domain_name: '도로명 주소', category: '연락처 및 주소', source: '행안부_공통표준', sample: '서울특별시 강남구 테헤란로 152' },
    { id: '8', name: 'created_at', domain_id: 'created_datetime', domain_name: '등록/생성 일시', category: '날짜 및 시간 공통', source: '행안부_공통표준', sample: '2025-11-14 15:32:09' }
  ]);

  const [targetRows, setTargetRows] = useState<number>(10000);
  const [exportFormat, setExportFormat] = useState<string>('csv');
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [generationResult, setGenerationResult] = useState<any | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Modal for domain picker
  const [isPickerOpen, setIsPickerOpen] = useState<boolean>(false);
  const [pickerTargetColId, setPickerTargetColId] = useState<string | null>(null);
  const [pickerSearch, setPickerSearch] = useState<string>('');
  const [pickerCategory, setPickerCategory] = useState<string>('전체');

  // History state
  const [dummyHistory, setDummyHistory] = useState<any[]>([]);

  const loadHistory = async () => {
    try {
      const hist = await getDummyHistory();
      setDummyHistory(hist);
    } catch (e) {
      console.error('더미 이력 로드 오류:', e);
    }
  };

  useEffect(() => {
    async function initData() {
      try {
        const [domRes, tmplRes, hist] = await Promise.all([getDummyDomains(), getDummyTemplates(), getDummyHistory()]);
        setAllDomains(domRes.domains);
        setGroupedDomains(domRes.grouped_domains);
        setCategories(['전체', ...domRes.categories]);
        setTemplates(tmplRes.templates);
        setDummyHistory(hist);
      } catch (e) {
        console.error('도메인 데이터 로드 오류:', e);
      }
    }
    initData();
  }, []);

  // Apply template
  const handleApplyTemplate = (tmpl: any) => {
    setTableName(tmpl.id);
    const newCols: ColumnItem[] = tmpl.columns.map((c: any, idx: number) => {
      const found = allDomains.find(d => d.id === c.domain_id) || {
        name: c.domain_id,
        category: '일반',
        source: '사용자정의',
        sample: 'SAMPLE'
      };
      return {
        id: String(idx + 1),
        name: c.name,
        domain_id: c.domain_id,
        domain_name: found.name,
        category: found.category,
        source: found.source || '공통표준',
        sample: found.sample || '-'
      };
    });
    setColumns(newCols);
    setGenerationResult(null);
  };

  // Add column
  const handleAddColumn = () => {
    const nextNum = columns.length + 1;
    const defaultDomain = allDomains[0] || { id: 'generic', name: '일반문자', category: '기본', sample: 'Sample' };
    setColumns([
      ...columns,
      {
        id: String(Date.now()),
        name: `col_${nextNum}`,
        domain_id: defaultDomain.id,
        domain_name: defaultDomain.name,
        category: defaultDomain.category,
        source: defaultDomain.source || '공통표준',
        sample: defaultDomain.sample || '-'
      }
    ]);
  };

  // Remove column
  const handleRemoveColumn = (id: string) => {
    if (columns.length <= 1) return;
    setColumns(columns.filter(c => c.id !== id));
  };

  // Update column name and auto-infer
  const handleColumnNameBlur = async (id: string, newName: string) => {
    if (!newName.trim()) return;
    try {
      const res = await inferDummyColumn(newName);
      const inferred = res.inferred_domain;
      setColumns(cols => cols.map(c => {
        if (c.id === id) {
          return {
            ...c,
            name: newName,
            domain_id: inferred.id,
            domain_name: inferred.name,
            category: inferred.category,
            source: inferred.source || '추론매칭',
            sample: inferred.sample || '-'
          };
        }
        return c;
      }));
    } catch (e) {
      console.error(e);
    }
  };

  // Open picker
  const openDomainPicker = (colId: string) => {
    setPickerTargetColId(colId);
    setPickerSearch('');
    setPickerCategory('전체');
    setIsPickerOpen(true);
  };

  // Select domain from picker
  const handleSelectDomain = (domain: any) => {
    if (!pickerTargetColId) return;
    setColumns(cols => cols.map(c => {
      if (c.id === pickerTargetColId) {
        return {
          ...c,
          domain_id: domain.id,
          domain_name: domain.name,
          category: domain.category,
          source: domain.source || '공통표준',
          sample: domain.sample || '-'
        };
      }
      return c;
    }));
    setIsPickerOpen(false);
  };

  // Generate data
  const handleGenerate = async () => {
    if (columns.length === 0) return;
    setIsGenerating(true);
    setErrorMsg(null);
    try {
      const payload = {
        table_name: tableName,
        columns: columns.map(c => ({ name: c.name, domain_id: c.domain_id })),
        target_rows: Number(targetRows),
        export_format: exportFormat
      };
      const res = await generateDummyData(payload);
      setGenerationResult(res);
      loadHistory();
    } catch (err: any) {
      setErrorMsg(err.message || '더미 데이터 생성 실패');
    } finally {
      setIsGenerating(false);
    }
  };

  const filteredPickerDomains = allDomains.filter(d => {
    const matchCat = pickerCategory === '전체' || d.category === pickerCategory;
    const matchSearch = pickerSearch.trim() === '' || 
      d.name.toLowerCase().includes(pickerSearch.toLowerCase()) || 
      d.id.toLowerCase().includes(pickerSearch.toLowerCase()) ||
      (d.aliases && d.aliases.some((a: string) => a.toLowerCase().includes(pickerSearch.toLowerCase())));
    return matchCat && matchSearch;
  });

  return (
    <div className="space-y-6">
      {/* Hero Banner */}
      <div className={`p-6 rounded-2xl border ${
        isDarkMode ? 'bg-gradient-to-r from-slate-900 via-indigo-950/40 to-slate-900 border-indigo-900/50' : 'bg-gradient-to-r from-sky-50 via-indigo-50/50 to-white border-sky-200 shadow-sm'
      }`}>
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 rounded-full bg-sky-500/10 text-sky-600 dark:text-sky-400 text-xs font-bold flex items-center gap-1">
                <Zap className="w-3.5 h-3.5" /> No-File Instant Dummy Generator
              </span>
              <span className="text-xs text-slate-400">행안부 공통표준 · Mockaroo · 마이데이터 100+ 도메인 탑재</span>
            </div>
            <h2 className={`text-xl font-black ${isDarkMode ? 'text-white' : 'text-slate-900'}`}>
              원본 파일 없는 '초고속 퀵 더미 생성기'
            </h2>
            <p className={`text-xs ${isDarkMode ? 'text-slate-400' : 'text-slate-600'}`}>
              사내 개발자/QA 테스트용 대량 데이터(1만~10만 건)를 3초 만에 생성하고 CSV, Excel, SQL INSERT 구문으로 즉시 다운로드하세요.
            </p>
          </div>
          <div className="text-right">
            <div className="text-2xl font-black text-indigo-600 dark:text-indigo-400">{allDomains.length}개+</div>
            <div className="text-[11px] text-slate-400 font-medium">표준 컬럼 도메인 지원</div>
          </div>
        </div>
      </div>

      {/* 1. Template Presets */}
      <div className={`p-5 rounded-2xl border space-y-3 ${
        isDarkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200 shadow-sm'
      }`}>
        <div className="flex items-center justify-between">
          <span className={`text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 ${isDarkMode ? 'text-slate-300' : 'text-slate-700'}`}>
            <Sparkles className="w-4 h-4 text-amber-500" />
            사내 표준 추천 템플릿 (1초 완성)
          </span>
          <span className="text-[11px] text-slate-400">클릭 시 컬럼 스키마가 즉시 세팅됩니다</span>
        </div>
        <div className="grid grid-cols-6 gap-3">
          {templates.map(tmpl => (
            <button
              key={tmpl.id}
              onClick={() => handleApplyTemplate(tmpl)}
              className={`p-3 rounded-xl border text-left transition-all ${
                tableName === tmpl.id
                  ? isDarkMode ? 'bg-indigo-950/60 border-indigo-500 ring-1 ring-indigo-500' : 'bg-indigo-50/80 border-indigo-500 ring-1 ring-indigo-400 text-indigo-900'
                  : isDarkMode ? 'bg-slate-950 border-slate-800 text-slate-300 hover:border-slate-700' : 'bg-slate-50 border-slate-200 text-slate-700 hover:border-slate-300 hover:bg-slate-100/80'
              }`}
            >
              <div className="font-bold text-xs truncate">{tmpl.name}</div>
              <div className="text-[10px] text-slate-400 mt-1 line-clamp-1">{tmpl.columns.length}개 컬럼</div>
            </button>
          ))}
        </div>
      </div>

      {/* 2. Schema Builder Table */}
      <div className={`rounded-2xl border overflow-hidden shadow-sm ${
        isDarkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'
      }`}>
        <div className={`px-6 py-4 border-b flex justify-between items-center ${
          isDarkMode ? 'border-slate-800 bg-slate-950/50' : 'border-slate-200 bg-slate-50/60'
        }`}>
          <div className="flex items-center gap-3">
            <h3 className={`font-bold text-sm flex items-center gap-2 ${isDarkMode ? 'text-white' : 'text-slate-900'}`}>
              <Table className="w-4 h-4 text-sky-500" />
              테이블 스키마 및 도메인 규칙 정의
            </h3>
            <div className="flex items-center gap-2 text-xs">
              <span className="text-slate-400">테이블명:</span>
              <input
                type="text"
                value={tableName}
                onChange={(e) => setTableName(e.target.value)}
                className={`px-2.5 py-1 rounded-lg border text-xs font-mono font-bold focus:outline-none focus:border-sky-500 ${
                  isDarkMode ? 'bg-slate-950 border-slate-700 text-white' : 'bg-white border-slate-300 text-slate-900'
                }`}
              />
            </div>
          </div>
          <button
            onClick={handleAddColumn}
            className="px-3 py-1.5 rounded-xl bg-sky-600 hover:bg-sky-500 text-white text-xs font-bold flex items-center gap-1.5 shadow-sm transition-all"
          >
            <Plus className="w-3.5 h-3.5" /> 컬럼 추가
          </button>
        </div>

        <div className="overflow-x-auto max-h-96">
          <table className="w-full text-left text-xs">
            <thead className={`sticky top-0 font-bold ${
              isDarkMode ? 'bg-slate-950 text-slate-400' : 'bg-slate-100 text-slate-600'
            }`}>
              <tr>
                <th className="px-4 py-3 w-12">#</th>
                <th className="px-4 py-3 w-48">컬럼명 (입력 시 자동추론)</th>
                <th className="px-4 py-3 w-64">매핑된 표준 도메인</th>
                <th className="px-4 py-3 w-32">분류 / 출처</th>
                <th className="px-4 py-3">실제 생성 샘플 미리보기</th>
                <th className="px-4 py-3 w-16 text-center">삭제</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDarkMode ? 'divide-slate-800/60' : 'divide-slate-200'}`}>
              {columns.map((col, idx) => (
                <tr key={col.id} className={isDarkMode ? 'hover:bg-slate-800/30' : 'hover:bg-slate-50'}>
                  <td className="px-4 py-2.5 text-slate-400 font-mono text-center">{idx + 1}</td>
                  <td className="px-4 py-2.5">
                    <input
                      type="text"
                      defaultValue={col.name}
                      onBlur={(e) => handleColumnNameBlur(col.id, e.target.value)}
                      className={`w-full px-2.5 py-1.5 rounded-lg border text-xs font-mono font-bold focus:outline-none focus:border-sky-500 ${
                        isDarkMode ? 'bg-slate-950 border-slate-700 text-white' : 'bg-white border-slate-300 text-slate-900'
                      }`}
                      placeholder="컬럼명 입력..."
                    />
                  </td>
                  <td className="px-4 py-2.5">
                    <button
                      type="button"
                      onClick={() => openDomainPicker(col.id)}
                      className={`px-2.5 py-1.5 rounded-lg border text-left w-full flex items-center justify-between group transition-all ${
                        isDarkMode ? 'bg-slate-950 border-slate-700 hover:border-sky-500 text-slate-200' : 'bg-slate-50 border-slate-300 hover:border-sky-500 text-slate-800'
                      }`}
                    >
                      <span className="font-bold text-xs truncate">{col.domain_name}</span>
                      <ChevronRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-sky-500" />
                    </button>
                  </td>
                  <td className="px-4 py-2.5">
                    <div className="text-[11px] font-medium text-slate-400">{col.category}</div>
                    <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-slate-500/10 text-slate-500 border border-slate-500/20">
                      {col.source}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 font-mono text-[11px] text-sky-600 dark:text-sky-400 truncate">
                    {col.sample}
                  </td>
                  <td className="px-4 py-2.5 text-center">
                    <button
                      onClick={() => handleRemoveColumn(col.id)}
                      className="p-1.5 rounded-lg text-rose-500 hover:bg-rose-500/10 transition-colors"
                      title="컬럼 삭제"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* 3. Generation Control Bar */}
      <div className={`p-6 rounded-2xl border space-y-4 shadow-sm ${
        isDarkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'
      }`}>
        <div className="flex items-center justify-between flex-wrap gap-4">
          {/* Target rows */}
          <div className="space-y-1.5">
            <label className={`block text-xs font-bold ${isDarkMode ? 'text-slate-300' : 'text-slate-700'}`}>생성 레코드 수</label>
            <div className="flex items-center gap-2">
              {[1000, 10000, 50000, 100000].map(cnt => (
                <button
                  key={cnt}
                  type="button"
                  onClick={() => setTargetRows(cnt)}
                  className={`px-3 py-1.5 rounded-xl border text-xs font-bold transition-all ${
                    targetRows === cnt
                      ? 'bg-sky-600 border-sky-600 text-white'
                      : isDarkMode ? 'bg-slate-950 border-slate-700 text-slate-300' : 'bg-slate-50 border-slate-300 text-slate-700'
                  }`}
                >
                  {cnt.toLocaleString()}건
                </button>
              ))}
              <input
                type="number"
                value={targetRows}
                onChange={(e) => setTargetRows(Number(e.target.value))}
                className={`w-28 px-3 py-1.5 rounded-xl border text-xs font-bold font-mono focus:outline-none focus:border-sky-500 ${
                  isDarkMode ? 'bg-slate-950 border-slate-700 text-white' : 'bg-white border-slate-300 text-slate-900'
                }`}
              />
            </div>
          </div>

          {/* Export format */}
          <div className="space-y-1.5">
            <label className={`block text-xs font-bold ${isDarkMode ? 'text-slate-300' : 'text-slate-700'}`}>내보내기 파일 포맷</label>
            <div className="flex items-center gap-2">
              {[
                { id: 'csv', label: 'CSV (.csv)' },
                { id: 'xlsx', label: 'Excel (.xlsx)' },
                { id: 'sql', label: 'SQL INSERT (.sql)' },
                { id: 'json', label: 'JSON (.json)' }
              ].map(f => (
                <button
                  key={f.id}
                  type="button"
                  onClick={() => setExportFormat(f.id)}
                  className={`px-3 py-1.5 rounded-xl border text-xs font-bold transition-all ${
                    exportFormat === f.id
                      ? 'bg-indigo-600 border-indigo-600 text-white'
                      : isDarkMode ? 'bg-slate-950 border-slate-700 text-slate-300' : 'bg-slate-50 border-slate-300 text-slate-700'
                  }`}
                >
                  {f.label}
                </button>
              ))}
            </div>
          </div>

          {/* Generate button */}
          <div className="pt-4">
            <button
              onClick={handleGenerate}
              disabled={isGenerating}
              className="px-8 py-3 rounded-xl bg-gradient-to-r from-sky-600 via-indigo-600 to-purple-600 hover:opacity-95 text-white font-bold text-sm flex items-center gap-2 shadow-lg shadow-sky-600/30 transition-all disabled:opacity-50"
            >
              {isGenerating ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  더미 데이터 고속 생성 중...
                </>
              ) : (
                <>
                  <Zap className="w-4 h-4 fill-current" />
                   {targetRows.toLocaleString()}건 더미 생성 및 다운로드
                </>
              )}
            </button>
          </div>
        </div>

        {errorMsg && (
          <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-600 dark:text-rose-400 text-xs">
            {errorMsg}
          </div>
        )}
      </div>

      {/* 4. Result & Live Preview Grid */}
      {generationResult && (
        <div className={`p-6 rounded-2xl border space-y-4 shadow-sm animate-in fade-in-50 duration-300 ${
          isDarkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'
        }`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-600 dark:text-emerald-400">
                <CheckCircle2 className="w-5 h-5" />
              </div>
              <div>
                <div className="font-bold text-sm text-emerald-600 dark:text-emerald-400">
                  더미 데이터 생성 완료 ({generationResult.rows_generated.toLocaleString()}건)
                </div>
                <div className="text-xs text-slate-400">
                  테이블: {generationResult.table_name} / 컬럼: {generationResult.columns.length}개
                </div>
              </div>
            </div>

            <a
              href={generationResult.download_url}
              className="px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs flex items-center gap-2 shadow-md shadow-emerald-600/20 transition-all"
            >
              <Download className="w-4 h-4" />
              {generationResult.file_name} 다운로드
            </a>
          </div>

          {/* Preview table */}
          <div className="border rounded-xl overflow-hidden">
            <div className={`px-4 py-2 border-b text-xs font-bold ${
              isDarkMode ? 'bg-slate-950 border-slate-800 text-slate-300' : 'bg-slate-50 border-slate-200 text-slate-700'
            }`}>
              생성 결과 상위 15건 실시간 미리보기 (Live Data Grid)
            </div>
            <div className="overflow-x-auto max-h-64">
              <table className="w-full text-left text-xs">
                <thead className={`sticky top-0 font-bold ${
                  isDarkMode ? 'bg-slate-950 text-slate-400' : 'bg-slate-100 text-slate-600'
                }`}>
                  <tr>
                    {generationResult.columns.map((c: string) => (
                      <th key={c} className="px-4 py-2.5 whitespace-nowrap">{c}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className={`divide-y ${isDarkMode ? 'divide-slate-800/60' : 'divide-slate-200'}`}>
                  {generationResult.preview.map((row: any, rIdx: number) => (
                    <tr key={rIdx} className={isDarkMode ? 'hover:bg-slate-800/30' : 'hover:bg-slate-50'}>
                      {generationResult.columns.map((c: string) => (
                        <td key={c} className="px-4 py-2 font-mono text-[11px] whitespace-nowrap text-slate-300 dark:text-slate-300">
                          {String(row[c] !== undefined ? row[c] : '')}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Recent Dummy Generation History Section */}
      {onOpenHistory && <button onClick={onOpenHistory} className="text-sm font-semibold text-amber-600 dark:text-amber-400">더미데이터 생성 이력을 통합 작업 이력에서 보기 →</button>}
      <div className={`p-6 rounded-2xl border transition-colors ${
        isDarkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200 shadow-sm'
      }`}>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2.5">
            <div className={`p-2 rounded-xl ${
              isDarkMode ? 'bg-amber-950/60 text-amber-400 border border-amber-800/50' : 'bg-amber-50 text-amber-700 border border-amber-200'
            }`}>
              <History className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-base text-slate-900 dark:text-white flex items-center gap-2">
                최근 더미데이터 생성 이력
                <span className={`text-xs px-2 py-0.5 rounded-full font-semibold ${
                  isDarkMode ? 'bg-slate-800 text-slate-300' : 'bg-slate-100 text-slate-700'
                }`}>
                  {dummyHistory.length}건
                </span>
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                개발 및 테스트용 목 데이터(SQL, CSV, Excel, JSON) 최근 생성 기록
              </p>
            </div>
          </div>

          <button
            onClick={loadHistory}
            className={`p-2 rounded-xl transition-colors border ${
              isDarkMode 
                ? 'bg-slate-800 hover:bg-slate-700 text-slate-300 border-slate-700' 
                : 'bg-white hover:bg-slate-50 text-slate-600 border-slate-200 shadow-sm'
            }`}
            title="이력 새로고침"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>

        {dummyHistory.length === 0 ? (
          <div className="text-center py-8 border border-dashed rounded-xl dark:border-slate-800">
            <Clock className="w-8 h-8 mx-auto text-slate-400 mb-2 opacity-60" />
            <p className="text-xs font-semibold text-slate-600 dark:text-slate-400">수행된 더미데이터 생성 이력이 없습니다.</p>
            <p className="text-[11px] text-slate-400 dark:text-slate-500 mt-0.5">상단에서 스키마 컬럼을 구성하고 생성을 실행하시면 자동으로 이력이 기록됩니다.</p>
          </div>
        ) : (
          <div className="overflow-x-auto rounded-xl border dark:border-slate-800">
            <table className="w-full text-left text-xs">
              <thead className={`border-b ${isDarkMode ? 'bg-slate-950/80 text-slate-300 border-slate-800' : 'bg-slate-50 text-slate-700 border-slate-200'}`}>
                <tr>
                  <th className="py-2.5 px-3 font-semibold">생성 일시</th>
                  <th className="py-2.5 px-3 font-semibold">테이블명</th>
                  <th className="py-2.5 px-3 font-semibold">산출 파일명</th>
                  <th className="py-2.5 px-3 font-semibold">컬럼 수</th>
                  <th className="py-2.5 px-3 font-semibold">생성 건수</th>
                  <th className="py-2.5 px-3 font-semibold">포맷</th>
                  <th className="py-2.5 px-3 font-semibold text-right">산출물 다운로드</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                {dummyHistory.map((h, idx) => (
                  <tr key={h.id || idx} className={`transition-colors ${isDarkMode ? 'hover:bg-slate-800/40' : 'hover:bg-slate-50/80'}`}>
                    <td className="py-2.5 px-3 font-mono text-slate-500 dark:text-slate-400 whitespace-nowrap">
                      {h.created_at}
                    </td>
                    <td className="py-2.5 px-3 font-bold text-sky-600 dark:text-sky-400">
                      {h.table_name}
                    </td>
                    <td className="py-2.5 px-3 font-mono text-slate-600 dark:text-slate-300 max-w-[180px] truncate" title={h.file_name}>
                      {h.file_name}
                    </td>
                    <td className="py-2.5 px-3 text-slate-700 dark:text-slate-300">
                      {h.columns_count ? `${h.columns_count}개 컬럼` : '-'}
                    </td>
                    <td className="py-2.5 px-3 font-mono font-semibold text-amber-600 dark:text-amber-400">
                      {h.rows_generated ? `${Number(h.rows_generated).toLocaleString()}건` : '-'}
                    </td>
                    <td className="py-2.5 px-3">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300 border border-slate-200 dark:border-slate-700 uppercase">
                        {h.export_format || 'CSV'}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      <a
                        href={getDownloadUrl(h.download_url)}
                        download={h.file_name}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold bg-amber-600 hover:bg-amber-500 text-white transition-colors shadow-sm"
                      >
                        <Download className="w-3.5 h-3.5" />
                        <span>다운로드</span>
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* 5. Domain Picker Modal */}
      {isPickerOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className={`w-full max-w-3xl rounded-2xl border shadow-2xl overflow-hidden flex flex-col max-h-[85vh] ${
            isDarkMode ? 'bg-slate-900 border-slate-800 text-slate-100' : 'bg-white border-slate-200 text-slate-900'
          }`}>
            {/* Header */}
            <div className="p-4 border-b flex items-center justify-between">
              <div>
                <h3 className="font-bold text-sm flex items-center gap-2">
                  <Database className="w-4 h-4 text-sky-500" />
                  100+ 국가/금융/글로벌 표준 컬럼 도메인 사전
                </h3>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  행정안전부 공통표준용어 · Mockaroo 필드 규격 · 금융보안원 마이데이터 통합 사전
                </p>
              </div>
              <button
                onClick={() => setIsPickerOpen(false)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Filter and search */}
            <div className="p-4 border-b space-y-3 bg-slate-50/50 dark:bg-slate-950/40">
              <div className="relative">
                <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
                <input
                  type="text"
                  value={pickerSearch}
                  onChange={(e) => setPickerSearch(e.target.value)}
                  placeholder="도메인명, 유의어(핸드폰, amount, 주민 등) 검색..."
                  className={`w-full pl-9 pr-4 py-2 rounded-xl border text-xs focus:outline-none focus:border-sky-500 ${
                    isDarkMode ? 'bg-slate-900 border-slate-700 text-white' : 'bg-white border-slate-300 text-slate-900'
                  }`}
                />
              </div>

              {/* Category tags */}
              <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-xs">
                {categories.map(cat => (
                  <button
                    key={cat}
                    onClick={() => setPickerCategory(cat)}
                    className={`px-3 py-1 rounded-lg font-medium whitespace-nowrap text-xs transition-all ${
                      pickerCategory === cat
                        ? 'bg-sky-600 text-white font-bold'
                        : isDarkMode ? 'bg-slate-800 text-slate-400 hover:text-white' : 'bg-slate-200/80 text-slate-700 hover:bg-slate-300'
                    }`}
                  >
                    {cat}
                  </button>
                ))}
              </div>
            </div>

            {/* Domain list */}
            <div className="overflow-y-auto p-4 flex-1 grid grid-cols-2 gap-3">
              {filteredPickerDomains.map(d => (
                <div
                  key={d.id}
                  onClick={() => handleSelectDomain(d)}
                  className={`p-3 rounded-xl border text-left cursor-pointer transition-all ${
                    isDarkMode ? 'bg-slate-950 border-slate-800 hover:border-sky-500 hover:bg-slate-800/40' : 'bg-slate-50 border-slate-200 hover:border-sky-500 hover:bg-sky-50/50'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-xs">{d.name}</span>
                    <span className="text-[10px] text-slate-400 font-mono">{d.english_name}</span>
                  </div>
                  <div className="text-[11px] text-sky-600 dark:text-sky-400 font-mono mt-1 truncate">
                    샘플: {d.sample}
                  </div>
                  <div className="flex items-center justify-between mt-2 pt-2 border-t border-slate-800/40 text-[10px] text-slate-400">
                    <span>{d.category}</span>
                    <span className="px-1.5 py-0.5 rounded bg-slate-500/10 text-slate-400 border border-slate-500/20">
                      {d.source}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
