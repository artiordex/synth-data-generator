# -*- coding: utf-8 -*-
# =============================================================================
# 파일명: logging.py
# 경로: apps/api/src/synthetic_api/core/logging.py
# 목적: 구조화된 JSON 및 콘솔 로깅 포맷터를 구성함
# 작성자: 개발팀
# 작성일: 2026-09-09
# 수정일: 2026-09-13
# =============================================================================
import logging

import sys



# setup logging 작업을 수행함
def setup_logging():

    logging.basicConfig(

        level=logging.INFO,

        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",

        handlers=[logging.StreamHandler(sys.stdout)]

    )



logger = logging.getLogger("synthetic_platform")
