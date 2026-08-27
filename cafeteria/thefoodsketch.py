import datetime
from pathlib import Path
import sys


PROJECT_DIR = Path(__file__).resolve().parent.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

import common
import kakao_menu

common.load_env_file(PROJECT_DIR / ".env")

CHANNEL_ID = "_nFfwj"


def bot_token():
    return common.get_required_env(kakao_menu.BOT_TOKEN_ENV)


def chat_id():
    return common.get_required_env(kakao_menu.CHAT_ID_ENV)


def send_photo():
    kakao_menu.send_menu_photo(
        bot_token(),
        chat_id(),
        CHANNEL_ID,
        "오늘의 푸드스케치 메뉴 입니다!!!😋",
    )


def main():
    holiday_name = common.get_korean_holiday_name(datetime.date.today())
    if holiday_name:
        return

    send_photo()


if __name__ == "__main__":
    main()
