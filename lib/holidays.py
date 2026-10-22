"""한국 공휴일 조회."""
import holidays


def get_korean_holiday_name(today):
    kr_holidays = holidays.KR()
    return kr_holidays.get(today)


def is_korean_holiday(today):
    return get_korean_holiday_name(today) is not None
