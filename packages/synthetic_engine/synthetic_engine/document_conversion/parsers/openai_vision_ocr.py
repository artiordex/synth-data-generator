# -*- coding: utf-8 -*-
"""Optional GPT-4o-mini Vision fallback for low-quality local OCR.

The image parser always runs the local OCR ensemble first. This module is
only called when the local quality gate says that a page needs review. It
keeps a dependency-free HTTP client for the API container.
"""
from __future__ import annotations

import base64
import json
import os
import re
from typing import Any, List, Optional
import urllib.error
import urllib.request


_REFUSAL_PATTERNS = (
    "죄송하지만",
    "이미지를 직접 처리할 수 없습니다",
    "다른 질문이나 요청이 있으시면",
    "도와드리겠습니다",
    "cannot process images",
    "can't process images",
    "unable to process images",
    "i cannot see the image",
    "i can't see the image",
    "i'm sorry",
)


def _vision_model(model_name: Optional[str]) -> str:
    """Return a model that accepts image_url content."""
    configured = (model_name or os.environ.get("OPENAI_OCR_MODEL", "")).strip()
    if not configured:
        return "gpt-4o-mini"
    lowered = configured.lower()
    if any(token in lowered for token in ("gpt-4o", "gpt-4.1", "gpt-4.5")):
        return configured
    # A text-only model in OPENAI_OCR_MODEL used to return a generic refusal.
    return "gpt-4o-mini"


def _message_text(message: Any) -> str:
    """Extract text from classic and multimodal Chat Completions responses."""
    if not isinstance(message, dict):
        return ""
    if message.get("refusal"):
        return str(message["refusal"])
    content = message.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            str(item.get("text", ""))
            for item in content
            if isinstance(item, dict) and item.get("type") in {"text", "output_text"}
        )
    return ""


def _clean_text(content: str) -> List[str]:
    value = str(content or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    value = re.sub(r"^```(?:text|markdown)?\s*\n", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\n```\s*$", "", value).strip()
    if not value:
        return []
    lowered = value.casefold()
    if any(pattern.casefold() in lowered for pattern in _REFUSAL_PATTERNS):
        return []
    paragraphs = re.split(r"\n\s*\n", value)
    return [paragraph.strip() for paragraph in paragraphs if paragraph.strip()]


def _env_int(name: str, default: int) -> int:
    try:
        return max(256, int(os.environ.get(name, str(default))))
    except (TypeError, ValueError):
        return default


def extract_text_with_openai_vision(
    image_bytes: bytes,
    mime_type: str = "image/png",
    model_name: Optional[str] = None,
) -> List[str]:
    """Extract visible text from one image with GPT-4o-mini Vision.

    An empty list means credentials are missing, the model refused, or the
    request failed. The caller then retains local OCR and requests review.
    """
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key or not image_bytes:
        return []

    target_model = _vision_model(model_name)
    b64_image = base64.b64encode(image_bytes).decode("ascii")
    prompt = (
        "첨부된 스캔 이미지를 직접 읽어 OCR하세요. 이미지에 실제로 보이는 한국어·영문·숫자만 "
        "원문 순서와 줄바꿈을 최대한 유지하여 출력하세요. 표는 각 행을 ' | '로 구분하고, "
        "추측·요약·번역·설명·안내 문구는 출력하지 마세요. 읽을 수 없는 문자는 빈칸으로 두고 "
        "거절 문구를 출력하지 마세요."
    )
    payload = {
        "model": target_model,
        "messages": [
            {
                "role": "system",
                "content": "당신은 공공문서 OCR 교정기입니다. 첨부 이미지의 텍스트만 정확히 전사합니다.",
            },
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
            },
        ],
        "temperature": 0.0,
        "max_tokens": _env_int("OPENAI_OCR_MAX_TOKENS", 4096),
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    try:
        request = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        timeout = float(os.environ.get("OPENAI_OCR_TIMEOUT_SEC", "45"))
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response_data = json.loads(response.read().decode("utf-8"))
        choices = response_data.get("choices") or []
        if not choices:
            return []
        content = _message_text((choices[0] or {}).get("message"))
        return _clean_text(content)
    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        TimeoutError,
        OSError,
        ValueError,
        TypeError,
        KeyError,
        IndexError,
        json.JSONDecodeError,
    ):
        return []


__all__ = ["extract_text_with_openai_vision"]
