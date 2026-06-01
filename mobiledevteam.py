import datetime
import os
from pathlib import Path

import requests

import common

common.load_env_file(Path(__file__).with_name(".env"))

BOT_TOKEN_ENV = "MDEVBOT"
CHAT_ID_ENV = "MDEV_CHATID"
OPENAI_API_KEY_ENV = "OPENAI_API_KEY"
OPENAI_MODEL_ENV = "OPENAI_MODEL"
DEFAULT_OPENAI_MODEL = "gpt-5.2"
WEATHER_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
WEATHER_LATITUDE = 37.5665
WEATHER_LONGITUDE = 126.9780
WEEKEND_TITLE = "🎉 즐거운 주말 보내세요! 🎉"
WEEKEND_FOOTER = "<b>Happy Weekend!</b>"
WEEKEND_MESSAGE_STYLES = (
    "차분하고 따뜻한 느낌",
    "밝고 에너지 있는 느낌",
    "살짝 재치있고 가벼운 느낌",
    "감성적이지만 과하지 않은 느낌",
    "날씨 이야기를 자연스럽게 살린 느낌",
)

WEATHER_CODE_LABELS = {
    0: "맑음",
    1: "대체로 맑음",
    2: "부분적으로 흐림",
    3: "흐림",
    45: "안개",
    48: "서리 안개",
    51: "약한 이슬비",
    53: "이슬비",
    55: "강한 이슬비",
    61: "약한 비",
    63: "비",
    65: "강한 비",
    71: "약한 눈",
    73: "눈",
    75: "강한 눈",
    80: "약한 소나기",
    81: "소나기",
    82: "강한 소나기",
    95: "뇌우",
    96: "우박 동반 뇌우",
    99: "강한 우박 동반 뇌우",
}

METTING_MESSAGE = """🔔 <b>자. 주간회의 진행 합시다.</b>

📍 <b>장소</b> 우림오피스 14층 601호

📝 <a href="https://mobiledev.makeshop.co.kr/s/mobiledev/p/-Of5JbmCy39">주간회의 회의록</a>
📌 <a href="https://cowave-ms.atlassian.net/jira/software/c/projects/MS/boards/588">Jira - 모바일팀</a>

⏰ <code>늦지 않게 모여주세요.</code>"""

def openai_api_key():
    return os.getenv(OPENAI_API_KEY_ENV)


def openai_model():
    return os.getenv(OPENAI_MODEL_ENV, DEFAULT_OPENAI_MODEL)


def bot_token():
    return common.get_required_env(BOT_TOKEN_ENV)


def chat_id():
    return common.get_required_env(CHAT_ID_ENV)


def weekend_style_for(now):
    return WEEKEND_MESSAGE_STYLES[now.isocalendar().week % len(WEEKEND_MESSAGE_STYLES)]


def weekend_dates(now):
    today = now.date()
    days_until_saturday = (5 - today.weekday()) % 7
    saturday = today + datetime.timedelta(days=days_until_saturday)
    sunday = saturday + datetime.timedelta(days=1)
    return saturday, sunday


def weather_label(code):
    return WEATHER_CODE_LABELS.get(code, f"날씨 코드 {code}")


def get_weekend_weather_summary(now, timeout=10):
    saturday, sunday = weekend_dates(now)
    response = requests.get(
        WEATHER_FORECAST_URL,
        params={
            "latitude": WEATHER_LATITUDE,
            "longitude": WEATHER_LONGITUDE,
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "timezone": "Asia/Seoul",
            "start_date": saturday.isoformat(),
            "end_date": sunday.isoformat(),
        },
        timeout=timeout,
    )
    response.raise_for_status()
    daily = response.json()["daily"]

    summaries = []
    for index, label in enumerate(("토요일", "일요일")):
        weather = weather_label(daily["weather_code"][index])
        min_temp = daily["temperature_2m_min"][index]
        max_temp = daily["temperature_2m_max"][index]
        rain_prob = daily.get("precipitation_probability_max", [None, None])[index]

        rain_text = ""
        if rain_prob is not None:
            rain_text = f", 강수확률 {rain_prob}%"

        summaries.append(f"{label}: {weather}, {min_temp:.0f}~{max_temp:.0f}도{rain_text}")

    return " / ".join(summaries)


