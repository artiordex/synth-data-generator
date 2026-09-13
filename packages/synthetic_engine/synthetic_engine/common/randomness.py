# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: randomness.py
# 경로: packages/synthetic_engine/synthetic_engine/common/randomness.py
# 목적: 합성 데이터 생성 시 재현성을 위한 난수 시드를 제어함.
# 작성자: AI Agent
# 작성일: 2026-09-13
# 수정일: 2026-09-13
# =============================================================================
from functools import wraps
import random
from threading import RLock

import numpy as np

_PIPELINE_RNG_LOCK = RLock()


# seeded pipeline 작업을 수행함
def seeded_pipeline(method):
    """파이프라인 실행 중 전역 Python·NumPy·Torch 난수를 격리함"""
    # run 작업을 수행함
    @wraps(method)
    def run(self, *args, **kwargs):
        """원래 난수 상태를 보존하면서 대상 메소드를 실행함"""
        # SDV training uses global NumPy/Torch state. Jobs in this process must
        # not reseed one another while training, sampling or applying rules.
        with _PIPELINE_RNG_LOCK:
            py_state, np_state = random.getstate(), np.random.get_state()
            import torch
            devices = list(range(torch.cuda.device_count())) if torch.cuda.is_available() else []
            try:
                with torch.random.fork_rng(devices=devices):
                    random.seed(self.config.seed)
                    np.random.seed(self.config.seed)
                    torch.manual_seed(self.config.seed)
                    if devices:
                        torch.cuda.manual_seed_all(self.config.seed)
                    return method(self, *args, **kwargs)
            finally:
                random.setstate(py_state)
                np.random.set_state(np_state)
    return run
