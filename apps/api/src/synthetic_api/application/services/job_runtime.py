# =============================================================================
# 파일명: job_runtime.py
# 경로: apps/api/src/synthetic_api/application/services/job_runtime.py
# 목적: 백그라운드 작업 상태와 취소 신호를 공통 관리함
# 작성자: 개발팀
# 작성일: 2026-09-09
# 수정일: 2026-09-09
# =============================================================================
"""Shared runtime primitives for API-owned background jobs.

This module is intentionally small: it centralizes the in-process job state that
will later be replaced by an external orchestrator or durable queue.
"""
from __future__ import annotations

from collections.abc import Callable
from threading import Thread

from synthetic_api.infrastructure.repositories.job_repo_impl import JobRepository


TERMINAL_JOB_STATUSES = frozenset({"completed", "failed", "canceled"})
RUNNING_JOB_STATUSES = frozenset({"pending", "processing"})

ACTIVE_TASKS: dict[str, Thread] = {}
CANCEL_FLAGS: dict[str, bool] = {}


def is_terminal(status: str | None) -> bool:
    """작업 상태가 종료 상태인지 확인함"""
    return status in TERMINAL_JOB_STATUSES


def register_cancelable(job_id: str) -> None:
    """작업을 취소 가능한 상태로 등록함"""
    CANCEL_FLAGS[job_id] = False


def request_cancel(job_id: str) -> bool:
    """작업에 취소 신호를 설정함"""
    if job_id not in CANCEL_FLAGS:
        return False
    CANCEL_FLAGS[job_id] = True
    return True


def cancel_requested(job_id: str) -> bool:
    """작업에 취소 요청이 등록되었는지 확인함"""
    return CANCEL_FLAGS.get(job_id, False)


def clear_runtime_job(job_id: str) -> None:
    """작업의 메모리 런타임 상태를 정리함"""
    ACTIVE_TASKS.pop(job_id, None)
    CANCEL_FLAGS.pop(job_id, None)


class JobProgressUpdater:
    """작업 진행률과 메시지를 저장하는 호출 가능 객체임"""
    """Update a persisted synthesis job and honor cooperative cancellation."""

    def __init__(
        self,
        job_id: str,
        repo: JobRepository,
        is_canceled: Callable[[str], bool] = cancel_requested,
    ) -> None:
        """진행률 저장에 사용할 작업 식별자와 저장소를 설정함"""
        self.job_id = job_id
        self.repo = repo
        self.is_canceled = is_canceled

    def __call__(self, pct: int, message: str) -> None:
        """진행률과 메시지를 작업 저장소에 갱신함"""
        if self.is_canceled(self.job_id):
            raise InterruptedError("Job canceled by user")
        job = self.repo.get_by_id(self.job_id)
        if not job:
            return
        job.status = "processing"
        job.progress = pct
        job.message = message
        self.repo.save(job)
