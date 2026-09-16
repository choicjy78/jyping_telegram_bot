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
WARNING_FREE_PERCENT = 20
CRITICAL_FREE_PERCENT = 10

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
    mem_total = meminfo["MemTotal"]
    mem_free = meminfo.get("MemFree", 0)
    mem_available = meminfo.get("MemAvailable", meminfo.get("MemFree", 0))
    mem_used = mem_total - mem_available
    mem_used_percent = (mem_used / mem_total) * 100 if mem_total else 0
    mem_free_percent = (mem_available / mem_total) * 100 if mem_total else 0

    swap_total = meminfo.get("SwapTotal", 0)
    swap_free = meminfo.get("SwapFree", 0)
    swap_used = swap_total - swap_free
    swap_used_percent = (swap_used / swap_total) * 100 if swap_total else 0
    swap_free_percent = (swap_free / swap_total) * 100 if swap_total else 0

    total_capacity = mem_total + swap_total
    total_available = mem_available + swap_free
    total_used = total_capacity - total_available
    total_used_percent = (total_used / total_capacity) * 100 if total_capacity else 0
    total_free_percent = (total_available / total_capacity) * 100 if total_capacity else 0

    return {
        "mem_total": mem_total,
        "mem_used": mem_used,
        "mem_free": mem_free,
        "mem_available": mem_available,
        "mem_used_percent": mem_used_percent,
        "mem_free_percent": mem_free_percent,
        "swap_total": swap_total,
        "swap_used": swap_used,
        "swap_free": swap_free,
        "swap_used_percent": swap_used_percent,
        "swap_free_percent": swap_free_percent,
        "total_capacity": total_capacity,
        "total_used": total_used,
        "total_available": total_available,
        "total_used_percent": total_used_percent,
        "total_free_percent": total_free_percent,
    }


def get_free_space_level(free_percent):
    if free_percent <= CRITICAL_FREE_PERCENT:
        return "위험"
    if free_percent <= WARNING_FREE_PERCENT:
        return "주의"
    return "정상"


def build_status_message():
    now = datetime.datetime.now()
    disk = get_disk_status(DISK_PATH)
    memory = get_memory_status()
    mem_level = get_free_space_level(memory["mem_free_percent"])
    swap_level = get_free_space_level(memory["swap_free_percent"]) if memory["swap_total"] else "없음"
    total_level = get_free_space_level(memory["total_free_percent"])

    return "\n".join(
        [
            f"*mobiledev 서버 현재 상태 ({now:%Y-%m-%d %H:%M})*",
            "",
            f"디스크({disk['path']}): {format_bytes(disk['used'])} / {format_bytes(disk['total'])} 사용 중 ({disk['used_percent']:.1f}%)",
            f"여유 디스크: {format_bytes(disk['free'])}",
            "",
            f"RAM: {format_bytes(memory['mem_used'])} / {format_bytes(memory['mem_total'])} 사용 중 ({memory['mem_used_percent']:.1f}%)",
            f"빈 RAM(free): {format_bytes(memory['mem_free'])}",
            f"사용 가능 RAM(available): {format_bytes(memory['mem_available'])} ({memory['mem_free_percent']:.1f}%, {mem_level})",
            "",
            f"Swap: {format_bytes(memory['swap_used'])} / {format_bytes(memory['swap_total'])} 사용 중 ({memory['swap_used_percent']:.1f}%)",
            f"남은 Swap: {format_bytes(memory['swap_free'])} ({memory['swap_free_percent']:.1f}%, {swap_level})",
            f"총 남은 공간(RAM+Swap): {format_bytes(memory['total_available'])} / {format_bytes(memory['total_capacity'])} ({memory['total_free_percent']:.1f}%, {total_level})",
            "",
            f"*판단 기준: 남은 비율 {WARNING_FREE_PERCENT}% 이하면 주의, {CRITICAL_FREE_PERCENT}% 이하면 위험*",
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

    common.send_telegram_text(bot_token(), chat_id(), build_status_message(), parse_mode="Markdown")
    print("서버 상태 공지를 보냈습니다.")


if __name__ == "__main__":
    main()
