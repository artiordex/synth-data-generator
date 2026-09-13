# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_confidence_ensemble.py
# 경로: tests/ocr/test_confidence_ensemble.py
# 목적: OCR 신뢰도 기반 앙상블 백엔드 결합 로직을 테스트함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
import numpy as np

from ocr.engine.base import OCRBackend
from ocr.engine.ensemble import ConfidenceEnsembleBackend
from ocr.pipeline.models import (
    BoundingBox,
    OCRPageResult,
    OCRStatus,
    OCRWord,
    PreprocessedImage,
    PreprocessingConfig,
    PreprocessingProfile,
    confidence_stats,
)


class StubBackend(OCRBackend):
    # StubBackend 인스턴스 멤버 변수 및 초기 설정을 구성함
    def __init__(self, name: str, page_words, region_words=()):
        self.name = name
        self.page_words = tuple(page_words)
        self.region_words = tuple(region_words)
        self.page_calls = 0
        self.region_calls = []

    # recognize 페이지 작업을 수행함
    def recognize_page(self, image, *, page_no=1):
        self.page_calls += 1
        return self._result(self.page_words, image, page_no)

    # recognize region 작업을 수행함
    def recognize_region(self, image, bbox, *, page_no=1):
        self.region_calls.append(bbox)
        return self._result(self.region_words, image, page_no)

    # 결과 작업을 수행함
    def _result(self, words, image, page_no):
        mean, median = confidence_stats(words)
        text = "\n".join(word.text for word in words)
        return OCRPageResult(
            page_no=page_no,
            raw_text=text,
            normalized_text=text,
            words=words,
            mean_confidence=mean,
            median_confidence=median,
            engine=self.name,
            profile=image.config.profile,
            status=OCRStatus.SUCCESS,
        )


# 이미지 작업을 수행함
def _image():
    return PreprocessedImage(
        image=np.zeros((100, 200, 3), dtype=np.uint8),
        config=PreprocessingConfig(profile=PreprocessingProfile.STANDARD),
        width_px=200,
        height_px=100,
        applied_steps=(),
    )


# 페이지 with 텍스트 components 작업을 수행함
def _page_with_text_components(*, include_uncovered: bool) -> PreprocessedImage:
    pixels = np.full((100, 200), 255, dtype=np.uint8)
    pixels[10:22, 10:40] = 0
    if include_uncovered:
        pixels[10:22, 110:140] = 0
    return PreprocessedImage(
        image=pixels,
        config=PreprocessingConfig(profile=PreprocessingProfile.STANDARD),
        width_px=200,
        height_px=100,
        applied_steps=(),
    )


# only low 인식 신뢰도 region is rechecked and improved 기능의 정상 동작 및 제약조건을 테스트함
def test_only_low_confidence_region_is_rechecked_and_improved() -> None:
    primary = StubBackend("primary", (
        OCRWord("정확", 0.96, BoundingBox(10, 10, 30, 12)),
        OCRWord("오인식", 0.52, BoundingBox(50, 10, 40, 12)),
    ))
    secondary = StubBackend("secondary", (), (
        OCRWord("교정문", 0.94, BoundingBox(0, 0, 40, 12)),
    ))
    result = ConfidenceEnsembleBackend(primary, secondary).recognize_page(_image())

    assert [word.text for word in result.words] == ["정확", "교정문"]
    assert secondary.region_calls == [(42, 2, 56, 28)]
    assert result.words[1].bbox == BoundingBox(50, 10, 40, 12)


# weaker secondary 결과 does not replace primary 기능의 정상 동작 및 제약조건을 테스트함
def test_weaker_secondary_result_does_not_replace_primary() -> None:
    primary = StubBackend("primary", (
        OCRWord("원문", 0.70, BoundingBox(10, 10, 30, 12)),
    ))
    secondary = StubBackend("secondary", (), (
        OCRWord("후보", 0.50, BoundingBox(0, 0, 30, 12)),
    ))
    result = ConfidenceEnsembleBackend(primary, secondary).recognize_page(_image())

    assert result.words[0].text == "원문"
    assert result.status == OCRStatus.REVIEW_REQUIRED


