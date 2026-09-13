# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: models.py
# 경로: packages/ocr/ocr/pipeline/models.py
# 목적: OCR 실행 상태, 페이지 결과, 단어 좌표 등 데이터 모델을 정의함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Shared OCR schema used by image, PDF, preprocessing, engine and evaluation layers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from statistics import median
from typing import TYPE_CHECKING, Any
from uuid import uuid4

if TYPE_CHECKING:
    from ..preprocessing.transforms import CoordinateTransform, TransformMetadata


class FileType(str, Enum):
    """Top-level OCR input type."""

    PDF = "PDF"
    IMAGE = "IMAGE"


class PdfType(str, Enum):
    """PDF classification before OCR routing."""

    TEXT_PDF = "TEXT_PDF"
    IMAGE_ONLY_PDF = "IMAGE_ONLY_PDF"
    MIXED_PDF = "MIXED_PDF"
    ENCRYPTED_PDF = "ENCRYPTED_PDF"
    CORRUPTED_PDF = "CORRUPTED_PDF"


class ImageIssue(str, Enum):
    """Image quality defects. Multiple issues may be present."""

    NORMAL = "NORMAL"
    LOW_RESOLUTION = "LOW_RESOLUTION"
    LOW_DPI = "LOW_DPI"
    LOW_CONTRAST = "LOW_CONTRAST"
    HIGH_NOISE = "HIGH_NOISE"
    BLURRED = "BLURRED"
    SKEWED = "SKEWED"
    ROTATED = "ROTATED"
    SHADOWED = "SHADOWED"
    TABLE_HEAVY = "TABLE_HEAVY"
    SMALL_TEXT = "SMALL_TEXT"
    SPARSE_TEXT = "SPARSE_TEXT"
    MIXED_PROBLEM = "MIXED_PROBLEM"
    ASPECT_DISTORTED = "ASPECT_DISTORTED"


class PreprocessingProfile(str, Enum):
    """Adaptive OpenCV preprocessing profiles."""

    STANDARD = "STANDARD"
    LOW_RESOLUTION = "LOW_RESOLUTION"
    LOW_CONTRAST = "LOW_CONTRAST"
    NOISY_SCAN = "NOISY_SCAN"
    BLURRED_SCAN = "BLURRED_SCAN"
    SKEWED_DOCUMENT = "SKEWED_DOCUMENT"
    TABLE_DOCUMENT = "TABLE_DOCUMENT"
    SMALL_TEXT = "SMALL_TEXT"
    SPARSE_TEXT = "SPARSE_TEXT"
    HIGH_ACCURACY = "HIGH_ACCURACY"
    HORIZONTAL_COMPRESSED = "HORIZONTAL_COMPRESSED"
    HORIZONTAL_EXPANDED = "HORIZONTAL_EXPANDED"


class OCRStatus(str, Enum):
    """Document, page or attempt status."""

    NOT_REQUIRED = "NOT_REQUIRED"
    READY = "READY"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    RETRY_REQUIRED = "RETRY_REQUIRED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    FAILED = "FAILED"


class ErrorCode(str, Enum):
    """Stable issue codes for pipeline, UI and benchmark reports."""

    FILE_OPEN_FAILED = "FILE_OPEN_FAILED"
    PDF_CORRUPTED = "PDF_CORRUPTED"
    PDF_ENCRYPTED = "PDF_ENCRYPTED"
    PDF_RENDER_FAILED = "PDF_RENDER_FAILED"
    PDF_TEXT_LAYER_INVALID = "PDF_TEXT_LAYER_INVALID"
    OCR_REQUIRED = "OCR_REQUIRED"
    OCR_FAILED = "OCR_FAILED"
    OCR_EMPTY_RESULT = "OCR_EMPTY_RESULT"
    OCR_LOW_CONFIDENCE = "OCR_LOW_CONFIDENCE"
    OCR_PARTIAL_RESULT = "OCR_PARTIAL_RESULT"
    IMAGE_LOW_DPI = "IMAGE_LOW_DPI"
    IMAGE_LOW_RESOLUTION = "IMAGE_LOW_RESOLUTION"
    IMAGE_BLUR = "IMAGE_BLUR"
    IMAGE_NOISE = "IMAGE_NOISE"
    IMAGE_LOW_CONTRAST = "IMAGE_LOW_CONTRAST"
    IMAGE_SKEWED = "IMAGE_SKEWED"
    IMAGE_ROTATED = "IMAGE_ROTATED"
    TABLE_DETECTION_FAILED = "TABLE_DETECTION_FAILED"
    TABLE_STRUCTURE_LOSS = "TABLE_STRUCTURE_LOSS"
    TEXT_EMPTY = "TEXT_EMPTY"
    TEXT_ENCODING_ERROR = "TEXT_ENCODING_ERROR"
    TEXT_BROKEN_CHARACTER = "TEXT_BROKEN_CHARACTER"


