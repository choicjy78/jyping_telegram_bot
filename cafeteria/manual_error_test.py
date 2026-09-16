"""메뉴 조회/전송 실패의 로그와 텔레그램 오류 알림을 수동으로 확인한다."""

import argparse
from contextlib import ExitStack
from pathlib import Path
import sys
from unittest.mock import Mock, patch

import requests


PROJECT_DIR = Path(__file__).resolve().parent.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

import common
import kakao_menu


def preview_message(bot_token, chat_id, text, timeout=10):
    print(f"텔레그램 알림 미리보기: {text}")


def main():
    parser = argparse.ArgumentParser(description="메뉴 오류 로그와 알림을 강제로 테스트합니다.")
    parser.add_argument("stage", choices=("profile", "photo"))
    parser.add_argument("--send", action="store_true", help="설정된 채팅으로 실제 오류 알림을 보냅니다.")
    args = parser.parse_args()

    if args.send:
        common.load_env_file(PROJECT_DIR / ".env")
        bot_token = common.get_required_env(kakao_menu.BOT_TOKEN_ENV)
        chat_id = common.get_required_env(kakao_menu.CHAT_ID_ENV)
    else:
        bot_token = "TEST_TOKEN"
        chat_id = "TEST_CHAT"

    with ExitStack() as patches:
        if not args.send:
            patches.enter_context(patch.object(common, "send_telegram_text", side_effect=preview_message))

        if args.stage == "profile":
            patches.enter_context(
                patch.object(requests, "get", side_effect=requests.Timeout("수동 테스트: 프로필 조회 실패"))
            )
            expected_error = requests.Timeout
        else:
            profile_response = Mock()
            profile_response.json.return_value = {
                "cards": [{
                    "type": "profile",
                    "profile": {"profile_image": {"url": "https://example.invalid/menu.jpg"}},
                }]
            }
            patches.enter_context(patch.object(requests, "get", return_value=profile_response))

            real_post = requests.post

            def fake_photo_post(url, **kwargs):
                if url.endswith("/sendPhoto"):
                    response = requests.Response()
                    response.status_code = 400
                    response._content = b'{"description":"manual test: sendPhoto failure"}'
                    response.url = url
                    return response
                if url.endswith("/sendMessage"):
                    return real_post(url, **kwargs)
                raise RuntimeError("수동 테스트에서 허용하지 않은 HTTP 요청입니다.")

            patches.enter_context(patch.object(requests, "post", side_effect=fake_photo_post))
            expected_error = requests.HTTPError

        try:
            kakao_menu.send_menu_photo(bot_token, chat_id, "TEST", "수동 오류 테스트")
        except expected_error:
            print(f"의도한 {args.stage} 실패가 발생했습니다.")
        else:
            raise AssertionError("강제 실패 테스트에서 오류가 발생하지 않았습니다.")

    print(f"로그 확인: {kakao_menu.LOG_DIR / 'kakao_menu.log'}")


if __name__ == "__main__":
    main()
