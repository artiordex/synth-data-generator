# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_pdf_retry.py
# 경로: tests/ocr/test_pdf_retry.py
# 목적: PDF 변환 실패 시 단계별 재시도 및 폴백 메커니즘을 테스트함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""PDF retries use in-memory fixtures; the orchestrator owns test execution."""

from dataclasses import replace
from types import SimpleNamespace

import pytest

fitz = pytest.importorskip("pymupdf")
pytest.importorskip("cv2")

from ocr.pdf.pipeline import run_pdf_ocr
from ocr.pdf.rendering import render_page_for_ocr
from ocr.pipeline.models import ErrorCode, OCRPageResult, OCRStatus


# PDF 문서 source 작업을 수행함
@pytest.fixture
def pdf_source(monkeypatch):
    original_open = fitz.open

    # make 작업을 수행함
    def make(*, pages=1, native=False):
        with original_open() as document:
            for index in range(pages):
                page = document.new_page(width=72, height=72)
                if native and index == 0:
                    page.insert_text((2, 20), "Native PDF text", fontsize=7)
            data = document.tobytes()
        monkeypatch.setattr(fitz, "open", lambda *args, **kwargs: original_open(stream=data, filetype="pdf"))
        return "in-memory.pdf"

    return make


class Backend:
    name = "sequence"

    # Backend 인스턴스 멤버 변수 및 초기 설정을 구성함
    def __init__(self, outcomes):
        self.outcomes = iter(outcomes)
        self.calls = []

    # recognize 페이지 작업을 수행함
    def recognize_page(self, image, *, page_no):
        self.calls.append((page_no, image.config.target_dpi))
        outcome = next(self.outcomes)
        if isinstance(outcome, Exception):
            raise outcome
        confidence, text = outcome
        return OCRPageResult(
            page_no=page_no, raw_text=text, normalized_text=text, words=(),
            mean_confidence=confidence, median_confidence=confidence,
            engine=self.name,
        )


# 재시도 improves and stops early 기능의 정상 동작 및 제약조건을 테스트함
def test_retry_improves_and_stops_early(pdf_source):
    backend = Backend([(0.3, "first"), (0.95, "better")])
    result = run_pdf_ocr(pdf_source(), backend=backend)
    assert backend.calls == [(1, 300), (1, 400)]
    assert result.status == OCRStatus.SUCCESS
    assert result.pages[0].raw_text == "better"
    assert result.best_attempts[0] == result.attempts[1]
    assert result.best_attempts[0].dpi == 400
    assert result.best_attempts[0].attempt_no == 2
    assert result.issues == ()
    assert result.plan.source.is_absolute()


# exhaustion keeps earlier best and failure metadata 기능의 정상 동작 및 제약조건을 테스트함
def test_exhaustion_keeps_earlier_best_and_failure_metadata(pdf_source):
    backend = Backend([(0.7, "best"), (0.2, "worse"), RuntimeError("backend failed")])
    result = run_pdf_ocr(pdf_source(), backend=backend)
    assert backend.calls == [(1, 300), (1, 400), (1, 500)]
    assert result.pages[0].raw_text == "best"
    assert result.status == OCRStatus.REVIEW_REQUIRED
    assert result.best_attempts[0].attempt_no == 1
    assert result.attempts[-1].page_result.issues == (ErrorCode.OCR_FAILED,)


# empty high 인식 신뢰도 결과 does not win 기능의 정상 동작 및 제약조건을 테스트함
def test_empty_high_confidence_result_does_not_win(pdf_source):
    result = run_pdf_ocr(pdf_source(), backend=Backend([(0.99, " "), (0.6, "usable")]), max_attempts=2)
    assert result.pages[0].raw_text == "usable"
    assert ErrorCode.OCR_EMPTY_RESULT in result.attempts[0].page_result.issues


# dpi cap deduplicates attempts 기능의 정상 동작 및 제약조건을 테스트함
def test_dpi_cap_deduplicates_attempts(pdf_source):
    backend = Backend([(0.1, "low"), (0.2, "low")])
    result = run_pdf_ocr(pdf_source(), backend=backend, dpi=550)
    assert backend.calls == [(1, 550), (1, 600)]
    assert len(result.attempts) == 2


# native 페이지 and later OCR 인식 survive backend failure 기능의 정상 동작 및 제약조건을 테스트함
def test_native_page_and_later_ocr_survive_backend_failure(pdf_source):
    backend = Backend([RuntimeError("failed"), (0.95, "last")])
    result = run_pdf_ocr(pdf_source(pages=3, native=True), backend=backend, max_attempts=1)
    assert backend.calls == [(2, 300), (3, 300)]
    assert [page.status for page in result.pages] == [
        OCRStatus.NOT_REQUIRED, OCRStatus.FAILED, OCRStatus.SUCCESS,
    ]
    assert result.status == OCRStatus.PARTIAL_SUCCESS
    assert [attempt.page_no for attempt in result.best_attempts] == [2, 3]


# all backend failures are failed 기능의 정상 동작 및 제약조건을 테스트함
def test_all_backend_failures_are_failed(pdf_source):
    result = run_pdf_ocr(pdf_source(), backend=Backend([RuntimeError("failed")]), max_attempts=1)
    assert result.status == OCRStatus.FAILED


