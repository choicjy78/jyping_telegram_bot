import requests

import common


PROFILE_API_URL = "https://pf.kakao.com/rocket-web/web/v2/profiles/{channel_id}"
BOT_TOKEN_ENV = "FSBOT"
CHAT_ID_ENV = "FSBOT_CHATID"


def find_image_url(channel_id, timeout=10):
    """카카오 채널의 프로필 이미지(오늘의 메뉴) URL을 반환한다."""
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
            return image_url.replace("http://", "https://", 1)

    raise RuntimeError(
        f"카카오 채널({channel_id}) 프로필 이미지 URL을 찾지 못했습니다."
    )


def send_menu_photo(bot_token, chat_id, channel_id, caption, timeout=10):
    """카카오 채널의 메뉴 이미지를 텔레그램 채팅으로 전송한다."""
    response = requests.post(
        common.telegram_api_url(bot_token, "sendPhoto"),
        data={
            "chat_id": chat_id,
            "photo": find_image_url(channel_id, timeout=timeout),
            "caption": caption,
        },
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json().get("result")