# duplicate low 인식 신뢰도 regions are rechecked once per backend 기능의 정상 동작 및 제약조건을 테스트함
def test_duplicate_low_confidence_regions_are_rechecked_once_per_backend() -> None:
    shared_box = BoundingBox(50, 10, 40, 12)
    primary = StubBackend("primary", (
        OCRWord("오", 0.52, shared_box),
        OCRWord("인", 0.53, shared_box),
    ))
    secondary = StubBackend("secondary", (), (
        OCRWord("교정", 0.94, BoundingBox(0, 0, 40, 12)),
    ))
    tiebreaker = StubBackend("tesseract", (), (
        OCRWord("교정", 0.90, BoundingBox(0, 0, 40, 12)),
    ))

    result = ConfidenceEnsembleBackend(
        primary, secondary, tiebreaker
    ).recognize_page(_image())

    assert [word.text for word in result.words] == ["교정", "교정"]
    assert secondary.region_calls == [(42, 2, 56, 28)]
    assert tiebreaker.region_calls == [(42, 2, 56, 28)]
    assert result.words[0].bbox == shared_box
    assert result.words[1].bbox == shared_box


# equal scored candidates prefer secondary before tiebreaker 기능의 정상 동작 및 제약조건을 테스트함
def test_equal_scored_candidates_prefer_secondary_before_tiebreaker() -> None:
    primary = StubBackend("primary", (
        OCRWord("원문", 0.40, BoundingBox(10, 10, 30, 12)),
    ))
    secondary = StubBackend("secondary", (), (
        OCRWord("후보", 0.90, BoundingBox(0, 0, 30, 12)),
    ))
    tiebreaker = StubBackend("tesseract", (), (
        OCRWord("동점", 0.90, BoundingBox(0, 0, 30, 12)),
    ))

    result = ConfidenceEnsembleBackend(
        primary, secondary, tiebreaker
    ).recognize_page(_image())

    assert result.words[0].text == "후보"


# secondary detection adds only uncovered 기하 구조 기능의 정상 동작 및 제약조건을 테스트함
def test_secondary_detection_adds_only_uncovered_geometry() -> None:
    first = OCRWord("첫째", 0.96, BoundingBox(10, 10, 30, 12))
    missing = OCRWord("둘째", 0.91, BoundingBox(110, 10, 30, 12))
    primary = StubBackend("primary", (first,))
    secondary = StubBackend("secondary", (first, missing))

    result = ConfidenceEnsembleBackend(primary, secondary).recognize_page(
        _page_with_text_components(include_uncovered=True)
    )

    assert [word.text for word in result.words] == ["첫째", "둘째"]
    assert secondary.page_calls == 1
    assert secondary.region_calls == []


# complete high 인식 신뢰도 detection does not call secondary 기능의 정상 동작 및 제약조건을 테스트함
def test_complete_high_confidence_detection_does_not_call_secondary() -> None:
    first = OCRWord("완료", 0.96, BoundingBox(10, 10, 30, 12))
    primary = StubBackend("primary", (first,))
    secondary = StubBackend("secondary", (first,))

    result = ConfidenceEnsembleBackend(primary, secondary).recognize_page(
        _page_with_text_components(include_uncovered=False)
    )

    assert [word.text for word in result.words] == ["완료"]
    assert secondary.page_calls == 0


# high 인식 신뢰도 implausible korean is rechecked 기능의 정상 동작 및 제약조건을 테스트함
def test_high_confidence_implausible_korean_is_rechecked() -> None:
    primary = StubBackend("primary", (
        OCRWord("이궁뚝용융여무", 0.93, BoundingBox(10, 10, 90, 12)),
    ))
    secondary = StubBackend("secondary", (), (
        OCRWord("데이터 발굴의 배경과 필요성", 0.66, BoundingBox(0, 0, 100, 12)),
    ))

    result = ConfidenceEnsembleBackend(primary, secondary).recognize_page(_image())

    assert [word.text for word in result.words] == ["데이터 발굴의 배경과 필요성"]
    assert secondary.region_calls == [(2, 2, 106, 28)]


# korean 품질 can beat raw 인식 신뢰도 기능의 정상 동작 및 제약조건을 테스트함
def test_korean_quality_can_beat_raw_confidence() -> None:
    primary = StubBackend("primary", (
        OCRWord("곡 극이료 수서위요 더무가지 동격이이금는", 0.86, BoundingBox(10, 10, 130, 12)),
    ))
    secondary = StubBackend("secondary", (), (
        OCRWord("정책 수립이 필요한 분야", 0.62, BoundingBox(0, 0, 130, 12)),
    ))

    result = ConfidenceEnsembleBackend(primary, secondary).recognize_page(_image())

    assert [word.text for word in result.words] == ["정책 수립이 필요한 분야"]
