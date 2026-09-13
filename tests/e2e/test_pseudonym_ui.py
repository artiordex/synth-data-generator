# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_pseudonym_ui.py
# 경로: tests/e2e/test_pseudonym_ui.py
# 목적: 가명화 UI 화면 및 사용자 인터랙션 E2E 테스트를 수행함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Run against an isolated preview server via PSEUDONYM_UI_URL."""
import os
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright, expect


# document and 표(테이블) review 기능의 정상 동작 및 제약조건을 테스트함
@pytest.mark.skipif(not os.getenv('PSEUDONYM_UI_URL'), reason='Preview server URL not configured')
def test_document_and_table_review(tmp_path):
    screenshots = Path(os.getenv('UI_SCREENSHOT_DIR', str(tmp_path)))
    screenshots.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch()
        try:
            page = browser.new_page(viewport={'width': 1440, 'height': 1080})
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(os.environ['PSEUDONYM_UI_URL'])
            page.get_by_role('button', name='가명데이터', exact=True).click()
            expect(page.get_by_text('PDF · HWP · HWPX · DOCX · MD', exact=True)).to_be_visible()
            page.locator('.ps-workspace').screenshot(path=str(screenshots / 'pseudonym-upload.png'))
            page.get_by_label('가명처리 파일 선택').set_input_files({
                'name': '개인정보_처리_검토용_문서.md', 'mimeType': 'text/markdown',
                'buffer': '# 담당자 연락처\n\n이메일: demo@example.org\n\n전화: 010-1234-5678\n\n검토용 문서입니다.'.encode('utf-8')})
            expect(page.get_by_text('문서 검토', exact=True)).to_be_visible(timeout=30000)
            page.get_by_role('button', name='원본 미리보기 열기').click()
            page.get_by_role('button', name='가명처리 실행', exact=True).click()
            expect(page.get_by_role('link', name='MD 다운로드')).to_be_visible(timeout=30000)
            after = page.locator('.ps-preview').last
            expect(after).not_to_contain_text('demo@example.org')
            expect(after).to_contain_text('검토용 문서입니다.')
            page.locator('.ps-workspace').screenshot(path=str(screenshots / 'pseudonym-document-desktop.png'))
            page.set_viewport_size({'width': 390, 'height': 844})
            assert page.locator('.ps-workspace').evaluate('(e) => e.scrollWidth <= e.clientWidth + 1')
            page.evaluate('window.scrollTo(0, 0)')
            page.screenshot(path=str(screenshots / 'pseudonym-document-mobile.png'), full_page=True)
            page.get_by_label('가명처리 파일 선택').set_input_files({
                'name': 'contacts.csv', 'mimeType': 'text/csv',
                'buffer': 'email,department\ndemo@example.org,Research\n'.encode('utf-8')})
            expect(page.get_by_text('데이터 검토', exact=True)).to_be_visible(timeout=30000)
            expect(page.get_by_label('내보내기 형식')).to_have_value('csv')
            expect(page.get_by_role('link', name='MD 다운로드')).to_have_count(0)
            page.get_by_label('일괄 처리방법').select_option('none')
            expect(page.get_by_role('button', name='가명처리 실행', exact=True)).to_be_disabled()
            page.get_by_label('email 처리방법').select_option('mask')
            page.get_by_role('button', name='가명처리 실행', exact=True).click()
            expect(page.get_by_role('link', name='CSV 다운로드')).to_be_visible(timeout=30000)
            page.set_viewport_size({'width': 1440, 'height': 1080})
            page.get_by_role('button', name='원본 미리보기 열기').click()
            page.locator('.ps-workspace').screenshot(path=str(screenshots / 'pseudonym-table-desktop.png'))
            page.get_by_label('email 처리방법').select_option('hash')
            expect(page.get_by_role('link', name='CSV 다운로드')).to_have_count(0)
            assert not errors, errors
        finally:
            browser.close()


