import os
from pathlib import Path
import runpy
import sys
import unittest
from unittest.mock import Mock, call, patch


PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from cafeteria import config, menu_bot


class RunAllTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.object(config, "initialize"))
        self.enterContext(patch.dict(os.environ, FSBOT="TEST", FSBOT_CHATID="CHAT"))
        self.send_poll = self.enterContext(patch.object(menu_bot.telegram, "send_poll"))

    def test_sends_poll_after_all_menus_in_order(self):
        delivery = Mock()
        delivery.attach_mock(self.send_poll, "poll")
        with patch.object(menu_bot.holidays, "get_korean_holiday_name", return_value=None), \
                patch.object(menu_bot, "send_menu_photo", delivery.menu):
            self.assertEqual(menu_bot.run_all(), 0)
        self.assertEqual(delivery.mock_calls, [
            call.menu(menu_bot.IMEAL),
            call.menu(menu_bot.THEFOODSKETCH),
            call.menu(menu_bot.STARVALLEYFOODFORYOU),
            call.menu(menu_bot.DAE_THEIRUM),
            call.poll(
                "TEST", "CHAT", "오늘 점심은 어디서 먹을까요?",
                ["아이밀", "담은(구 푸드스케치)", "스타밸리푸드포유", "더이룸", "기타(외식 등)"],
                is_anonymous=True, open_period=config.POLL_DURATION_SECONDS,
            ),
        ])

    def test_one_failure_does_not_skip_other_menus(self):
        with patch.object(menu_bot.holidays, "get_korean_holiday_name", return_value=None), \
                patch.object(menu_bot, "send_menu_photo", side_effect=[None, RuntimeError("실패"), None, None]) as send, \
                patch.object(menu_bot, "logger"):
            self.assertEqual(menu_bot.run_all(), 1)
        self.assertEqual(send.call_args_list, [call(menu) for menu in menu_bot.MENUS])
        self.send_poll.assert_not_called()

    def test_poll_failure_returns_error_without_retrying(self):
        error = RuntimeError("투표 실패")
        self.send_poll.side_effect = error
        with patch.object(menu_bot.holidays, "get_korean_holiday_name", return_value=None), \
                patch.object(menu_bot, "send_menu_photo"), \
                patch.object(menu_bot, "_notify_error") as notify, \
                patch.object(menu_bot, "logger"):
            self.assertEqual(menu_bot.run_all(), 1)
        self.send_poll.assert_called_once()
        notify.assert_called_once_with(
            "TEST", "CHAT", "lunch_poll", "점심 투표 전송 실패", error, timeout=10,
        )

    def test_holiday_skips_every_menu(self):
        with patch.object(menu_bot.holidays, "get_korean_holiday_name", return_value="공휴일"), \
                patch.object(menu_bot, "send_menu_photo") as send:
            self.assertEqual(menu_bot.run_all(), 0)
        send.assert_not_called()
        self.send_poll.assert_not_called()

    def test_individual_scripts_keep_their_entry_points(self):
        for filename, menu in (("imeal.py", menu_bot.IMEAL),
                               ("thefoodsketch.py", menu_bot.THEFOODSKETCH),
                               ("starvalleyfoodforyou.py", menu_bot.STARVALLEYFOODFORYOU),
                               ("dae_theirum.py", menu_bot.DAE_THEIRUM)):
            with self.subTest(filename=filename):
                with patch.object(menu_bot, "run_menu") as run:
                    runpy.run_path(str(PROJECT_DIR / "cafeteria" / filename), run_name="__main__")
                run.assert_called_once_with(menu)
        self.send_poll.assert_not_called()

    def test_combined_script_propagates_exit_code(self):
        with patch.object(menu_bot, "run_all", return_value=1):
            with self.assertRaises(SystemExit) as raised:
                runpy.run_path(str(PROJECT_DIR / "cafeteria/run_all.py"), run_name="__main__")
        self.assertEqual(raised.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
