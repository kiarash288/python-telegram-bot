import requests
from telegram import Update
from telegram.ext import ContextTypes


# ── API URLs ──────────────────────────────────────────────────────────
TGJU_API = (
    "https://call2.tgju.org/ajax.json"
    "?rev=ZnJtH9UMnDmx3fRLiipjCG5wWUM8cdtyHqUyohjHGjQegGDp7Q573gVniUw3"
)


# ── Helper Functions ──────────────────────────────────────────────────
def _fetch_data():
    """دریافت داده از API تی‌جی‌جی‌یو"""
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/144.0.0.0 Safari/537.36"
            )
        }
        resp = requests.get(TGJU_API, headers=headers, timeout=15)
        resp.raise_for_status()
        return resp.json().get("current", {})
    except Exception as e:
        print(f"TGJU Error: {e}")
        return None


def _to_toman(price_str):
    """تبدیل ریال به تومان با فرمت‌بندی"""
    try:
        val = int(str(price_str).replace(",", "").replace("\t", "").strip())
        return f"{val // 10:,}"
    except (ValueError, TypeError):
        return str(price_str)


def _change_text(dt, dp):
    """آیکون و متن تغییرات قیمت"""
    try:
        dp_val = float(dp)
    except (ValueError, TypeError):
        dp_val = 0.0

    if dp_val > 0 and dt == "high":
        return f"🔺 +{dp}%"
    if dp_val > 0 and dt == "low":
        return f"🔻 -{dp}%"
    return "➖ بدون تغییر"


def _format_time(t):
    """فرمت‌بندی زمان از فیلد t (فارسی مثل ۲۲:۱۷:۳۱)"""
    if not t:
        return "---"
    return str(t).strip()


def _price_line(data, key, label, to_toman=True):
    """ساخت یک خط اطلاعات قیمت"""
    item = data.get(key)
    if not item:
        return None

    p = item.get("p", "---")
    dt = item.get("dt", "")
    dp = item.get("dp", 0)
    ts = item.get("t", "")

    price_display = f"{_to_toman(p)} تومان" if to_toman else f"${p}"
    change = _change_text(dt, dp)
    time = _format_time(ts)

    return f"▫️ {label}:\n   💲 {price_display}  {change}\n   🕐 {time}"


def _get_target(update: Update):
    """دریافت هدف ارسال پیام"""
    if update.callback_query:
        return update.callback_query.message
    return update.message


# ── Gold & Coins ──────────────────────────────────────────────────────
async def get_gold_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش قیمت لحظه‌ای طلا و سکه"""
    data = _fetch_data()
    target = _get_target(update)

    if not data:
        await target.reply_text("❌ خطا در دریافت اطلاعات. لطفاً دوباره تلاش کنید.")
        return

    gold_items = [
        ("geram18", "طلای ۱۸ عیار (هر گرم)"),
        ("geram24", "طلای ۲۴ عیار (هر گرم)"),
        ("mesghal", "مثقال طلا"),
        ("sekee", "سکه امامی"),
        ("sekeb", "سکه بهار آزادی"),
        ("nim", "نیم سکه"),
        ("rob", "ربع سکه"),
        ("gerami", "سکه گرمی"),
    ]

    lines = ["🪙 قیمت لحظه‌ای طلا و سکه\n━━━━━━━━━━━━━━━━━━"]

    for key, label in gold_items:
        line = _price_line(data, key, label)
        if line:
            lines.append(line)

    # اونس جهانی (دلاری)
    ons = data.get("ons", {})
    if ons:
        ons_p = ons.get("p", "---")
        ons_ts = _format_time(ons.get("t", ""))
        lines.append(f"▫️ اونس جهانی طلا:\n   💲 ${ons_p}\n   🕐 {ons_ts}")

    await target.reply_text("\n".join(lines))


# ── Currency ──────────────────────────────────────────────────────────
async def get_currency_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش قیمت لحظه‌ای ارز"""
    data = _fetch_data()
    target = _get_target(update)

    if not data:
        await target.reply_text("❌ خطا در دریافت اطلاعات. لطفاً دوباره تلاش کنید.")
        return

    currency_items = [
        ("price_dollar_rl", "دلار آمریکا"),
        ("price_eur", "یورو"),
        ("price_gbp", "پوند انگلیس"),
        ("price_aed", "درهم امارات"),
        ("price_try", "لیر ترکیه"),
        ("price_cny", "یوان چین"),
        ("price_sar", "ریال عربستان"),
        ("price_cad", "دلار کانادا"),
        ("price_aud", "دلار استرالیا"),
    ]

    lines = ["💵 قیمت لحظه‌ای ارز\n━━━━━━━━━━━━━━━━━━"]

    for key, label in currency_items:
        line = _price_line(data, key, label)
        if line:
            lines.append(line)

    await target.reply_text("\n".join(lines))


# ── Crypto ────────────────────────────────────────────────────────────
async def get_crypto_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش قیمت لحظه‌ای رمز ارزها"""
    data = _fetch_data()
    target = _get_target(update)

    if not data:
        await target.reply_text("❌ خطا در دریافت اطلاعات. لطفاً دوباره تلاش کنید.")
        return

    crypto_list = [
        ("crypto-bitcoin", "crypto-bitcoin-irr", "بیت‌کوین", "BTC"),
        ("crypto-ethereum", "crypto-ethereum-irr", "اتریوم", "ETH"),
        ("crypto-tether", "crypto-tether-irr", "تتر", "USDT"),
        ("crypto-binance-coin", "crypto-binance-coin-irr", "بایننس کوین", "BNB"),
        ("crypto-solana", "crypto-solana-irr", "سولانا", "SOL"),
        ("crypto-ripple", "crypto-ripple-irr", "ریپل", "XRP"),
        ("crypto-cardano", "crypto-cardano-irr", "کاردانو", "ADA"),
        ("crypto-dogecoin", "crypto-dogecoin-irr", "دوج‌کوین", "DOGE"),
        ("crypto-toncoin", "crypto-toncoin-irr", "تون‌کوین", "TON"),
        ("crypto-tron", "crypto-tron-irr", "ترون", "TRX"),
        ("crypto-litecoin", "crypto-litecoin-irr", "لایت‌کوین", "LTC"),
        ("crypto-chainlink", "crypto-chainlink-irr", "چین‌لینک", "LINK"),
        ("crypto-polkadot", "crypto-polkadot-irr", "پولکادات", "DOT"),
        ("crypto-avalanche", "crypto-avalanche-irr", "آوالانچ", "AVAX"),
        ("crypto-monero", "crypto-monero-irr", "مونرو", "XMR"),
    ]

    lines = ["💎 قیمت لحظه‌ای رمز ارزها\n━━━━━━━━━━━━━━━━━━"]

    for usd_key, irr_key, name, symbol in crypto_list:
        usd_item = data.get(usd_key, {})
        irr_item = data.get(irr_key, {})
        if not usd_item:
            continue

        usd_p = usd_item.get("p", "---")
        change = _change_text(usd_item.get("dt", ""), usd_item.get("dp", 0))
        time = _format_time(usd_item.get("t", ""))

        # قیمت تومانی
        irr_line = ""
        if irr_item:
            irr_p = irr_item.get("p", "")
            if irr_p:
                irr_line = f"\n   💰 {_to_toman(irr_p)} تومان"

        lines.append(
            f"▫️ {name} ({symbol}):\n"
            f"   💵 ${usd_p}  {change}{irr_line}\n"
            f"   🕐 {time}"
        )

    await target.reply_text("\n".join(lines))
