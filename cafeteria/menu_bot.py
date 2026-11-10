"""식당별 조회·전송·오류 알림과 실행 정책."""
import datetime

import requests

from lib import env, holidays, telegram
from lib.retry import is_retryable, wait_for_retry
from cafeteria import config
from cafeteria.config import (
    BOT_TOKEN_ENV, CHAT_ID_ENV, MAX_RETRIES, logger,
    IMEAL, THEFOODSKETCH, STARVALLEYFOODFORYOU, DAE_THEIRUM, MENUS,
)


def _error_summary(exc):
    response = getattr(exc, "response", None)
    status_code = getattr(response, "status_code", None)
    if status_code is not None:
        summary = f"HTTP {status_code}"
        try:
            payload = response.json()
        except Exception:
            return summary
        if isinstance(payload, dict) and isinstance(payload.get("description"), str):
            return f"{summary}: {payload['description']}"
        return summary
    if isinstance(exc, requests.Timeout):
        return "요청 시간 초과"
    if isinstance(exc, requests.ConnectionError):
        return "연결 실패"
    if isinstance(exc, RuntimeError):
        return " ".join(str(exc).split())
    return type(exc).__name__


def _notify_error(bot_token, chat_id, source_id, stage, exc, timeout):
    try:
        message = f"메뉴봇 오류: {stage} ({source_id}) - {_error_summary(exc)}"
        if bot_token:
            message = message.replace(bot_token, "[봇 토큰]")
        message = " ".join(message.split())[:200]
        telegram.send_text(bot_token, chat_id, message, timeout=timeout)
        logger.info("텔레그램 오류 알림 전송 성공: source_id=%s stage=%s", source_id, stage)
    except Exception as notify_exc:
        status_code = getattr(getattr(notify_exc, "response", None), "status_code", None)
        logger.error(
            "텔레그램 오류 알림 전송 실패: source_id=%s stage=%s error_type=%s status_code=%s",
            source_id,
            stage,
            type(notify_exc).__name__,
            status_code,
        )


def _send_photo(bot_token, chat_id, image_url, caption, source_id, timeout=10):
    """이미 조회한 이미지 URL을 전송한다."""
    for attempt in range(1, MAX_RETRIES + 2):
        logger.info(
            "텔레그램 메뉴 사진 전송 시작: source_id=%s attempt=%s/%s",
            source_id,
            attempt,
            MAX_RETRIES + 1,
        )
        try:
            result = telegram.send_photo(bot_token, chat_id, image_url, caption, timeout=timeout)
            message_id = result.get("message_id") if isinstance(result, dict) else None
            logger.info(
                "텔레그램 메뉴 사진 전송 성공: source_id=%s message_id=%s attempt=%s/%s",
                source_id,
                message_id,
                attempt,
                MAX_RETRIES + 1,
            )
            return result
        except Exception as exc:
            status_code = getattr(getattr(exc, "response", None), "status_code", None)
            logger.error(
                "텔레그램 메뉴 사진 전송 실패: source_id=%s error_type=%s status_code=%s attempt=%s/%s",
                source_id,
                type(exc).__name__,
                status_code,
                attempt,
                MAX_RETRIES + 1,
            )
            if attempt <= MAX_RETRIES and is_retryable(exc, photo=True):
                wait_for_retry("텔레그램 메뉴 사진 전송", source_id, attempt, exc, MAX_RETRIES)
                continue
            _notify_error(bot_token, chat_id, source_id, "메뉴 사진 전송 실패", exc, timeout)
            raise


def send_menu_photo(menu, timeout=10):
    config.initialize()
    bot_token = env.get_required_env(BOT_TOKEN_ENV)
    chat_id = env.get_required_env(CHAT_ID_ENV)
    for attempt in range(1, MAX_RETRIES + 2):
        try:
            options = dict(menu.options)
            if menu.token_env:
                options["token"] = env.get_required_env(menu.token_env)
            image_url = menu.source.find_image_url(menu.source_id, timeout=timeout, **options)
            break
        except Exception as exc:
            if attempt <= MAX_RETRIES and is_retryable(exc):
                wait_for_retry(menu.lookup_stage, menu.source_id, attempt, exc, MAX_RETRIES)
                continue
            _notify_error(bot_token, chat_id, menu.source_id,
                          menu.lookup_error_stage, exc, timeout)
            raise
    return _send_photo(bot_token, chat_id, image_url, menu.caption,
                       menu.source_id, timeout=timeout)


def run_menu(menu):
    config.initialize()
    if holidays.get_korean_holiday_name(datetime.date.today()):
        return
    return send_menu_photo(menu)


def run_all():
    """모든 식당 메뉴 전송에 성공하면 점심 투표를 연다."""
    config.initialize()
    if holidays.get_korean_holiday_name(datetime.date.today()):
        return 0
    failed = False
    for menu in MENUS:
        try:
            send_menu_photo(menu)
        except Exception:
            logger.exception("식당 메뉴 처리 실패: name=%s", menu.name)
            failed = True
    if failed:
        return 1

    bot_token = env.get_required_env(BOT_TOKEN_ENV)
    chat_id = env.get_required_env(CHAT_ID_ENV)
    options = [menu.name for menu in MENUS] + [config.POLL_EXTRA_OPTION]
    try:
        telegram.send_poll(
            bot_token, chat_id, "오늘 점심은 어디서 먹을까요?", options,
            is_anonymous=True, open_period=config.POLL_DURATION_SECONDS,
        )
    except Exception as exc:
        logger.error("텔레그램 점심 투표 전송 실패: error_type=%s", type(exc).__name__)
        _notify_error(bot_token, chat_id, "lunch_poll", "점심 투표 전송 실패", exc, timeout=10)
        return 1
    return 0
