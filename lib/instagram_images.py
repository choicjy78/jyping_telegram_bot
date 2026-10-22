"""Apify Instagram Post Scraper를 통한 피드 이미지 조회."""
import json
import logging
from pathlib import Path
from urllib.parse import urlsplit

import requests

logger = logging.getLogger(__name__)

# Apify Instagram Post Scraper를 동기 실행하고 결과(dataset items)를 바로 받는 엔드포인트
APIFY_RUN_URL = (
    "https://api.apify.com/v2/acts/apify~instagram-post-scraper"
    "/run-sync-get-dataset-items"
)
# Actor 실행에는 수십 초가 걸리므로 공통 timeout(10초)보다 길게 기다린다.
APIFY_MIN_TIMEOUT = 180


def _check_response(response):
    # 과금·인증 오류는 짧은 재시도로 해결되지 않으므로 바로 중단한다.
    messages = {
        400: "Apify HTTP 400: 입력값이 잘못되었습니다.",
        401: "Apify HTTP 401: 전달한 토큰이 올바르지 않습니다.",
        402: "Apify HTTP 402: 크레딧이 부족합니다. Apify 결제/사용량을 확인하세요.",
        403: "Apify HTTP 403: 이 Actor를 실행할 권한이 없습니다.",
        404: "Apify HTTP 404: Actor를 찾지 못했습니다.",
    }
    if response.status_code in messages:
        raise RuntimeError(messages[response.status_code])
    response.raise_for_status()


def _is_pinned(post):
    return bool(post.get("isPinned") or post.get("pinned") or post.get("pinnedForUsers"))


def _log_apify_result(response, debug_path=None):
    """디버깅 로그 실패가 본 처리를 막지 않도록 감싼다."""
    try:
        _write_apify_debug(response, debug_path)
    except Exception:
        logger.exception("Apify 응답 디버그 로그 실패")


def _write_apify_debug(response, debug_path=None):
    """Apify 응답 원문을 파일로 저장하고 요약을 로그에 남긴다."""
    log = logger
    log.info("Apify 응답: status=%s content_type=%s length=%s",
             response.status_code, response.headers.get("Content-Type"), len(response.content or b""))
    try:
        if debug_path is not None:
            debug_path = Path(debug_path)
            debug_path.parent.mkdir(parents=True, exist_ok=True)
            debug_path.write_text(response.text, encoding="utf-8")
            log.info("Apify 응답 원문 저장: %s", debug_path)
    except Exception:
        log.exception("Apify 응답 원문 저장 실패")
    try:
        items = response.json()
    except ValueError:
        log.warning("Apify 응답이 JSON이 아닙니다: %s", response.text[:500])
        return
    if not isinstance(items, list):
        log.warning("Apify 응답이 리스트가 아닙니다: %s", json.dumps(items, ensure_ascii=False)[:500])
        return
    log.info("Apify 결과 항목 수: %s", len(items))
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            log.info("  item[%s] = %r", i, item)
            continue
        log.info("  item[%s] keys=%s", i, sorted(item.keys()))
        log.info("  post[%s] ownerUsername=%s error=%s type=%s isPinned=%r pinned=%r timestamp=%s shortCode=%s displayUrl=%s",
                 i, item.get("ownerUsername"), item.get("error"), item.get("type"),
                 item.get("isPinned"), item.get("pinned"), item.get("timestamp"),
                 item.get("shortCode"), (item.get("displayUrl") or "")[:80])


def _first_feed_image_url(items, skip_pinned=False):
    """Apify 결과에서 선택한 정책에 따른 첫 피드 이미지 URL을 반환한다."""
    if not isinstance(items, list):
        raise RuntimeError("Apify 게시물 응답 형식이 올바르지 않습니다.")
    if not items:
        raise RuntimeError("Apify 게시물 결과가 비어 있습니다. 게시물이 수집되지 않았습니다.")
    for post in items:
        if not isinstance(post, dict):
            raise RuntimeError("Apify 게시물 응답 형식이 올바르지 않습니다.")
        if post.get("error"):
            raise RuntimeError(f"Apify 게시물 조회 오류: {post.get('error')}")
        if skip_pinned and _is_pinned(post):
            continue
        image_url = post.get("displayUrl")  # 슬라이드 게시물이면 첫 장
        if isinstance(image_url, str):
            parsed = urlsplit(image_url)
            if parsed.scheme in ("http", "https") and parsed.netloc:
                return image_url
        raise RuntimeError("인스타그램 첫 번째 피드에 이미지 URL이 없습니다.")
    raise RuntimeError("인스타그램 피드에 고정되지 않은 게시물이 없습니다.")


def find_image_url(username, timeout=10, *, token, skip_pinned=False,
                   results_limit=5, debug_path=None):
    """Apify Instagram Post Scraper로 첫 번째 피드 이미지 URL을 반환한다."""
    logger.info("인스타그램 피드 조회 시작(Apify): username=%s", username)
    try:
        if not token:
            raise RuntimeError("Apify 토큰이 비어 있습니다.")
        response = requests.post(
            APIFY_RUN_URL,
            headers={"Authorization": f"Bearer {token}"},
            json={
                "username": [username],
                "resultsLimit": results_limit,
                "dataDetailLevel": "basicData",
            },
            timeout=max(timeout, APIFY_MIN_TIMEOUT),
        )
        _log_apify_result(response, debug_path)
        _check_response(response)
        image_url = _first_feed_image_url(response.json(), skip_pinned=skip_pinned)
        logger.info("인스타그램 피드 조회 성공(Apify): username=%s", username)
        return image_url
    except Exception:
        logger.exception("인스타그램 피드 조회 실패(Apify): username=%s", username)
        raise

