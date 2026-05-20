import datetime
import json
import os
import sys
from pathlib import Path
from urllib.parse import quote

import requests

import common

common.load_env_file(Path(__file__).with_name(".env"))

BOT_TOKEN_ENV = "FSBOT"
CHAT_ID_ENV = "FSBOT_CHATID"

# 카카오톡 프로필 관련
CHANNEL_ID = "_nFfwj"
PROFILE_API_URL = f"https://pf.kakao.com/rocket-web/web/v2/profiles/{CHANNEL_ID}"

# 텔레그램 투표 결과
POLL_STATE_FILE = Path(__file__).with_name("thefoodsketch_poll.json")
POLL_GOING_OPTION = "푸스 갈거에요!"
POLL_NOT_GOING_OPTION = "오늘은 패스ㅠ"
POLL_ABSENT = "외부에 있거나 연차 입니다."

# 주변 맛집 검색
NEARBY_RESTAURANT_QUERY = "가산디지털단지역 맛집"

def bot_token():
    return common.get_required_env(BOT_TOKEN_ENV)


def chat_id():
    return common.get_required_env(CHAT_ID_ENV)


# 메뉴 이미지 가져오기
def find_image_url():
    response = requests.get(PROFILE_API_URL, timeout=10)
    response.raise_for_status()
    data = response.json()

    for card in data.get("cards", []):
        if card.get("type") != "profile":
            continue

        profile_image = card.get("profile", {}).get("profile_image", {})
        image_url = profile_image.get("url")
        if image_url:
            return image_url.replace("http://", "https://", 1)

    raise RuntimeError("카카오 채널 프로필 이미지 URL을 찾지 못했습니다.")


def send_photo():
    url = common.telegram_api_url(bot_token(), "sendPhoto")
    image_url = find_image_url()

    requests.post(
        url,
        data={
            "chat_id": chat_id(),
            "photo": image_url,
            "caption": "오늘의 푸드스케치 메뉴 입니다!!!😋"
        },
        timeout=10
    ).raise_for_status()

    print("보냈으니 맛점하삼.😄")


# 투표 메세지 ID 저장
def save_poll_state(message_id):
    POLL_STATE_FILE.write_text(
        json.dumps(
            {
                "date": datetime.date.today().isoformat(),
                "chat_id": chat_id(),
                "message_id": message_id
            }
        ),
        encoding="utf-8"
    )

# JSON 파일에서 메세지 ID 읽어오기
def load_poll_state():
    if not POLL_STATE_FILE.exists():
        raise RuntimeError("저장된 투표 메시지를 찾지 못했습니다.")

    state = json.loads(POLL_STATE_FILE.read_text(encoding="utf-8"))
    today = datetime.date.today().isoformat()
    if state.get("date") != today:
        raise RuntimeError("오늘 생성된 투표 메시지가 아닙니다.")

    return state

# 투표 보내기
def send_poll():
    result = common.send_telegram_poll(
        bot_token(),
        chat_id(),
        "푸스 가실분?",
        [
            POLL_GOING_OPTION,
            POLL_NOT_GOING_OPTION,
            POLL_ABSENT,
        ],
    )
    message_id = result["message_id"]
    save_poll_state(message_id)
    poll = result.get("poll", {})
    if poll.get("allows_revoting") is not True:
        raise RuntimeError(f"투표 재선택 설정이 적용되지 않았습니다: {poll}")

    print("투표 보냈음.")

# 투표 결과에 따라 출발 여부 판단하기
def send_lunch_message_by_poll():
    state = load_poll_state()
    poll = common.stop_telegram_poll(bot_token(), state["chat_id"], state["message_id"])
    print(f"투표 닫음. is_closed={poll.get('is_closed')}, allows_revoting={poll.get('allows_revoting')}")
    going_count = 0
    for option in poll.get("options", []):
        if option.get("text") == POLL_GOING_OPTION:
            going_count = option.get("voter_count", 0)
            break

    if going_count > 0:
        common.send_telegram_text(bot_token(), chat_id(), f"{going_count}명 출발 대기. 지금 출발 할까요?")
    else:
        common.send_telegram_text(bot_token(), chat_id(), build_nearby_restaurant_message())

    print("투표 결과 기준 메시지 보냈음.")


# 가디 주변 맛집 네이버지도 쿼리 연결
def build_nearby_restaurant_message():
    query = quote(NEARBY_RESTAURANT_QUERY)
    return (
        "오늘은 아무도 선택을 안했네요. 주변 맛집 한번 찾아볼까요?\n\n"
        f"https://map.naver.com/p/search/{query}\n"
    )

def main():
    today = datetime.date.today()
    holiday_name = common.get_korean_holiday_name(today)
    if holiday_name:
        print(f"오늘 노는 날이얌. 😏 {holiday_name}")
        return

    mode = sys.argv[1] if len(sys.argv) > 1 else "photo"

    if mode == "finish":
        send_lunch_message_by_poll()
    else:
        send_photo()
        send_poll()


if __name__ == "__main__":
    main()