def extract_openai_text(data):
    message = data.get("output_text", "").strip()
    if message:
        return message

    text_parts = []
    for output in data.get("output", []):
        for content in output.get("content", []):
            if content.get("type") == "output_text":
                text = content.get("text", "").strip()
                if text:
                    text_parts.append(text)

    return "\n".join(text_parts).strip()


def add_weather_paragraph_spacing(body):
    if "\n\n" in body:
        return body

    weather_markers = ("서울은", "토요일", "이번 주말", "날씨는")
    for marker in weather_markers:
        marker_index = body.find(marker)
        if marker_index > 0:
            return f"{body[:marker_index].rstrip()}\n\n{body[marker_index:].lstrip()}"

    return body


def format_weekend_message(body):
    body = add_weather_paragraph_spacing(body.strip())
    if not body:
        return None
    return f"{WEEKEND_TITLE}\n\n{body}\n\n\n{WEEKEND_FOOTER}"


def generate_weekend_message(now, timeout=15):
    api_key = openai_api_key()
    if not api_key:
        print(f"{OPENAI_API_KEY_ENV} 환경변수가 없어 주말 메시지를 보내지 않습니다.")
        return None

    try:
        weather_summary = get_weekend_weather_summary(now)
    except (requests.RequestException, KeyError, IndexError, TypeError, ValueError) as exc:
        print(f"주말 날씨 조회 실패, 날씨 없이 메시지를 생성합니다: {exc}")
        weather_summary = "날씨 정보를 가져오지 못했습니다."

    response = requests.post(
        "https://api.openai.com/v1/responses",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": openai_model(),
            "input": [
                {
                    "role": "developer",
                    "content": (
                        "너는 (주) 커넥트웨이브 메이크샵 사업부 모바일팀의 텔레그램 봇 메시지 작성자다. "
                        "금요일 저녁에 보낼 주말 인사 메시지의 본문만 작성한다. "
                        "타이틀과 Happy Weekend 문구는 시스템이 따로 붙이므로 절대 출력하지 않는다. "
                        "텔레그램 HTML parse_mode에서 안전한 텍스트만 작성한다. "
                        "HTML 태그를 써야 한다면 <b>, <code>만 사용한다. "
                        "토요일과 일요일 날씨 요약을 자연스럽게 포함한다. "
                        "매주 다른 느낌이 나도록 요청된 분위기를 반영한다. "
                        "본문은 두 문단으로 작성한다. "
                        "첫 문단은 한 주를 마무리하는 기분 좋은 인사말 1~2줄로 작성한다. "
                        "두 번째 문단은 토요일과 일요일 날씨 안내와 주말 제안 2~3줄로 작성한다. "
                        "두 문단 사이에는 반드시 빈 줄을 하나 넣는다. "
                        "전체는 4~6줄로 작성하고, 과장된 표현은 줄이고, 이모지는 적당히 사용한다. "
                        "설명 없이 메시지 본문만 출력한다."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"오늘 날짜는 {now.date().isoformat()}이고 금요일 저녁 6시 주말 인사 메시지를 보낼 시간이다.\n"
                        f"이번 주말 서울 날씨: {weather_summary}\n"
                        f"이번 주 메시지 분위기: {weekend_style_for(now)}"
                    ),
                },
            ],
            "max_output_tokens": 250,
        },
        timeout=timeout,
    )
    response.raise_for_status()

    message = extract_openai_text(response.json())
    return format_weekend_message(message)


def message_for_now(now):
    if now.weekday() == 3 and now.hour == 11:
        return METTING_MESSAGE
    if now.weekday() == 4 and now.hour == 18:
        try:
            return generate_weekend_message(now)
        except requests.HTTPError as exc:
            error_message = exc.response.text if exc.response is not None else str(exc)
            print(f"AI 주말 메시지 생성 실패, 주말 메시지를 보내지 않습니다: {exc} / {error_message}")
            return None
        except requests.RequestException as exc:
            print(f"AI 주말 메시지 생성 실패, 주말 메시지를 보내지 않습니다: {exc}")
            return None
    return None


def main():
    now = datetime.datetime.now()
    message = message_for_now(now)

    if not message:
        print("보낼 매세지가 없습니다.")
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
