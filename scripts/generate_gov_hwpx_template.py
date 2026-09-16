# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: generate_gov_hwpx_template.py
# 경로: scripts/generate_gov_hwpx_template.py
# 목적: 공공기관 및 공무원 보고서 표준 서식(표 중심 A4 레이아웃)의
#       AI 친화·고가치 데이터셋 가이드 HWPX 파일을 자동 생성하는 소스코드 엔진
# 표준 근거:
#   - [REF-01] 공공데이터의 인공지능 친화적 관리 가이드라인 v1.1 (행정안전부·NIA)
#   - [REF-02] AI 데이터 품질관리 가이드 v4.0 (NIA)
#   - [REF-07] 국가데이터 통합 연계를 위한 데이터 카탈로그 표준 가이드 v1.0
# 작성일: 2026-09-16
# =============================================================================
"""Standalone Generator for Government-Standard AI-Ready Dataset HWPX Guide."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Dict, Optional

# 루트 및 패키지 경로 추가
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api" / "src"))
sys.path.insert(0, str(ROOT / "packages" / "synthetic_engine"))

from synthetic_api.application.services.ai_guide_template import (
    render_template,
    TemplateGuideRequest,
    FieldAnnotation,
)


def get_default_gov_template_metadata() -> Dict[str, Any]:
    """공무원 및 공공기관 보고서용 기본 표준 템플릿 메타데이터 모델 (Canonical Model v2 기반)."""
    return {
        "schema_version": "2.0",
        "data_category": "file",  # file | api
        "format": "csv",
        "root_type": "table",
        "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "byte_size": 1048576,
        "title": "공공 행정 AI 친화 표준 데이터셋",
        "tables": [
            {"name": "TB_PUB_DATA_STD", "row_count": 50000, "col_count": 8}
        ],
        "record_sets": [
            {"name": "주요 공공 업무 레코드셋", "count": 50000}
        ],
        "fields": [
            {
                "path": "연번",
                "types": ["integer"],
                "occurrences": 50000,
                "null_count": 0,
                "empty_count": 0,
                "examples": [1, 2, 3]
            },
            {
                "path": "기관코드",
                "types": ["string"],
                "occurrences": 50000,
                "null_count": 0,
                "empty_count": 0,
                "examples": ["1470000", "1471000"]
            },
            {
                "path": "데이터셋명",
                "types": ["string"],
                "occurrences": 50000,
                "null_count": 0,
                "empty_count": 0,
                "examples": ["의약품 허가 공시 데이터", "식품 안전 시험성적"]
            },
            {
                "path": "기준일자",
                "types": ["string"],
                "occurrences": 50000,
                "null_count": 0,
                "empty_count": 0,
                "examples": ["2026-01-01", "2026-06-30"]
            },
            {
                "path": "분류구분",
                "types": ["string"],
                "occurrences": 50000,
                "null_count": 12,
                "empty_count": 0,
                "examples": ["보건의료", "안전위생"]
            },
            {
                "path": "측정수치",
                "types": ["number"],
                "occurrences": 50000,
                "null_count": 45,
                "empty_count": 0,
                "examples": [98.5, 102.3, 89.1]
            },
            {
                "path": "품질적합여부",
                "types": ["string"],
                "occurrences": 50000,
                "null_count": 0,
                "empty_count": 0,
                "examples": ["Y", "N"]
            },
            {
                "path": "처리상태코드",
                "types": ["string"],
                "occurrences": 50000,
                "null_count": 0,
                "empty_count": 0,
                "examples": ["01", "02"]
            }
        ],
        "quality_metrics": [
            {
                "category": "COMPLETENESS",
                "status": "MEASURED",
                "scope": "전체 50,000행 대상 전수 검사",
                "observed": 399943,
                "missing": 57,
                "score": 99
            },
            {
                "category": "VALIDITY",
                "status": "MEASURED",
                "scope": "표준 데이터 타입 및 날짜 포맷 규칙",
                "score": 100
            },
            {
                "category": "CONSISTENCY",
                "status": "MEASURED",
                "scope": "기관코드-명칭 간 논리적 정합성 검증",
                "score": 100
            },
            {
                "category": "ACCURACY",
                "status": "REVIEW_REQUIRED",
                "scope": "수치 이상치(Outlier) 및 측정 도메인 기준",
                "score": None
            },
            {
                "category": "UNIQUENESS",
                "status": "MEASURED",
                "scope": "복합키 (기관코드 + 연번) 중복 검사",
                "score": 100
            },
            {
                "category": "TIMELINESS",
                "status": "REVIEW_REQUIRED",
                "scope": "공공데이터포털 등록 주기 및 갱신 시점 확인 필요",
                "score": None
            }
        ],
        "warnings": [
            "주의: 측정수치 컬럼에 45건의 결측치가 관측되었습니다. AI 학습 시 결측치 대체(Imputation) 전략 검토가 권장됩니다.",
            "대용량 권고: 데이터가 10만 행 이상으로 확장될 경우 Parquet 압축 포맷 전환을 권장합니다."
        ]
    }


def get_default_gov_institutional_metadata() -> Dict[str, str]:
    """공무원들이 필요로 하는 행정/기관 메타데이터 기본 입력값."""
    return {
        "publisher": "대한민국 식품의약품안전처",
        "description": "공공 행정 업무 자동화 및 AI 친화 데이터 구축을 위한 표준 데이터셋 가이드라인 보고서입니다.",
        "department": "디지털안전정보과",
        "legal_basis": "공공데이터의 제공 및 이용 활성화에 관한 법률 제17조",
        "landing_page": "https://www.data.go.kr",
        "contact": "데이터 담당관 (043-719-0000)",
        "license": "공공누리 제1유형: 출처표시 (상업적 이용 및 변형 가능)",
        "rights": "식품의약품안전처 공공저작물",
        "update_frequency": "반기 (연 2회)",
        "version": "v1.0.0",
        "issued": "2026-01-01",
        "modified": "2026-06-30",
        "temporal": "2026-01-01 ~ 2026-06-30",
        "spatial": "대한민국 전역",
        "source_datasets": "식약처 통합 공공데이터 연계 저장소",
        "transformation": "연번 생성, 식별자 코드 매핑, 결측치 플래그 처리",
        "imputation": "선형 보간 및 최빈값 대체 적용",
        "training_split": "지도학습/분류 모델 (학습:검증:평가 = 70:15:15)",
        "limitations": "특정 기간의 행정 공시 데이터이므로 도메인 외 예측 시 편향 가능성 존재"
    }


def get_default_field_annotations() -> Dict[str, Dict[str, str]]:
    """데이터사전 컬럼별 상세 설명, 단위, 코드 명세."""
    return {
        "연번": {
            "label": "일련번호",
            "description": "레코드 고유 식별 일련번호 (PK)",
            "unit": "무차원 (Sequence)",
            "codes": "1 이상의 정수"
        },
        "기관코드": {
            "label": "행정기관코드",
            "description": "행정표준코드관리시스템 공공기관 코드",
            "unit": "코드",
            "codes": "7자리 숫자코드"
        },
        "데이터셋명": {
            "label": "공시 데이터 명칭",
            "description": "품목허가 및 안전관리 대상 공시 명칭",
            "unit": "문자열",
            "codes": "해당 없음"
        },
        "기준일자": {
            "label": "측정 기준일자",
            "description": "데이터 수집 및 공시 기준일자 (ISO 8601)",
            "unit": "일자 (YYYY-MM-DD)",
            "codes": "정규 날짜 포맷"
        },
        "분류구분": {
            "label": "업무 분류",
            "description": "식품, 의약품, 의료기기 대분류",
            "unit": "범주 (Category)",
            "codes": "보건의료, 안전위생, 품질관리"
        },
        "측정수치": {
            "label": "품질 정량 계측값",
            "description": "실험실 및 현장 표준 계측 수치",
            "unit": "ppm / mg",
            "codes": "수치 (정밀도 소수점 1자리)"
        },
        "품질적합여부": {
            "label": "공식 적합 판정",
            "description": "공공 기준 규격 적합 여부 플래그",
            "unit": "이진 플래그 (Binary)",
            "codes": "Y: 적합, N: 부적합"
        },
        "처리상태코드": {
            "label": "업무 진행상태",
            "description": "행정 처리 단계별 공통 상태 코드",
            "unit": "코드",
            "codes": "01: 접수, 02: 심사, 03: 승인, 04: 반려"
        }
    }


# 공공기관 및 공무원 보고서 표준 HWPX 가이드 문서를 생성함
def create_gov_hwpx_guide(
    canonical_metadata: Optional[Dict[str, Any]] = None,
    institutional_metadata: Optional[Dict[str, str]] = None,
    field_annotations: Optional[Dict[str, Dict[str, str]]] = None,
    output_path: Optional[Path | str] = None,
) -> bytes:
    """공공기관 및 공무원 보고서 표준 HWPX 가이드 문서를 생성하는 핵심 함수.

    Args:
        canonical_metadata: 데이터셋 분석 결과 (None인 경우 기본 표준 템플릿 모델 사용)
        institutional_metadata: 행정/기관 입력 메타데이터 (제공기관, 법령, 담당자 등)
        field_annotations: 데이터사전 상세 설명/단위/코드
        output_path: 저장할 파일 경로 (지정 시 파일로 기록)

    Returns:
        bytes: 생성된 HWPX 바이너리 바이트
    """
    c_meta = canonical_metadata or get_default_gov_template_metadata()
    i_meta = institutional_metadata or get_default_gov_institutional_metadata()
    raw_ann = field_annotations or get_default_field_annotations()

    converted_ann = {
        k: FieldAnnotation(**v) if isinstance(v, dict) else v
        for k, v in raw_ann.items()
    }

    req = TemplateGuideRequest(
        canonical_metadata=c_meta,
        metadata=i_meta,
        field_annotations=converted_ann,
    )

    hwpx_bytes = render_template(req)

    if output_path:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_bytes(hwpx_bytes)
        print(f"[성공] 공공기관용 HWPX 보고서 생성 완료: {out_p.resolve()} ({len(hwpx_bytes):,} bytes)")

    return hwpx_bytes


# 커맨드라인 인자를 파싱하여 공공 표준 HWPX 보고서 생성을 실행함
def main():
    parser = argparse.ArgumentParser(
        description="공공기관 표준 AI 친화·고가치 데이터셋 HWPX 보고서 생성기"
    )
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        default=None,
        help="사용자 정의 JSON 메타데이터 파일 경로 (생략 시 표준 기본 템플릿 사용)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=str(ROOT / "docs" / "adr" / "AI친화_고가치_데이터셋_공공기관용_템플릿.hwpx"),
        help="생성될 HWPX 파일의 저장 경로",
    )
    parser.add_argument(
        "--title",
        "-t",
        type=str,
        default=None,
        help="문서 제목 오버라이드",
    )
    parser.add_argument(
        "--category",
        "-c",
        type=str,
        choices=["file", "api"],
        default=None,
        help="데이터 범주 (file: 파일데이터, api: API데이터)",
    )

    args = parser.parse_args()

    c_meta = None
    i_meta = None
    ann = None

    if args.input:
        in_path = Path(args.input)
        if not in_path.exists():
            print(f"[오류] 입력 파일이 존재하지 않습니다: {in_path}", file=sys.stderr)
            sys.exit(1)
        data = json.loads(in_path.read_text(encoding="utf-8"))
        c_meta = data.get("canonical_metadata") or data
        i_meta = data.get("metadata")
        ann = data.get("field_annotations")

    if args.title and c_meta:
        c_meta["title"] = args.title
    if args.category and c_meta:
        c_meta["data_category"] = args.category

    create_gov_hwpx_guide(
        canonical_metadata=c_meta,
        institutional_metadata=i_meta,
        field_annotations=ann,
        output_path=args.output,
    )


if __name__ == "__main__":
    main()
