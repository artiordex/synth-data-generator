# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: openai_vision_ocr.py
# 경로: packages/synthetic_engine/synthetic_engine/document_conversion/parsers/openai_vision_ocr.py
# 목적: OpenAI GPT-4o Vision API를 활용하여 스캔 이미지의 한글 텍스트 및 문단을 초고정밀 추출함
# 작성자: 개발팀
# 작성일: 2026-09-16
# 수정일: 2026-09-16
# =============================================================================
"""OpenAI Vision API client for high-accuracy scanned image OCR."""
from __future__ import annotations

import base64
import json
import os
import re
from typing import List, Optional
import urllib.error
import urllib.request


# OpenAI Vision 모델을 통해 이미지 바이트로부터 정제된 텍스트 문단 목록을 추출함
def extract_text_with_openai_vision(
    image_bytes: bytes,
    mime_type: str = "image/png",
    model_name: Optional[str] = None,
) -> List[str]:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        return []

    target_model = model_name or os.environ.get("OPENAI_OCR_MODEL", "gpt-4o-mini")
    b64_image = base64.b64encode(image_bytes).decode("ascii")

    prompt = (
        "이미지에 포함된 모든 한글 및 영문 텍스트를 원본 이미지의 문맥과 어순에 맞추어 정확하게 추출하시오.\n"
        "- 문단과 줄바꿈 구조를 유지할 것.\n"
        "- 문맥상 자연스러운 한글 표준 맞춤법을 준수하여 오탈자 없이 복원할 것.\n"
        "- 설명, 부연, 안내 문구 일체 없이 오직 추출된 본문 텍스트만 출력할 것."
    )

    payload = {
        "model": target_model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{b64_image}",
                            "detail": "high",
                        },
                    },
                ],
            }
        ],
        "temperature": 0.0,
        "max_tokens": 4096,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
        )
        with urllib.request.urlopen(req, timeout=45) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            content = res_data["choices"][0]["message"]["content"].strip()
            # 마크다운 코드 블록 제거 처리함
            content = re.sub(r"^```[a-zA-Z]*\n", "", content)
            content = re.sub(r"\n```$", "", content).strip()
            # 빈 줄 기준으로 문단 분할함
            raw_paragraphs = re.split(r"\n{2,}", content)
            cleaned = [p.strip() for p in raw_paragraphs if p.strip()]
            return cleaned
    except (urllib.error.URLError, urllib.error.HTTPError, KeyError, IndexError, json.JSONDecodeError):
        # OpenAI 호출 실패 시 빈 목록을 반환하여 로컬 파이프라인으로 안전하게 폴백함
        return []
