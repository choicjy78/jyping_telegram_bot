import datetime
import os
import shutil
import sys
from pathlib import Path

import common

common.load_env_file(Path(__file__).with_name(".env"))

BOT_TOKEN_ENV = "MDEVBOT"
CHAT_ID_ENV = "MDEV_CHATID"
DISK_PATH = "/"

def bot_token():
    return common.get_required_env(BOT_TOKEN_ENV)


def chat_id():
    return common.get_required_env(CHAT_ID_ENV)

def format_bytes(size):
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    value = float(size)

    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024


def get_disk_status(path):
    total, used, free = shutil.disk_usage(path)
    used_percent = (used / total) * 100 if total else 0

    return {
        "path": path,
        "total": total,
        "used": used,
        "free": free,
        "used_percent": used_percent,
    }


def read_meminfo():
    meminfo = {}
    with open("/proc/meminfo", encoding="utf-8") as meminfo_file:
        for line in meminfo_file:
            key, value = line.split(":", 1)
            meminfo[key] = int(value.strip().split()[0]) * 1024
    return meminfo


def get_memory_status():
    meminfo = read_meminfo()
    total = meminfo["MemTotal"]
    available = meminfo.get("MemAvailable", meminfo.get("MemFree", 0))
    used = total - available
    used_percent = (used / total) * 100 if total else 0

    return {
        "total": total,
        "used": used,
        "available": available,
        "used_percent": used_percent,
    }


def build_status_message():
    now = datetime.datetime.now()
    disk = get_disk_status(DISK_PATH)
    memory = get_memory_status()

    return "\n".join(
        [
            f"mobiledev 서버 현재 상태 ({now:%Y-%m-%d %H:%M})",
            "",
            f"디스크({disk['path']}): {format_bytes(disk['used'])} / {format_bytes(disk['total'])} 사용 중 ({disk['used_percent']:.1f}%)",
            f"여유 디스크: {format_bytes(disk['free'])}",
            "",
            f"RAM: {format_bytes(memory['used'])} / {format_bytes(memory['total'])} 사용 중 ({memory['used_percent']:.1f}%)",
            f"사용 가능 RAM: {format_bytes(memory['available'])}",
        ]
    )


def should_send_today(today):
    return today.weekday() < 5


def main():
    if "--dry-run" in sys.argv:
        print(build_status_message())
        return

    today = datetime.date.today()
    if not should_send_today(today):
        print("주말이라 서버 상태 공지를 보내지 않습니다.")
        return

    common.send_telegram_text(bot_token(), chat_id(), build_status_message())
    print("서버 상태 공지를 보냈습니다.")


if __name__ == "__main__":
    main()
