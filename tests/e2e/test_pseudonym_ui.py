"""Run against an isolated preview server via PSEUDONYM_UI_URL."""
import os
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright, expect


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
