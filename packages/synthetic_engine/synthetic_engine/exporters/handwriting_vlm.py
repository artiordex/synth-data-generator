# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: handwriting_vlm.py
# 경로: packages/synthetic_engine/synthetic_engine/exporters/handwriting_vlm.py
# 목적: VLM 기반 필기체 텍스트 및 서명 영역 인식 처리를 수행함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Local-only handwriting, mark and form-control analysis."""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date
from functools import lru_cache
import math
import os
from pathlib import Path
import re
import shutil
from typing import Any, Callable, Dict, Iterable, Optional, Protocol, Tuple

import cv2
import numpy as np


@dataclass
class OcrCellResult:
    text: str
    confidence: float
    source: str
    bbox: Tuple[int, int, int, int]
    is_handwritten: bool = False
    is_checkbox: bool = False
    checkbox_checked: Optional[bool] = None
    is_signature_seal: bool = False
    cell_metadata: Dict[str, Any] = field(default_factory=dict)

    # post init 작업을 수행함
    def __post_init__(self) -> None:
        if self.source not in {"printed_ocr", "local_recognizer", "heuristic_fallback"}:
            raise ValueError("지원하지 않는 OCR 결과 출처입니다.")
        if not math.isfinite(self.confidence) or not 0.0 <= self.confidence <= 1.0:
            raise ValueError("OCR 신뢰도는 0과 1 사이여야 합니다.")
        if len(self.bbox) != 4 or any(not isinstance(value, int) or value < 0 for value in self.bbox):
            raise ValueError("bbox는 음수가 아닌 정수 4개여야 합니다.")


@dataclass(frozen=True)
class LocalRecognitionCandidate:
    text: str
    confidence: float
    engine: str
    normalized_text: str = ""
    valid_format: bool = True

    # post init 작업을 수행함
    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("candidate text must not be empty")
        try:
            confidence = float(self.confidence)
        except (TypeError, ValueError) as exc:
            raise ValueError("candidate confidence must be finite") from exc
        if not math.isfinite(confidence):
            raise ValueError("candidate confidence must be finite")
        object.__setattr__(self, "confidence", max(0.0, min(1.0, confidence)))
        object.__setattr__(self, "engine", str(self.engine)[:80] or "local")


@dataclass(frozen=True)
class LocalRecognitionDecision:
    text: str
    confidence: float
    engine: str
    review_required: bool
    candidate_count: int
    agreement_count: int
    valid_format: bool
    alternatives: Tuple[LocalRecognitionCandidate, ...] = ()

    # as dict 작업을 수행함
    def as_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "confidence": self.confidence,
            "engine": self.engine,
            "review_required": self.review_required,
            "candidate_count": self.candidate_count,
            "agreement_count": self.agreement_count,
            "valid_format": self.valid_format,
            "alternatives": [
                {
                    "text": candidate.text,
                    "confidence": candidate.confidence,
                    "engine": candidate.engine,
                    "normalized_text": candidate.normalized_text,
                    "valid_format": candidate.valid_format,
                }
                for candidate in self.alternatives[:5]
            ],
        }


class LocalOCRAdapter(Protocol):
    name: str

    # recognize 작업을 수행함
    def recognize(
        self, crop_img: np.ndarray, context: Dict[str, Any]
    ) -> Iterable[LocalRecognitionCandidate]:
        """Return local OCR candidates for one crop."""


class CallableOCRAdapter:
    """Small test/extension adapter around a callable candidate source."""

    # CallableOCRAdapter 인스턴스 멤버 변수 및 초기 설정을 구성함
    def __init__(
        self,
        name: str,
        recognizer: Callable[[np.ndarray, Dict[str, Any]], Any],
    ) -> None:
        self.name = name
        self._recognizer = recognizer

    # recognize 작업을 수행함
    def recognize(
        self, crop_img: np.ndarray, context: Dict[str, Any]
    ) -> Iterable[LocalRecognitionCandidate]:
        parsed = _parse_recognizer_payload(self._recognizer(crop_img, context), self.name)
        return (parsed,) if parsed else ()


