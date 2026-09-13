# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_handwriting_vlm.py
# 경로: packages/synthetic_engine/tests/test_handwriting_vlm.py
# 목적: VLM 기반 손글씨 인식 어댑터 기능을 테스트함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
import cv2
import numpy as np
import pytest

from synthetic_engine.exporters import handwriting_vlm
from synthetic_engine.exporters.handwriting_vlm import (
    CallableOCRAdapter,
    LocalHandwritingRecognizer,
    LocalRecognitionCandidate,
    OcrCellResult,
    detect_checkbox_state,
    detect_signature_or_seal,
    is_handwritten_region,
    refine_handwritten_cell,
)


# canvas 작업을 수행함
def canvas(width=80, height=80):
    return np.full((height, width, 3), 255, np.uint8)


# checkbox 작업을 수행함
def checkbox(checked):
    image = canvas()
    cv2.rectangle(image, (18, 18), (62, 62), (0, 0, 0), 3)
    if checked:
        cv2.line(image, (28, 40), (38, 52), (0, 0, 0), 4)
        cv2.line(image, (38, 52), (55, 28), (0, 0, 0), 4)
    return image


# handwriting vlm 결과 validates contract 기능의 정상 동작 및 제약조건을 테스트함
def test_handwriting_vlm_result_validates_contract():
    result = OcrCellResult('값', 0.9, 'local_recognizer', (0, 0, 10, 10))
    assert result.cell_metadata == {}
    with pytest.raises(ValueError):
        OcrCellResult('값', 1.1, 'local_recognizer', (0, 0, 10, 10))


# handwriting vlm low 인식 신뢰도 and uniform stroke 규칙 목록 기능의 정상 동작 및 제약조건을 테스트함
def test_handwriting_vlm_low_confidence_and_uniform_stroke_rules():
    image = canvas()
    cv2.line(image, (10, 40), (70, 40), (0, 0, 0), 4)
    assert not is_handwritten_region(image, 0.50)
    assert not is_handwritten_region(image, 0.99)


# handwriting vlm checkbox state 기능의 정상 동작 및 제약조건을 테스트함
@pytest.mark.parametrize(('checked', 'expected'), [(False, False), (True, True)])
def test_handwriting_vlm_checkbox_state(checked, expected):
    assert detect_checkbox_state(checkbox(checked)) == (True, expected)


# handwriting vlm rejects non checkbox 기능의 정상 동작 및 제약조건을 테스트함
def test_handwriting_vlm_rejects_non_checkbox():
    image = canvas()
    cv2.line(image, (10, 40), (70, 40), (0, 0, 0), 3)
    assert detect_checkbox_state(image) == (False, None)


# handwriting vlm detects red seal and black signature 기능의 정상 동작 및 제약조건을 테스트함
def test_handwriting_vlm_detects_red_seal_and_black_signature():
    seal = canvas(100, 80)
    cv2.circle(seal, (50, 40), 22, (0, 0, 210), 5)
    assert detect_signature_or_seal(seal) == (True, 'seal')

    signature = canvas(140, 60)
    points = np.array([[8, 40], [25, 20], [38, 43], [55, 12], [68, 42], [92, 18], [130, 38]], np.int32)
    cv2.polylines(signature, [points], False, (0, 0, 0), 3)
    assert detect_signature_or_seal(signature) == (True, 'signature')


# handwriting vlm checkbox 폴백 is deterministic 기능의 정상 동작 및 제약조건을 테스트함
def test_handwriting_vlm_checkbox_fallback_is_deterministic(monkeypatch):
    monkeypatch.delenv('OCR_VLM_ENABLED', raising=False)
    first = refine_handwritten_cell(checkbox(True), {'bbox': (1, 2, 80, 80)})
    second = refine_handwritten_cell(checkbox(True), {'bbox': (1, 2, 80, 80)})
    assert first == second
    assert first.text == '[선택]'
    assert first.checkbox_checked is True
    assert first.source == 'heuristic_fallback'


# handwriting vlm typed 폴백 normalizes without api 기능의 정상 동작 및 제약조건을 테스트함
def test_handwriting_vlm_typed_fallback_normalizes_without_api(monkeypatch):
    monkeypatch.delenv('OCR_VLM_ENABLED', raising=False)
    image = canvas()
    amount = refine_handwritten_cell(image, {'ocr_text': '1O,5OO원', 'expected_type': 'amount'})
    date = refine_handwritten_cell(image, {'ocr_text': '2O26.9.1O', 'expected_type': 'date'})
    assert amount.text == '10,500'
    assert date.text == '2026-09-10'


