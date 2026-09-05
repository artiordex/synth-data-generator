# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
import sys
import uuid
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from synthetic_api.core.config import settings
from synthetic_api.application.services.dataset_service import DatasetService
from synthetic_engine.profiling.analyzer import read_table

router = APIRouter(prefix="/converter", tags=["converter"])


def _convert_word_to_pdf(input_path: Path, output_path: Path) -> None:
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    word = None
    doc = None
    try:
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        doc = word.Documents.Open(str(input_path.resolve()))
        doc.SaveAs(str(output_path.resolve()), FileFormat=17)  # 17 = wdFormatPDF
    finally:
        if doc is not None:
            try:
                doc.Close(False)
            except Exception:
                pass
        if word is not None:
            try:
                word.Quit()
            except Exception:
                pass
        pythoncom.CoUninitialize()


def _convert_hwp_doc(input_path: Path, output_path: Path, target_fmt: str) -> None:
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    hwp = None
    try:
        hwp = win32com.client.Dispatch("HWPFrame.HwpObject")
        try:
            hwp.XHwpWindows.Item(0).Visible = False
        except Exception:
            pass
        try:
            hwp.RegisterModule("FilePathCheckDLL", "FilePathCheckerModule")
        except Exception:
            pass

        opened = hwp.Open(str(input_path.resolve()))
        if not opened:
            raise RuntimeError("한글 문서를 열 수 없습니다. 파일이 손상되었거나 암호가 설정되어 있을 수 있습니다.")

        fmt_arg = "PDF" if target_fmt.lower() == "pdf" else ("HTML" if target_fmt.lower() == "html" else "HWPX")
        saved = hwp.SaveAs(str(output_path.resolve()), fmt_arg, "")
        if not saved or not output_path.exists():
            raise RuntimeError(f"한글 문서를 {fmt_arg} 형식으로 저장하지 못했습니다.")
    finally:
        if hwp is not None:
            try:
                hwp.Clear(1)
            except Exception:
                pass
            try:
                hwp.Quit()
            except Exception:
                pass
        pythoncom.CoUninitialize()


def _convert_docx_to_markdown(input_path: Path) -> str:
    """Convert DOCX file to Markdown preserving headings, lists, and tables."""
    try:
        import docx
        doc = docx.Document(input_path)
        md_lines: List[str] = []

        for p in doc.paragraphs:
            text = p.text.strip()
            if not text:
                continue
            style_name = p.style.name.lower() if p.style and p.style.name else ""
            if "heading 1" in style_name:
                md_lines.append(f"# {text}\n")
            elif "heading 2" in style_name:
                md_lines.append(f"## {text}\n")
            elif "heading 3" in style_name:
                md_lines.append(f"### {text}\n")
            elif "list" in style_name or "bullet" in style_name:
                md_lines.append(f"- {text}")
            else:
                md_lines.append(f"{text}\n")

        for table in doc.tables:
            t_rows = []
            col_count = 0
            for r_idx, row in enumerate(table.rows):
                cells = [c.text.strip().replace("\n", " ").replace("|", "/") for c in row.cells]
                if cells:
                    col_count = max(col_count, len(cells))
                    t_rows.append("| " + " | ".join(cells) + " |")
                    if r_idx == 0:
                        t_rows.append("| " + " | ".join(["---"] * len(cells)) + " |")
            if t_rows:
                md_lines.append("\n" + "\n".join(t_rows) + "\n")

        return "\n".join(md_lines).strip()
    except Exception as exc:
        raise RuntimeError(f"Word 마크다운 변환 실패: {str(exc)}")


