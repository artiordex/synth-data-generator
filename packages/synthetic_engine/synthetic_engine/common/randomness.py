"""Isolate the global RNGs used by SDV/PyTorch across pipeline jobs."""
from functools import wraps
import random
from threading import RLock

import numpy as np

_PIPELINE_RNG_LOCK = RLock()


def seeded_pipeline(method):
    @wraps(method)
    def run(self, *args, **kwargs):
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
