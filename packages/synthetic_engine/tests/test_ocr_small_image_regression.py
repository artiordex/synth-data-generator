# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_ocr_small_image_regression.py
# 경로: packages/synthetic_engine/tests/test_ocr_small_image_regression.py
# 목적: 저해상도 소형 이미지 OCR 인식 안정성을 테스트함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
import numpy as np

from ocr.pipeline.models import (
    BoundingBox,
    OCRPageResult,
    OCRStatus,
    OCRWord as EngineOCRWord,
    PreprocessingProfile,
)
from synthetic_engine.exporters import ocr_table_reconstructor as reconstructor


class FakeBackend:
    # FakeBackend 인스턴스 멤버 변수 및 초기 설정을 구성함
    def __init__(self) -> None:
        self.widths: list[int] = []

    # recognize 페이지 작업을 수행함
    def recognize_page(self, image, *, page_no=1):
        width = int(image.image.shape[1])
        self.widths.append(width)
        if width > 200:
            words = (
                EngineOCRWord(
                    "데이터 발굴의 배경과 필요성",
                    0.64,
                    BoundingBox(25, 30, 125, 25),
                ),
                EngineOCRWord(
                    "공유 데이터 제공 노력",
                    0.70,
                    BoundingBox(25, 70, 105, 25),
                ),
            )
        else:
            words = (
                EngineOCRWord("이궁뚝용융여무", 0.96, BoundingBox(10, 12, 50, 10)),
            )
        mean = sum(word.confidence for word in words) / len(words)
        return OCRPageResult(
            page_no=page_no,
            raw_text="\n".join(word.text for word in words),
            normalized_text="\n".join(word.text for word in words),
            words=words,
            mean_confidence=mean,
            median_confidence=mean,
            engine="fake",
            profile=PreprocessingProfile.STANDARD,
            status=OCRStatus.SUCCESS,
        )


# small 이미지 OCR 인식 prefers upscaled korean candidate 기능의 정상 동작 및 제약조건을 테스트함
def test_small_image_ocr_prefers_upscaled_korean_candidate(monkeypatch) -> None:
    backend = FakeBackend()
    monkeypatch.setattr(reconstructor, "get_ocr_backend", lambda: backend)
    monkeypatch.setenv("OCR_SMALL_IMAGE_UPSCALE", "2.5")

    image = np.full((120, 160, 3), 255, dtype=np.uint8)
    words = reconstructor._run_ocr_on_image(image)

    assert backend.widths == [160, 400]
    assert [word.text for word in words] == [
        "데이터 발굴의 배경과 필요성",
        "공유 데이터 제공 노력",
    ]
    assert words[0].bbox == (10, 12, 60, 22)

