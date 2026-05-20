import datetime
from pathlib import Path

import common

common.load_env_file(Path(__file__).with_name(".env"))

BOT_TOKEN_ENV = "MDEVBOT"
CHAT_ID_ENV = "MDEV_CHATID"
MESSAGE = """🔔 <b>자. 주간회의 진행 합시다.</b>

📍 <b>장소</b> 우림오피스 14층 601호

⏰ <code>늦지 않게 모여주세요.</code>"""


def bot_token():
    return common.get_required_env(BOT_TOKEN_ENV)


def chat_id():
    return common.get_required_env(CHAT_ID_ENV)


def main():
    today = datetime.date.today()
    holiday_name = common.get_korean_holiday_name(today)
    if holiday_name:
        print(f"공휴일이라 주간회의 알림을 보내지 않습니다: {holiday_name}")
        return

    common.send_telegram_text(bot_token(), chat_id(), MESSAGE, parse_mode="HTML")
    print("주간회의 알림을 보냈습니다.")


if __name__ == "__main__":
    main()