# handwriting uses bounded local recognizer 기능의 정상 동작 및 제약조건을 테스트함
def test_handwriting_uses_bounded_local_recognizer(monkeypatch):
    monkeypatch.setattr(handwriting_vlm, 'is_handwritten_region', lambda *_: True)
    local_recognizer = lambda image, context: {
        'text': '홍길동', 'confidence': 0.73, 'engine': 'local-handwriting-test'
    }
    result = refine_handwritten_cell(canvas(), {
        'ocr_confidence': 0.2,
        'expected_type': 'name',
        'local_recognizer': local_recognizer,
    })
    assert result.text == '홍길동'
    assert result.source == 'local_recognizer'
    assert result.confidence == 0.73
    assert result.cell_metadata['review_required'] is True
    assert result.is_handwritten


# default local recognizer is wired when not injected 기능의 정상 동작 및 제약조건을 테스트함
def test_default_local_recognizer_is_wired_when_not_injected(monkeypatch):
    monkeypatch.setattr(handwriting_vlm, 'is_handwritten_region', lambda *_: True)
    recognizer = LocalHandwritingRecognizer([
        CallableOCRAdapter(
            'fake-local',
            lambda image, context: {
                'text': 'A-102',
                'confidence': 0.91,
                'engine': 'fake-local',
            },
        )
    ])
    monkeypatch.setattr(handwriting_vlm, '_default_local_recognizer', lambda: recognizer)

    result = refine_handwritten_cell(canvas(), {
        'ocr_confidence': 0.2,
        'expected_type': 'text',
    })

    assert result.text == 'A-102'
    assert result.source == 'local_recognizer'
    assert result.cell_metadata['engine'] == 'fake-local'
    assert result.cell_metadata['review_required'] is False


# structured candidates need format consensus 기능의 정상 동작 및 제약조건을 테스트함
def test_structured_candidates_need_format_consensus():
    recognizer = LocalHandwritingRecognizer([
        CallableOCRAdapter('rapidocr', lambda *_: {'text': '1O,5OO원', 'confidence': 0.94}),
        CallableOCRAdapter('easyocr', lambda *_: {'text': '10500', 'confidence': 0.90}),
    ])

    decision = recognizer.recognize(canvas(), {'expected_type': 'amount'})

    assert decision is not None
    assert decision.text == '10,500'
    assert decision.review_required is False
    assert decision.agreement_count == 2
    assert decision.valid_format is True


# structured candidates without consensus stay review required 기능의 정상 동작 및 제약조건을 테스트함
def test_structured_candidates_without_consensus_stay_review_required():
    recognizer = LocalHandwritingRecognizer([
        CallableOCRAdapter('rapidocr', lambda *_: {'text': '2026.09.10', 'confidence': 0.98}),
        CallableOCRAdapter('easyocr', lambda *_: {'text': '2026.09.18', 'confidence': 0.96}),
    ])

    decision = recognizer.recognize(canvas(), {'expected_type': 'date'})

    assert decision is not None
    assert decision.review_required is True
    assert decision.agreement_count == 1
    assert decision.valid_format is True


# unavailable local adapter is quietly skipped 기능의 정상 동작 및 제약조건을 테스트함
def test_unavailable_local_adapter_is_quietly_skipped():
    class UnavailableAdapter:
        name = 'missing'

        # recognize 작업을 수행함
        def recognize(self, image, context):
            raise RuntimeError('not installed')

    recognizer = LocalHandwritingRecognizer([
        UnavailableAdapter(),
        CallableOCRAdapter(
            'working',
            lambda *_: LocalRecognitionCandidate('홍길동', 0.92, 'working'),
        ),
    ])

    decision = recognizer.recognize(canvas(), {'expected_type': 'name'})

    assert decision is not None
    assert decision.text == '홍길동'
    assert decision.engine == 'working'


# cloud configuration cannot enable 이미지 transfer 기능의 정상 동작 및 제약조건을 테스트함
def test_cloud_configuration_cannot_enable_image_transfer(monkeypatch):
    monkeypatch.setenv('OCR_VLM_ENABLED', 'true')
    monkeypatch.setenv('OPENAI_API_KEY', 'must-not-be-used')
    monkeypatch.setenv('OCR_VLM_MODEL', 'must-not-be-used')
    monkeypatch.setattr(
        handwriting_vlm,
        '_default_local_recognizer',
        lambda: LocalHandwritingRecognizer([]),
    )

    assert handwriting_vlm.recognize_multilingual_text(canvas(), {}) is None
