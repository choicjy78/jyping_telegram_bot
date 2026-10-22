"""아이밀·푸드스케치·더이룸 메뉴를 순서대로 전송한다."""
from pathlib import Path
import sys

PROJECT_DIR = Path(__file__).resolve().parent.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from cafeteria import menu_bot


def main():
    return menu_bot.run_all()


if __name__ == "__main__":
    raise SystemExit(main())
