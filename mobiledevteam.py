import datetime
from pathlib import Path

import common

common.load_env_file(Path(__file__).with_name(".env"))

BOT_TOKEN_ENV = "MDEVBOT"
CHAT_ID_ENV = "MDEV_CHATID"
MESSAGE = """🔔 <b>자. 주간회의 진행 합시다.</b>

📍 <b>장소</b> 우림오피스 14층 601호

📝 <a href="https://mobiledev.makeshop.co.kr/s/mobiledev/p/-Of5JbmCy39">주간회의 회의록</a>
📌 <a href="https://cowave-ms.atlassian.net/jira/software/c/projects/MS/boards/588">Jira - 모바일팀</a>

⏰ <code>늦지 않게 모여주세요.</code>"""

WEEKEND_MESSAGE = """🎉 <b>즐거운 주말 보내세요!</b> 🎉

이번 주도 모두 고생 많으셨습니다.
이제부터 불금 모드 ON! 🔥🔥🔥🔥 🪩

🍻 맛있는 거 드시고
🛌 푹 쉬고
✨ 에너지 충전 가득 하세요!

<code>Happy Weekend!</code>"""


def bot_token():
    return common.get_required_env(BOT_TOKEN_ENV)


def chat_id():
    return common.get_required_env(CHAT_ID_ENV)


def message_for_now(now):
    if now.weekday() == 3 and now.hour == 11:
        return MESSAGE
    if now.weekday() == 4 and now.hour == 18:
        return WEEKEND_MESSAGE
    return None


def main():
    now = datetime.datetime.now()
    message = message_for_now(now)

    if not message:
        print("보낼 메시지가 있는 시간이 아닙니다.")
        return

    today = now.date()
    holiday_name = common.get_korean_holiday_name(today)
    if holiday_name:
        print(f"공휴일이라 알림을 보내지 않습니다: {holiday_name}")
        return

    common.send_telegram_text(bot_token(), chat_id(), message, parse_mode="HTML")
    print("알림을 보냈습니다.")


if __name__ == "__main__":
    main()