def _convert_hwp_to_markdown(input_path: Path) -> str:
    """Convert HWP file to Markdown via Hwp COM HTML export and BeautifulSoup parser."""
    import pythoncom
    import win32com.client
    from bs4 import BeautifulSoup
    import tempfile

    pythoncom.CoInitialize()
    hwp = None
    try:
        hwp = win32com.client.Dispatch("HWPFrame.HwpObject")
        try:
            hwp.XHwpWindows.Item(0).Visible = False
        except Exception:
            pass
        try:
            hwp.RegisterModule("FilePathCheckDLL", "FilePathCheckerModule")
        except Exception:
            pass

        opened = hwp.Open(str(input_path.resolve()))
        if not opened:
            raise RuntimeError("한글 문서를 열 수 없습니다.")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_html = Path(tmpdir) / "temp_hwp.html"
            hwp.SaveAs(str(tmp_html.resolve()), "HTML", "")
            
            if not tmp_html.exists():
                raise RuntimeError("한글 문서 HTML 임시 내보내기에 실패했습니다.")

            # Try reading with euc-kr then utf-8
            raw_bytes = tmp_html.read_bytes()
            for enc in ("euc-kr", "cp949", "utf-8"):
                try:
                    html_content = raw_bytes.decode(enc)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                html_content = raw_bytes.decode("euc-kr", errors="ignore")

            soup = BeautifulSoup(html_content, "html.parser")
            lines: List[str] = []

            for el in soup.find_all(["h1", "h2", "h3", "h4", "p", "table", "ul", "ol"]):
                if el.name in ("h1", "h2", "h3", "h4"):
                    level = int(el.name[1])
                    lines.append("#" * level + " " + el.get_text(strip=True) + "\n")
                elif el.name == "p":
                    t = el.get_text(strip=True)
                    if t:
                        lines.append(t + "\n")
                elif el.name in ("ul", "ol"):
                    for li in el.find_all("li"):
                        lines.append(f"- {li.get_text(strip=True)}")
                    lines.append("")
                elif el.name == "table":
                    rows = el.find_all("tr")
                    t_rows = []
                    for idx, r in enumerate(rows):
                        cells = [c.get_text(strip=True).replace("\n", " ").replace("|", "/") for c in r.find_all(["th", "td"])]
                        if cells:
                            t_rows.append("| " + " | ".join(cells) + " |")
                            if idx == 0:
                                t_rows.append("| " + " | ".join(["---"] * len(cells)) + " |")
                    if t_rows:
                        lines.append("\n" + "\n".join(t_rows) + "\n")

            return "\n".join(lines).strip()
    finally:
        if hwp is not None:
            try:
                hwp.Clear(1)
            except Exception:
                pass
            try:
                hwp.Quit()
            except Exception:
                pass
        pythoncom.CoUninitialize()


def _convert_hwpx_to_markdown(input_path: Path) -> str:
    """Convert HWPX file to Markdown by parsing internal section XML and text."""
    try:
        lines: List[str] = []
        with zipfile.ZipFile(input_path, "r") as zf:
            # Check for section xmls
            section_names = [n for n in zf.namelist() if "section" in n.lower() and n.endswith(".xml")]
            if section_names:
                for s_name in sorted(section_names):
                    xml_data = zf.read(s_name)
                    root = ET.fromstring(xml_data)
                    hp_ns = {"hp": "http://www.hancom.co.kr/hwpml/2011/paragraph"}
                    for p in root.findall(".//hp:p", hp_ns):
                        p_texts = [t.text for t in p.findall(".//hp:t", hp_ns) if t.text]
                        if p_texts:
                            lines.append("".join(p_texts) + "\n")
                    for tbl in root.findall(".//hp:tbl", hp_ns):
                        t_rows = []
                        for r_idx, tr in enumerate(tbl.findall(".//hp:tr", hp_ns)):
                            cells = []
                            for tc in tr.findall(".//hp:tc", hp_ns):
                                c_texts = [t.text for t in tc.findall(".//hp:t", hp_ns) if t.text]
                                cells.append(" ".join(c_texts).replace("|", "/"))
                            if cells:
                                t_rows.append("| " + " | ".join(cells) + " |")
                                if r_idx == 0:
                                    t_rows.append("| " + " | ".join(["---"] * len(cells)) + " |")
                        if t_rows:
                            lines.append("\n" + "\n".join(t_rows) + "\n")
            elif "Preview/PrvText.txt" in zf.namelist():
                txt = zf.read("Preview/PrvText.txt").decode("utf-16", errors="ignore")
                lines.append(txt)

        return "\n".join(lines).strip()
    except Exception as exc:
        raise RuntimeError(f"HWPX 마크다운 파싱 실패: {str(exc)}")


