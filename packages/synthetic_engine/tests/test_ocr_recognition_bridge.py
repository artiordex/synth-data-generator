# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_ocr_recognition_bridge.py
# 경로: packages/synthetic_engine/tests/test_ocr_recognition_bridge.py
# 목적: OCR 인식 결과와 IR 트리 매핑 브리지를 테스트함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
import numpy as np

from ocr.pipeline.models import (
    BoundingBox,
    OCRPageResult,
    OCRStatus,
    OCRWord,
    PreprocessingProfile,
)
from synthetic_engine.exporters.ocr_recognition_bridge import recognize_page_words


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
                OCRWord("평가 착안사항", 0.70, BoundingBox(25, 20, 100, 20)),
                OCRWord("데이터 발굴의 배경과 필요성", 0.64, BoundingBox(25, 60, 125, 25)),
                OCRWord("................................", 0.99, BoundingBox(5, 100, 200, 5)),
            )
        else:
            words = (
                OCRWord("이궁뚝용융여무", 0.96, BoundingBox(10, 12, 50, 10)),
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


# recognize 페이지 words selects upscaled attempt and restores 바운딩 박스 기능의 정상 동작 및 제약조건을 테스트함
def test_recognize_page_words_selects_upscaled_attempt_and_restores_bbox(monkeypatch) -> None:
    backend = FakeBackend()
    monkeypatch.setenv("OCR_SMALL_IMAGE_UPSCALE", "2.5")

    image = np.full((120, 160, 3), 255, dtype=np.uint8)
    words = recognize_page_words(image, backend_factory=lambda: backend)

    assert backend.widths == [160, 400]
    assert [word.text for word in words] == [
        "평가 착안사항",
        "데이터 발굴의 배경과 필요성",
    ]
    assert words[0].bbox == (10, 8, 50, 16)
    assert words[1].bbox == (10, 24, 60, 34)

