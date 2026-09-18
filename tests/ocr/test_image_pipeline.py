# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_image_pipeline.py
# 경로: tests/ocr/test_image_pipeline.py
# 목적: 이미지 전처리 및 OCR 파이프라인 파이프라인 실행을 테스트함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import ocr.image.pipeline as image_pipeline
from ocr.engine.fake import FakeOCRBackend
from ocr.image.pipeline import run_image_ocr
from ocr.pipeline.models import OCRStatus, PreprocessingProfile


# 텍스트 이미지 데이터를 파일에 기록함
def _write_text_image(path: Path, *, dpi=(300, 300), fill="white"):
    image = Image.new("RGB", (1400, 900), fill)
    draw = ImageDraw.Draw(image)
    draw.text((80, 120), "식약처 OCR 123", fill="black", font=ImageFont.load_default())
    image.save(path, dpi=dpi)


# 기본 이미지 진입점이 로컬 앙상블 팩토리를 사용하는지 검증함
def test_image_pipeline_uses_local_backend_factory_by_default(tmp_path, monkeypatch):
    source = tmp_path / "factory.png"
    _write_text_image(source)
    factory_calls: list[Path | None] = []

    def factory(workspace_root=None):
        factory_calls.append(workspace_root)
        return FakeOCRBackend(lambda image: ("local result", 0.95))

    monkeypatch.setattr(image_pipeline, "build_local_ocr_backend", factory)

    result = run_image_ocr(
        source,
        workspace_root=tmp_path,
        max_attempts=1,
        min_quality_score=0.1,
    )

    assert factory_calls == [tmp_path]
    assert result.engine == "fake"
    assert result.pages[0].raw_text == "local result"


# 이미지 pipeline retries and selects best attempt 기능의 정상 동작 및 제약조건을 테스트함
def test_image_pipeline_retries_and_selects_best_attempt(tmp_path):
    source = tmp_path / "korean.png"
    _write_text_image(source)

    # recognizer 작업을 수행함
    def recognizer(preprocessed):
        if preprocessed.config.profile == PreprocessingProfile.HIGH_ACCURACY:
            return "식약처 OCR 123", 0.96
        return "식약처 OGR 123", 0.60

    result = run_image_ocr(
        source,
        backend=FakeOCRBackend(recognizer),
        ground_truth="식약처 OCR 123",
        max_attempts=5,
    )

    assert result.file_type.value == "IMAGE"
    assert result.ground_truth_available is True
    assert result.character_accuracy == 1.0
    assert result.best_attempt_no == len(result.attempts)
    assert result.profile == PreprocessingProfile.HIGH_ACCURACY
    assert result.status == OCRStatus.SUCCESS
    assert result.pages[0].raw_text == "식약처 OCR 123"


# 이미지 pipeline reports 인식 신뢰도 without ground truth 정확도 기능의 정상 동작 및 제약조건을 테스트함
def test_image_pipeline_reports_confidence_without_ground_truth_accuracy(tmp_path):
    source = tmp_path / "korean.png"
    _write_text_image(source)

    result = run_image_ocr(
        source,
        backend=FakeOCRBackend(lambda image: ("식약처 OCR 123", 0.92)),
        ground_truth=None,
        max_attempts=2,
        min_quality_score=0.10,
    )

    assert result.ground_truth_available is False
    assert result.character_accuracy is None
    assert result.confidence == 0.92
    assert result.quality_score > 0
    assert result.pages[0].normalized_text == "식약처 OCR 123"


# 이미지 pipeline recovers from engine timeout 기능의 정상 동작 및 제약조건을 테스트함
def test_image_pipeline_recovers_from_engine_timeout(tmp_path):
    source = tmp_path / "retry.png"
    _write_text_image(source)
    calls = []

    # recognize 작업을 수행함
    def recognize(image):
        calls.append(image.config.profile)
        if len(calls) == 1:
            raise RuntimeError("OCR timeout")
        return "recovered", 0.95

    result = run_image_ocr(source, backend=FakeOCRBackend(recognize),
                           max_attempts=2, min_quality_score=0.1)
    assert result.attempts[0].page_result.status == OCRStatus.FAILED
    assert result.pages[0].raw_text == "recovered"
    assert result.status == OCRStatus.SUCCESS


# 이미지 pipeline all attempts fail 기능의 정상 동작 및 제약조건을 테스트함
def test_image_pipeline_all_attempts_fail(tmp_path):
    source = tmp_path / "failed.png"
    _write_text_image(source)

    # recognize 작업을 수행함
    def recognize(image):
        raise RuntimeError("OCR timeout")

    result = run_image_ocr(source, backend=FakeOCRBackend(recognize), max_attempts=2)
    assert len(result.attempts) == 2
    assert result.status == OCRStatus.FAILED


# 이미지 pipeline uses horizontal 재시도 for 너비 distortion 기능의 정상 동작 및 제약조건을 테스트함
def test_image_pipeline_uses_horizontal_retry_for_width_distortion(tmp_path):
    source = tmp_path / "aspect.png"
    _write_text_image(source)

    # recognizer 작업을 수행함
    def recognizer(preprocessed):
        if preprocessed.config.profile == PreprocessingProfile.HORIZONTAL_EXPANDED:
            return "식약처 OCR 123", 0.96
        return "식약처 OGR 123", 0.60

    result = run_image_ocr(
        source,
        backend=FakeOCRBackend(recognizer),
        ground_truth="식약처 OCR 123",
        max_attempts=7,
    )

    assert result.profile == PreprocessingProfile.HORIZONTAL_EXPANDED
    assert result.character_accuracy == 1.0
    assert (result.pages[0].coordinate_width_px, result.pages[0].coordinate_height_px) == (1750, 900)
