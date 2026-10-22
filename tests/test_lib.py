from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import requests

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from lib import instagram_images, telegram
from lib.logging_utils import configure_logging


class LibraryTests(unittest.TestCase):
    def test_import_does_not_read_env_or_create_log_files(self):
        script = '''
from unittest.mock import patch
# 외부 패키지의 메타데이터 로딩과 프로젝트 초기화를 구분한다.
import holidays
import requests
with patch("pathlib.Path.read_text", side_effect=AssertionError("file read on import")), \\
     patch("pathlib.Path.mkdir", side_effect=AssertionError("mkdir on import")), \\
     patch("logging.handlers.RotatingFileHandler", side_effect=AssertionError("file logger on import")):
    from lib import env, holidays, instagram_images, kakao_images, telegram, retry
    from cafeteria import config, menu_bot
'''
        result = subprocess.run([sys.executable, "-c", script], cwd=PROJECT_DIR,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_logging_setup_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested/bot.log"
            logger = configure_logging(path, logger_name="test.file_logging")
            try:
                configure_logging(path, logger_name="test.file_logging")
                self.assertEqual(len(logger.handlers), 1)
                logger.info("test message")
                self.assertIn("test message", path.read_text())
            finally:
                for handler in logger.handlers[:]:
                    logger.removeHandler(handler)
                    handler.close()

    def test_telegram_api_does_not_retry_or_send_error_notifications(self):
        with patch.object(telegram.requests, "post", side_effect=requests.ReadTimeout()) as post:
            with self.assertRaises(requests.ReadTimeout):
                telegram.send_photo("TEST", "CHAT", "https://example.invalid/image.jpg")
        post.assert_called_once()
        self.assertTrue(post.call_args.args[0].endswith("/sendPhoto"))

    def test_poll_api_preserves_options_and_result(self):
        response = Mock()
        response.json.return_value = {"result": {"message_id": 123}}
        with patch.object(telegram.requests, "post", return_value=response) as post:
            self.assertEqual(telegram.send_poll("TEST", "CHAT", "선택", ["A", "B"]),
                             {"message_id": 123})
        self.assertTrue(post.call_args.args[0].endswith("/sendPoll"))
        self.assertEqual(post.call_args.kwargs["json"]["options"],
                         [{"text": "A"}, {"text": "B"}])

    def test_instagram_pin_policy_is_optional(self):
        posts = [{"displayUrl": "https://example.invalid/pinned.jpg", "isPinned": True},
                 {"displayUrl": "https://example.invalid/latest.jpg"}]
        self.assertEqual(instagram_images._first_feed_image_url(posts), posts[0]["displayUrl"])
        self.assertEqual(instagram_images._first_feed_image_url(posts, skip_pinned=True),
                         posts[1]["displayUrl"])


if __name__ == "__main__":
    unittest.main()
