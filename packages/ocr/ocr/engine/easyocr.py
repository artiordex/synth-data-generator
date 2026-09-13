# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: easyocr.py
# 경로: packages/ocr/ocr/engine/easyocr.py
# 목적: EasyOCR 엔진 기반 텍스트 인식 어댑터를 제공함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Optional offline EasyOCR adapter with workspace-contained model paths."""

from __future__ import annotations

from dataclasses import replace
from math import ceil, floor, isfinite
from pathlib import Path
from typing import Any

from .base import OCRBackend, OCREngineUnavailable, crop_region
from ..pipeline.models import (
    BoundingBox,
    ErrorCode,
    LowConfidenceRegion,
    OCRPageResult,
    OCRStatus,
    OCRWord,
    PreprocessedImage,
    confidence_stats,
)
from ..text.layout import cluster_words_into_lines, merge_touching_fragments, render_lines
from ..text.normalization import normalize_ocr_text, normalize_structured_token


class EasyOCRBackend(OCRBackend):
    """Read Korean and English on CPU using existing local models only.

    Relative directories resolve against workspace_root. Each detection remains
    one OCRWord because EasyOCR supplies a single confidence and box per segment.
    An injected reader must implement readtext and is used without importing
    EasyOCR. The caller is responsible for that reader's offline behavior.
    """

    name = "easyocr"

    # EasyOCRBackend 인스턴스 멤버 변수 및 초기 설정을 구성함
    def __init__(
        self,
        workspace_root: Path,
        model_storage_directory: Path,
        user_network_directory: Path,
        reader: Any = None,
        *,
        download_enabled: bool = False,
    ):
        self.workspace_root = Path(workspace_root).resolve(strict=True)
        if not self.workspace_root.is_dir():
            raise ValueError("workspace_root must be an existing directory")
        self.model_storage_directory = self._directory(model_storage_directory)
        self.user_network_directory = self._directory(user_network_directory)
        self._reader = reader
        self.download_enabled = download_enabled

    # 디렉터리 경로 작업을 수행함
    def _directory(self, value: str | Path) -> Path:
        path = Path(value)
        if not path.is_absolute():
            path = self.workspace_root / path
        path = path.resolve(strict=True)
        if not path.is_relative_to(self.workspace_root):
            raise ValueError("EasyOCR directories must resolve within workspace_root")
        if not path.is_dir():
            raise ValueError("EasyOCR paths must be existing directories")
        return path

    # reader 정보를 조회하여 반환함
    def _get_reader(self):
        # Recheck containment before initialization in case a directory changed.
        models = self._directory(self.model_storage_directory)
        networks = self._directory(self.user_network_directory)
        if self._reader is None:
            try:
                from easyocr import Reader
            except ImportError as exc:
                raise OCREngineUnavailable("easyocr is not installed") from exc
            try:
                self._reader = Reader(
                    ["ko", "en"],
                    gpu=False,
                    download_enabled=self.download_enabled,
                    model_storage_directory=str(models),
                    user_network_directory=str(networks),
                    verbose=False,
                )
            except (OSError, RuntimeError, ValueError) as exc:
                raise OCREngineUnavailable(
                    "EasyOCR could not initialize existing offline models"
                ) from exc
        return self._reader

    # recognize 페이지 작업을 수행함
    def recognize_page(self, image: PreprocessedImage, *, page_no: int = 1) -> OCRPageResult:
        return self._recognize_array(image.image, image=image, page_no=page_no)

    # recognize region 작업을 수행함
    def recognize_region(
        self,
        image: PreprocessedImage,
        bbox: tuple[int, int, int, int],
        *,
        page_no: int = 1,
    ) -> OCRPageResult:
        return self._recognize_array(
            crop_region(image, bbox),
            image=image,
            page_no=page_no,
            offset=(max(0, bbox[0]), max(0, bbox[1])),
        )

    # recognize array 작업을 수행함
    def _recognize_array(
        self, pixels, *, image: PreprocessedImage, page_no: int,
        offset: tuple[int, int] = (0, 0),
    ) -> OCRPageResult:
        detections = self._get_reader().readtext(
            pixels, detail=1, paragraph=False, workers=0, batch_size=1,
        )
        words = []
        height, width = pixels.shape[:2]
        for polygon, text, score in detections:
            text = normalize_ocr_text(str(text))
            if not text.strip():
                continue
            confidence = float(score)
            if not isfinite(confidence):
                confidence = 0.0
            xs, ys = zip(*polygon)
            left = max(0, min(width, floor(min(xs))))
            top = max(0, min(height, floor(min(ys))))
            right = max(0, min(width, ceil(max(xs))))
            bottom = max(0, min(height, ceil(max(ys))))
            if right <= left or bottom <= top:
                continue
            words.append(OCRWord(
                text=text,
                confidence=max(0.0, min(1.0, confidence)),
                bbox=BoundingBox(left + offset[0], top + offset[1], right - left, bottom - top),
            ))
        lines = merge_touching_fragments(cluster_words_into_lines(words))
        ordered_words = tuple(word for line in lines for word in line)
        raw_text = render_lines(lines)
        normalized_text = normalize_ocr_text(
            render_lines(
                [
                    [replace(word, text=normalize_structured_token(word.text)) for word in line]
                    for line in lines
                ]
            )
        )
        mean, median = confidence_stats(ordered_words)
        low_regions = tuple(
            LowConfidenceRegion(page_no=page_no, bbox=word.bbox,
                                text=word.text, confidence=word.confidence)
            for word in ordered_words if word.confidence < 0.70
        )
        issues = () if raw_text else (ErrorCode.OCR_EMPTY_RESULT,)
        return OCRPageResult(
            page_no=page_no,
            raw_text=raw_text,
            normalized_text=normalized_text,
            words=ordered_words,
            mean_confidence=mean,
            median_confidence=median,
            low_confidence_regions=low_regions,
            engine=self.name,
            profile=image.config.profile,
            psm=image.config.psm,
            status=OCRStatus.REVIEW_REQUIRED if issues else OCRStatus.SUCCESS,
            issues=issues,
            coordinate_width_px=image.width_px,
            coordinate_height_px=image.height_px,
        )


# assemble lines 작업을 수행함
def _assemble_lines(words: list[OCRWord]) -> list[list[OCRWord]]:
    """Group horizontal text by overlap with each line's first box."""

    lines: list[list[OCRWord]] = []
    for word in sorted(words, key=lambda item: (item.bbox.y, item.bbox.x)):
        box = word.bbox
        candidates = []
        for index, line in enumerate(lines):
            anchor = line[0].bbox
            overlap = min(box.y + box.height, anchor.y + anchor.height) - max(box.y, anchor.y)
            ratio = overlap / min(box.height, anchor.height)
            if ratio >= 0.5:
                candidates.append((ratio, index))
        if candidates:
            lines[max(candidates)[1]].append(word)
        else:
            lines.append([word])
    return [sorted(line, key=lambda item: item.bbox.x) for line in lines]
