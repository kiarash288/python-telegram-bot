from datetime import datetime, timezone
from collections import defaultdict

PERSIAN_MONTHS = {
    "فروردین": 1,
    "اردیبهشت": 2,
    "خرداد": 3,
    "تیر": 4,
    "مرداد": 5,
    "شهریور": 6,
    "مهر": 7,
    "آبان": 8,
    "آذر": 9,
    "دی": 10,
    "بهمن": 11,
    "اسفند": 12,
}


def normalize_persian_digits(text: str) -> str:
    digit_map = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
    return text.translate(digit_map)


def gregorian_to_jalali(gy: int, gm: int, gd: int) -> tuple[int, int, int]:
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    if gy > 1600:
        jy = 979
        gy -= 1600
    else:
        jy = 0
        gy -= 621
    gy2 = gm > 2 and gy + 1 or gy
    days = 365 * gy + (gy2 + 3) // 4 - (gy2 + 99) // 100 + (gy2 + 399) // 400 - 80 + gd + g_d_m[gm - 1]
    jy += 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    jm = 1 + (days < 186 and days // 31 or (days - 186) // 30)
    jd = 1 + (days < 186 and days % 31 or (days - 186) % 30)
    return jy, jm, jd


def jalali_to_gregorian(jy: int, jm: int, jd: int) -> tuple[int, int, int]:
    if jy > 979:
        gy = 1600
        jy -= 979
    else:
        gy = 621
    days = 365 * jy + (jy // 33) * 8 + ((jy % 33) + 3) // 4 + 78 + jd
    days += (jm - 1) * 31 if jm < 7 else (jm - 7) * 30 + 186
    gy += 400 * (days // 146097)
    days %= 146097
    if days > 36524:
        gy += 100 * ((days - 1) // 36524)
        days = (days - 1) % 36524
        if days >= 365:
            days += 1
    gy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        gy += (days - 1) // 365
        days = (days - 1) % 365
    gd = days + 1
    sal_a = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    leap = gy % 4 == 0 and (gy % 100 != 0 or gy % 400 == 0)
    if leap:
        sal_a[2] = 29
    gm = 1
    while gm <= 12 and gd > sal_a[gm]:
        gd -= sal_a[gm]
        gm += 1
    return gy, gm, gd


def parse_forecast_args(args: list[str]) -> tuple[str, datetime] | tuple[None, None]:
    if len(args) < 3:
        return None, None
    city = args[0]
    day_text = normalize_persian_digits(args[1])
    month_text = args[2]
    year_text = normalize_persian_digits(args[3]) if len(args) > 3 else None
    try:
        day = int(day_text)
    except ValueError:
        return None, None
    month = PERSIAN_MONTHS.get(month_text)
    if not month:
        return None, None
    if year_text:
        try:
            year = int(year_text)
        except ValueError:
            return None, None
    else:
        now = datetime.now()
        year, _, _ = gregorian_to_jalali(now.year, now.month, now.day)
    gy, gm, gd = jalali_to_gregorian(year, month, day)
    return city, datetime(gy, gm, gd)