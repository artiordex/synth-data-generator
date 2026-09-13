# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: com_session.py
# 경로: packages/synthetic_engine/synthetic_engine/common/com_session.py
# 목적: Windows COM 자동화 세션 수명주기 및 안전 격리를 관리함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
"""Isolated COM ownership and cleanup. Never terminate processes by image name."""
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)


# snapshot 데이터를 처리함
def _process_snapshot():
    try:
        import win32process
        return set(win32process.EnumProcesses())
    except Exception:
        return None


# own 합성 작업 작업을 수행함
def _own_job(app, app_name, existing):
    """Tie only a newly created application's process to this worker's lifetime."""
    if existing is None:
        return None
    job = None
    try:
        import win32api
        import win32job
        import win32process
        if app_name == 'Word.Application':
            hwnd = app.Hwnd
        else:
            hwnd = app.XHwpWindows.Item(0).WindowHandle
        _, pid = win32process.GetWindowThreadProcessId(int(hwnd))
        if not pid or pid in existing:
            return None
        job = win32job.CreateJobObject(None, None)
        info = win32job.QueryInformationJobObject(job, win32job.JobObjectExtendedLimitInformation)
        info['BasicLimitInformation']['LimitFlags'] |= win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        win32job.SetInformationJobObject(job, win32job.JobObjectExtendedLimitInformation, info)
        process = win32api.OpenProcess(0x0100 | 0x0001, False, pid)
        try:
            win32job.AssignProcessToJobObject(job, process)
        finally:
            process.Close()
        return job
    except Exception as exc:
        if job is not None:
            job.Close()
        logger.warning('COM process could not be placed in an owned job: %s', exc)
        return None


# win32 com 세션 작업을 수행함
@contextmanager
def win32_com_session(app_name: str, visible: bool = False):
    import pythoncom
    import win32com.client

    app = job = None
    pythoncom.CoInitialize()
    try:
        existing = _process_snapshot()
        app = win32com.client.DispatchEx(app_name)
        job = _own_job(app, app_name, existing)
        try:
            if app_name == 'HWPFrame.HwpObject':
                app.XHwpWindows.Item(0).Visible = visible
                app.RegisterModule('FilePathCheckDLL', 'FilePathCheckerModule')
            else:
                app.Visible = visible
                app.DisplayAlerts = 0
        except Exception as exc:
            logger.warning('COM application initialization option failed: %s', exc)
        yield app
    finally:
        if app is not None:
            try:
                if app_name == 'HWPFrame.HwpObject':
                    app.Clear(1)
                elif app_name == 'Word.Application':
                    app.Documents.Close(SaveChanges=0)
            except Exception as exc:
                logger.warning('COM document close failed: %s', exc)
            try:
                if app_name == 'Word.Application':
                    app.Quit(SaveChanges=0)
                else:
                    app.Quit()
            except Exception as exc:
                logger.warning('COM application quit failed: %s', exc)
        app = None
        try:
            if job is not None:
                job.Close()
        finally:
            pythoncom.CoUninitialize()
