# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_rapidocr_korean_adapter.py
# 경로: tests/ocr/test_rapidocr_korean_adapter.py
# 목적: RapidOCR 한국어 모델 어댑터 연동 기능을 테스트함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
import sys
from types import SimpleNamespace

import numpy as np
import pytest

from ocr.engine.rapidocr_korean import RapidOCRKoreanBackend
from ocr.pipeline.models import (
    BoundingBox,
    ErrorCode,
    OCRStatus,
    PreprocessedImage,
    PreprocessingConfig,
    PreprocessingProfile,
)


class StubRapidOCR:
    # StubRapidOCR 인스턴스 멤버 변수 및 초기 설정을 구성함
    def __init__(self, output):
        self.output = output
        self.calls = []

    # StubRapidOCR 인스턴스를 호출하여 작업을 실행함
    def __call__(self, pixels):
        self.calls.append(pixels)
        return self.output


# 이미지 작업을 수행함
def _image() -> PreprocessedImage:
    return PreprocessedImage(
        image=np.zeros((100, 200, 3), dtype=np.uint8),
        config=PreprocessingConfig(profile=PreprocessingProfile.STANDARD),
        width_px=200,
        height_px=100,
        applied_steps=(),
    )


# rapidocr output is adapted and ordered 기능의 정상 동작 및 제약조건을 테스트함
def test_rapidocr_output_is_adapted_and_ordered() -> None:
    output = SimpleNamespace(
        boxes=np.array([
            [[80, 40], [130, 40], [130, 55], [80, 55]],
            [[10.2, 10.1], [60.8, 10.1], [60.8, 24.2], [10.2, 24.2]],
        ]),
        txts=("둘째 줄", "첫째 줄"),
        scores=(0.96, 0.93),
    )
    reader = StubRapidOCR(output)
    result = RapidOCRKoreanBackend(reader=reader).recognize_page(_image(), page_no=2)

    assert result.raw_text == "첫째 줄\n둘째 줄"
    assert result.words[0].bbox == BoundingBox(10, 10, 51, 15)
    assert result.engine == "rapidocr_korean_ppocrv5"
    assert result.status == OCRStatus.SUCCESS
    assert (result.coordinate_width_px, result.coordinate_height_px) == (200, 100)
    assert reader.calls[0].shape == (100, 200, 3)


# structured repairs do not mutate raw rapidocr output 기능의 정상 동작 및 제약조건을 테스트함
def test_structured_repairs_do_not_mutate_raw_rapidocr_output() -> None:
    output = SimpleNamespace(
        boxes=np.array([[[10, 10], [90, 10], [90, 25], [10, 25]]]),
        txts=("2026. O9. 0I",),
        scores=(0.98,),
    )

    result = RapidOCRKoreanBackend(reader=StubRapidOCR(output)).recognize_page(_image())

    assert result.words[0].text == "2026. O9. 0I"
    assert result.raw_text == "2026. O9. 0I"
    assert result.normalized_text == "2026.09.01"


# low 인식 신뢰도 is explicitly marked for review 기능의 정상 동작 및 제약조건을 테스트함
def test_low_confidence_is_explicitly_marked_for_review() -> None:
    output = SimpleNamespace(
        boxes=np.array([[[10, 10], [50, 10], [50, 25], [10, 25]]]),
        txts=("검토 필요",),
        scores=(0.61,),
    )
    result = RapidOCRKoreanBackend(reader=StubRapidOCR(output)).recognize_page(_image())

    assert result.status == OCRStatus.REVIEW_REQUIRED
    assert result.issues == (ErrorCode.OCR_LOW_CONFIDENCE,)
    assert result.low_confidence_regions[0].text == "검토 필요"


# region 기하 좌표 are returned in 페이지 space 기능의 정상 동작 및 제약조건을 테스트함
def test_region_coordinates_are_returned_in_page_space() -> None:
    output = SimpleNamespace(
        boxes=np.array([[[2, 3], [22, 3], [22, 13], [2, 13]]]),
        txts=("영역",),
        scores=(0.95,),
    )
    result = RapidOCRKoreanBackend(reader=StubRapidOCR(output)).recognize_region(
        _image(), (30, 40, 50, 30)
    )
    assert result.words[0].bbox == BoundingBox(32, 43, 20, 10)