def _convert_pdf_to_markdown(input_path: Path) -> str:
    """Convert PDF to Markdown page by page using pypdf."""
    import pypdf
    try:
        reader = pypdf.PdfReader(str(input_path.resolve()))
        pages_md: List[str] = []
        for idx, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            if text.strip():
                pages_md.append(f"## Page {idx + 1}\n\n{text.strip()}\n")
        if not pages_md:
            return "PDF에서 추출 가능한 텍스트가 없습니다 (스캔 이미지 PDF일 수 있습니다)."
        return "\n---\n\n".join(pages_md)
    except Exception as exc:
        raise RuntimeError(f"PDF 텍스트/마크다운 변환 실패: {str(exc)}")


def _dataframe_to_markdown(df, limit: int = 500) -> str:
    """Convert dataframe to GitHub Flavored Markdown table with safe pure-python fallback."""
    sample = df.head(limit)
    try:
        import tabulate  # noqa: F401
        return sample.to_markdown(index=False)
    except Exception:
        # Resilient pure-Python GFM markdown table generator
        cols = [str(c) for c in sample.columns]
        header_row = "| " + " | ".join(cols) + " |"
        sep_row = "| " + " | ".join(["---"] * len(cols)) + " |"
        rows = []
        for _, row in sample.iterrows():
            cells = [
                str(v if v is not None and not (isinstance(v, float) and v != v) else "")
                .replace("\r", "")
                .replace("\n", " ")
                .replace("|", "\\|")
                for v in row
            ]
            rows.append("| " + " | ".join(cells) + " |")
        return "\n".join([header_row, sep_row] + rows)


