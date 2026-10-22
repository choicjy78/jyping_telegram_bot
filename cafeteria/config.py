"""식당 설정. 파일 로딩과 로그 설정은 initialize()에서만 수행한다."""
from dataclasses import dataclass, field
import logging
from pathlib import Path
from types import ModuleType

from lib import env, instagram_images, kakao_images
from lib.logging_utils import configure_logging

PROJECT_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = PROJECT_DIR / "log"
LOG_PATH = LOG_DIR / "kakao_menu.log"
BOT_TOKEN_ENV = "FSBOT"
CHAT_ID_ENV = "FSBOT_CHATID"
MAX_RETRIES = 3
logger = logging.getLogger("cafeteria")


@dataclass(frozen=True)
class Menu:
    name: str
    source: ModuleType
    source_id: str
    caption: str
    lookup_stage: str
    lookup_error_stage: str
    options: dict = field(default_factory=dict)
    token_env: str | None = None


IMEAL = Menu("아이밀", kakao_images, "_vygYn", "오늘의 아이밀 메뉴 입니다!!!😋",
             "카카오 프로필 메뉴 조회", "프로필 메뉴 조회 실패")
THEFOODSKETCH = Menu("푸드스케치", kakao_images, "_nFfwj", "오늘의 푸드스케치 메뉴 입니다!!!😋",
                     "카카오 프로필 메뉴 조회", "프로필 메뉴 조회 실패")
DAE_THEIRUM = Menu("더이룸", instagram_images, "dae_theirum", "오늘의 더이룸 메뉴 입니다!!!😋",
                   "인스타그램 피드 조회", "인스타그램 피드 조회 실패",
                   options={"skip_pinned": True, "results_limit": 5,
                            "debug_path": LOG_DIR / "apify_last_response.json"},
                   token_env="APIFY_TOKEN")
MENUS = (IMEAL, THEFOODSKETCH, DAE_THEIRUM)



def initialize():
    env.load_env_file(PROJECT_DIR / ".env")
    configure_logging(LOG_PATH)