# legacy list output and percent 인식 신뢰도 are supported 기능의 정상 동작 및 제약조건을 테스트함
def test_legacy_list_output_and_percent_confidence_are_supported() -> None:
    output = (
        [
            (
                [[-1.5, 1.2], [20.2, 1.2], [20.2, 12.1], [-1.5, 12.1]],
                "legacy",
                93,
            )
        ],
        0.01,
    )
    result = RapidOCRKoreanBackend(reader=StubRapidOCR(output)).recognize_page(_image())

    assert result.raw_text == "legacy"
    assert result.words[0].confidence == pytest.approx(0.93)
    assert result.words[0].bbox == BoundingBox(0, 1, 21, 12)


# legacy numpy record output is supported 기능의 정상 동작 및 제약조건을 테스트함
def test_legacy_numpy_record_output_is_supported() -> None:
    output = np.array([
        (
            np.array([[2, 3], [22, 3], [22, 13], [2, 13]]),
            "array-record",
            0.92,
        )
    ], dtype=object)

    result = RapidOCRKoreanBackend(reader=StubRapidOCR(output)).recognize_page(_image())

    assert result.raw_text == "array-record"
    assert result.words[0].confidence == pytest.approx(0.92)
    assert result.words[0].bbox == BoundingBox(2, 3, 20, 10)


# 인식 신뢰도 is finite and bounded 기능의 정상 동작 및 제약조건을 테스트함
@pytest.mark.parametrize("score, expected", [(1.2, 1.0), (-0.2, 0.0), (float("nan"), 0.0)])
def test_confidence_is_finite_and_bounded(score, expected) -> None:
    output = SimpleNamespace(
        boxes=np.array([[[10, 10], [50, 10], [50, 25], [10, 25]]]),
        txts=("점수",),
        scores=(score,),
    )
    result = RapidOCRKoreanBackend(reader=StubRapidOCR(output)).recognize_page(_image())

    assert result.words[0].confidence == pytest.approx(expected)


# empty or unknown output requires review 기능의 정상 동작 및 제약조건을 테스트함
def test_empty_or_unknown_output_requires_review() -> None:
    result = RapidOCRKoreanBackend(reader=StubRapidOCR(None)).recognize_page(_image())

    assert result.raw_text == ""
    assert result.words == ()
    assert result.status == OCRStatus.REVIEW_REQUIRED
    assert result.issues == (ErrorCode.OCR_EMPTY_RESULT,)


# reader is lazy and reused with korean cpu params 기능의 정상 동작 및 제약조건을 테스트함
def test_reader_is_lazy_and_reused_with_korean_cpu_params(monkeypatch, tmp_path) -> None:
    calls = []
    reader = StubRapidOCR(SimpleNamespace(boxes=(), txts=(), scores=()))

    class FakeRapidOCR:
        # FakeRapidOCR 인스턴스 멤버 변수 및 초기 설정을 구성함
        def __init__(self, *, params):
            calls.append(params)

        # FakeRapidOCR 인스턴스를 호출하여 작업을 실행함
        def __call__(self, pixels):
            return reader(pixels)

    fake_module = SimpleNamespace(
        EngineType=SimpleNamespace(ONNXRUNTIME="onnxruntime"),
        LangDet=SimpleNamespace(CH="ch"),
        LangRec=SimpleNamespace(KOREAN="korean"),
        ModelType=SimpleNamespace(MOBILE="mobile"),
        OCRVersion=SimpleNamespace(PPOCRV5="PP-OCRv5"),
        RapidOCR=FakeRapidOCR,
    )
    monkeypatch.setitem(sys.modules, "rapidocr", fake_module)
    backend = RapidOCRKoreanBackend(model_root_directory=tmp_path / "rapidocr")

    assert calls == []
    backend.recognize_page(_image())
    backend.recognize_page(_image())

    assert len(calls) == 1
    params = calls[0]
    assert params["Rec.lang_type"] == "korean"
    assert params["Rec.engine_type"] == "onnxruntime"
    assert params["EngineConfig.onnxruntime.use_cuda"] is False
    assert params["EngineConfig.onnxruntime.use_dml"] is False
    assert params["EngineConfig.onnxruntime.enable_cpu_mem_arena"] is False
    assert params["Global.model_root_dir"] == str((tmp_path / "rapidocr").resolve())
    assert len(reader.calls) == 2
