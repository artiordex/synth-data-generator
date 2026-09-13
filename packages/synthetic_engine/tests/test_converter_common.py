# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: test_converter_common.py
# 경로: packages/synthetic_engine/tests/test_converter_common.py
# 목적: 문서 변환기 공통 유틸리티 및 기본 기능을 테스트함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock

import pytest

from synthetic_engine.common import bin_finder, com_session


# converter binary module 폴백 기능의 정상 동작 및 제약조건을 테스트함
def test_converter_binary_module_fallback(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, 'executable', str(tmp_path / 'python.exe'))
    monkeypatch.setattr(bin_finder.shutil, 'which', lambda _: None)
    assert bin_finder.find_pyhwp_bin('hwp5html') == [sys.executable, '-m', 'hwp5.hwp5html']
    executable = tmp_path / 'hwp5html.exe'
    executable.touch()
    assert bin_finder.find_pyhwp_bin('hwp5html') == [str(executable)]


# install com 작업을 수행함
def _install_com(monkeypatch, app):
    pythoncom = SimpleNamespace(CoInitialize=Mock(), CoUninitialize=Mock())
    client = ModuleType('win32com.client')
    client.DispatchEx = Mock(return_value=app)
    package = ModuleType('win32com')
    package.client = client
    monkeypatch.setitem(sys.modules, 'pythoncom', pythoncom)
    monkeypatch.setitem(sys.modules, 'win32com', package)
    monkeypatch.setitem(sys.modules, 'win32com.client', client)
    monkeypatch.setattr(com_session, '_process_snapshot', lambda: None)
    return pythoncom, client


# converter com cleanup does not hide original error 기능의 정상 동작 및 제약조건을 테스트함
def test_converter_com_cleanup_does_not_hide_original_error(monkeypatch):
    app = Mock()
    app.Clear.side_effect = RuntimeError('close failed')
    app.Quit.side_effect = RuntimeError('quit failed')
    pythoncom, client = _install_com(monkeypatch, app)
    with pytest.raises(ValueError, match='conversion failed'):
        with com_session.win32_com_session('HWPFrame.HwpObject'):
            raise ValueError('conversion failed')
    client.DispatchEx.assert_called_once_with('HWPFrame.HwpObject')
    app.Clear.assert_called_once_with(1)
    app.Quit.assert_called_once()
    pythoncom.CoUninitialize.assert_called_once()


# converter com dispatch failure balances apartment 기능의 정상 동작 및 제약조건을 테스트함
def test_converter_com_dispatch_failure_balances_apartment(monkeypatch):
    pythoncom, client = _install_com(monkeypatch, Mock())
    client.DispatchEx.side_effect = RuntimeError('not installed')
    with pytest.raises(RuntimeError, match='not installed'):
        with com_session.win32_com_session('Word.Application'):
            pass
    pythoncom.CoInitialize.assert_called_once()
    pythoncom.CoUninitialize.assert_called_once()


# converter com word closes without saving 기능의 정상 동작 및 제약조건을 테스트함
def test_converter_com_word_closes_without_saving(monkeypatch):
    app = Mock()
    pythoncom, _ = _install_com(monkeypatch, app)
    with com_session.win32_com_session('Word.Application') as word:
        assert word is app
    app.Documents.Close.assert_called_once_with(SaveChanges=0)
    app.Quit.assert_called_once_with(SaveChanges=0)
    pythoncom.CoUninitialize.assert_called_once()


# converter com does not own existing process 기능의 정상 동작 및 제약조건을 테스트함
def test_converter_com_does_not_own_existing_process(monkeypatch):
    job_api = SimpleNamespace(CreateJobObject=Mock())
    monkeypatch.setitem(sys.modules, 'win32job', job_api)
    monkeypatch.setitem(sys.modules, 'win32api', SimpleNamespace())
    monkeypatch.setitem(sys.modules, 'win32process', SimpleNamespace(GetWindowThreadProcessId=lambda _: (1, 123)))
    assert com_session._own_job(SimpleNamespace(Hwnd=10), 'Word.Application', {123}) is None
    job_api.CreateJobObject.assert_not_called()


# converter com owned 합성 작업 closed after quit failure 기능의 정상 동작 및 제약조건을 테스트함
def test_converter_com_owned_job_closed_after_quit_failure(monkeypatch):
    app = Mock()
    app.Quit.side_effect = RuntimeError('quit failed')
    pythoncom, _ = _install_com(monkeypatch, app)
    job = Mock()
    monkeypatch.setattr(com_session, '_own_job', lambda *args: job)
    with com_session.win32_com_session('Word.Application'):
        pass
    job.Close.assert_called_once()
    pythoncom.CoUninitialize.assert_called_once()
