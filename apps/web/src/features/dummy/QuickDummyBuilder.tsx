/**
 * 파일명: QuickDummyBuilder.tsx
 * 경로: apps/web/src/features/dummy/QuickDummyBuilder.tsx
 * 목적: 더미데이터 생성 화면을 제공함
 * 작성자: 개발팀
 * 작성일: 2026-09-09
 * 수정일: 2026-09-09
 */
import React, { useState, useEffect } from 'react';
import { 
  Sparkles, Zap, Plus, Trash2, Download, Table,
  CheckCircle2, Database, RefreshCw, ChevronRight, Search, X, FileCode,
} from 'lucide-react';
import { getDummyDomains, getDummyTemplates, inferDummyColumn, generateDummyData, importDummySchema, generateDummySchema } from '../../services/api';

interface ColumnItem {
  id: string;
  name: string;
  domain_id: string;
  domain_name: string;
  category: string;
  source: string;
  sample: string;
  rule?: any;
  primary_key?: boolean;
  unique?: boolean;
  nullable?: boolean;
  constraints?: any;
}

interface Props {
  isDarkMode: boolean;
  onStepChange?: (step: number) => void;
}

export const QuickDummyBuilder: React.FC<Props> = ({ isDarkMode, onStepChange }) => {
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
  const [scenario, setScenario] = useState<string>('normal');
  const [schemaType, setSchemaType] = useState<'ddl' | 'json-schema' | 'openapi'>('ddl');
  const [schemaContent, setSchemaContent] = useState<string>('');
  const [showSchemaImport, setShowSchemaImport] = useState<boolean>(false);
  const [importedSchema, setImportedSchema] = useState<any>(null);
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [generationResult, setGenerationResult] = useState<any | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Modal for domain picker
  const [isPickerOpen, setIsPickerOpen] = useState<boolean>(false);
  const [pickerTargetColId, setPickerTargetColId] = useState<string | null>(null);
  const [pickerSearch, setPickerSearch] = useState<string>('');
  const [pickerCategory, setPickerCategory] = useState<string>('전체');

  useEffect(() => {
    async function initData() {
      try {
        const [domRes, tmplRes] = await Promise.all([getDummyDomains(), getDummyTemplates()]);
        setAllDomains(domRes.domains);
        setGroupedDomains(domRes.grouped_domains);
        setCategories(['전체', ...domRes.categories]);
        setTemplates(tmplRes.templates);
      } catch (e) {
        console.error('도메인 데이터 로드 오류:', e);
      }
    }
    initData();
  }, []);

  useEffect(() => {
    onStepChange?.(generationResult ? 4 : isGenerating ? 3 : showSchemaImport ? 1 : 2);
  }, [generationResult, isGenerating, onStepChange, showSchemaImport]);

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
  const handleSchemaImport = async () => {
    if (!schemaContent.trim()) return;
    setErrorMsg(null);
    try {
      const result = await importDummySchema(schemaType, schemaContent);
      setImportedSchema(result);
      const table = result.tables[0];
      setTableName(table.name);
      setColumns(table.columns.map((column: any, index: number) => ({
        id: `schema-${index}`, name: column.name, domain_id: '',
        domain_name: column.data_type + (column.primary_key ? ' · PK' : ''),
        category: column.nullable ? '선택' : '필수', source: schemaType.toUpperCase(),
        sample: column.rule?.type || column.data_type, rule: column.rule,
        primary_key: column.primary_key, unique: column.unique,
        nullable: column.nullable, constraints: column.constraints,
      })));
      setShowSchemaImport(false);
      setGenerationResult(null);
    } catch (err: any) {
      setErrorMsg(err.message || '스키마 가져오기 실패');
    }
  };

  const handleGenerate = async () => {
    if (columns.length === 0) return;
    setIsGenerating(true);
    setErrorMsg(null);
    try {
      const payload = {
        table_name: tableName,
        columns: columns.map(c => ({ name: c.name, domain_id: c.domain_id || undefined, rule: c.rule,
          primary_key: c.primary_key, unique: c.unique, nullable: c.nullable, constraints: c.constraints })),
        target_rows: Number(targetRows),
        export_format: exportFormat,
        scenario,
      };
      const res = importedSchema?.tables?.length > 1
        ? await generateDummySchema(importedSchema, Number(targetRows), scenario)
        : await generateDummyData(payload);
      setGenerationResult(res);
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
      {/* 0. Schema Import Panel */}
      <div className="ui-panel p-4 sm:p-5">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <div className="text-sm font-bold text-fg flex items-center gap-1.5">
              <FileCode className="w-4 h-4 text-accent" />
              DDL · JSON Schema · OpenAPI 스키마 가져오기
            </div>
            <div className="text-xs text-fg-muted mt-0.5 break-keep">
              기존 데이터베이스 DDL 또는 스키마 명세를 붙여 넣으면 컬럼 타입과 규칙을 자동 구성합니다.
            </div>
          </div>
          <button
            type="button"
            onClick={() => setShowSchemaImport(!showSchemaImport)}
            className="ui-button-secondary whitespace-nowrap self-start sm:self-auto shrink-0"
          >
            {showSchemaImport ? '닫기' : '스키마 가져오기'}
          </button>
        </div>

        {showSchemaImport && (
          <div className="mt-4 space-y-3 pt-3 border-t border-subtle">
            <div className="flex flex-wrap gap-2">
              {(['ddl', 'json-schema', 'openapi'] as const).map(type => (
                <button
                  key={type}
                  type="button"
                  onClick={() => setSchemaType(type)}
                  className={`rounded-lg border px-3 py-1.5 text-xs font-bold transition-colors ${
                    schemaType === type
                      ? 'border-accent bg-accent/10 text-accent'
                      : 'border-subtle text-fg-muted hover:text-fg hover:bg-surface-muted'
                  }`}
                >
                  {type.toUpperCase()}
                </button>
              ))}
            </div>
            <textarea
              value={schemaContent}
              onChange={e => setSchemaContent(e.target.value)}
              rows={7}
              placeholder="CREATE TABLE ...; 또는 JSON 문서를 붙여 넣으세요."
              className="ui-field p-3 font-mono text-xs"
            />
            <button
              type="button"
              onClick={handleSchemaImport}
              className="ui-button-primary px-5 py-2 text-xs"
            >
              분석하여 컬럼에 적용
            </button>
          </div>
        )}
      </div>

      {/* 1. Template Presets */}
      <div className="ui-panel space-y-3 p-4 sm:p-5">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1">
          <span className="text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 text-fg">
            <Sparkles className="w-4 h-4 text-accent shrink-0" />
            사내 표준 추천 템플릿 (1초 완성)
          </span>
          <span className="text-2xs text-fg-muted">클릭 시 추천 컬럼 스키마가 즉시 세팅됩니다</span>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2 sm:gap-2.5">
          {templates.map(tmpl => (
            <button
              key={tmpl.id}
              type="button"
              onClick={() => handleApplyTemplate(tmpl)}
              className={`p-2.5 sm:p-3 rounded-xl border text-left transition-all ${
                tableName === tmpl.id
                  ? 'bg-accent/10 border-accent ring-1 ring-accent/40 text-fg'
                  : 'bg-surface-muted/40 border-subtle text-fg-muted hover:text-fg hover:border-subtle hover:bg-surface-muted'
              }`}
            >
              <div className="font-bold text-xs truncate text-fg">{tmpl.name}</div>
              <div className="text-2xs text-fg-muted mt-1">{tmpl.columns.length}개 컬럼</div>
            </button>
          ))}
        </div>
      </div>

      {/* 2. Schema Builder Card / Table */}
      <div className="ui-panel overflow-hidden">
        {/* Header */}
        <div className="px-4 sm:px-6 py-3.5 border-b border-subtle bg-surface-muted/30 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="flex flex-wrap items-center gap-3">
            <h3 className="font-bold text-sm flex items-center gap-2 text-fg">
              <Table className="w-4 h-4 text-accent shrink-0" />
              <span>테이블 스키마 및 도메인 정의</span>
            </h3>
            <div className="flex items-center gap-1.5 text-xs text-fg-muted">
              <span className="whitespace-nowrap">테이블명:</span>
              <input
                type="text"
                value={tableName}
                onChange={(e) => setTableName(e.target.value)}
                className="ui-field py-1 px-2.5 font-mono font-bold text-xs w-36 sm:w-44"
                placeholder="table_name"
              />
            </div>
          </div>
          <button
            type="button"
            onClick={handleAddColumn}
            className="ui-button-primary min-h-0 px-3.5 py-1.5 text-xs whitespace-nowrap self-start sm:self-auto"
          >
            <Plus className="w-3.5 h-3.5" /> 컬럼 추가
          </button>
        </div>

        {/* Mobile View (< md): Clean Touch Cards (No horizontal crushing!) */}
        <div className="md:hidden divide-y divide-subtle">
          {columns.map((col, idx) => (
            <div key={col.id} className="p-4 space-y-3 hover:bg-surface-muted/20 transition-colors">
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2 flex-1 min-w-0">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-surface-muted font-mono font-bold text-xs text-fg-muted border border-subtle">
                    {idx + 1}
                  </span>
                  <input
                    type="text"
                    defaultValue={col.name}
                    onBlur={(e) => handleColumnNameBlur(col.id, e.target.value)}
                    className="ui-field py-1 px-2.5 font-mono font-bold text-xs flex-1 min-w-0"
                    placeholder="컬럼명 (예: user_id, email)"
                  />
                </div>
                <button
                  type="button"
                  onClick={() => handleRemoveColumn(col.id)}
                  disabled={columns.length <= 1}
                  className="p-1.5 text-rose-500 hover:bg-rose-500/10 rounded-lg transition-colors shrink-0 disabled:opacity-30 disabled:cursor-not-allowed"
                  title="컬럼 삭제"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>

              {/* Mapped Domain Picker */}
              <div className="space-y-1">
                <div className="flex items-center justify-between text-2xs text-fg-muted">
                  <span>매핑 도메인</span>
                  <span className="text-2xs font-medium bg-surface-muted px-1.5 py-0.5 rounded border border-subtle text-fg-subtle">
                    {col.category} · {col.source}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => openDomainPicker(col.id)}
                  className="w-full flex items-center justify-between px-3 py-2 rounded-xl border border-subtle bg-surface-muted/40 hover:border-accent text-left text-xs transition-all group"
                >
                  <span className="font-bold truncate text-fg group-hover:text-accent">{col.domain_name}</span>
                  <ChevronRight className="w-4 h-4 text-fg-muted group-hover:text-accent shrink-0" />
                </button>
              </div>

              {/* Sample Preview */}
              <div className="flex items-center justify-between rounded-lg bg-surface-muted/30 px-3 py-1.5 text-2xs border border-subtle">
                <span className="text-fg-subtle text-2xs">생성 샘플:</span>
                <span className="font-mono text-accent font-medium truncate max-w-[200px]" title={col.sample}>
                  {col.sample}
                </span>
              </div>
            </div>
          ))}
        </div>

        {/* Desktop View (>= md): Full Structured Table */}
        <div className="hidden md:block overflow-x-auto max-h-[440px]">
          <table className="w-full text-left text-xs min-w-[760px]">
            <thead className="sticky top-0 font-bold bg-surface-muted text-fg-muted border-b border-subtle text-2xs uppercase tracking-wider">
              <tr>
                <th className="px-4 py-3 w-12 text-center whitespace-nowrap">#</th>
                <th className="px-4 py-3 w-52 whitespace-nowrap">컬럼명 (입력 시 자동추론)</th>
                <th className="px-4 py-3 w-64 whitespace-nowrap">매핑된 표준 도메인</th>
                <th className="px-4 py-3 w-36 whitespace-nowrap">분류 / 출처</th>
                <th className="px-4 py-3 whitespace-nowrap min-w-[200px]">실제 생성 샘플 미리보기</th>
                <th className="px-4 py-3 w-16 text-center whitespace-nowrap">삭제</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-subtle">
              {columns.map((col, idx) => (
                <tr key={col.id} className="hover:bg-surface-muted/40 transition-colors">
                  <td className="px-4 py-2.5 text-fg-muted font-mono text-center">{idx + 1}</td>
                  <td className="px-4 py-2.5">
                    <input
                      type="text"
                      defaultValue={col.name}
                      onBlur={(e) => handleColumnNameBlur(col.id, e.target.value)}
                      className="ui-field py-1.5 font-mono font-bold text-xs"
                      placeholder="컬럼명 입력..."
                    />
                  </td>
                  <td className="px-4 py-2.5">
                    <button
                      type="button"
                      onClick={() => openDomainPicker(col.id)}
                      className="px-2.5 py-1.5 rounded-lg border border-subtle text-left w-full flex items-center justify-between group transition-all bg-surface hover:border-accent hover:bg-surface-muted/30"
                    >
                      <span className="font-bold text-xs truncate text-fg group-hover:text-accent">{col.domain_name}</span>
                      <ChevronRight className="w-3.5 h-3.5 text-fg-muted group-hover:text-accent shrink-0" />
                    </button>
                  </td>
                  <td className="px-4 py-2.5">
                    <div className="text-2xs font-medium text-fg">{col.category}</div>
                    <span className="px-1.5 py-0.5 rounded text-2xs font-bold bg-surface-muted text-fg-muted border border-subtle">
                      {col.source}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 font-mono text-2xs text-accent truncate max-w-xs">
                    {col.sample}
                  </td>
                  <td className="px-4 py-2.5 text-center">
                    <button
                      type="button"
                      onClick={() => handleRemoveColumn(col.id)}
                      disabled={columns.length <= 1}
                      className="p-1.5 rounded-lg text-rose-500 hover:bg-rose-500/10 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
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
      <div className="ui-panel space-y-4 p-4 sm:p-6">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          {/* Target rows */}
          <div className="space-y-1.5">
            <label className="block text-xs font-bold text-fg">생성 레코드 수</label>
            <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
              {[1000, 10000, 50000, 100000].map(cnt => (
                <button
                  key={cnt}
                  type="button"
                  onClick={() => setTargetRows(cnt)}
                  className={`px-3 py-1.5 rounded-xl border text-xs font-bold transition-all ${
                    targetRows === cnt
                      ? 'bg-accent border-accent text-accent-fg shadow-xs'
                      : 'border-subtle bg-surface-muted/40 text-fg-muted hover:text-fg hover:bg-surface-muted'
                  }`}
                >
                  {cnt.toLocaleString()}건
                </button>
              ))}
              <input
                type="number"
                value={targetRows}
                onChange={(e) => setTargetRows(Number(e.target.value))}
                className="ui-field w-28 py-1.5 font-mono font-bold text-xs"
              />
            </div>
          </div>

          {/* Export format */}
          <div className="space-y-1.5">
            <label className="block text-xs font-bold text-fg">내보내기 파일 포맷</label>
            <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
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
                      ? 'bg-accent border-accent text-accent-fg shadow-xs'
                      : 'border-subtle bg-surface-muted/40 text-fg-muted hover:text-fg hover:bg-surface-muted'
                  }`}
                >
                  {f.label}
                </button>
              ))}
            </div>
          </div>

          {/* Test scenario */}
          <div className="space-y-1.5">
            <label className="block text-xs font-bold text-fg">테스트 시나리오</label>
            <select
              value={scenario}
              onChange={e => setScenario(e.target.value)}
              className="ui-field font-bold text-xs w-full sm:w-auto"
            >
              <option value="normal">정상 데이터</option>
              <option value="boundary">경계값 포함</option>
              <option value="invalid">오류 데이터</option>
              <option value="mixed">정상 95% + 오류 5%</option>
            </select>
          </div>
        </div>

        {/* Generate button */}
        <div className="pt-2 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-t border-subtle">
          <p className="text-xs text-fg-muted">
            사내 개발 및 QA 부하 테스트용 대량 모의 데이터를 즉시 생성합니다.
          </p>
          <button
            type="button"
            onClick={handleGenerate}
            disabled={isGenerating}
            className="ui-button-primary px-6 sm:px-8 py-2.5 text-sm font-bold w-full sm:w-auto justify-center"
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

        {errorMsg && (
          <div className="ui-error mt-2">
            {errorMsg}
          </div>
        )}
      </div>

      {/* 4. Result & Live Preview Grid */}
      {generationResult && (
        <div className="ui-panel animate-in space-y-4 p-4 sm:p-6 duration-300 fade-in-50">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-600 dark:text-emerald-400 shrink-0">
                <CheckCircle2 className="w-5 h-5" />
              </div>
              <div>
                <div className="font-bold text-sm text-emerald-600 dark:text-emerald-400">
                  더미 데이터 생성 완료 ({generationResult.rows_generated.toLocaleString()}건)
                </div>
                <div className="text-xs text-fg-muted">
                  테이블: {generationResult.table_name} / 컬럼: {generationResult.columns.length}개
                </div>
              </div>
            </div>

            <a
              href={generationResult.download_url}
              className="px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs flex items-center justify-center gap-2 shadow-md shadow-emerald-600/20 transition-all self-start sm:self-auto w-full sm:w-auto"
            >
              <Download className="w-4 h-4" />
              {generationResult.file_name} 다운로드
            </a>
          </div>

          {/* Preview table */}
          <div className="border border-subtle rounded-xl overflow-hidden">
            <div className="px-4 py-2 border-b border-subtle text-xs font-bold bg-surface-muted text-fg">
              생성 결과 상위 15건 실시간 미리보기 (Live Data Grid)
            </div>
            <div className="overflow-x-auto max-h-64">
              <table className="w-full text-left text-xs min-w-[500px]">
                <thead className="sticky top-0 font-bold bg-surface-muted text-fg-muted border-b border-subtle">
                  <tr>
                    {generationResult.columns.map((c: string) => (
                      <th key={c} className="px-4 py-2.5 whitespace-nowrap">{c}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-subtle">
                  {generationResult.preview.map((row: any, rIdx: number) => (
                    <tr key={rIdx} className="hover:bg-surface-muted/30 transition-colors">
                      {generationResult.columns.map((c: string) => (
                        <td key={c} className="px-4 py-2 font-mono text-xs whitespace-nowrap text-fg">
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

      {/* 5. Domain Picker Modal */}
      {isPickerOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-3 sm:p-4">
          <div className="w-full max-w-3xl rounded-2xl border border-subtle bg-surface shadow-2xl overflow-hidden flex flex-col max-h-[88vh]">
            {/* Header */}
            <div className="p-4 border-b border-subtle flex items-center justify-between gap-3">
              <div>
                <h3 className="font-bold text-sm flex items-center gap-2 text-fg">
                  <Database className="w-4 h-4 text-accent" />
                  100+ 국가/금융/글로벌 표준 컬럼 도메인 사전
                </h3>
                <p className="text-xs text-fg-muted mt-0.5 break-keep">
                  행정안전부 공통표준용어 · Mockaroo 필드 규격 · 금융보안원 마이데이터 통합 사전
                </p>
              </div>
              <button
                type="button"
                onClick={() => setIsPickerOpen(false)}
                className="p-1.5 rounded-lg text-fg-muted hover:text-fg hover:bg-surface-muted transition-colors shrink-0"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Filter and search */}
            <div className="p-4 border-b border-subtle space-y-3 bg-surface-muted/40">
              <div className="relative">
                <Search className="w-4 h-4 absolute left-3 top-2.5 text-fg-muted" />
                <input
                  type="text"
                  value={pickerSearch}
                  onChange={(e) => setPickerSearch(e.target.value)}
                  placeholder="도메인명, 유의어(핸드폰, amount, 주민 등) 검색..."
                  className="ui-field pl-9 pr-4 py-2 text-xs"
                />
              </div>

              {/* Category tags */}
              <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-xs scrollbar-none">
                {categories.map(cat => (
                  <button
                    key={cat}
                    type="button"
                    onClick={() => setPickerCategory(cat)}
                    className={`px-3 py-1 rounded-lg font-medium whitespace-nowrap text-xs transition-all ${
                      pickerCategory === cat
                        ? 'bg-accent text-accent-fg font-bold shadow-xs'
                        : 'bg-surface-muted text-fg-muted hover:text-fg hover:bg-surface-muted/80'
                    }`}
                  >
                    {cat}
                  </button>
                ))}
              </div>
            </div>

            {/* Domain list */}
            <div className="overflow-y-auto p-3 sm:p-4 flex-1 grid grid-cols-1 sm:grid-cols-2 gap-2.5 sm:gap-3">
              {filteredPickerDomains.map(d => (
                <div
                  key={d.id}
                  onClick={() => handleSelectDomain(d)}
                  className="p-3 rounded-xl border border-subtle bg-surface-muted/30 hover:border-accent hover:bg-accent/5 text-left cursor-pointer transition-all"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-bold text-xs text-fg truncate">{d.name}</span>
                    <span className="text-xs text-fg-muted font-mono shrink-0">{d.english_name}</span>
                  </div>
                  <div className="text-xs text-accent font-mono mt-1 truncate">
                    샘플: {d.sample}
                  </div>
                  <div className="flex items-center justify-between mt-2 pt-2 border-t border-subtle text-xs text-fg-muted">
                    <span>{d.category}</span>
                    <span className="px-1.5 py-0.5 rounded bg-surface-muted text-fg-muted border border-subtle">
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