# native 텍스트 counts as partial success 기능의 정상 동작 및 제약조건을 테스트함
def test_native_text_counts_as_partial_success(pdf_source):
    result = run_pdf_ocr(pdf_source(pages=2, native=True),
                         backend=Backend([RuntimeError("failed")]), max_attempts=1)
    assert result.status == OCRStatus.PARTIAL_SUCCESS


# budget on 재시도 retains successful render 기능의 정상 동작 및 제약조건을 테스트함
def test_budget_on_retry_retains_successful_render(pdf_source):
    backend = Backend([(0.6, "retained")])
    result = run_pdf_ocr(pdf_source(), backend=backend, max_pixels=90_000)
    assert backend.calls == [(1, 300)]
    assert result.pages[0].raw_text == "retained"
    assert result.best_attempts[0].dpi == 300
    assert len(result.attempts) == 2
    assert result.attempts[1].page_result.issues == (ErrorCode.PDF_RENDER_FAILED,)


# returned failure cannot win on 인식 신뢰도 기능의 정상 동작 및 제약조건을 테스트함
def test_returned_failure_cannot_win_on_confidence(pdf_source):
    class FailedResultBackend(Backend):
        # recognize 페이지 작업을 수행함
        def recognize_page(self, image, *, page_no):
            result = super().recognize_page(image, page_no=page_no)
            return replace(result, status=OCRStatus.FAILED) if len(self.calls) == 1 else result

    result = run_pdf_ocr(pdf_source(), backend=FailedResultBackend([(1.0, "failed"), (0.5, "usable")]), max_attempts=2)
    assert result.pages[0].raw_text == "usable"
    assert result.attempts[0].page_result.status == OCRStatus.FAILED


# render failure is isolated 기능의 정상 동작 및 제약조건을 테스트함
def test_render_failure_is_isolated(pdf_source, monkeypatch):
    from ocr.pdf import pipeline

    original_render = pipeline.render_page_for_ocr

    # render 작업을 수행함
    def render(page, **kwargs):
        if page.number == 0:
            raise RuntimeError("broken page")
        return original_render(page, **kwargs)

    monkeypatch.setattr(pipeline, "render_page_for_ocr", render)
    backend = Backend([(0.95, "second")])
    result = run_pdf_ocr(pdf_source(pages=2), backend=backend)
    assert backend.calls == [(2, 300)]
    assert result.pages[0].issues == (ErrorCode.PDF_RENDER_FAILED,)
    assert result.status == OCRStatus.PARTIAL_SUCCESS
    assert len(result.attempts) == 2


# inspection failure falls back and preserves later 페이지 목록 기능의 정상 동작 및 제약조건을 테스트함
def test_inspection_failure_falls_back_and_preserves_later_pages(pdf_source, monkeypatch):
    original_get_text = fitz.Page.get_text

    # 텍스트 정보를 조회하여 반환함
    def get_text(page, *args, **kwargs):
        if page.number == 0:
            raise RuntimeError("broken text layer")
        return original_get_text(page, *args, **kwargs)

    monkeypatch.setattr(fitz.Page, "get_text", get_text)
    backend = Backend([(0.95, "first"), (0.95, "second")])
    result = run_pdf_ocr(pdf_source(pages=2), backend=backend)
    assert result.status == OCRStatus.SUCCESS
    assert backend.calls == [(1, 300), (2, 300)]
    assert ErrorCode.PDF_TEXT_LAYER_INVALID in result.plan.inspection.pages[0].issues


# pixel budget rejects before allocation 기능의 정상 동작 및 제약조건을 테스트함
def test_pixel_budget_rejects_before_allocation():
    calls = []
    page = SimpleNamespace(rect=fitz.Rect(0, 0, 72, 72), get_pixmap=lambda **kwargs: calls.append(kwargs))
    with pytest.raises(ValueError, match="pixel budget"):
        render_page_for_ocr(page, dpi=300, max_pixels=89_999)
    assert calls == []


# pixel budget exact boundary and 환경 설정 dpi 기능의 정상 동작 및 제약조건을 테스트함
def test_pixel_budget_exact_boundary_and_config_dpi():
    from ocr.pipeline.models import PreprocessingConfig, PreprocessingProfile

    with fitz.open() as document:
        page = document.new_page(width=72, height=72)
        config = PreprocessingConfig(profile=PreprocessingProfile.STANDARD, target_dpi=100)
        image = render_page_for_ocr(page, dpi=300, max_pixels=90_000, config=config)
    assert (image.width_px, image.height_px) == (300, 300)
    assert image.config == replace(config, target_dpi=300)


# invalid 재시도 options fail before open 기능의 정상 동작 및 제약조건을 테스트함
@pytest.mark.parametrize("options", [
    {"dpi": 0}, {"dpi": 601}, {"dpi": float("inf")},
    {"max_attempts": 0}, {"max_attempts": 4}, {"dpi_step": 0},
    {"min_confidence": float("nan")}, {"min_confidence": 1.1},
    {"max_pixels": 0},
])
def test_invalid_retry_options_fail_before_open(monkeypatch, options):
    # unexpected open 작업을 수행함
    def unexpected_open(*args, **kwargs):
        pytest.fail("invalid options must not open the input")

    monkeypatch.setattr(fitz, "open", unexpected_open)
    with pytest.raises(ValueError):
        run_pdf_ocr("unused.pdf", backend=Backend([]), **options)
