# Universal Document Conversion Foundations

## Continuation Checkpoint (2026-09-10)

The supplied Universal Document Compiler specification ends with a restricted
first implementation request (section 57). Its nine requested areas map to
the existing package rather than a second standalone repository:

| Requested area | Implementation | State |
|---|---|---|
| Package structure | `document_conversion/` and its tests | Implemented |
| Enums | `core/enums.py` | Implemented |
| Source provenance | `core/source_ref.py` | Implemented |
| Universal IR | `core/ir.py` | Implemented |
| Point units | `core/units.py` | Implemented |
| Deduplicated resources | `core/resources.py` | Implemented |
| Capability declarations | `core/capabilities.py` | Implemented |
| Table geometry | `geometry/table_geometry.py` | Implemented |
| Executable regression tests | `tests/document_conversion/` | Verified |

Verification in the current Windows workspace:

```powershell
.venv/Scripts/python.exe -m pytest packages/synthetic_engine/tests/document_conversion -q
```

Result: 98 passed (95 foundation tests and 3 PDF parser tests). This confirms
the foundation checkpoint, not all final document fidelity acceptance criteria.
The earlier PDF inspection integration is retained; it is separate from the
restricted initial scope. No duplicate IR or stub conversion entry point is added.

The next implementation phase in the supplied sequence is HWPX parsing:

1. Add bounded ZIP reading with entry count, total size, per-entry size,
   compression-ratio and traversal checks before XML parsing.
2. Identify HWPX from package contents and signature, not extension alone.
3. Resolve header styles and fonts by namespace URI; preserve source XML paths.
4. Map paragraphs, runs, inline controls, section geometry, tables, spans,
   nested content and images to the existing IR without text normalization.
5. Retain uninterpreted content with explicit unsupported-feature diagnostics.
6. Verify Unicode controls, nested tables, merged-cell occupancy and image
   extraction before proceeding to DOCX rendering.

HWP5 parsing, semantic PDF table inference, renderers, round-trip QA, automatic
loss reports and generic converter migration remain outstanding. They are not
implied by the above foundation test result.

## Scope and Status

The data-conversion engine lives in
`packages/synthetic_engine/synthetic_engine/document_conversion`.
The foundation implements the universal IR, units, resources, capability
declarations, and table geometry. Subsequent increments add PDF inspection and
a partial IR conversion pipeline described below.

The existing converter API and UI retain their current conversion behavior.
Their migration to the IR pipeline is a subsequent phase. No fidelity scores or
support claims for unimplemented parsers/renderers are emitted by this foundation.

## Ownership

- `core/enums.py`: formatting, severity, support status, and fidelity vocabulary.
- `core/source_ref.py`: source provenance and point-based page rectangles.
- `core/ir.py`: document, section, block, inline, formula and unknown-record data.
- `core/units.py`: point conversion for HWPUNIT, EMU, twips, inches and millimeters.
- `core/resources.py`: immutable SHA-256-addressed resource payloads.
- `core/capabilities.py`: explicitly declared native capabilities, false by default.
- `geometry/table_geometry.py`: logical occupancy validation and width normalization.
- `exceptions.py`: conversion, unsupported-feature and geometry exceptions.

Future parsers, normalization, renderers, optional adapters and QA modules belong
under the same package. They are not represented by executable placeholders.
API orchestration will live in `application/services/document_conversion_service.py`,
using the existing `routes/v1/converter.py` and converter UI. Existing source/target
eligibility rules remain distinct from per-renderer feature capabilities.

## Data Contracts

Internal dimensions use points. Unknown page sizes remain `None`; text is never
stripped, Unicode-normalized or split and rejoined. Paragraph boundaries are
separate ParagraphIR objects; tabs and inline soft/hard breaks are separate nodes.
Page-number fields preserve their type independently from cached presentation.