class OCRBackendAdapter:
    """Bridge the optional local OCR package backends into crop candidates."""

    # OCRBackendAdapter 인스턴스 멤버 변수 및 초기 설정을 구성함
    def __init__(self, name: str, backend_factory: Callable[[], Any]) -> None:
        self.name = name
        self._backend_factory = backend_factory
        self._backend: Any = None
        self._available = True

    # recognize 작업을 수행함
    def recognize(
        self, crop_img: np.ndarray, context: Dict[str, Any]
    ) -> Iterable[LocalRecognitionCandidate]:
        if not self._available:
            return ()
        try:
            backend = self._get_backend()
            page = backend.recognize_page(_preprocessed_image_for_crop(crop_img), page_no=1)
        except (ImportError, OSError, RuntimeError, ValueError):
            self._available = False
            return ()
        text = str(getattr(page, "normalized_text", "") or getattr(page, "raw_text", ""))
        text = _clean_candidate_text(text)
        if not text:
            return ()
        confidence = _bounded_confidence(getattr(page, "mean_confidence", 0.0))
        return (LocalRecognitionCandidate(text=text, confidence=confidence, engine=self.name),)

    # backend 정보를 조회하여 반환함
    def _get_backend(self) -> Any:
        if self._backend is None:
            try:
                self._backend = self._backend_factory()
            except (ImportError, OSError, RuntimeError, ValueError) as exc:
                self._available = False
                raise RuntimeError(f"{self.name} is not available") from exc
        return self._backend


class LocalHandwritingRecognizer:
    """Consensus recognizer over locally installed OCR engines only."""

    # LocalHandwritingRecognizer 인스턴스 멤버 변수 및 초기 설정을 구성함
    def __init__(
        self,
        adapters: Iterable[LocalOCRAdapter] | None = None,
        *,
        review_threshold: float = 0.85,
        structured_agreement_count: int = 2,
    ) -> None:
        self.adapters = (
            tuple(build_default_handwriting_adapters())
            if adapters is None
            else tuple(adapters)
        )
        self.review_threshold = max(0.0, min(1.0, review_threshold))
        self.structured_agreement_count = max(1, structured_agreement_count)

    # LocalHandwritingRecognizer 인스턴스를 호출하여 작업을 실행함
    def __call__(self, crop_img: np.ndarray, context: Dict[str, Any]) -> dict[str, Any] | None:
        decision = self.recognize(crop_img, context)
        return decision.as_dict() if decision else None

    # recognize 작업을 수행함
    def recognize(
        self, crop_img: np.ndarray, context: Dict[str, Any]
    ) -> LocalRecognitionDecision | None:
        candidates: list[LocalRecognitionCandidate] = []
        for adapter in self.adapters:
            try:
                for candidate in adapter.recognize(crop_img, context):
                    if candidate.text.strip():
                        candidates.append(candidate)
            except (OSError, RuntimeError, ValueError):
                continue
        if not candidates:
            return None
        return _decide_local_candidate(candidates, str(context.get("expected_type", "text")))


# default handwriting adapters 구조를 생성 및 조립함
def build_default_handwriting_adapters(
    workspace_root: str | Path | None = None,
) -> Tuple[LocalOCRAdapter, ...]:
    """Build adapters for installed local engines without downloading models."""
    root = Path(workspace_root or Path.cwd()).resolve()
    model_root = _resolve_ocr_model_root(root)
    adapters: list[LocalOCRAdapter] = []

    rapidocr_dir = model_root / "rapidocr"
    if rapidocr_dir.is_dir() and any(rapidocr_dir.glob("*.onnx")):
        adapters.append(OCRBackendAdapter(
            "rapidocr_korean",
            lambda directory=rapidocr_dir: _rapidocr_backend(directory),
        ))

    easyocr_model_dir = model_root / "easyocr" / "models"
    easyocr_network_dir = model_root / "easyocr" / "user_network"
    if easyocr_model_dir.is_dir() and easyocr_network_dir.is_dir() and any(easyocr_model_dir.glob("*.pth")):
        adapters.append(OCRBackendAdapter(
            "easyocr",
            lambda root=root, models=easyocr_model_dir, networks=easyocr_network_dir: _easyocr_backend(
                root, models, networks
            ),
        ))

    if shutil.which("tesseract") is not None:
        adapters.append(OCRBackendAdapter("tesseract", _tesseract_backend))
    return tuple(adapters)


