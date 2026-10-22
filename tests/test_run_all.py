from pathlib import Path
import runpy
import sys
import unittest
from unittest.mock import call, patch


PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from cafeteria import config, menu_bot


class RunAllTests(unittest.TestCase):
    def setUp(self):
        initialize = patch.object(config, "initialize")
        initialize.start()
        self.addCleanup(initialize.stop)

    def test_sends_all_menus_in_order(self):
        with patch.object(menu_bot.holidays, "get_korean_holiday_name", return_value=None), \
                patch.object(menu_bot, "send_menu_photo") as send:
            self.assertEqual(menu_bot.run_all(), 0)
        self.assertEqual(send.call_args_list, [call(menu) for menu in menu_bot.MENUS])

    def test_one_failure_does_not_skip_other_menus(self):
        with patch.object(menu_bot.holidays, "get_korean_holiday_name", return_value=None), \
                patch.object(menu_bot, "send_menu_photo", side_effect=[None, RuntimeError("실패"), None]) as send, \
                patch.object(menu_bot, "logger"):
            self.assertEqual(menu_bot.run_all(), 1)
        self.assertEqual(send.call_args_list, [call(menu) for menu in menu_bot.MENUS])

    def test_holiday_skips_every_menu(self):
        with patch.object(menu_bot.holidays, "get_korean_holiday_name", return_value="공휴일"), \
                patch.object(menu_bot, "send_menu_photo") as send:
            self.assertEqual(menu_bot.run_all(), 0)
        send.assert_not_called()

    def test_individual_scripts_keep_their_entry_points(self):
        for filename, menu in (("imeal.py", menu_bot.IMEAL),
                               ("thefoodsketch.py", menu_bot.THEFOODSKETCH),
                               ("dae_theirum.py", menu_bot.DAE_THEIRUM)):
            with self.subTest(filename=filename):
                with patch.object(menu_bot, "run_menu") as run:
                    runpy.run_path(str(PROJECT_DIR / "cafeteria" / filename), run_name="__main__")
                run.assert_called_once_with(menu)

    def test_combined_script_propagates_exit_code(self):
        with patch.object(menu_bot, "run_all", return_value=1):
            with self.assertRaises(SystemExit) as raised:
                runpy.run_path(str(PROJECT_DIR / "cafeteria/run_all.py"), run_name="__main__")
        self.assertEqual(raised.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
