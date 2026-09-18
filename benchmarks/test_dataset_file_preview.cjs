/**
 * 파일명: test_dataset_file_preview.cjs
 * 경로: benchmarks/test_dataset_file_preview.cjs
 * 목적: 실제 파일 기반 미리보기와 JSON 정밀도·원본 컬럼·시트 보존을 검증함
 * 작성자: 개발팀
 * 작성일: 2026-09-17
 * 수정일: 2026-09-17
 */
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const ts = require('typescript');
const XLSX = require('xlsx');

// 프로젝트 TypeScript 코드를 메모리에서 컴파일하여 산출물 없이 검사함
const filename = path.resolve(__dirname, '../apps/web/src/features/converter/datasetFilePreview.ts');
const compiled = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
  compilerOptions: { target: ts.ScriptTarget.ES2020, module: ts.ModuleKind.CommonJS, esModuleInterop: true },
}).outputText;
const loaded = new Module(filename, module);
loaded.paths = Module._nodeModulePaths(path.dirname(filename));
loaded._compile(compiled, filename);
const preview = loaded.exports;

test('JSON formatting preserves large numbers, whitespace in strings, escapes and order', () => {
  const raw = '{"id":9007199254740993,"code":"001","url":"https:\\/\\/example.com","text":" A { B } ","nested":[],"empty":{}}';
  const formatted = preview.formatJsonText(raw);
  assert.match(formatted, /9007199254740993/);
  assert.match(formatted, /https:\\\/\\\/example.com/);
  assert.match(formatted, /" A \{ B \} "/);
  assert.deepEqual(JSON.parse(formatted), JSON.parse(raw));
  assert.deepEqual(Object.keys(JSON.parse(formatted)), Object.keys(JSON.parse(raw)));
  assert.equal(preview.formatJsonText('['.repeat(500) + '0' + ']'.repeat(500)), '['.repeat(500) + '0' + ']'.repeat(500));
});

test('actual CCTV original JSON is JSON, not converted row preview', async () => {
  const raw = fs.readFileSync(path.resolve(__dirname, '../docs/adr/청주시cctv.json'));
  const result = await preview.parseFilePreview(new Blob([raw]), 'JSON');
  const model = JSON.parse(result.text);
  assert.equal(result.table, undefined);
  assert.equal(model.response.body.totalCount, 100755);
  assert.equal(model.response.body.items.length, 1000);
  assert.deepEqual(model, JSON.parse(raw.toString('utf8')));
  assert.equal(preview.defaultPreviewMode('JSON'), 'code');
});

test('actual CCTV XML displays original XML tags, never path-like columns', async () => {
  const raw = fs.readFileSync(path.resolve(__dirname, '../docs/adr/청주시cctv.xml'));
  const result = await preview.parseFilePreview(new Blob([raw]), 'XML');
  assert.equal(result.text, raw.toString('utf8').replace(/^\uFEFF/, ''));
  assert.match(result.text, /<items><item>/);
  assert.equal(result.table, undefined);
  assert.equal(preview.defaultPreviewMode('XML'), 'code');
});

test('CSV uses its own Korean headers, preserves quotes, multiline text and codes', async () => {
  const text = '코드,설명\r\n001,"A,B"\r\n002,"두\n줄"\r\n,\r\n';
  const result = await preview.parseFilePreview(new Blob([text]), 'csv');
  assert.equal(result.text, text);
  assert.deepEqual(result.table.headers, ['코드','설명']);
  assert.deepEqual(result.table.rows, [['001','A,B'],['002','두\n줄'],['','']]);
});

test('TSV preserves duplicate headers and cells without JSON conversion', async () => {
  const result = await preview.parseFilePreview(new Blob(['a\ta\n001\tNA']), 'tsv');
  assert.deepEqual(result.table, { headers:['a','a'], rows:[['001','NA']] });
});

