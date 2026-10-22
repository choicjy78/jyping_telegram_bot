import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import requests


PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from cafeteria import config, menu_bot
from lib import instagram_images, retry, telegram


IMAGE_URL = "https://example.invalid/first.jpg?x=1&y=2"


def post(url, pinned=False):
    return {"displayUrl": url, "isPinned": pinned}


def apify(posts=None, items=None, status_code=200):
    if items is None:
        items = posts or []
    text = json.dumps(items)
    response = Mock(status_code=status_code, text=text, content=text.encode(),
                    headers={"Content-Type": "application/json"})
    response.json.return_value = items
    return response


class InstagramFeedTests(unittest.TestCase):
    def setUp(self):
        initialize = patch.object(config, "initialize")
        initialize.start()
        self.addCleanup(initialize.stop)
        for module in (retry, menu_bot):
            logger_patch = patch.object(module, "logger")
            logger_patch.start()
            self.addCleanup(logger_patch.stop)
        logger_patch = patch.object(instagram_images, "logger")
        logger_patch.start()
        self.addCleanup(logger_patch.stop)
        env_patch = patch.dict(os.environ, {"APIFY_TOKEN": "TEST_APIFY"})
        env_patch.start()
        self.addCleanup(env_patch.stop)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.debug_path = Path(tmp.name) / "apify_last_response.json"

    def lookup(self, token="TEST_APIFY"):
        return instagram_images.find_image_url(
            "dae_theirum", token=token, skip_pinned=True, debug_path=self.debug_path,
        )

    def test_first_feed_image_from_apify(self):
        posts = [post(IMAGE_URL), post("https://example.invalid/second.jpg")]
        with patch.object(instagram_images.requests, "post", return_value=apify(posts)) as call:
            self.assertEqual(self.lookup(), IMAGE_URL)
        call.assert_called_once()
        self.assertEqual(call.call_args.args[0], "https://api.apify.com/v2/acts/apify~instagram-post-scraper/run-sync-get-dataset-items")
        self.assertEqual(call.call_args.kwargs["json"], {"username": ["dae_theirum"], "resultsLimit": 5, "dataDetailLevel": "basicData"})
        self.assertEqual(call.call_args.kwargs["headers"], {"Authorization": "Bearer TEST_APIFY"})
        self.assertGreaterEqual(call.call_args.kwargs["timeout"], instagram_images.APIFY_MIN_TIMEOUT)

    def test_raw_response_is_saved_for_debugging(self):
        with patch.object(instagram_images.requests, "post", return_value=apify([post(IMAGE_URL)])):
            self.lookup()
        saved = json.loads(self.debug_path.read_text(encoding="utf-8"))
        self.assertEqual(saved[0]["displayUrl"], IMAGE_URL)

    def test_debug_logging_failure_does_not_break_lookup(self):
        with patch.object(instagram_images, "_write_apify_debug", side_effect=OSError("disk")), \
                patch.object(instagram_images.requests, "post", return_value=apify([post(IMAGE_URL)])):
            self.assertEqual(self.lookup(), IMAGE_URL)

    def test_pinned_posts_are_skipped(self):
        posts = [post("https://example.invalid/pinned.jpg", pinned=True), post(IMAGE_URL)]
        with patch.object(instagram_images.requests, "post", return_value=apify(posts)):
            self.assertEqual(self.lookup(), IMAGE_URL)

    def test_first_post_without_image_does_not_select_second_post(self):
        posts = [{"isPinned": False}, post("https://example.invalid/second.jpg")]
        with patch.object(instagram_images.requests, "post", return_value=apify(posts)):
            with self.assertRaisesRegex(RuntimeError, "첫 번째 피드"):
                self.lookup()

    def test_empty_or_error_results_raise(self):
        cases = [([], "비어 있습니다"),
                 ([{"error": "not_found"}], "not_found"),
                 ([{"username": "dae_theirum"}], "첫 번째 피드"),
                 ([{"latestPosts": []}], "첫 번째 피드"),
                 ([None], "응답 형식"),
                 ({"error": "invalid"}, "응답 형식")]
        for items, message in cases:
            with self.subTest(items=items):
                with patch.object(instagram_images.requests, "post", return_value=apify(items=items)):
                    with self.assertRaisesRegex(RuntimeError, message):
                        self.lookup()

    def test_all_pinned_posts_raise(self):
        with self.assertRaisesRegex(RuntimeError, "고정되지 않은 게시물"):
            instagram_images._first_feed_image_url([post(IMAGE_URL, pinned=True)], skip_pinned=True)

    def test_image_url_must_be_http(self):
        for value in ("invalid", "file:///tmp/image.jpg", 123):
            with self.subTest(value=value):
                with self.assertRaisesRegex(RuntimeError, "첫 번째 피드"):
                    instagram_images._first_feed_image_url([post(value)])

    def test_missing_token_raises_before_request(self):
        with patch.dict(os.environ, {"APIFY_TOKEN": ""}), \
                patch.object(instagram_images.requests, "post") as call:
            with self.assertRaisesRegex(RuntimeError, "토큰"):
                self.lookup(token="")
        call.assert_not_called()

    def test_apify_errors_stop_without_retry_or_photo(self):
        for status in (401, 402, 403):
            with self.subTest(status=status):
                with patch.object(menu_bot.env, "get_required_env", side_effect=lambda name: {"FSBOT": "TEST_TOKEN", "FSBOT_CHATID": "TEST_CHAT", "APIFY_TOKEN": "TEST_APIFY"}[name]), \
                        patch.object(instagram_images.requests, "post",
                                     return_value=apify(status_code=status)) as call, \
                        patch.object(retry.time, "sleep") as sleep, \
                        patch.object(telegram, "send_text") as notify:
                    with self.assertRaisesRegex(RuntimeError, f"HTTP {status}"):
                        menu_bot.send_menu_photo(menu_bot.DAE_THEIRUM)
                call.assert_called_once()  # Apify 호출 1회, sendPhoto는 호출되지 않음
                sleep.assert_not_called()
                notify.assert_called_once()
                self.assertIn(f"HTTP {status}", notify.call_args.args[2])

    def test_lookup_timeout_uses_existing_retry_and_telegram_delivery(self):
        photo = Mock()
        photo.json.return_value = {"result": {"message_id": 123}}
        with patch.object(menu_bot.env, "get_required_env", side_effect=lambda name: {"FSBOT": "TEST_TOKEN", "FSBOT_CHATID": "TEST_CHAT", "APIFY_TOKEN": "TEST_APIFY"}[name]), \
                patch.object(instagram_images, "find_image_url", side_effect=[requests.Timeout(), IMAGE_URL]) as find, \
                patch.object(instagram_images.requests, "post", return_value=photo) as call, \
                patch.object(retry.time, "sleep") as sleep, \
                patch.object(telegram, "send_text") as notify:
            self.assertEqual(menu_bot.send_menu_photo(menu_bot.DAE_THEIRUM), {"message_id": 123})
        self.assertEqual(find.call_count, 2)
        sleep.assert_called_once_with(1)
        notify.assert_not_called()
        self.assertTrue(call.call_args.args[0].endswith("/sendPhoto"))
        self.assertEqual(call.call_args.kwargs["data"], {
            "chat_id": "TEST_CHAT", "photo": IMAGE_URL,
            "caption": "오늘의 더이룸 메뉴 입니다!!!😋",
        })

    def test_lookup_failure_notifies_without_sending_photo(self):
        with patch.object(menu_bot.env, "get_required_env", side_effect=lambda name: {"FSBOT": "TEST_TOKEN", "FSBOT_CHATID": "TEST_CHAT", "APIFY_TOKEN": "TEST_APIFY"}[name]), \
                patch.object(instagram_images, "find_image_url", side_effect=RuntimeError("피드 없음")), \
                patch.object(instagram_images.requests, "post") as call, \
                patch.object(telegram, "send_text") as notify:
            with self.assertRaises(RuntimeError):
                menu_bot.send_menu_photo(menu_bot.DAE_THEIRUM)
        call.assert_not_called()
        notify.assert_called_once()
        self.assertIn("인스타그램 피드 조회 실패", notify.call_args.args[2])

    def test_holiday_skips_delivery(self):
        with patch.object(menu_bot.holidays, "get_korean_holiday_name", return_value="공휴일"), \
                patch.object(menu_bot, "send_menu_photo") as send:
            menu_bot.run_menu(menu_bot.DAE_THEIRUM)
        send.assert_not_called()


if __name__ == "__main__":
    unittest.main()