@dataclass(frozen=True)
class BoundingBox:
    """Pixel-space bounding box."""

    x: int
    y: int
    width: int
    height: int

    # area 작업을 수행함
    @property
    def area(self) -> int:
        """Area in square pixels."""

        return max(0, self.width) * max(0, self.height)


@dataclass(frozen=True)
class OCRWord:
    """Recognized word with confidence and bbox."""

    text: str
    confidence: float
    bbox: BoundingBox


@dataclass(frozen=True)
class LowConfidenceRegion:
    """Region that needs human review or a later targeted retry."""

    page_no: int
    bbox: BoundingBox
    text: str
    confidence: float


@dataclass(frozen=True)
class ImageInspection:
    """Image measurements and classified quality issues."""

    path: Path
    format: str
    width_px: int
    height_px: int
    dpi_x: float | None
    dpi_y: float | None
    blur_score: float
    noise_score: float
    contrast_score: float
    skew_angle_deg: float
    issues: tuple[ImageIssue, ...]

    # megapixels 작업을 수행함
    @property
    def megapixels(self) -> float:
        """Image size in megapixels."""

        return (self.width_px * self.height_px) / 1_000_000.0


@dataclass(frozen=True)
class PreprocessingConfig:
    """Configurable OpenCV operations for one attempt."""

    profile: PreprocessingProfile
    target_dpi: int = 300
    upscale: float = 1.0
    interpolation: str = "CUBIC"
    grayscale: bool = True
    denoise: str = "none"
    clahe: bool = False
    clahe_clip_limit: float = 2.0
    deskew: str = "standard"
    threshold: str = "OTSU"
    morphology: str = "minimal"
    remove_border: bool = False
    shadow_reduction: bool = False
    psm: int = 3
    language: str = "kor+eng"
    # Anisotropic x scaling is intentionally separate from ``upscale``.
    # ``upscale`` preserves glyph geometry; this field compensates for scans
    # whose character width was stretched or compressed before OCR.
    horizontal_scale: float = 1.0


@dataclass(frozen=True)
class PreprocessedImage:
    """Image after preprocessing plus audit metadata."""

    image: Any
    config: PreprocessingConfig
    width_px: int
    height_px: int
    applied_steps: tuple[str, ...]
    detected_skew_deg: float = 0.0
    original_width_px: int | None = None
    original_height_px: int | None = None
    ocr_width_px: int | None = None
    ocr_height_px: int | None = None
    transform_metadata: "TransformMetadata | None" = None

    # original 크기 px 작업을 수행함
    @property
    def original_size_px(self) -> tuple[int, int]:
        """Original image dimensions as ``(width, height)``."""

        return (
            self.original_width_px if self.original_width_px is not None else self.width_px,
            self.original_height_px if self.original_height_px is not None else self.height_px,
        )

    # OCR 인식 크기 px 작업을 수행함
    @property
    def ocr_size_px(self) -> tuple[int, int]:
        """OCR image dimensions as ``(width, height)``."""

        return (
            self.ocr_width_px if self.ocr_width_px is not None else self.width_px,
            self.ocr_height_px if self.ocr_height_px is not None else self.height_px,
        )

    # 좌표 transform 작업을 수행함
    @property
    def coordinate_transform(self) -> "CoordinateTransform":
        """Composite transform from original image space to OCR image space."""

        from ..preprocessing.transforms import CoordinateTransform

        if self.transform_metadata is not None:
            return self.transform_metadata.coordinate_transform
        return CoordinateTransform.identity(size=self.original_size_px)


