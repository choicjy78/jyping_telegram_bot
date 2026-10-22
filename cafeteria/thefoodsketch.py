from pathlib import Path
import sys

PROJECT_DIR = Path(__file__).resolve().parent.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from cafeteria import menu_bot


def send_photo():
    return menu_bot.send_menu_photo(menu_bot.THEFOODSKETCH)


def main():
    return menu_bot.run_menu(menu_bot.THEFOODSKETCH)


if __name__ == "__main__":
    main()
