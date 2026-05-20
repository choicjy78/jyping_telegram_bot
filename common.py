import os

import holidays
import requests


def load_env_file(path, override=False):
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip().strip("\"'")
        if not name:
            continue
        if override or name not in os.environ:
            os.environ[name] = value


def get_required_env(name):
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} 환경변수가 설정되지 않았습니다.")
    return value


def telegram_api_url(bot_token, method):
    return f"https://api.telegram.org/bot{bot_token}/{method}"


def send_telegram_text(bot_token, chat_id, text, timeout=10, parse_mode=None):
    data = {
        "chat_id": chat_id,
        "text": text,
    }
    if parse_mode:
        data["parse_mode"] = parse_mode

    requests.post(
        telegram_api_url(bot_token, "sendMessage"),
        data=data,
        timeout=timeout,
    ).raise_for_status()


def send_telegram_poll(
    bot_token,
    chat_id,
    question,
    options,
    poll_type="regular",
    is_anonymous=False,
    allows_revoting=True,
    allows_multiple_answers=False,
    timeout=10,
):
    payload = {
        "chat_id": chat_id,
        "question": question,
        "options": [{"text": option} for option in options],
        "type": poll_type,
        "is_anonymous": is_anonymous,
        "allows_revoting": allows_revoting,
        "allows_multiple_answers": allows_multiple_answers,
    }
    response = requests.post(
        telegram_api_url(bot_token, "sendPoll"),
        json=payload,
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()["result"]


def stop_telegram_poll(bot_token, chat_id, message_id, timeout=10):
    response = requests.post(
        telegram_api_url(bot_token, "stopPoll"),
        data={
            "chat_id": chat_id,
            "message_id": message_id,
        },
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()["result"]


def get_korean_holiday_name(today):
    kr_holidays = holidays.KR()
    return kr_holidays.get(today)


def is_korean_holiday(today):
    return get_korean_holiday_name(today) is not None