# 이미지 유효성 및 제약조건을 검증함
def _validate_image(image: np.ndarray) -> np.ndarray:
    if not isinstance(image, np.ndarray) or image.size == 0:
        raise ValueError("비어 있지 않은 NumPy 이미지가 필요합니다.")
    if image.dtype != np.uint8:
        raise ValueError("OCR 이미지는 uint8 형식이어야 합니다.")
    if image.ndim == 2:
        return image
    if image.ndim == 3 and image.shape[2] in {3, 4}:
        code = cv2.COLOR_BGRA2GRAY if image.shape[2] == 4 else cv2.COLOR_BGR2GRAY
        return cv2.cvtColor(image, code)
    raise ValueError("OCR 이미지는 grayscale, BGR 또는 BGRA 형식이어야 합니다.")


# foreground 작업을 수행함
def _foreground(gray: np.ndarray) -> np.ndarray:
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    return cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]


# handwritten region 여부 및 유효성을 판별함
def is_handwritten_region(
    crop_img: np.ndarray,
    ocr_confidence: float,
    contour_irregularity_threshold: float = 0.35,
) -> bool:
    """Classify handwriting from stroke geometry, not confidence alone."""
    if not math.isfinite(ocr_confidence) or not 0.0 <= ocr_confidence <= 1.0:
        raise ValueError("ocr_confidence는 0과 1 사이여야 합니다.")
    if not 0.0 < contour_irregularity_threshold <= 2.0:
        raise ValueError("손글씨 불규칙성 임계값이 올바르지 않습니다.")
    gray = _validate_image(crop_img)
    ink = _foreground(gray)
    if cv2.countNonZero(ink) < 12:
        return False
    distance = cv2.distanceTransform(ink, cv2.DIST_L2, 5)
    ridge = (distance >= cv2.dilate(distance, np.ones((3, 3), np.uint8)) - 1e-6) & (distance > 0.5)
    widths = distance[ridge] * 2.0
    stroke_cv = float(np.std(widths) / max(np.mean(widths), 1e-6)) if widths.size >= 2 else 0.0

    contours, _ = cv2.findContours(ink, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    irregularities = []
    weights = []
    for contour in contours:
        area = cv2.contourArea(contour)
        perimeter = cv2.arcLength(contour, True)
        if area >= 4 and perimeter > 0:
            irregularities.append(1.0 - min(1.0, 4.0 * math.pi * area / (perimeter * perimeter)))
            weights.append(area)
    contour_score = float(np.average(irregularities, weights=weights)) if weights else 0.0
    combined = 0.75 * stroke_cv + 0.25 * contour_score
    # Low OCR confidence supports, but never decides, the handwriting label.
    effective_threshold = (
        contour_irregularity_threshold * 0.85
        if ocr_confidence < 0.60
        else contour_irregularity_threshold
    )
    return combined > effective_threshold


# square candidates 작업을 수행함
def _square_candidates(ink: np.ndarray) -> list[tuple[int, int, int, int, float]]:
    contours, _ = cv2.findContours(ink, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    height, width = ink.shape
    candidates = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        ratio = w / max(h, 1)
        area_ratio = w * h / max(width * height, 1)
        if 0.8 <= ratio <= 1.2 and 0.04 <= area_ratio <= 0.95 and min(w, h) >= 8:
            perimeter = cv2.arcLength(contour, True)
            polygon = cv2.approxPolyDP(contour, 0.04 * perimeter, True)
            if 4 <= len(polygon) <= 10:
                candidates.append((x, y, w, h, area_ratio))
    return sorted(candidates, key=lambda item: item[4], reverse=True)


# 감지 checkbox state 작업을 수행함
def detect_checkbox_state(crop_img: np.ndarray) -> Tuple[bool, Optional[bool]]:
    """Detect a square checkbox and whether its inner area contains a mark."""
    ink = _foreground(_validate_image(crop_img))
    candidates = _square_candidates(ink)
    if not candidates:
        return False, None
    x, y, width, height, _ = candidates[0]
    inset = max(2, int(round(min(width, height) * 0.20)))
    inner = ink[y + inset:y + height - inset, x + inset:x + width - inset]
    if inner.size == 0:
        return True, False
    fill_ratio = cv2.countNonZero(inner) / inner.size
    edges = cv2.Canny(inner, 50, 150)
    lines = cv2.HoughLinesP(
        edges, 1, np.pi / 180, threshold=max(4, min(inner.shape) // 3),
        minLineLength=max(3, min(inner.shape) // 3), maxLineGap=2,
    )
    diagonal_count = 0
    if lines is not None:
        for x1, y1, x2, y2 in lines[:, 0]:
            angle = abs(math.degrees(math.atan2(y2 - y1, x2 - x1)))
            if 20 <= angle <= 70 or 110 <= angle <= 160:
                diagonal_count += 1
    return True, bool(fill_ratio >= 0.20 or diagonal_count >= 1)


# 감지 signature or seal 작업을 수행함
def detect_signature_or_seal(crop_img: np.ndarray) -> Tuple[bool, str]:
    """Detect a red seal first, then a wide irregular monochrome signature."""
    gray = _validate_image(crop_img)
    if crop_img.ndim == 3:
        bgr = crop_img[:, :, :3]
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        red = cv2.bitwise_or(
            cv2.inRange(hsv, np.array((0, 70, 45)), np.array((10, 255, 255))),
            cv2.inRange(hsv, np.array((170, 70, 45)), np.array((180, 255, 255))),
        )
        if cv2.countNonZero(red) / red.size >= 0.015:
            contours, _ = cv2.findContours(red, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if any(cv2.contourArea(contour) >= red.size * 0.005 for contour in contours):
                return True, "seal"

    ink = _foreground(gray)
    points = cv2.findNonZero(ink)
    if points is None or len(points) < 20:
        return False, "none"
    x, y, width, height = cv2.boundingRect(points)
    ink_ratio = cv2.countNonZero(ink[y:y + height, x:x + width]) / max(width * height, 1)
    contours, _ = cv2.findContours(ink, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    long_strokes = sum(cv2.arcLength(contour, False) >= max(width, height) * 0.35 for contour in contours)
    if width / max(height, 1) >= 2.0 and 0.015 <= ink_ratio <= 0.45 and long_strokes >= 1:
        return True, "signature"
    return False, "none"


# local recognizer 작업을 실행함
def _run_local_recognizer(
    crop_img: np.ndarray, context: Dict[str, Any]
) -> Optional[LocalRecognitionDecision]:
    """Run an injected or default local recognizer with a bounded contract."""
    recognizer = context.get("local_recognizer")
    if not callable(recognizer):
        recognizer = _default_local_recognizer()
        if not recognizer.adapters:
            return None
    _validate_image(crop_img)
    safe_context = {
        key: context.get(key)
        for key in (
            "bbox", "row_header", "col_header", "expected_type",
            "language_mode", "ocr_text", "ocr_confidence",
        )
    }
    try:
        result = recognizer(crop_img, safe_context)
    except (OSError, RuntimeError, ValueError):
        return None
    if isinstance(result, LocalRecognitionDecision):
        return result
    if isinstance(result, dict):
        text = str(result.get("text", ""))
        try:
            confidence = float(result.get("confidence", 0.0))
        except (TypeError, ValueError):
            return None
        engine = str(result.get("engine", "local"))[:80]
        review_required = bool(result.get("review_required", confidence < 0.85))
        candidate_count = int(result.get("candidate_count", 1) or 1)
        agreement_count = int(result.get("agreement_count", 1) or 1)
        valid_format = bool(result.get("valid_format", True))
    else:
        text = str(result or "")
        confidence = 0.0
        engine = "local"
        review_required = True
        candidate_count = 1
        agreement_count = 1
        valid_format = True
    text = _clean_candidate_text(text)
    if not text or not math.isfinite(confidence):
        return None
    return LocalRecognitionDecision(
        text=text,
        confidence=max(0.0, min(1.0, confidence)),
        engine=engine,
        review_required=review_required,
        candidate_count=max(1, candidate_count),
        agreement_count=max(1, agreement_count),
        valid_format=valid_format,
    )


# recognize multilingual 텍스트 작업을 수행함
def recognize_multilingual_text(
    crop_img: np.ndarray, context: Optional[Dict[str, Any]] = None
) -> Optional[str]:
    """Run only a caller-provided local recognizer for an isolated crop."""
    context = dict(context or {})
    context["language_mode"] = "multilingual"
    result = _run_local_recognizer(crop_img, context)
    if result and not result.review_required:
        return result.text
    return None


# 폴백 텍스트 데이터를 표준 형식으로 정규화함
def _normalize_fallback_text(text: str, expected_type: str) -> str:
    value = re.sub(r"\s+", " ", text).strip()
    if expected_type in {"amount", "date", "code"}:
        value = value.translate(str.maketrans({"O": "0", "o": "0", "I": "1", "l": "1", "S": "5"}))
    if expected_type == "amount":
        digits = re.sub(r"[^0-9-]", "", value)
        if digits and digits != "-":
            sign = "-" if digits.startswith("-") else ""
            number = digits.lstrip("-")
            return sign + f"{int(number):,}"
    if expected_type == "date":
        match = re.search(r"(\d{4})\D*(\d{1,2})\D*(\d{1,2})", value)
        if match:
            year, month, day = (int(part) for part in match.groups())
            if 1 <= month <= 12 and 1 <= day <= 31:
                return f"{year:04d}-{month:02d}-{day:02d}"
    return value


# refine handwritten 셀 작업을 수행함
def refine_handwritten_cell(crop_img: np.ndarray, context: Dict[str, Any]) -> OcrCellResult:
    """Return local recognition or retain OCR evidence for human review."""
    gray = _validate_image(crop_img)
    context = dict(context or {})
    bbox_value = context.get("bbox", (0, 0, int(gray.shape[1]), int(gray.shape[0])))
    bbox = tuple(int(max(0, value)) for value in bbox_value)
    if len(bbox) != 4:
        raise ValueError("context.bbox는 값 4개가 필요합니다.")
    confidence = float(context.get("ocr_confidence", 0.0))
    confidence = max(0.0, min(1.0, confidence))

    if context.get("language_mode") == "multilingual":
        local_result = _run_local_recognizer(crop_img, context)
        if local_result:
            return OcrCellResult(
                text=local_result.text, confidence=local_result.confidence,
                source="local_recognizer", bbox=bbox,
                is_handwritten=False,
                cell_metadata={
                    "language_mode": "multilingual",
                    "engine": local_result.engine,
                    "review_required": local_result.review_required,
                    "candidate_count": local_result.candidate_count,
                    "agreement_count": local_result.agreement_count,
                    "valid_format": local_result.valid_format,
                },
            )

    is_checkbox, checked = detect_checkbox_state(crop_img)
    if is_checkbox:
        return OcrCellResult(
            text="[선택]" if checked else "[미선택]", confidence=0.98,
            source="heuristic_fallback", bbox=bbox, is_checkbox=True,
            checkbox_checked=checked, cell_metadata={"detector": "square-density-diagonal"},
        )

    detected_mark, mark_type = detect_signature_or_seal(crop_img)
    handwritten = is_handwritten_region(crop_img, confidence)
    local_result = _run_local_recognizer(crop_img, context) if handwritten else None
    if local_result:
        return OcrCellResult(
            text=local_result.text, confidence=local_result.confidence,
            source="local_recognizer", bbox=bbox,
            is_handwritten=True, is_signature_seal=detected_mark,
            cell_metadata={
                "mark_type": mark_type,
                "engine": local_result.engine,
                "review_required": local_result.review_required,
                "candidate_count": local_result.candidate_count,
                "agreement_count": local_result.agreement_count,
                "valid_format": local_result.valid_format,
            },
        )

    raw_text = str(context.get("ocr_text", context.get("printed_text", "")))
    expected_type = str(context.get("expected_type", "text")).strip().lower()
    text = _normalize_fallback_text(raw_text, expected_type)
    if detected_mark and not text:
        text = "[직인]" if mark_type == "seal" else "[서명]"
    component_count = max(0, cv2.connectedComponents((_foreground(gray) > 0).astype(np.uint8))[0] - 1)
    return OcrCellResult(
        text=text, confidence=confidence if text else 0.0,
        source="heuristic_fallback", bbox=bbox, is_handwritten=handwritten,
        is_signature_seal=detected_mark,
        cell_metadata={
            "mark_type": mark_type,
            "connected_components": component_count,
            "review_required": bool(handwritten or confidence < 0.85),
            "reason": (
                "로컬 손글씨 인식 모델이 없어 원 OCR 결과를 유지했습니다."
                if handwritten
                else "OCR 신뢰도가 검토 기준보다 낮습니다."
                if confidence < 0.85
                else ""
            ),
        },
    )


# default local recognizer 작업을 수행함
@lru_cache(maxsize=1)
def _default_local_recognizer() -> LocalHandwritingRecognizer:
    return LocalHandwritingRecognizer()


# candidate 텍스트 데이터를 정제 및 정리함
def _clean_candidate_text(text: str) -> str:
    return re.sub(r"[\r\n\t]+", " ", text).strip().strip("`\"'")[:200]


# bounded 인식 신뢰도 작업을 수행함
def _bounded_confidence(value: Any) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(confidence):
        return 0.0
    return max(0.0, min(1.0, confidence))


# recognizer payload 데이터를 분석하여 파싱함
def _parse_recognizer_payload(payload: Any, engine: str) -> LocalRecognitionCandidate | None:
    if isinstance(payload, LocalRecognitionCandidate):
        return payload
    if isinstance(payload, dict):
        text = _clean_candidate_text(str(payload.get("text", "")))
        if not text:
            return None
        return LocalRecognitionCandidate(
            text=text,
            confidence=_bounded_confidence(payload.get("confidence", 0.0)),
            engine=str(payload.get("engine", engine)),
        )
    text = _clean_candidate_text(str(payload or ""))
    if not text:
        return None
    return LocalRecognitionCandidate(text=text, confidence=0.0, engine=engine)


# decide local candidate 작업을 수행함
def _decide_local_candidate(
    candidates: list[LocalRecognitionCandidate], expected_type: str
) -> LocalRecognitionDecision:
    kind = _structured_kind(expected_type)
    enriched = [_with_format(candidate, kind) for candidate in candidates]
    if kind:
        valid = [candidate for candidate in enriched if candidate.valid_format]
        if valid:
            groups: dict[str, list[LocalRecognitionCandidate]] = defaultdict(list)
            for candidate in valid:
                groups[candidate.normalized_text].append(candidate)
            normalized, group = max(
                groups.items(),
                key=lambda item: (
                    len({candidate.engine for candidate in item[1]}),
                    sum(candidate.confidence for candidate in item[1]) / len(item[1]),
                ),
            )
            agreement_count = len({candidate.engine for candidate in group})
            best = max(group, key=lambda candidate: candidate.confidence)
            review_required = agreement_count < 2 or best.confidence < 0.85
            return LocalRecognitionDecision(
                text=normalized,
                confidence=best.confidence,
                engine="+".join(sorted({candidate.engine for candidate in group})),
                review_required=review_required,
                candidate_count=len(enriched),
                agreement_count=agreement_count,
                valid_format=True,
                alternatives=tuple(sorted(enriched, key=lambda item: item.confidence, reverse=True)),
            )
        best = max(enriched, key=lambda candidate: candidate.confidence)
        return LocalRecognitionDecision(
            text=best.text,
            confidence=best.confidence,
            engine=best.engine,
            review_required=True,
            candidate_count=len(enriched),
            agreement_count=0,
            valid_format=False,
            alternatives=tuple(sorted(enriched, key=lambda item: item.confidence, reverse=True)),
        )

    normalized_counts = Counter(candidate.text for candidate in enriched)
    best = max(
        enriched,
        key=lambda candidate: (
            normalized_counts[candidate.text],
            candidate.confidence,
            len(candidate.text),
        ),
    )
    agreement_count = normalized_counts[best.text]
    return LocalRecognitionDecision(
        text=best.text,
        confidence=best.confidence,
        engine=best.engine,
        review_required=best.confidence < 0.85,
        candidate_count=len(enriched),
        agreement_count=agreement_count,
        valid_format=True,
        alternatives=tuple(sorted(enriched, key=lambda item: item.confidence, reverse=True)),
    )


# structured kind 작업을 수행함
def _structured_kind(expected_type: str) -> str:
    value = expected_type.strip().lower()
    if value in {"amount", "money", "currency", "금액"}:
        return "amount"
    if value in {"date", "datetime", "birthdate", "날짜"}:
        return "date"
    if value in {"number", "numeric", "integer", "float", "decimal", "숫자"}:
        return "number"
    if value in {"code", "short_code", "id_code", "코드"}:
        return "code"
    return ""


# with format 작업을 수행함
def _with_format(candidate: LocalRecognitionCandidate, kind: str) -> LocalRecognitionCandidate:
    if not kind:
        return candidate
    normalized, valid = _normalize_structured_candidate(candidate.text, kind)
    return LocalRecognitionCandidate(
        text=candidate.text,
        confidence=candidate.confidence,
        engine=candidate.engine,
        normalized_text=normalized,
        valid_format=valid,
    )


# structured candidate 데이터를 표준 형식으로 정규화함
def _normalize_structured_candidate(text: str, kind: str) -> tuple[str, bool]:
    value = _clean_candidate_text(text).translate(
        str.maketrans({"O": "0", "o": "0", "I": "1", "l": "1", "S": "5"})
    )
    if kind == "amount":
        compact = re.sub(r"[\s,원₩$€¥]", "", value)
        if re.fullmatch(r"-?\d+", compact):
            sign = "-" if compact.startswith("-") else ""
            number = compact.lstrip("-")
            return sign + f"{int(number):,}", True
        return value, False
    if kind == "date":
        match = re.search(r"(\d{4})\D*(\d{1,2})\D*(\d{1,2})", value)
        if match:
            year, month, day = (int(part) for part in match.groups())
            try:
                return date(year, month, day).isoformat(), True
            except ValueError:
                return value, False
        return value, False
    if kind == "number":
        compact = re.sub(r"[\s,]", "", value)
        if re.fullmatch(r"-?\d+(\.\d+)?", compact):
            if "." in compact:
                return compact.rstrip("0").rstrip("."), True
            return str(int(compact)), True
        return value, False
    if kind == "code":
        compact = re.sub(r"\s+", "", value).upper()
        if re.fullmatch(r"[A-Z0-9][A-Z0-9._/\-]{1,31}", compact):
            return compact, True
        return value, False
    return value, True


# resolve OCR 인식 모델 root 작업을 수행함
def _resolve_ocr_model_root(root: Path) -> Path:
    configured = Path(os.getenv("OCR_MODEL_DIR", "storage/models/ocr"))
    model_root = configured if configured.is_absolute() else root / configured
    try:
        model_root = model_root.resolve()
    except OSError:
        return root / "storage" / "models" / "ocr"
    try:
        if not model_root.is_relative_to(root):
            return root / "storage" / "models" / "ocr"
    except ValueError:
        return root / "storage" / "models" / "ocr"
    return model_root


# preprocessed 이미지 for 자르기 작업을 수행함
def _preprocessed_image_for_crop(crop_img: np.ndarray) -> Any:
    from ocr.pipeline.models import PreprocessedImage, PreprocessingConfig, PreprocessingProfile

    image = np.asarray(crop_img)
    height, width = image.shape[:2]
    return PreprocessedImage(
        image=image,
        config=PreprocessingConfig(profile=PreprocessingProfile.STANDARD, psm=7),
        width_px=int(width),
        height_px=int(height),
        applied_steps=("handwriting-crop",),
    )


# rapidocr backend 작업을 수행함
def _rapidocr_backend(model_root: Path) -> Any:
    from ocr.engine.rapidocr_korean import RapidOCRKoreanBackend

    return RapidOCRKoreanBackend(model_root_directory=model_root, input_padding=4)


# easyocr backend 작업을 수행함
def _easyocr_backend(root: Path, model_dir: Path, network_dir: Path) -> Any:
    from ocr.engine.easyocr import EasyOCRBackend

    return EasyOCRBackend(
        root,
        model_dir,
        network_dir,
        download_enabled=False,
    )


# tesseract backend 작업을 수행함
def _tesseract_backend() -> Any:
    from ocr.engine.tesseract import TesseractBackend

    return TesseractBackend(language="kor+eng", timeout_seconds=10.0)


__all__ = [
    "CallableOCRAdapter",
    "LocalHandwritingRecognizer",
    "LocalOCRAdapter",
    "LocalRecognitionCandidate",
    "LocalRecognitionDecision",
    "OcrCellResult", "is_handwritten_region", "detect_checkbox_state",
    "detect_signature_or_seal", "recognize_multilingual_text",
    "refine_handwritten_cell", "build_default_handwriting_adapters",
]