Table rows contain only logical anchor cells. Covered merge coordinates repeat
the anchor reference in the virtual grid, not in the stored row lists. Empty
physical rows beneath a vertical merge are represented by empty lists. Unoccupied
coordinates remain `None`, so no synthetic cell is counted as source content.
Padding order is top, right, bottom, left. Row and column indices are zero-based;
source page/section numbers are one-based.

`repair_table_geometry` can reorder anchors into their recorded rows and extend
missing row slots. Overlaps fail with GeometryError; conflicting source data is
never discarded. Width inference uses explicit tracks, then cell measurements,
then available table width or the documented fallback. Width repair is an inferred
layout operation, not evidence that the source specified those measurements.

`normalize_column_widths` shrinks tracks proportionally and updates spanning cell
widths. Nested tables respect their containing cell's horizontal padding. An
infeasible minimum track width raises GeometryError. Both operations plan changes
before mutation, so a failed descendant leaves ancestor geometry unchanged.
Font measurement, unbreakable-text layout, image downscaling and pagination remain
later layout work; this table module does not claim to solve them.

Document construction interns all image payloads including table, header and footer
occurrences. Placements stay independent; identical bytes share one canonical
immutable object. Call `document.intern_resources()` after adding or replacing
images in a mutable document. Resources can also be stored directly for drawings
or attachments. MIME metadata is a source claim, not magic-byte detection.

## Running Tests

From the repository root, in the configured workspace environment:

```bash
uv run pytest packages/synthetic_engine/tests/document_conversion
```

The foundation needs no document parsing or machine-learning dependencies:

```bash
PYTHONPATH=packages/synthetic_engine python -m pytest packages/synthetic_engine/tests/document_conversion
```

The parent `synthetic_engine` package now resolves its existing public exports
lazily. Importing the document foundation does not load optional synthesis engines.
Existing top-level export names and their implementing modules are preserved.

Tests cover Unicode/control preservation, simultaneous row/column spans, nested
tables, conflict rejection, proportional widths, transactional failures, resource
identity, source references, formatting fields and independent package imports.
Rendered output, actual document fidelity and source/target round trips are not
validated until the corresponding parsers and renderers exist.

## PDF Inspection Integration (2026-09-10)

`parsers/pdf.py` now reads PDF page dimensions, positioned text spans, font size,
bold/italic/color, line/span source references, and embedded image placements.
Text remains exactly as extracted by PyMuPDF; no stripping or Unicode folding
is performed. Extracted lines are represented as ParagraphIR blocks and a warning
explicitly distinguishes them from recovered semantic paragraphs. Image payloads
are interned, while the complete source PDF is also retained as a resource for
records not yet interpreted. That source resource contains original personal data
and must never be included in a pseudonymized download.

`application/services/document_conversion_service.py` uses this parser for the
native document privacy inspection and rescan endpoints. HWP/HWPX still use the
existing Hancom rendering adapter; parsing that PDF is not a native HWP parser.
The native editor continues to modify the source file and perform its existing
pixel/residual checks. No new renderer, inferred table geometry, OCR, or native
HWP record parser is claimed. The generic converter retains its default engine;
an explicit IR engine option is described below.

PDF reading requires PyMuPDF, imported only when parse_pdf is called. Foundation
imports remain independent of that optional dependency. Parser tests cover text
and formatting, source references, source-byte retention, image deduplication,
and page limits. The privacy route tests cover integration and download gating.

## Standalone Scaffold Integration and IR Conversion

The source inspected at `C:/Users/PRO/universal-document-engine` contains the
`docengine` package skeleton, version 0.1.0, dependency declarations and README.
It contains no parser/renderer implementation or test modules at this checkpoint.
Its public import contract is now implemented by
`packages/synthetic_engine/docengine/__init__.py`, a lazy facade over this engine.
Setuptools includes both package names; IR classes exist only under
`synthetic_engine.document_conversion`. The external directory is not modified
or required at runtime. Its declared parsing dependencies are recorded in the
existing package manifest and workspace lockfile.

```python
from pathlib import Path
from docengine import convert_document

result = convert_document(Path('sample.hwpx'), 'docx', output_dir=Path('output'))
```

