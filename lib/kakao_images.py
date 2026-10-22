"""카카오 채널 프로필의 메뉴 이미지 조회."""
import logging

import requests

logger = logging.getLogger(__name__)

PROFILE_API_URL = "https://pf.kakao.com/rocket-web/web/v2/profiles/{channel_id}"

def find_image_url(channel_id, timeout=10):
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