@dataclass(frozen=True)
class OCRPageResult:
    """OCR result for one image or PDF page."""

    page_no: int
    raw_text: str
    normalized_text: str
    words: tuple[OCRWord, ...]
    mean_confidence: float
    median_confidence: float
    low_confidence_regions: tuple[LowConfidenceRegion, ...] = ()
    engine: str = ""
    profile: PreprocessingProfile = PreprocessingProfile.STANDARD
    psm: int = 3
    status: OCRStatus = OCRStatus.SUCCESS
    issues: tuple[ErrorCode, ...] = ()
    # Coordinates in ``words`` refer to this processed image space.  Keeping
    # it explicit prevents aspect/upscale retries from being evaluated against
    # the wrong source dimensions.
    coordinate_width_px: int | None = None
    coordinate_height_px: int | None = None


@dataclass(frozen=True)
class OCRAttempt:
    """One OCR attempt with a preprocessing profile and backend result."""

    attempt_no: int
    profile: PreprocessingProfile
    psm: int
    engine: str
    page_result: OCRPageResult
    quality_score: float
    character_accuracy: float | None = None
    cer: float | None = None
    wer: float | None = None
    duration_ms: float = 0.0


@dataclass(frozen=True)
class OCRDocumentResult:
    """Final OCR output with all attempts retained."""

    document_id: str
    source: Path
    file_type: FileType
    pages: tuple[OCRPageResult, ...]
    attempts: tuple[OCRAttempt, ...]
    best_attempt_no: int | None
    engine: str
    profile: PreprocessingProfile | None
    confidence: float
    ground_truth_available: bool
    cer: float | None
    wer: float | None
    character_accuracy: float | None
    quality_score: float
    status: OCRStatus
    issues: tuple[ErrorCode, ...] = ()

    # attempts 데이터로부터 객체를 생성함
    @classmethod
    def from_attempts(
        cls,
        *,
        source: Path,
        file_type: FileType,
        attempts: list[OCRAttempt],
        ground_truth_available: bool,
        document_id: str | None = None,
    ) -> "OCRDocumentResult":
        """Build a document result from retained attempts."""

        best = max(attempts, key=lambda item: (
            item.page_result.status != OCRStatus.FAILED,
            bool(item.page_result.raw_text), item.quality_score,
        )) if attempts else None
        page = best.page_result if best is not None else None
        return cls(
            document_id=document_id or str(uuid4()),
            source=source,
            file_type=file_type,
            pages=(page,) if page is not None else (),
            attempts=tuple(attempts),
            best_attempt_no=best.attempt_no if best is not None else None,
            engine=best.engine if best is not None else "",
            profile=best.profile if best is not None else None,
            confidence=page.mean_confidence if page is not None else 0.0,
            ground_truth_available=ground_truth_available,
            cer=best.cer if best is not None else None,
            wer=best.wer if best is not None else None,
            character_accuracy=best.character_accuracy if best is not None else None,
            quality_score=best.quality_score if best is not None else 0.0,
            status=page.status if page is not None else OCRStatus.FAILED,
            issues=tuple(page.issues) if page is not None else (ErrorCode.OCR_FAILED,),
        )


# 인식 신뢰도 stats 작업을 수행함
def confidence_stats(words: tuple[OCRWord, ...]) -> tuple[float, float]:
    """Return mean and median confidence from OCR words."""

    if not words:
        return 0.0, 0.0
    values = [max(0.0, min(1.0, word.confidence)) for word in words]
    return sum(values) / len(values), float(median(values))
