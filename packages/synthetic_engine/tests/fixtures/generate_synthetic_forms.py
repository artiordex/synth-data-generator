# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: generate_synthetic_forms.py
# 경로: packages/synthetic_engine/tests/fixtures/generate_synthetic_forms.py
# 목적: 테스트용 합성 서식 문서 생성 도구를 제공함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


# korean 글꼴 작업을 수행함
def _korean_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (
        Path("C:/Windows/Fonts/malgun.ttf"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/truetype/nanum/NanumGothic.ttf"),
    )
    for candidate in candidates:
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


# synthetic public form 데이터를 생성하여 반환함
def generate_synthetic_public_form(seed: int = 20260910) -> tuple[np.ndarray, dict[str, Any]]:
    """Generate a reproducible noisy 5x4 Korean form with spans and controls."""
    rng = np.random.default_rng(seed)
    width, height = 840, 560
    image = np.full((height, width, 3), 255, dtype=np.uint8)
    x_edges = [40, 220, 410, 610, 800]
    y_edges = [40, 120, 210, 300, 390, 500]

    image[y_edges[0]:y_edges[1], x_edges[0]:x_edges[-1]] = (239, 231, 219)
    for x in x_edges:
        cv2.line(image, (x, y_edges[0]), (x, y_edges[-1]), (35, 35, 35), 2)
    for y in y_edges:
        cv2.line(image, (x_edges[0], y), (x_edges[-1], y), (35, 35, 35), 2)
    # Header spans four columns; erase only the three internal header rules.
    for x in x_edges[1:-1]:
        cv2.line(image, (x, y_edges[0] + 2), (x, y_edges[1] - 2), (239, 231, 219), 5)

    canvas = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(canvas)
    font = _korean_font(24)
    labels = [
        ("공공데이터 제공 신청서", (260, 65)),
        ("성명", (65, 150)), ("홍길동", (250, 150)),
        ("생년월일", (435, 150)), ("1990-01-02", (635, 150)),
        ("공개여부", (65, 240)), ("□ 비공개  ■ 공개", (250, 240)),
        ("신청금액", (65, 330)), ("1,250,000원", (250, 330)),
        ("서명", (435, 420)),
    ]
    for text, position in labels:
        draw.text(position, text, fill=(20, 20, 20), font=font)
    image = cv2.cvtColor(np.asarray(canvas), cv2.COLOR_RGB2BGR)

    signature = np.array([[625, 455], [650, 430], [675, 468], [705, 425], [750, 460]], np.int32)
    cv2.polylines(image, [signature], False, (0, 0, 0), 3)
    noise = rng.normal(0, 2.2, image.shape).astype(np.int16)
    image = np.clip(image.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    image = cv2.GaussianBlur(image, (3, 3), 0.35)

    metadata = {
        "rows": 5,
        "cols": 4,
        "header_span": (0, 0, 1, 4),
        "x_edges": x_edges,
        "y_edges": y_edges,
        "seed": seed,
    }
    return image, metadata


if __name__ == "__main__":
    fixture, _ = generate_synthetic_public_form()
    cv2.imwrite(str(Path(__file__).with_name("synthetic_public_form.png")), fixture)
