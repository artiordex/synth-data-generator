# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: parse_gov_document_data.py
# 경로: scripts/parse_gov_document_data.py
# 목적: 공공 기술검토 문서(DOCX, HWPX) 및 XML·JSON 데이터를 파싱하여
#       내포된 XML·JSON 응답 및 파라미터를 표(Table)로 추출하고,
#       'AI친화_고가치_데이터셋_파일데이터용_템플릿.docx' 디자인을 준수하는 표 보고서로 생성하는 CLI 도구
# 작성자: 개발팀
# 작성일: 2026-09-16
# =============================================================================
"""Command-line utility to parse government technical review documents into structured tables and formatted reports."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api" / "src"))
sys.path.insert(0, str(ROOT / "packages" / "synthetic_engine"))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from synthetic_engine.document_conversion.parsers.gov_doc_data_parser import (
    GovDocDataParser,
    render_parsed_report_docx,
)


# 커맨드라인 인자를 파싱하여 공공 문서 및 데이터 파싱을 실행함
def main():
    parser = argparse.ArgumentParser(description="공공 문서(DOCX/HWPX) 및 XML/JSON 표(Table) 자동 파싱 도구")
    parser.add_argument("file_path", help="파싱할 문서 파일 경로 (.docx, .hwpx, .xml, .json)")
    parser.add_argument("--output", "-o", default=None, help="파싱 결과 저장 파일 경로 (미지정시 자동 생성)")
    parser.add_argument("--format", "-f", choices=["console", "docx", "md", "json", "all"], default="console", help="출력 포맷 (기본: console)")

    args = parser.parse_args()
    input_p = Path(args.file_path)

    if not input_p.exists():
        print(f"[오류] 입력 파일을 찾을 수 없습니다: {input_p}")
        sys.exit(1)

    print("==================================================================")
    print(" 공공 문서 및 XML·JSON 표(Table) 파싱 시작")
    print(f" - 입력 파일: {input_p.resolve()} ({input_p.stat().st_size:,} bytes)")
    print(f" - 포맷 모드: {args.format}")
    print("==================================================================")

    # 1. 문서 파싱 실행
    result = GovDocDataParser.parse_file(input_p)

    print(f"\n[파싱 완료 요약]")
    print(f"- 문서 제목: {result.title}")
    print(f"- 원본 형식: {result.format.upper()}")
    print(f"- 추출된 총 표 수: {len(result.all_tables())}개")
    print(f"  - XML/JSON 파싱 데이터 그리드 표: {len(result.payload_data_tables)}개")
    print(f"  - 요청/응답 파라미터 명세 표: {len(result.parameter_tables)}개")
    print(f"  - 서비스/데이터셋 개요 표: {len(result.overview_tables)}개")
    print(f"  - 상세기능(오퍼레이션) 표: {len(result.operation_tables)}개")
    print(f"  - 에러/오류 코드 표: {len(result.error_code_tables)}개")
    print(f"  - 기타 추출 표: {len(result.other_tables)}개\n")

    # 콘솔 출력
    if args.format in ("console", "all"):
        print("------------------------------------------------------------------")
        print(result.to_markdown())
        print("------------------------------------------------------------------")

    # 출력 경로 결정
    base_out = Path(args.output) if args.output else input_p.parent / f"{input_p.stem}_파싱결과"

    # DOCX 내보내기 ('AI친화_고가치_데이터셋_파일데이터용_템플릿.docx' 표준 서식)
    if args.format in ("docx", "all") or (args.output and args.output.endswith(".docx")):
        docx_out = base_out if str(base_out).endswith(".docx") else base_out.with_suffix(".docx")
        render_parsed_report_docx(result, docx_out)

    # 마크다운 내보내기
    if args.format in ("md", "all") or (args.output and args.output.endswith(".md")):
        md_out = base_out if str(base_out).endswith(".md") else base_out.with_suffix(".md")
        md_out.write_text(result.to_markdown(), encoding="utf-8")
        print(f"[성공] 마크다운 표 보고서 저장 완료: {md_out.resolve()}")

    # JSON 내보내기
    if args.format in ("json", "all") or (args.output and args.output.endswith(".json")):
        json_out = base_out if str(base_out).endswith(".json") else base_out.with_suffix(".json")
        json_out.write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[성공] JSON 구조화 표 데이터 저장 완료: {json_out.resolve()}")

    print("\n==================================================================")
    print(" 공공 기술문서 데이터 표 파싱 작업이 완료되었습니다.")
    print("==================================================================")


if __name__ == "__main__":
    main()