Implemented partial input paths: HWPX, PDF, DOCX, HTML/HTM.
Implemented partial output paths: DOCX and standalone HTML.
All paths pass through IR. Each conversion creates a sibling
`.conversion-report.json`. HTML and DOCX outputs are parsed back for exact
extracted-text comparison and source/target object counts. Unmeasured fidelity
dimensions remain null. Strict mode rejects these partial renderers explicitly.

HWPX parsing validates ZIP entry/expanded-size/ratio/path limits, disables XML
entities, reads section text, inline tabs/breaks, basic run styles, explicit
merged/nested tables and resolvable picture references. Unmapped XML is retained
with diagnostics. Full style inheritance, header/footer and drawing mapping are
not complete. DOCX/HTML parsers and renderers likewise have explicit partial
style/resource support, listed in the report; no fidelity threshold is claimed.

The existing POST `/api/v1/converter/convert` accepts multipart `engine=ir` and
`strict=false` alongside `file` and `target_format`. The response includes
`conversion_report` and `report_download_url`, and records conversion history.
The default remains `engine=legacy` until the remaining fidelity work is verified.
The web UI does not yet select the IR engine automatically.

Current verification: 125 tests passed across document_conversion, conversion
rules and native privacy tests. Includes an actual python-hwpx package -> IR ->
DOCX -> IR table test and the public `docengine` facade.

Outstanding: HWP5, Markdown/XLSX parsers, HWPX/PDF/Markdown/XLSX renderers,
full styling/resources, normalized/visual/structure/resource QA, capability
adaptation and default UI migration. This checkpoint is not project completion.

## Format Registration Increment (Implementation Only)

At the user's request this increment was implemented without running tests,
builds, round-trip commands or sample conversions. Earlier passing test counts
do not validate this increment.

`registry.py` now registers all requested input formats (HWP5, HWPX, PDF, DOCX,
HTML/HTM, Markdown, XLSX) and output formats (HWPX, PDF, DOCX, HTML, Markdown,
XLSX). PDF signatures, OLE HWP headers and ZIP package markers identify binary
formats; text formats retain extension-based identification. Imports are lazy.

New implementations:

- HWP5: bounded OLE streams, compression flags, record headers/extended sizes,
  paragraph UTF-16 controls, raw unsupported records and source provenance.
  Semantic HWP table/control trees and style resolution remain partial.
- Markdown: Python-Markdown grammar and structural IR through the HTML parser.
  Original source syntax is retained as a resource.
- XLSX: worksheets, logical merged anchors, values, formulas and cached values,
  basic font properties and number formats. Charts/images and advanced styles
  are not mapped yet.
- Markdown output: paragraphs plus HTML fallback for complex blocks.
- XLSX output: independent tables/sheets, merged cells, literal strings,
  formulas and number formats. Nested tables are separate sheets.
- HWPX output: python-hwpx package generation, text and nested merged tables.
- PDF output: PyMuPDF Story layout of IR-derived offline HTML; limited to 1000
  generated pages and currently one page-size policy for the document.

`pipeline.convert_document` now uses the registry for every source and target.
The runtime audit is implemented to parse output again; no such audit was run
during this implementation increment. Source warnings and unmeasured fidelity
dimensions remain explicit. `strict=True` still blocks the partial renderers.
The API accepts all registered outputs when `engine=ir`, including XLSX input
to document outputs, independently of the legacy dataset matrix.

Registration of every format is not full fidelity support. Full style/resource
mapping, native HWP geometry, default UI selection and final acceptance
verification remain incomplete. The default API engine remains legacy.

## Legacy Fidelity Hardening (2026-09-10)

The default exporters now preserve arbitrary PDF table column counts, multiline
cells and cell font metadata across HTML, DOCX, XLSX, HWPX and Markdown. Table
extraction tries line, text and explicit-edge strategies with bounding-box
deduplication. Single-column text detections are rejected to avoid clipping prose.
Blocks partly overlapping tables retain text not represented by extracted cells.

