# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_easyocr_adapter.py
# 경로: tests/ocr/test_easyocr_adapter.py
# 목적: EasyOCR 엔진 어댑터 연동 및 추론 처리를 테스트함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
import builtins
import sys
from types import SimpleNamespace

import numpy as np
import pytest

from ocr.engine.base import OCREngineUnavailable
from ocr.engine.easyocr import EasyOCRBackend
from ocr.pipeline.models import (
    BoundingBox, ErrorCode, OCRStatus, PreprocessedImage,
    PreprocessingConfig, PreprocessingProfile,
)


class StubReader:
    # StubReader 인스턴스 멤버 변수 및 초기 설정을 구성함
    def __init__(self, detections=()):
        self.detections = detections
        self.calls = []

    # readtext 작업을 수행함
    def readtext(self, pixels, **kwargs):
        self.calls.append((pixels, kwargs))
        return self.detections


# 경로 목록 작업을 수행함
@pytest.fixture
def paths(tmp_path):
    models = tmp_path / "models"
    networks = tmp_path / "networks"
    models.mkdir()
    networks.mkdir()
    return dict(workspace_root=tmp_path, model_storage_directory=models,
                user_network_directory=networks)


# 이미지 작업을 수행함
@pytest.fixture
def image():
    return PreprocessedImage(
        image=np.zeros((100, 200, 3), dtype=np.uint8),
        config=PreprocessingConfig(profile=PreprocessingProfile.STANDARD),
        width_px=200, height_px=100, applied_steps=(),
    )


# detection 작업을 수행함
def detection(text, confidence, x, y, width=20, height=10):
    return ([[x, y], [x + width, y], [x + width, y + height], [x, y + height]],
            text, confidence)


# reader is lazy offline cpu and reused 기능의 정상 동작 및 제약조건을 테스트함
def test_reader_is_lazy_offline_cpu_and_reused(paths, image, monkeypatch):
    calls = []
    reader = StubReader()

    # factory 작업을 수행함
    def factory(*args, **kwargs):
        calls.append((args, kwargs))
        return reader

    monkeypatch.setitem(sys.modules, "easyocr", SimpleNamespace(Reader=factory))
    backend = EasyOCRBackend(**paths)
    assert calls == []
    backend.recognize_page(image)
    backend.recognize_page(image)
    assert calls == [((["ko", "en"],), dict(
        gpu=False, download_enabled=False, verbose=False,
        model_storage_directory=str(paths["model_storage_directory"].resolve()),
        user_network_directory=str(paths["user_network_directory"].resolve()),
    ))]
    assert reader.calls[0][0] is image.image
    assert reader.calls[0][1] == {
        "detail": 1, "paragraph": False, "workers": 0, "batch_size": 1,
    }


# injected reader never imports easyocr 기능의 정상 동작 및 제약조건을 테스트함
def test_injected_reader_never_imports_easyocr(paths, image, monkeypatch):
    original = builtins.__import__

    # guarded 작업을 수행함
    def guarded(name, *args, **kwargs):
        if name == "easyocr":
            raise AssertionError("EasyOCR must not be imported")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded)
    EasyOCRBackend(**paths, reader=StubReader()).recognize_page(image)


# rejects outside 경로 목록 even with injected reader 기능의 정상 동작 및 제약조건을 테스트함
@pytest.mark.parametrize("key", ["model_storage_directory", "user_network_directory"])
def test_rejects_outside_paths_even_with_injected_reader(paths, key):
    paths[key] = paths["workspace_root"].parent
    with pytest.raises(ValueError, match="within workspace_root"):
        EasyOCRBackend(**paths, reader=StubReader())


# missing directories are not created 기능의 정상 동작 및 제약조건을 테스트함
@pytest.mark.parametrize("key", ["model_storage_directory", "user_network_directory"])
def test_missing_directories_are_not_created(paths, key):
    paths[key] = paths["workspace_root"] / "missing"
    with pytest.raises(FileNotFoundError):
        EasyOCRBackend(**paths)
    assert not paths[key].exists()


# relative 경로 목록 resolve against workspace 기능의 정상 동작 및 제약조건을 테스트함
def test_relative_paths_resolve_against_workspace(paths):
    paths.update(model_storage_directory="models", user_network_directory="networks")
    backend = EasyOCRBackend(**paths, reader=StubReader())
    assert backend.model_storage_directory == paths["workspace_root"] / "models"


# symlink escape is rejected 기능의 정상 동작 및 제약조건을 테스트함
def test_symlink_escape_is_rejected(paths):
    link = paths["workspace_root"] / "escape"
    try:
        link.symlink_to(paths["workspace_root"].parent, target_is_directory=True)
    except OSError:
        pytest.skip("Directory symlinks unavailable")
    paths["user_network_directory"] = link
    with pytest.raises(ValueError, match="within workspace_root"):
        EasyOCRBackend(**paths)


# missing optional dependency is reported lazily 기능의 정상 동작 및 제약조건을 테스트함
def test_missing_optional_dependency_is_reported_lazily(paths, image, monkeypatch):
    monkeypatch.setitem(sys.modules, "easyocr", None)
    backend = EasyOCRBackend(**paths)
    with pytest.raises(OCREngineUnavailable, match="not installed"):
        backend.recognize_page(image)


