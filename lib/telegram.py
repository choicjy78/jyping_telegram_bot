"""텔레그램 API 호출. 봇별 오류 알림·재시도 정책은 호출자가 결정한다."""
import requests


def api_url(bot_token, method):
    return f"https://api.telegram.org/bot{bot_token}/{method}"


def send_text(bot_token, chat_id, text, timeout=10, parse_mode=None):
    data = {
        "chat_id": chat_id,
        "text": text,
    }
    if parse_mode:
        data["parse_mode"] = parse_mode

    requests.post(
        api_url(bot_token, "sendMessage"),
        data=data,
        timeout=timeout,
    ).raise_for_status()


def send_poll(
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
        api_url(bot_token, "sendPoll"),
        json=payload,
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()["result"]


def stop_poll(bot_token, chat_id, message_id, timeout=10):
    response = requests.post(
        api_url(bot_token, "stopPoll"),
        data={
            "chat_id": chat_id,
            "message_id": message_id,
        },
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()["result"]


def send_photo(bot_token, chat_id, image_url, caption="", timeout=10):
    response = requests.post(
        api_url(bot_token, "sendPhoto"),
        data={"chat_id": chat_id, "photo": image_url, "caption": caption},
        timeout=timeout,
    )
    response.raise_for_status()
    result = response.json().get("result")
    if result is None:
        raise RuntimeError("텔레그램 API 응답에 result가 없습니다.")
    return result