HWP HTML exports retain nested tables in HWPX/DOCX, validate merge occupancy and
use proportional column widths. HWPX includes stylesheet properties and Markdown
inline runs. DOCX walks text leaves once to preserve mixed plain/styled text
without duplicating nested spans. Repeated PDF image placements are retained,
including small images, with image output in HWPX and Markdown.

`document_structure.quality` reports source-to-preview non-whitespace character
coverage, independently of visual fidelity. It counts character occurrences, not
their order or position. It is not an output-file audit or proof of layout
equivalence. Layout similarity remains null and manual review remains required.
PDF pages without extractable text are listed for OCR review; unsupported or
failed source inspection is unmeasured, never assigned a success percentage.
The converter UI shows measured text coverage and inspection warnings.

No universal 95% or lossless-format guarantee is made. Native HWP5 layout,
scanned/handwritten OCR, arbitrary vectors, embedded fonts, advanced merged PDF
cells and output-level visual comparison still need representative acceptance
fixtures. Markdown and Excel cannot represent every original page-layout feature.

## Conversion Service And Native Lifetimes

The converter router delegates conversion and history to DocumentConversionService.
Blocking work runs in Starlette's thread pool; the service raises ConversionError
and the HTTP boundary maps it to the existing status/detail contract. Legacy
private helper imports remain available through a compatibility lookup. Service
tests patch the service's dependencies rather than globals in the router.
The engine never imports the API: API -> application service -> synthetic_engine.
History writes are atomic and serialized within one process; multi-worker history
coordination still requires a shared store or cross-process lock.

common/bin_finder.py owns pyhwp command discovery. common/com_session.py creates
isolated DispatchEx objects, balances COM apartments and attempts document close
and application quit independently. A newly created process identifiable from
its window handle is assigned to a Windows kill-on-job-close job where possible.
Already-running processes are never assigned or killed by process name. The
native Hancom subprocess uses this same context, including its timeout path.

Forced termination before job assignment, unsupported window handles, or failed
job assignment cannot be fully covered by a Python context manager. Those cases
fall back to normal cleanup and warning logs. Real Office installation/version
coverage is separate from the mocked lifecycle tests; no unconditional leak-free
guarantee is claimed.

PDF privacy editing keeps unrotated edit coordinates and stores rotation-mapped
display rectangles for pixel comparison. Page rotation (90/180/270) and cropped
pages are covered; intrinsically angled target text remains fail-closed. Missing
targets are named in errors rather than silently skipped.

Images fully contained in a known PDF table cell are attached to inline_images
and rendered inside/at that cell in all five outputs. Partially intersecting images
remain standalone. HWPX column rounding puts the residual in the last column so
the sum is exactly the intended width.

## Native HWPX Preservation Verification

Native replacement now edits only affected text slots and preserves untouched
ZIP members byte-for-byte. Replacements are matched against original text and
applied in reverse offset order, including matches across styled runs. Different
replacement lengths no longer truncate suffixes or unrelated text. XML text
controls form search boundaries. The public privacy API retains its existing
equal-length validation policy; variable-length tests exercise the XML editor.

Results are staged until all targets are found and real HWPX packages can be
reopened. Failure leaves an existing destination unchanged. Cached Preview files
are removed to prevent residual PII, along with their container/manifest references;
this is an intentional exception to byte-preservation, not an image-body rewrite.

The native process renders the edited HWPX to PDF for verification but does not
SaveAs the final HWPX. The downloadable package is the directly edited package.

Tests create a real python-hwpx package with mixed-style text, merged cells,
unequal widths and two image placements sharing one resource. They compare image
IDs through the OPF manifest to binary files, ancestor cell addresses, XML paths,
the complete non-text section tree, and unchanged package members after reload.
The application-flow test mocks only Hancom rendering; it is not a claim of
visual validation in every installed Hancom version. Actual native rendering,
font availability and long-text reflow remain deployment acceptance checks.
