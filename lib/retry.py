"""HTTP 재시도 판단과 지수 대기. 실행 횟수는 호출자가 제어한다."""
import logging
import time

import requests

logger = logging.getLogger(__name__)


def is_retryable(exc, photo=False):
    if isinstance(exc, requests.HTTPError):
        status_code = getattr(getattr(exc, "response", None), "status_code", None)
        return status_code == 429 or (status_code is not None and 500 <= status_code < 600)
    if photo:
        return isinstance(exc, requests.ConnectTimeout)
    return isinstance(exc, (requests.Timeout, requests.ConnectionError))


def wait_for_retry(stage, source_id, attempt, exc, max_retries=3):
    delay = 2 ** (attempt - 1)
    status_code = getattr(getattr(exc, "response", None), "status_code", None)
    logger.warning(
        "%s 재시도 예정: source_id=%s attempt=%s/%s error_type=%s status_code=%s delay=%ss",
        stage,
        source_id,
        attempt,
        max_retries + 1,
        type(exc).__name__,
        status_code,
        delay,
    )
    time.sleep(delay)
