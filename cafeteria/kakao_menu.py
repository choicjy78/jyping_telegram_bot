import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import time

import requests

import common


PROFILE_API_URL = "https://pf.kakao.com/rocket-web/web/v2/profiles/{channel_id}"
BOT_TOKEN_ENV = "FSBOT"
CHAT_ID_ENV = "FSBOT_CHATID"
MAX_RETRIES = 3

LOG_DIR = Path(__file__).resolve().parent.parent / "log"
LOG_DIR.mkdir(exist_ok=True)
logger = logging.getLogger("cafeteria.kakao_menu")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = RotatingFileHandler(
        LOG_DIR / "kakao_menu.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
        delay=True,
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
logger.propagate = False


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


def _notify_error(bot_token, chat_id, channel_id, stage, exc, timeout):
    try:
        message = f"메뉴봇 오류: {stage} ({channel_id}) - {_error_summary(exc)}"
        if bot_token:
            message = message.replace(bot_token, "[봇 토큰]")
        message = " ".join(message.split())[:200]
        common.send_telegram_text(bot_token, chat_id, message, timeout=timeout)
        logger.info("텔레그램 오류 알림 전송 성공: channel_id=%s stage=%s", channel_id, stage)
    except Exception as notify_exc:
        status_code = getattr(getattr(notify_exc, "response", None), "status_code", None)
        logger.error(
            "텔레그램 오류 알림 전송 실패: channel_id=%s stage=%s error_type=%s status_code=%s",
            channel_id,
            stage,
            type(notify_exc).__name__,
            status_code,
        )


def _is_retryable(exc, photo=False):
    if isinstance(exc, requests.HTTPError):
        status_code = getattr(getattr(exc, "response", None), "status_code", None)
        return status_code == 429 or (status_code is not None and 500 <= status_code < 600)
    if photo:
        return isinstance(exc, requests.ConnectTimeout)
    return isinstance(exc, (requests.Timeout, requests.ConnectionError))


def _wait_for_retry(stage, channel_id, attempt, exc):
    delay = 2 ** (attempt - 1)
    status_code = getattr(getattr(exc, "response", None), "status_code", None)
    logger.warning(
        "%s 재시도 예정: channel_id=%s attempt=%s/%s error_type=%s status_code=%s delay=%ss",
        stage,
        channel_id,
        attempt,
        MAX_RETRIES + 1,
        type(exc).__name__,
        status_code,
        delay,
    )
    time.sleep(delay)


def _find_image_url(channel_id, timeout=10):
    """카카오 채널의 프로필 이미지(오늘의 메뉴) URL을 반환한다."""
    logger.info("카카오 프로필 메뉴 조회 시작: channel_id=%s", channel_id)
    try:
        response = requests.get(
            PROFILE_API_URL.format(channel_id=channel_id),
            timeout=timeout,
        )
        response.raise_for_status()

        for card in response.json().get("cards", []):
            if card.get("type") != "profile":
                continue

            image_url = card.get("profile", {}).get("profile_image", {}).get("url")
            if image_url:
                logger.info("카카오 프로필 메뉴 조회 성공: channel_id=%s", channel_id)
                return image_url.replace("http://", "https://", 1)

        raise RuntimeError(
            f"카카오 채널({channel_id}) 프로필 이미지 URL을 찾지 못했습니다."
        )
    except Exception:
        logger.exception("카카오 프로필 메뉴 조회 실패: channel_id=%s", channel_id)
        raise


def send_menu_photo(bot_token, chat_id, channel_id, caption, timeout=10):
    """카카오 채널의 메뉴 이미지를 텔레그램 채팅으로 전송한다."""
    for attempt in range(1, MAX_RETRIES + 2):
        try:
            image_url = _find_image_url(channel_id, timeout=timeout)
            break
        except Exception as exc:
            if attempt <= MAX_RETRIES and _is_retryable(exc):
                _wait_for_retry("카카오 프로필 메뉴 조회", channel_id, attempt, exc)
                continue
            _notify_error(bot_token, chat_id, channel_id, "프로필 메뉴 조회 실패", exc, timeout)
            raise

    for attempt in range(1, MAX_RETRIES + 2):
        logger.info(
            "텔레그램 메뉴 사진 전송 시작: channel_id=%s attempt=%s/%s",
            channel_id,
            attempt,
            MAX_RETRIES + 1,
        )
        try:
            response = requests.post(
                common.telegram_api_url(bot_token, "sendPhoto"),
                data={
                    "chat_id": chat_id,
                    "photo": image_url,
                    "caption": caption,
                },
                timeout=timeout,
            )
            response.raise_for_status()
            result = response.json().get("result")
            if result is None:
                raise RuntimeError("텔레그램 API 응답에 result가 없습니다.")
            message_id = result.get("message_id") if isinstance(result, dict) else None
            logger.info(
                "텔레그램 메뉴 사진 전송 성공: channel_id=%s message_id=%s attempt=%s/%s",
                channel_id,
                message_id,
                attempt,
                MAX_RETRIES + 1,
            )
            return result
        except Exception as exc:
            status_code = getattr(getattr(exc, "response", None), "status_code", None)
            logger.error(
                "텔레그램 메뉴 사진 전송 실패: channel_id=%s error_type=%s status_code=%s attempt=%s/%s",
                channel_id,
                type(exc).__name__,
                status_code,
                attempt,
                MAX_RETRIES + 1,
            )
            if attempt <= MAX_RETRIES and _is_retryable(exc, photo=True):
                _wait_for_retry("텔레그램 메뉴 사진 전송", channel_id, attempt, exc)
                continue
            _notify_error(bot_token, chat_id, channel_id, "메뉴 사진 전송 실패", exc, timeout)
            raise