# native document exclude rescan and restore 기능의 정상 동작 및 제약조건을 테스트함
@pytest.mark.skipif(not os.getenv('PSEUDONYM_UI_URL'), reason='Preview server URL not configured')
def test_native_document_exclude_rescan_and_restore(tmp_path):
    import pymupdf
    screenshots = Path(os.getenv('UI_SCREENSHOT_DIR', str(tmp_path)))
    screenshots.mkdir(parents=True, exist_ok=True)
    with pymupdf.open() as doc:
        page = doc.new_page(width=400, height=300)
        page.insert_text((40, 60), 'Unchanged heading')
        page.insert_text((40, 100), 'Phone: 010-1234-5678')
        payload = doc.tobytes()
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch()
        try:
            page = browser.new_page(viewport={'width': 1440, 'height': 1080})
            page.goto(os.environ['PSEUDONYM_UI_URL'])
            page.get_by_role('button', name='가명데이터', exact=True).click()
            page.get_by_label('가명처리 파일 선택').set_input_files({
                'name': 'native-review.pdf', 'mimeType': 'application/pdf', 'buffer': payload})
            expect(page.get_by_label('원문 1', exact=True)).to_have_value('010-1234-5678', timeout=30000)
            page.get_by_role('button', name='항목 1 제외', exact=True).click()
            expect(page.get_by_label('원문 1', exact=True)).to_have_count(0)
            page.get_by_role('button', name='재검사', exact=True).click()
            expect(page.get_by_role('button', name='재검사', exact=True)).to_be_enabled()
            expect(page.get_by_label('원문 1', exact=True)).to_have_count(0)
            page.get_by_text('이 문서 제외 목록 · 1개', exact=True).click()
            page.get_by_role('button', name='010-1234-5678 제외 해제', exact=True).click()
            expect(page.get_by_text('이 문서 제외 목록 · 1개', exact=True)).to_have_count(0)
            page.get_by_role('button', name='재검사', exact=True).click()
            expect(page.get_by_label('원문 1', exact=True)).to_have_value('010-1234-5678')
            page.get_by_label('대체값 1', exact=True).fill('010-8765-4321')
            page.get_by_role('button', name='치환 및 검증', exact=True).click()
            expect(page.get_by_role('link', name='검증 완료 · 다운로드')).to_be_visible(timeout=30000)
            with page.expect_download() as download_info:
                page.get_by_role('link', name='검증 완료 · 다운로드').click()
            assert download_info.value.suggested_filename.endswith('.pdf')
            expect(page.get_by_role('link', name='PDF 다운로드')).to_have_count(0)
            expect(page.get_by_alt_text('원본 1페이지')).to_be_visible()
            expect(page.get_by_alt_text('처리본 1페이지')).to_be_visible()
            for img in page.locator('.ps-native-page').all():
                expect(img).to_have_js_property('complete', True)
                assert img.evaluate('(e) => e.naturalWidth') > 0
            page.locator('.ps-workspace').screenshot(path=str(screenshots / 'native-document-desktop.png'))
            page.set_viewport_size({'width': 390, 'height': 844})
            assert page.locator('.ps-workspace').evaluate('(e) => e.scrollWidth <= e.clientWidth + 1')
            page.evaluate('window.scrollTo(0, 0)')
            page.screenshot(path=str(screenshots / 'native-document-mobile.png'), full_page=True)
            page.get_by_role('button', name='항목 1 제외', exact=True).click()
            expect(page.get_by_role('link', name='검증 완료 · 다운로드')).to_have_count(0)
        finally:
            browser.close()


# native document without candidates can be verified and downloaded 기능의 정상 동작 및 제약조건을 테스트함
@pytest.mark.skipif(not os.getenv('PSEUDONYM_UI_URL'), reason='Preview server URL not configured')
def test_native_document_without_candidates_can_be_verified_and_downloaded():
    import pymupdf
    with pymupdf.open() as doc:
        page = doc.new_page(width=400, height=300)
        page.insert_text((40, 60), 'Public report without personal data')
        payload = doc.tobytes()
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch()
        try:
            page = browser.new_page(viewport={'width': 1440, 'height': 1080})
            page.goto(os.environ['PSEUDONYM_UI_URL'])
            page.get_by_role('button', name='가명데이터', exact=True).click()
            page.get_by_label('가명처리 파일 선택').set_input_files({
                'name': 'no-pii.pdf', 'mimeType': 'application/pdf', 'buffer': payload})
            expect(page.get_by_role('button', name='원본 형식 검증 및 다운로드', exact=True)).to_be_visible(timeout=30000)
            page.get_by_role('button', name='원본 형식 검증 및 다운로드', exact=True).click()
            expect(page.get_by_role('link', name='검증 완료 · 다운로드')).to_be_visible(timeout=30000)
            expect(page.get_by_text('유사도 100.0%', exact=False)).to_be_visible()
            with page.expect_download() as download_info:
                page.get_by_role('link', name='검증 완료 · 다운로드').click()
            assert download_info.value.suggested_filename.endswith('.pdf')
        finally:
            browser.close()
