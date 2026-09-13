# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_image_preprocessing.py
# 경로: tests/ocr/test_image_preprocessing.py
# 목적: 이미지 회전, 노이즈 필터링 등 전처리 알고리즘을 테스트함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from ocr.image.inspection import inspect_image
from ocr.pipeline.models import ImageIssue, PreprocessingConfig, PreprocessingProfile
from ocr.preprocessing.opencv import preprocess_image
from ocr.preprocessing.profiles import build_attempt_plan, get_profile_config


# low contrast 이미지 데이터를 파일에 기록함
def _write_low_contrast_image(path: Path):
    image = Image.new("RGB", (700, 500), "#dddddd")
    draw = ImageDraw.Draw(image)
    draw.text((50, 80), "식약처 OCR", fill="#999999", font=ImageFont.load_default())
    image = image.filter(ImageFilter.GaussianBlur(radius=0.6))
    image.save(path, dpi=(150, 150))


# 이미지 inspection selects adaptive profiles 기능의 정상 동작 및 제약조건을 테스트함
def test_image_inspection_selects_adaptive_profiles(tmp_path):
    source = tmp_path / "low-contrast.png"
    _write_low_contrast_image(source)

    inspection = inspect_image(source)
    plan = build_attempt_plan(inspection, max_attempts=5)
    profiles = [config.profile for config in plan]

    assert ImageIssue.LOW_RESOLUTION in inspection.issues
    assert ImageIssue.LOW_DPI in inspection.issues
    assert ImageIssue.LOW_CONTRAST in inspection.issues
    assert profiles[0] == PreprocessingProfile.STANDARD
    assert PreprocessingProfile.LOW_RESOLUTION in profiles
    assert PreprocessingProfile.LOW_CONTRAST in profiles


# preprocessing applies clahe 임계값 and upscale 기능의 정상 동작 및 제약조건을 테스트함
def test_preprocessing_applies_clahe_threshold_and_upscale(tmp_path):
    source = tmp_path / "low-contrast.png"
    _write_low_contrast_image(source)

    low_res = preprocess_image(source, get_profile_config(PreprocessingProfile.LOW_RESOLUTION))
    low_contrast = preprocess_image(source, get_profile_config(PreprocessingProfile.LOW_CONTRAST))

    assert low_res.width_px > 700
    assert "upscale:2" in low_res.applied_steps
    assert low_res.original_size_px == (700, 500)
    assert low_res.ocr_size_px == (1400, 1000)
    assert low_res.transform_metadata is not None
    assert [transform.name for transform in low_res.transform_metadata.transforms] == ["upscale"]
    assert low_res.transform_metadata.original_to_ocr_bbox((10, 20, 30, 40)) == (20, 40, 60, 80)
    assert "clahe" in low_contrast.applied_steps
    assert "threshold:adaptive_gaussian" in low_contrast.applied_steps


# horizontal 재시도 preserves 높이 and changes only 너비 기능의 정상 동작 및 제약조건을 테스트함
def test_horizontal_retry_preserves_height_and_changes_only_width(tmp_path):
    source = tmp_path / "wide-glyphs.png"
    _write_low_contrast_image(source)

    config = get_profile_config(PreprocessingProfile.HORIZONTAL_COMPRESSED)
    processed = preprocess_image(source, config)

    assert processed.height_px == 500
    assert processed.width_px == 560
    assert "horizontal_scale:0.8" in processed.applied_steps
    assert processed.transform_metadata is not None
    assert [transform.name for transform in processed.transform_metadata.transforms] == ["horizontal_scale"]


# preprocessing records deskew transform 기능의 정상 동작 및 제약조건을 테스트함
def test_preprocessing_records_deskew_transform(tmp_path, monkeypatch):
    source = tmp_path / "skewed.png"
    _write_low_contrast_image(source)
    monkeypatch.setattr("ocr.preprocessing.opencv.estimate_skew_angle", lambda *args, **kwargs: 5.0)

    processed = preprocess_image(
        source,
        PreprocessingConfig(
            profile=PreprocessingProfile.SKEWED_DOCUMENT,
            deskew="standard",
            threshold="NONE",
            morphology="none",
        ),
    )

    assert processed.detected_skew_deg == 5.0
    assert processed.original_size_px == (700, 500)
    assert processed.ocr_size_px == (700, 500)
    assert processed.transform_metadata is not None
    assert [transform.name for transform in processed.transform_metadata.transforms] == ["deskew"]
    assert processed.transform_metadata.transforms[0].parameters["angle_deg"] == 5.0


# extended attempt plan contains both 너비 variants 기능의 정상 동작 및 제약조건을 테스트함
def test_extended_attempt_plan_contains_both_width_variants(tmp_path):
    source = tmp_path / "wide-glyphs.png"
    _write_low_contrast_image(source)
    inspection = inspect_image(source)

    plan = build_attempt_plan(inspection, max_attempts=7)
    profiles = [config.profile for config in plan]

    assert PreprocessingProfile.HORIZONTAL_COMPRESSED in profiles
    assert PreprocessingProfile.HORIZONTAL_EXPANDED in profiles


# 너비 variants are reserved when many 품질 issues exist 기능의 정상 동작 및 제약조건을 테스트함
def test_width_variants_are_reserved_when_many_quality_issues_exist(tmp_path):
    source = tmp_path / "problematic.png"
    _write_low_contrast_image(source)
    inspection = inspect_image(source)

    profiles = [config.profile for config in build_attempt_plan(inspection, max_attempts=7)]

    assert profiles[-2:] == [
        PreprocessingProfile.HORIZONTAL_COMPRESSED,
        PreprocessingProfile.HORIZONTAL_EXPANDED,
    ]
