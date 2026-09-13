# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: profiles.py
# 경로: packages/ocr/ocr/preprocessing/profiles.py
# 목적: 문서 유형별 이미지 전처리 프로파일 및 파라미터를 관리함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Preprocessing profiles for adaptive OCR attempts."""

from __future__ import annotations

import os

from ..pipeline.models import ImageInspection, ImageIssue, PreprocessingConfig, PreprocessingProfile


# aspect scale 작업을 수행함
def _aspect_scale(name: str, default: float) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except ValueError:
        value = default
    return max(0.55, min(1.80, value))


PROFILE_CONFIGS: dict[PreprocessingProfile, PreprocessingConfig] = {
    PreprocessingProfile.STANDARD: PreprocessingConfig(profile=PreprocessingProfile.STANDARD, psm=3),
    PreprocessingProfile.LOW_RESOLUTION: PreprocessingConfig(
        profile=PreprocessingProfile.LOW_RESOLUTION,
        upscale=2.0,
        interpolation="LANCZOS4",
        psm=6,
    ),
    PreprocessingProfile.LOW_CONTRAST: PreprocessingConfig(
        profile=PreprocessingProfile.LOW_CONTRAST,
        clahe=True,
        threshold="ADAPTIVE_GAUSSIAN",
        psm=6,
    ),
    PreprocessingProfile.NOISY_SCAN: PreprocessingConfig(
        profile=PreprocessingProfile.NOISY_SCAN,
        denoise="strong",
        clahe=True,
        morphology="open",
        psm=6,
    ),
    PreprocessingProfile.BLURRED_SCAN: PreprocessingConfig(
        profile=PreprocessingProfile.BLURRED_SCAN,
        upscale=1.5,
        denoise="light",
        clahe=True,
        psm=6,
    ),
    PreprocessingProfile.SKEWED_DOCUMENT: PreprocessingConfig(
        profile=PreprocessingProfile.SKEWED_DOCUMENT,
        deskew="aggressive",
        psm=3,
    ),
    PreprocessingProfile.TABLE_DOCUMENT: PreprocessingConfig(
        profile=PreprocessingProfile.TABLE_DOCUMENT,
        threshold="ADAPTIVE_GAUSSIAN",
        morphology="close",
        psm=6,
    ),
    PreprocessingProfile.SMALL_TEXT: PreprocessingConfig(
        profile=PreprocessingProfile.SMALL_TEXT,
        upscale=2.0,
        interpolation="LANCZOS4",
        clahe=True,
        psm=6,
    ),
    PreprocessingProfile.SPARSE_TEXT: PreprocessingConfig(
        profile=PreprocessingProfile.SPARSE_TEXT,
        psm=11,
    ),
    PreprocessingProfile.HIGH_ACCURACY: PreprocessingConfig(
        profile=PreprocessingProfile.HIGH_ACCURACY,
        upscale=1.5,
        interpolation="LANCZOS4",
        denoise="light",
        clahe=True,
        threshold="ADAPTIVE_GAUSSIAN",
        psm=6,
    ),
    # OCR retry variants for horizontally stretched/compressed glyphs.  The
    # transform is deliberately bounded; extreme resampling creates more
    # artifacts than signal on public-form scans.
    PreprocessingProfile.HORIZONTAL_COMPRESSED: PreprocessingConfig(
        profile=PreprocessingProfile.HORIZONTAL_COMPRESSED,
        horizontal_scale=_aspect_scale("OCR_ASPECT_COMPRESS_SCALE", 0.80),
        psm=6,
    ),
    PreprocessingProfile.HORIZONTAL_EXPANDED: PreprocessingConfig(
        profile=PreprocessingProfile.HORIZONTAL_EXPANDED,
        horizontal_scale=_aspect_scale("OCR_ASPECT_EXPAND_SCALE", 1.25),
        psm=6,
    ),
}


# 프로파일 환경 설정 정보를 조회하여 반환함
def get_profile_config(profile: PreprocessingProfile) -> PreprocessingConfig:
    """Return an immutable profile config."""

    return PROFILE_CONFIGS[profile]


# attempt plan 구조를 생성 및 조립함
def build_attempt_plan(inspection: ImageInspection, *, max_attempts: int = 5) -> list[PreprocessingConfig]:
    """Build a bounded profile plan from image quality issues."""

    if max_attempts < 1:
        raise ValueError("max_attempts must be at least one")
    profiles: list[PreprocessingProfile] = [PreprocessingProfile.STANDARD]
    issue_map = {
        ImageIssue.LOW_RESOLUTION: PreprocessingProfile.LOW_RESOLUTION,
        ImageIssue.LOW_DPI: PreprocessingProfile.LOW_RESOLUTION,
        ImageIssue.LOW_CONTRAST: PreprocessingProfile.LOW_CONTRAST,
        ImageIssue.HIGH_NOISE: PreprocessingProfile.NOISY_SCAN,
        ImageIssue.BLURRED: PreprocessingProfile.BLURRED_SCAN,
        ImageIssue.SKEWED: PreprocessingProfile.SKEWED_DOCUMENT,
        ImageIssue.TABLE_HEAVY: PreprocessingProfile.TABLE_DOCUMENT,
        ImageIssue.SMALL_TEXT: PreprocessingProfile.SMALL_TEXT,
        ImageIssue.SPARSE_TEXT: PreprocessingProfile.SPARSE_TEXT,
    }
    for issue in inspection.issues:
        profile = issue_map.get(issue)
        if profile is not None and profile not in profiles:
            profiles.append(profile)
    if PreprocessingProfile.HIGH_ACCURACY not in profiles:
        profiles.append(PreprocessingProfile.HIGH_ACCURACY)

    # Keep the historical five-attempt contract unchanged.  Once the
    # production pipeline opts into the expanded budget, reserve two slots
    # for anisotropic retries so a noisy/blurred page cannot crowd them out.
    if max_attempts <= 5:
        selected = profiles[:max_attempts]
    else:
        aspect_profiles = (
            PreprocessingProfile.HORIZONTAL_COMPRESSED,
            PreprocessingProfile.HORIZONTAL_EXPANDED,
        )
        reserved = min(len(aspect_profiles), max_attempts - 1)
        selected = profiles[: max_attempts - reserved] + list(aspect_profiles[:reserved])
    return [get_profile_config(profile) for profile in selected]
