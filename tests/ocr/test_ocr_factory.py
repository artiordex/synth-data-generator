# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_ocr_factory.py
# 경로: tests/ocr/test_ocr_factory.py
# 목적: 설정 기반 OCR 엔진 인스턴스 팩토리 생성을 테스트함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
from pathlib import Path

import pytest

from ocr.engine import factory


# default local factory uses rapidocr primary and offline easyocr 기능의 정상 동작 및 제약조건을 테스트함
def test_default_local_factory_uses_rapidocr_primary_and_offline_easyocr(
    monkeypatch, tmp_path
) -> None:
    created = {}

    class FakeRapid:
        name = "rapid"

        # FakeRapid 인스턴스 멤버 변수 및 초기 설정을 구성함
        def __init__(self, model_root_directory, *, review_threshold):
            created["rapid"] = (Path(model_root_directory), review_threshold)

    class FakeEasy:
        name = "easy"

        # FakeEasy 인스턴스 멤버 변수 및 초기 설정을 구성함
        def __init__(
            self,
            workspace_root,
            model_storage_directory,
            user_network_directory,
            *,
            download_enabled,
        ):
            created["easy"] = (
                Path(workspace_root),
                Path(model_storage_directory),
                Path(user_network_directory),
                download_enabled,
            )

    class FakeEnsemble:
        # FakeEnsemble 인스턴스 멤버 변수 및 초기 설정을 구성함
        def __init__(
            self,
            primary,
            secondary,
            tiebreaker,
            *,
            review_threshold,
            supplemental_detection,
            uncovered_component_ratio,
            supplemental_min_confidence,
        ):
            self.primary = primary
            self.secondary = secondary
            self.tiebreaker = tiebreaker
            self.review_threshold = review_threshold
            self.supplemental_detection = supplemental_detection
            self.uncovered_component_ratio = uncovered_component_ratio
            self.supplemental_min_confidence = supplemental_min_confidence

    monkeypatch.setattr(factory, "RapidOCRKoreanBackend", FakeRapid)
    monkeypatch.setattr(factory, "EasyOCRBackend", FakeEasy)
    monkeypatch.setattr(factory, "ConfidenceEnsembleBackend", FakeEnsemble)
    monkeypatch.setattr(factory.shutil, "which", lambda name: None)
    monkeypatch.delenv("OCR_PRIMARY_BACKEND", raising=False)
    monkeypatch.delenv("OCR_SECONDARY_BACKEND", raising=False)
    monkeypatch.delenv("OCR_ALLOW_MODEL_DOWNLOAD", raising=False)

    backend = factory.build_local_ocr_backend(tmp_path)

    assert isinstance(backend.primary, FakeRapid)
    assert isinstance(backend.secondary, FakeEasy)
    assert backend.tiebreaker is None
    assert backend.supplemental_detection is True
    assert backend.uncovered_component_ratio == 0.20
    assert backend.supplemental_min_confidence == 0.55
    assert created["rapid"] == (tmp_path / "storage/models/ocr/rapidocr", 0.85)
    assert created["easy"][3] is False


# 모델 디렉터리 경로 must stay inside workspace 기능의 정상 동작 및 제약조건을 테스트함
def test_model_directory_must_stay_inside_workspace(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("OCR_MODEL_DIR", str(tmp_path.parent))

    with pytest.raises(ValueError, match="within workspace_root"):
        factory.build_local_ocr_backend(tmp_path)


# tesseract tiebreaker uses configured timeout 기능의 정상 동작 및 제약조건을 테스트함
def test_tesseract_tiebreaker_uses_configured_timeout(monkeypatch, tmp_path) -> None:
    created = {}

    class FakeRapid:
        name = "rapid"

        # FakeRapid 인스턴스 멤버 변수 및 초기 설정을 구성함
        def __init__(self, model_root_directory, *, review_threshold):
            pass

    class FakeEnsemble:
        # FakeEnsemble 인스턴스 멤버 변수 및 초기 설정을 구성함
        def __init__(
            self,
            primary,
            secondary,
            tiebreaker,
            *,
            review_threshold,
            supplemental_detection,
            uncovered_component_ratio,
            supplemental_min_confidence,
        ):
            self.tiebreaker = tiebreaker

    class FakeTesseract:
        name = "tesseract"

        # FakeTesseract 인스턴스 멤버 변수 및 초기 설정을 구성함
        def __init__(self, *, language, timeout_seconds):
            created["tesseract"] = (language, timeout_seconds)

    monkeypatch.setattr(factory, "RapidOCRKoreanBackend", FakeRapid)
    monkeypatch.setattr(factory, "ConfidenceEnsembleBackend", FakeEnsemble)
    monkeypatch.setattr(factory, "TesseractBackend", FakeTesseract)
    monkeypatch.setattr(factory.shutil, "which", lambda name: "tesseract")
    monkeypatch.setenv("OCR_SECONDARY_BACKEND", "none")
    monkeypatch.setenv("OCR_TESSERACT_TIMEOUT_SECONDS", "7.5")

    backend = factory.build_local_ocr_backend(tmp_path)

    assert isinstance(backend.tiebreaker, FakeTesseract)
    assert created["tesseract"] == ("kor+eng", 7.5)