def _wrap_html_page(title: str, body_html: str, filename: str, is_table: bool = False) -> str:
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    table_search_block = """
    <div style="margin-bottom: 1.25rem; display: flex; align-items: center; gap: 0.75rem;">
      <input type="text" id="tableFilter" onkeyup="filterTable()" placeholder="표 내용 실시간 검색..." style="padding: 0.5rem 0.85rem; border: 1px solid var(--border-color); border-radius: 6px; background: var(--card-bg); color: var(--text-main); width: 280px; font-size: 0.875rem;">
      <span id="rowCount" style="font-size: 0.85rem; color: var(--text-sub);"></span>
    </div>
    <script>
      function filterTable() {
        const input = document.getElementById("tableFilter");
        const filter = input.value.toLowerCase();
        const table = document.querySelector("table");
        if (!table) return;
        const rows = table.querySelectorAll("tbody tr");
        let visibleCount = 0;
        rows.forEach(r => {
          const match = r.textContent.toLowerCase().includes(filter);
          r.style.display = match ? "" : "none";
          if (match) visibleCount++;
        });
        const cntElem = document.getElementById("rowCount");
        if (cntElem) {
          cntElem.textContent = filter ? `${visibleCount} / ${rows.length}행 표시 중` : `${rows.length}행`;
        }
      }
      document.addEventListener("DOMContentLoaded", () => {
        const table = document.querySelector("table");
        if (table) {
          const cntElem = document.getElementById("rowCount");
          const rows = table.querySelectorAll("tbody tr");
          if (cntElem) cntElem.textContent = `총 ${rows.length}행`;
        }
      });
    </script>
    """ if is_table else ""

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>
    :root {{
      --bg-color: #f8fafc;
      --card-bg: #ffffff;
      --text-main: #0f172a;
      --text-sub: #64748b;
      --border-color: #e2e8f0;
      --primary: #2563eb;
      --table-stripe: #f8fafc;
      --table-hover: #f1f5f9;
    }}
    @media (prefers-color-scheme: dark) {{
      :root {{
        --bg-color: #0b0f17;
        --card-bg: #131b2e;
        --text-main: #f1f5f9;
        --text-sub: #94a3b8;
        --border-color: #1e293b;
        --primary: #3b82f6;
        --table-stripe: #172138;
        --table-hover: #1f2d4d;
      }}
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Pretendard", sans-serif;
      background-color: var(--bg-color);
      color: var(--text-main);
      line-height: 1.65;
      padding: 2.5rem 1.5rem;
    }}
    .container {{
      max-width: 1040px;
      margin: 0 auto;
      background: var(--card-bg);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      padding: 2.5rem;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
    }}
    .doc-header {{
      border-bottom: 1px solid var(--border-color);
      padding-bottom: 1.25rem;
      margin-bottom: 2rem;
    }}
    .doc-title {{ font-size: 1.5rem; font-weight: 700; }}
    .doc-meta {{ font-size: 0.875rem; color: var(--text-sub); margin-top: 0.35rem; }}
    h1, h2, h3, h4, h5, h6 {{ margin-top: 1.75rem; margin-bottom: 0.75rem; font-weight: 600; line-height: 1.3; }}
    h1 {{ font-size: 1.875rem; border-bottom: 1px solid var(--border-color); padding-bottom: 0.5rem; }}
    h2 {{ font-size: 1.5rem; }}
    h3 {{ font-size: 1.25rem; }}
    p {{ margin-bottom: 1rem; }}
    ul, ol {{ margin-bottom: 1.25rem; padding-left: 1.75rem; }}
    li {{ margin-bottom: 0.4rem; }}
    .table-container {{
      width: 100%;
      overflow-x: auto;
      border: 1px solid var(--border-color);
      border-radius: 8px;
      margin: 1.25rem 0;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 0;
      font-size: 0.9rem;
    }}
    th, td {{
      border: 1px solid var(--border-color);
      padding: 0.65rem 0.9rem;
      text-align: left;
    }}
    th {{
      background-color: var(--table-stripe);
      font-weight: 600;
      white-space: nowrap;
    }}
    tr:nth-child(even) td {{
      background-color: var(--table-stripe);
    }}
    tr:hover td {{
      background-color: var(--table-hover);
    }}
    pre, code {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 0.875rem;
    }}
    code {{
      background: var(--table-stripe);
      padding: 0.15rem 0.35rem;
      border-radius: 4px;
      border: 1px solid var(--border-color);
    }}
    pre code {{
      border: none;
      padding: 0;
    }}
    pre {{
      background: var(--table-stripe);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 1rem;
      overflow-x: auto;
      margin: 1.25rem 0;
    }}
    blockquote {{
      border-left: 4px solid var(--primary);
      padding-left: 1rem;
      color: var(--text-sub);
      margin: 1.25rem 0;
    }}
    hr {{
      border: none;
      border-top: 1px solid var(--border-color);
      margin: 2rem 0;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="doc-header">
      <div class="doc-title">{title}</div>
      <div class="doc-meta">생성 일시: {created_at} | 원본 파일: {filename}</div>
    </div>
    {table_search_block}
    <div class="doc-body">
      {body_html}
    </div>
  </div>
</body>
</html>
"""


def _convert_docx_to_html(input_path: Path) -> str:
    """Convert DOCX to clean HTML using mammoth or fallback via markdown."""
    try:
        import mammoth
        with open(input_path, "rb") as docx_file:
            res = mammoth.convert_to_html(docx_file)
            return res.value
    except Exception:
        md = _convert_docx_to_markdown(input_path)
        try:
            import markdown
            return markdown.markdown(md, extensions=["tables", "fenced_code", "nl2br"])
        except Exception:
            return f"<pre>{md}</pre>"


def _convert_word_to_html(input_path: Path, output_path: Path) -> None:
    """Convert Word DOC/DOCX to HTML."""
    if input_path.suffix.lower() == ".docx":
        body = _convert_docx_to_html(input_path)
        full_html = _wrap_html_page(input_path.stem, body, input_path.name)
        output_path.write_text(full_html, encoding="utf-8")
        return

    # For legacy .doc: Use Word COM if possible, else text fallback
    try:
        import pythoncom
        import win32com.client

        pythoncom.CoInitialize()
        word = None
        doc = None
        try:
            word = win32com.client.Dispatch("Word.Application")
            word.Visible = False
            doc = word.Documents.Open(str(input_path.resolve()))
            doc.SaveAs(str(output_path.resolve()), FileFormat=8)  # 8 = wdFormatHTML
        finally:
            if doc is not None:
                try:
                    doc.Close(False)
                except Exception:
                    pass
            if word is not None:
                try:
                    word.Quit()
                except Exception:
                    pass
            pythoncom.CoUninitialize()
    except Exception:
        md = _convert_docx_to_markdown(input_path)
        import markdown
        body = markdown.markdown(md, extensions=["tables", "fenced_code", "nl2br"])
        full_html = _wrap_html_page(input_path.stem, body, input_path.name)
        output_path.write_text(full_html, encoding="utf-8")


def _convert_hwp_to_html(input_path: Path, output_path: Path) -> None:
    """Convert HWP/HWPX to HTML."""
    try:
        _convert_hwp_doc(input_path, output_path, "html")
        if output_path.exists() and output_path.stat().st_size > 0:
            return
    except Exception:
        pass

    # Fallback via Markdown -> HTML
    if input_path.suffix.lower() == ".hwp":
        md = _convert_hwp_to_markdown(input_path)
    else:
        md = _convert_hwpx_to_markdown(input_path)

    try:
        import markdown
        body = markdown.markdown(md, extensions=["tables", "fenced_code", "nl2br"])
    except Exception:
        body = f"<pre>{md}</pre>"
    full_html = _wrap_html_page(input_path.stem, body, input_path.name)
    output_path.write_text(full_html, encoding="utf-8")


def _convert_markdown_to_html(input_path: Path) -> str:
    """Convert Markdown to HTML."""
    raw_md = input_path.read_text(encoding="utf-8", errors="ignore")
    try:
        import markdown
        return markdown.markdown(raw_md, extensions=["tables", "fenced_code", "nl2br"])
    except Exception:
        return f"<pre>{raw_md}</pre>"


def _convert_pdf_to_html(input_path: Path) -> str:
    """Convert PDF to HTML."""
    md = _convert_pdf_to_markdown(input_path)
    try:
        import markdown
        return markdown.markdown(md, extensions=["tables", "fenced_code", "nl2br"])
    except Exception:
        return f"<pre>{md}</pre>"


@router.post("/convert")
async def convert_file(
    file: UploadFile = File(...),
    target_format: str = Form(...),
    encoding: Optional[str] = Form("utf-8"),
    table_name: Optional[str] = Form("converted_data"),
):
    """
    Convert datasets (CSV, XLSX, TSV, JSON, Parquet, SQL, Markdown) or documents (HWP, HWPX, DOCX, PDF -> PDF, HWPX, MD, TXT, HTML).
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="파일명이 필요합니다.")

    conv_dir = settings.OUTPUT_DIR / "converted"
    conv_dir.mkdir(parents=True, exist_ok=True)

    uid = uuid.uuid4().hex[:8]
    raw_ext = Path(file.filename).suffix.lower()
    stem = Path(file.filename).stem
    target_fmt = target_format.lower().strip()

    # 1. Save uploaded file
    try:
        saved_info = DatasetService.save_upload_file(file.file, file.filename, unique=True)
        src_path = Path(saved_info["path"])
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"파일 업로드 실패: {str(exc)}")
    finally:
        file.file.close()

    doc_exts = {".hwp", ".hwpx", ".doc", ".docx", ".pdf", ".md"}
    data_exts = {".csv", ".xlsx", ".xls", ".tsv", ".txt", ".json", ".jsonl", ".parquet", ".pq"}

    # 2. Document Conversion branch
    if raw_ext in doc_exts:
        # A. Markdown Conversion (.md)
        if target_fmt in ("md", "markdown"):
            out_name = f"{stem}_{uid}.md"
            out_path = conv_dir / out_name

            if raw_ext in (".docx", ".doc"):
                md_text = _convert_docx_to_markdown(src_path)
            elif raw_ext == ".hwpx":
                md_text = _convert_hwpx_to_markdown(src_path)
            elif raw_ext == ".hwp":
                md_text = _convert_hwp_to_markdown(src_path)
            elif raw_ext == ".pdf":
                md_text = _convert_pdf_to_markdown(src_path)
            elif raw_ext == ".md":
                md_text = src_path.read_text(encoding="utf-8", errors="ignore")
            else:
                raise HTTPException(status_code=400, detail=f"{raw_ext} 마크다운 변환을 지원하지 않습니다.")

            out_path.write_text(md_text, encoding="utf-8")
            download_url = f"/api/v1/files/download?path={out_path.as_posix()}"
            file_size = out_path.stat().st_size

            entry = {
                "id": uid,
                "category": "document",
                "original_filename": file.filename,
                "output_filename": out_name,
                "source_format": raw_ext.replace(".", "").upper(),
                "target_format": "MD",
                "file_size": file_size,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "download_url": download_url,
            }
            _record_history(conv_dir, entry)

            return {
                "status": "success",
                "category": "document",
                "file_name": out_name,
                "original_filename": file.filename,
                "download_url": download_url,
                "file_size": file_size,
                "source_format": raw_ext.replace(".", "").upper(),
                "target_format": "MD",
                "markdown_preview": md_text[:5000],
                "message": f"{file.filename} 파일이 마크다운(.md)으로 성공적으로 변환되었습니다."
            }

        # B. Pure Text Conversion (.txt)
        elif target_fmt == "txt":
            out_name = f"{stem}_{uid}.txt"
            out_path = conv_dir / out_name
            if raw_ext in (".docx", ".doc"):
                txt = _convert_docx_to_markdown(src_path)
            elif raw_ext == ".hwp":
                txt = _convert_hwp_to_markdown(src_path)
            elif raw_ext == ".hwpx":
                txt = _convert_hwpx_to_markdown(src_path)
            elif raw_ext == ".pdf":
                txt = _convert_pdf_to_markdown(src_path)
            else:
                txt = src_path.read_text(encoding="utf-8", errors="ignore")

            out_path.write_text(txt, encoding="utf-8")
            download_url = f"/api/v1/files/download?path={out_path.as_posix()}"
            file_size = out_path.stat().st_size
            return {
                "status": "success",
                "category": "document",
                "file_name": out_name,
                "original_filename": file.filename,
                "download_url": download_url,
                "file_size": file_size,
                "source_format": raw_ext.replace(".", "").upper(),
                "target_format": "TXT",
                "markdown_preview": txt[:5000],
                "message": f"{file.filename} 텍스트 추출 완료."
            }

        # C. PDF Conversion
        elif target_fmt == "pdf":
            out_name = f"{stem}_{uid}.pdf"
            out_path = conv_dir / out_name
            try:
                if raw_ext in (".doc", ".docx"):
                    _convert_word_to_pdf(src_path, out_path)
                elif raw_ext in (".hwp", ".hwpx"):
                    _convert_hwp_doc(src_path, out_path, "pdf")
                else:
                    raise HTTPException(status_code=400, detail=f"{raw_ext} PDF 변환을 지원하지 않습니다.")
            except Exception as exc:
                raise HTTPException(status_code=500, detail=f"PDF 변환 실패: {str(exc)}")

            download_url = f"/api/v1/files/download?path={out_path.as_posix()}"
            file_size = out_path.stat().st_size
            return {
                "status": "success",
                "category": "document",
                "file_name": out_name,
                "original_filename": file.filename,
                "download_url": download_url,
                "file_size": file_size,
                "source_format": raw_ext.replace(".", "").upper(),
                "target_format": "PDF",
                "message": f"{file.filename} 고해상도 PDF 변환 완료."
            }

        # D. HWPX Conversion
        elif target_fmt == "hwpx":
            out_name = f"{stem}_{uid}.hwpx"
            out_path = conv_dir / out_name
            try:
                if raw_ext == ".hwp":
                    _convert_hwp_doc(src_path, out_path, "hwpx")
                else:
                    raise HTTPException(status_code=400, detail="HWPX 변환은 구형 HWP 파일만 지원합니다.")
            except Exception as exc:
                raise HTTPException(status_code=500, detail=f"HWPX 변환 실패: {str(exc)}")

            download_url = f"/api/v1/files/download?path={out_path.as_posix()}"
            file_size = out_path.stat().st_size
            return {
                "status": "success",
                "category": "document",
                "file_name": out_name,
                "original_filename": file.filename,
                "download_url": download_url,
                "file_size": file_size,
                "source_format": raw_ext.replace(".", "").upper(),
                "target_format": "HWPX",
                "message": f"{file.filename} 개방형 HWPX 변환 완료."
            }

        # E. HTML Web Document Conversion (.html)
        elif target_fmt in ("html", "htm"):
            out_name = f"{stem}_{uid}.html"
            out_path = conv_dir / out_name
            try:
                if raw_ext in (".docx", ".doc"):
                    _convert_word_to_html(src_path, out_path)
                elif raw_ext in (".hwp", ".hwpx"):
                    _convert_hwp_to_html(src_path, out_path)
                elif raw_ext == ".pdf":
                    body = _convert_pdf_to_html(src_path)
                    full_html = _wrap_html_page(stem, body, file.filename)
                    out_path.write_text(full_html, encoding="utf-8")
                elif raw_ext == ".md":
                    body = _convert_markdown_to_html(src_path)
                    full_html = _wrap_html_page(stem, body, file.filename)
                    out_path.write_text(full_html, encoding="utf-8")
                else:
                    raise HTTPException(status_code=400, detail=f"{raw_ext} HTML 변환을 지원하지 않습니다.")
            except Exception as exc:
                raise HTTPException(status_code=500, detail=f"HTML 변환 실패: {str(exc)}")

            download_url = f"/api/v1/files/download?path={out_path.as_posix()}"
            file_size = out_path.stat().st_size
            html_content = out_path.read_text(encoding="utf-8", errors="ignore")

            entry = {
                "id": uid,
                "category": "document",
                "original_filename": file.filename,
                "output_filename": out_name,
                "source_format": raw_ext.replace(".", "").upper(),
                "target_format": "HTML",
                "file_size": file_size,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "download_url": download_url,
            }
            _record_history(conv_dir, entry)

            return {
                "status": "success",
                "category": "document",
                "file_name": out_name,
                "original_filename": file.filename,
                "download_url": download_url,
                "file_size": file_size,
                "source_format": raw_ext.replace(".", "").upper(),
                "target_format": "HTML",
                "html_preview": html_content[:25000],
                "message": f"{file.filename} 파일이 반응형 HTML 웹 문서로 성공적으로 변환되었습니다."
            }
        else:
            raise HTTPException(
                status_code=400,
                detail=f"문서 파일({raw_ext})은 'html', 'pdf', 'hwpx', 'md', 'txt' 형식으로 변환할 수 있습니다."
            )

    # 3. Tabular Dataset Conversion branch
    elif raw_ext in data_exts:
        try:
            df = read_table(src_path)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"데이터셋 파싱 실패: {str(exc)}")

        clean_table = "".join(c for c in (table_name or "converted_data") if c.isalnum() or c in ("_", "-")) or "converted_data"
        md_preview_text = None
        html_preview_text = None

        try:
            if target_fmt in ("md", "markdown"):
                out_name = f"{stem}_{uid}.md"
                out_path = conv_dir / out_name
                # Convert up to 500 rows to markdown table
                md_preview_text = _dataframe_to_markdown(df, limit=500)
                header_comment = f"<!-- Converted from {file.filename} ({len(df):,} rows, {len(df.columns)} columns) -->\n\n"
                out_path.write_text(header_comment + md_preview_text, encoding="utf-8")
            elif target_fmt in ("html", "htm"):
                out_name = f"{stem}_{uid}.html"
                out_path = conv_dir / out_name
                # Convert dataset to styled HTML table with live search
                sample_df = df.head(1000)
                table_raw_html = sample_df.to_html(classes="dataframe styled-table", index=False, border=0)
                table_wrapper = f'<div class="table-container">{table_raw_html}</div>'
                full_html = _wrap_html_page(
                    title=f"{clean_table} 데이터 테이블",
                    body_html=table_wrapper,
                    filename=file.filename,
                    is_table=True
                )
                out_path.write_text(full_html, encoding="utf-8")
                html_preview_text = full_html[:25000]
            elif target_fmt == "csv":
                out_name = f"{stem}_{uid}.csv"
                out_path = conv_dir / out_name
                df.to_csv(out_path, index=False, encoding="utf-8-sig")
            elif target_fmt in ("xlsx", "xls"):
                out_name = f"{stem}_{uid}.xlsx"
                out_path = conv_dir / out_name
                df.to_excel(out_path, index=False)
            elif target_fmt == "tsv":
                out_name = f"{stem}_{uid}.tsv"
                out_path = conv_dir / out_name
                df.to_csv(out_path, sep="\t", index=False, encoding="utf-8-sig")
            elif target_fmt == "json":
                out_name = f"{stem}_{uid}.json"
                out_path = conv_dir / out_name
                df.to_json(out_path, orient="records", force_ascii=False, indent=2)
            elif target_fmt == "jsonl":
                out_name = f"{stem}_{uid}.jsonl"
                out_path = conv_dir / out_name
                df.to_json(out_path, orient="records", lines=True, force_ascii=False)
            elif target_fmt in ("parquet", "pq"):
                out_name = f"{stem}_{uid}.parquet"
                out_path = conv_dir / out_name
                df.to_parquet(out_path, index=False)
            elif target_fmt == "sql":
                out_name = f"{stem}_{uid}.sql"
                out_path = conv_dir / out_name
                from synthetic_engine.generators.dummy.dummy_generator import DummyDataGenerator
                sql_content = DummyDataGenerator.to_sql_insert(df, table_name=clean_table, limit=min(len(df), 50000))
                out_path.write_text(sql_content, encoding="utf-8")
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"지원하지 않는 대상 데이터 포맷입니다: {target_fmt}"
                )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"데이터 변환 처리 실패: {str(exc)}")

        download_url = f"/api/v1/files/download?path={out_path.as_posix()}"
        file_size = out_path.stat().st_size
        preview_records = df.head(15).fillna("").to_dict(orient="records")

        entry = {
            "id": uid,
            "category": "dataset",
            "original_filename": file.filename,
            "output_filename": out_name,
            "source_format": raw_ext.replace(".", "").upper(),
            "target_format": target_fmt.upper(),
            "file_size": file_size,
            "rows_count": len(df),
            "columns_count": len(df.columns),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "download_url": download_url,
        }
        _record_history(conv_dir, entry)

        return {
            "status": "success",
            "category": "dataset",
            "file_name": out_name,
            "original_filename": file.filename,
            "download_url": download_url,
            "file_size": file_size,
            "source_format": raw_ext.replace(".", "").upper(),
            "target_format": target_fmt.upper(),
            "rows_count": len(df),
            "columns_count": len(df.columns),
            "columns": list(df.columns),
            "preview": preview_records,
            "markdown_preview": md_preview_text,
            "html_preview": html_preview_text,
            "message": f"{file.filename} ({len(df):,}행)이 {target_fmt.upper()} 포맷으로 성공적으로 변환되었습니다."
        }

    else:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 파일 형식입니다: {raw_ext}. 지원 형식: CSV, XLSX, TSV, JSON, Parquet, HWP, HWPX, DOCX, PDF, MD"
        )


@router.get("/history")
async def get_converter_history():
    conv_dir = settings.OUTPUT_DIR / "converted"
    hist_file = conv_dir / "converter_history.json"
    if not hist_file.exists():
        return []
    try:
        with hist_file.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _record_history(conv_dir: Path, entry: Dict[str, Any]) -> None:
    hist_file = conv_dir / "converter_history.json"
    hist_list = []
    if hist_file.exists():
        try:
            with hist_file.open("r", encoding="utf-8") as f:
                hist_list = json.load(f)
        except Exception:
            hist_list = []
    hist_list.insert(0, entry)
    hist_list = hist_list[:50]
    try:
        with hist_file.open("w", encoding="utf-8") as f:
            json.dump(hist_list, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
