import sys
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

import requests


PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))
sys.path.insert(0, str(PROJECT_DIR / "cafeteria"))

import kakao_menu


def profile_response():
    response = Mock()
    response.json.return_value = {
        "cards": [{
            "type": "profile",
            "profile": {"profile_image": {"url": "https://example.invalid/menu.jpg"}},
        }]
    }
    return response


def photo_response():
    response = Mock()
    response.json.return_value = {"result": {"message_id": 123}}
    return response


def failed_photo_response(status_code):
    response = Mock(status_code=status_code)
    response.json.return_value = {"description": "test failure"}
    response.raise_for_status.side_effect = requests.HTTPError("test failure", response=response)
    return response


class SendMenuPhotoRetryTests(unittest.TestCase):
    def setUp(self):
        self.notify_patch = patch.object(kakao_menu.common, "send_telegram_text")
        self.sleep_patch = patch.object(kakao_menu.time, "sleep")
        self.logger_patch = patch.object(kakao_menu, "logger")
        self.notify = self.notify_patch.start()
        self.sleep = self.sleep_patch.start()
        self.logger_patch.start()
        self.addCleanup(self.notify_patch.stop)
        self.addCleanup(self.sleep_patch.stop)
        self.addCleanup(self.logger_patch.stop)

    def send(self):
        return kakao_menu.send_menu_photo("TEST_TOKEN", "TEST_CHAT", "TEST", "menu")

    def test_profile_timeout_recovers_without_alert(self):
        with patch.object(kakao_menu.requests, "get", side_effect=[
            requests.Timeout("test"), requests.Timeout("test"), profile_response(),
        ]) as get, patch.object(kakao_menu.requests, "post", return_value=photo_response()) as post:
            self.assertEqual(self.send(), {"message_id": 123})
        self.assertEqual(get.call_count, 3)
        post.assert_called_once()
        self.assertEqual([call.args[0] for call in self.sleep.call_args_list], [1, 2])
        self.notify.assert_not_called()

    def test_profile_timeout_alerts_once_after_three_retries(self):
        with patch.object(kakao_menu.requests, "get", side_effect=requests.Timeout("test")) as get, patch.object(kakao_menu.requests, "post") as post:
            with self.assertRaises(requests.Timeout):
                self.send()
        self.assertEqual(get.call_count, 4)
        post.assert_not_called()
        self.assertEqual([call.args[0] for call in self.sleep.call_args_list], [1, 2, 4])
        self.notify.assert_called_once()
        self.assertIn("프로필 메뉴 조회 실패", self.notify.call_args.args[2])

    def test_photo_server_error_recovers_without_alert(self):
        responses = [failed_photo_response(503), failed_photo_response(503), photo_response()]
        with patch.object(kakao_menu.requests, "get", return_value=profile_response()) as get, patch.object(kakao_menu.requests, "post", side_effect=responses) as post:
            self.assertEqual(self.send(), {"message_id": 123})
        get.assert_called_once()
        self.assertEqual(post.call_count, 3)
        self.assertEqual([call.args[0] for call in self.sleep.call_args_list], [1, 2])
        self.notify.assert_not_called()

    def test_photo_server_error_alerts_once_after_three_retries(self):
        with patch.object(kakao_menu.requests, "get", return_value=profile_response()) as get, patch.object(kakao_menu.requests, "post", return_value=failed_photo_response(503)) as post:
            with self.assertRaises(requests.HTTPError):
                self.send()
        get.assert_called_once()
        self.assertEqual(post.call_count, 4)
        self.assertEqual([call.args[0] for call in self.sleep.call_args_list], [1, 2, 4])
        self.notify.assert_called_once()
        self.assertIn("메뉴 사진 전송 실패", self.notify.call_args.args[2])

    def test_photo_bad_request_and_read_timeout_do_not_retry(self):
        for failure in (failed_photo_response(400), requests.ReadTimeout("test")):
            with self.subTest(failure=type(failure).__name__):
                self.notify.reset_mock()
                self.sleep.reset_mock()
                if isinstance(failure, Exception):
                    post_patch = patch.object(kakao_menu.requests, "post", side_effect=failure)
                else:
                    post_patch = patch.object(kakao_menu.requests, "post", return_value=failure)
                with patch.object(kakao_menu.requests, "get", return_value=profile_response()), post_patch as post:
                    with self.assertRaises((requests.HTTPError, requests.ReadTimeout)):
                        self.send()
                post.assert_called_once()
                self.sleep.assert_not_called()
                self.notify.assert_called_once()


if __name__ == "__main__":
    unittest.main()