# missing 모델 목록 do not trigger 폴백 기능의 정상 동작 및 제약조건을 테스트함
def test_missing_models_do_not_trigger_fallback(paths, image, monkeypatch):
    # factory 작업을 수행함
    def factory(*args, **kwargs):
        assert kwargs["download_enabled"] is False
        raise FileNotFoundError("Missing model")

    monkeypatch.setitem(sys.modules, "easyocr", SimpleNamespace(Reader=factory))
    with pytest.raises(OCREngineUnavailable, match="offline models"):
        EasyOCRBackend(**paths).recognize_page(image)


# 페이지 assembles lines and 인식 신뢰도 기능의 정상 동작 및 제약조건을 테스트함
def test_page_assembles_lines_and_confidence(paths, image):
    reader = StubReader([
        detection("last", 0.9, 10, 50),
        detection("OCR", 0.5, 60, 11),
        detection("\uc2dd\uc57d\ucc98", 1.0, 10, 10),
        detection(" ", 0.0, 100, 10),
    ])
    result = EasyOCRBackend(**paths, reader=reader).recognize_page(image, page_no=3)
    assert result.raw_text == "\uc2dd\uc57d\ucc98 OCR\nlast"
    assert result.mean_confidence == pytest.approx(0.8)
    assert result.median_confidence == 0.9
    assert result.engine == "easyocr"
    assert result.status == OCRStatus.SUCCESS
    assert result.profile == image.config.profile
    assert result.psm == image.config.psm
    assert result.words[0].bbox == BoundingBox(10, 10, 20, 10)
    assert len(result.low_confidence_regions) == 1
    low = result.low_confidence_regions[0]
    assert (low.page_no, low.text, low.confidence) == (3, "OCR", 0.5)
    assert low.bbox == result.words[1].bbox


# structured repairs do not mutate raw easyocr output 기능의 정상 동작 및 제약조건을 테스트함
def test_structured_repairs_do_not_mutate_raw_easyocr_output(paths, image):
    reader = StubReader([detection("1, 00O원", 0.98, 10, 10)])

    result = EasyOCRBackend(**paths, reader=reader).recognize_page(image)

    assert result.words[0].text == "1, 00O원"
    assert result.raw_text == "1, 00O원"
    assert result.normalized_text == "1,000원"


# region returns 페이지 기하 좌표 기능의 정상 동작 및 제약조건을 테스트함
@pytest.mark.parametrize("region, expected, shape", [
    ((30, 40, 50, 30), BoundingBox(32, 43, 20, 10), (30, 50, 3)),
    ((-10, -5, 50, 30), BoundingBox(2, 3, 20, 10), (25, 40, 3)),
])
def test_region_returns_page_coordinates(paths, image, region, expected, shape):
    reader = StubReader([detection("text", 0.4, 2, 3)])
    result = EasyOCRBackend(**paths, reader=reader).recognize_region(image, region, page_no=4)
    assert reader.calls[0][0].shape == shape
    assert result.words[0].bbox == expected
    assert result.low_confidence_regions[0].bbox == expected
    assert result.low_confidence_regions[0].page_no == 4


# invalid region does not call reader 기능의 정상 동작 및 제약조건을 테스트함
def test_invalid_region_does_not_call_reader(paths, image):
    reader = StubReader()
    with pytest.raises(ValueError):
        EasyOCRBackend(**paths, reader=reader).recognize_region(image, (300, 0, 10, 10))
    assert reader.calls == []


# boxes are rounded outward and clipped 기능의 정상 동작 및 제약조건을 테스트함
def test_boxes_are_rounded_outward_and_clipped(paths, image):
    reader = StubReader([detection("text", 0.9, -0.5, 1.2, 21, 10.1)])
    result = EasyOCRBackend(**paths, reader=reader).recognize_page(image)
    assert result.words[0].bbox == BoundingBox(0, 1, 21, 11)


# 인식 신뢰도 is finite and bounded 기능의 정상 동작 및 제약조건을 테스트함
@pytest.mark.parametrize("score, expected", [(1.2, 1.0), (-0.2, 0.0), (float("nan"), 0.0)])
def test_confidence_is_finite_and_bounded(paths, image, score, expected):
    reader = StubReader([detection("text", score, 0, 0)])
    result = EasyOCRBackend(**paths, reader=reader).recognize_page(image)
    assert result.words[0].confidence == expected
    assert result.mean_confidence == expected


# empty 결과 requires review 기능의 정상 동작 및 제약조건을 테스트함
def test_empty_result_requires_review(paths, image):
    result = EasyOCRBackend(**paths, reader=StubReader()).recognize_page(image)
    assert result.raw_text == ""
    assert result.words == ()
    assert result.mean_confidence == result.median_confidence == 0.0
    assert result.status == OCRStatus.REVIEW_REQUIRED
    assert result.issues == (ErrorCode.OCR_EMPTY_RESULT,)