test('CP949 and UTF16 input are decoded from their actual bytes', async () => {
  const cp949 = Buffer.from([0x63,0x6f,0x64,0x65,0x0a,0xc3,0xbb,0xc1,0xd6]);
  const result = await preview.parseFilePreview(new Blob([cp949]), 'csv', undefined, 'cp949');
  assert.equal(result.table.rows[0][0], '청주');
  const xml = '<rows><row>청주</row></rows>';
  const utf16 = Buffer.concat([Buffer.from([0xff,0xfe]),Buffer.from(xml,'utf16le')]);
  assert.equal((await preview.parseFilePreview(new Blob([utf16]), 'xml')).text, xml);
});

test('XLSX original and selected sheet retain original headers and formulas', async () => {
  const book = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(book, XLSX.utils.aoa_to_sheet([['unused'],[123]]), 'First');
  const sheet = XLSX.utils.aoa_to_sheet([['코드','수치','상태','수식'],['001',0,false,3]]);
  sheet.D2.f = '1+2';
  XLSX.utils.book_append_sheet(book, sheet, 'Second');
  const data = XLSX.write(book, { type:'buffer', bookType:'xlsx' });
  const result = await preview.parseFilePreview(new Blob([data]), 'xlsx', 'Second');
  assert.deepEqual(result.sheets, ['First','Second']);
  assert.equal(result.sheet,'Second');
  assert.deepEqual(result.table.headers,['코드','수치','상태','수식']);
  assert.deepEqual(result.table.rows,[['001',0,false,'=1+2']]);
  assert.equal(result.text,undefined);
});

test('text outputs are shown in their actual format rather than fabricated JSON', async () => {
  for (const [format,text] of [['jsonl','{"code":"001"}\n{"code":"002"}\n'],['sql','INSERT INTO sample VALUES (1);'],['md','# 설명서\n'],['html','<table><tr><td>001</td></tr></table>'],['txt','원문 텍스트']]) {
    const result = await preview.parseFilePreview(new Blob([text]),format);
    assert.equal(result.text,text);
    assert.equal(result.table,undefined);
  }
});

test('large text is bounded and explicitly labelled as incomplete', async () => {
  const result = await preview.parseFilePreview(new Blob(['x'.repeat(3*1024*1024)]),'json');
  assert.equal(result.text.length,2*1024*1024);
  assert.match(result.notice,/2 MiB/);
});

test('binary Parquet is explicitly a table summary, not JSON source code', () => {
  const result = preview.parquetPreview(['code'],[{code:'001'}]);
  assert.equal(result.text,undefined);
  assert.deepEqual(result.table,{headers:['code'],rows:[['001']]});
  assert.match(result.notice,/바이너리/);
});

test('actual target download is bounded instead of replaced with row-preview JSON', async () => {
  const saved = global.fetch;
  let cancelled = false;
  const body = new ReadableStream({
    start(controller) { controller.enqueue(new Uint8Array(3*1024*1024).fill(65)); },
    cancel() { cancelled = true; },
  });
  global.fetch = async () => new Response(body);
  try {
    const blob = await preview.downloadPreviewBlob('http://localhost/result.json','json');
    assert.equal(blob.size,2*1024*1024+1);
    assert.equal(cancelled,true);
    assert.match((await preview.parseFilePreview(blob,'json')).notice,/2 MiB/);
  } finally { global.fetch = saved; }
});

test('download errors are explicit and never generate another file format as fallback', async () => {
  const saved = global.fetch;
  global.fetch = async () => new Response('missing',{status:404});
  try { await assert.rejects(preview.downloadPreviewBlob('http://localhost/missing.xml','xml'),/HTTP 404/); }
  finally { global.fetch = saved; }
});

test('UTF8 clipping does not make the whole JSON preview decode as CP949', async () => {
  const bytes = Buffer.concat([Buffer.from('{"text":"청주'),Buffer.from([0xec,0x95])]);
  const result = await preview.parseFilePreview(new Blob([bytes]),'json');
  assert.match(result.text,/청주/);
});
