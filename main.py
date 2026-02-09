import requests
import time
from collections import defaultdict
from dotenv import load_dotenv
import os
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
load_dotenv()
from weather_advanced import (
    weather_command,
    forecast_command,
    get_current_weather,
    get_forecast_weather,
)
from date import parse_forecast_args
from datetime import datetime, timedelta
import jdatetime
from bot_ai import handle_message
from main_ai import AIAgent
from gold import get_gold_price, get_currency_price, get_crypto_price
BOT_TOKEN = os.getenv("API_TELEGRAM")
MY_ID = os.getenv("MY_ID")

# ── Anti-Spam ─────────────────────────────────────────────────────────
SPAM_MAX_MESSAGES = 5        # حداکثر تعداد پیام مجاز
SPAM_TIME_WINDOW = 10        # در بازه زمانی (ثانیه)
SPAM_BAN_DURATION = 30 * 60  # مدت بلاک (۳۰ دقیقه)

_user_messages: dict[int, list[float]] = defaultdict(list)
_banned_users: dict[int, float] = {}


async def check_spam(update: Update) -> bool:
    """بررسی اسپم بودن کاربر. True برمی‌گرداند اگر باید نادیده گرفته شود."""
    user = update.effective_user
    if user is None:
        return False

    user_id = user.id
    now = time.time()

    # اگه بلاک شده، چک کن هنوز وقتش تموم نشده
    if user_id in _banned_users:
        ban_expires = _banned_users[user_id]
        if now < ban_expires:
            remaining = int(ban_expires - now)
            minutes = remaining // 60
            seconds = remaining % 60
            msg = update.effective_message
            if msg:
                await msg.reply_text(
                    f"🚫 به دلیل ارسال پیام زیاد، دسترسی شما به مدت "
                    f"{minutes} دقیقه و {seconds} ثانیه مسدود است.\n"
                    f"لطفاً کمی صبر کنید."
                )
            return True
        else:
            # بلاک تموم شده
            del _banned_users[user_id]
            _user_messages[user_id].clear()

    # ثبت پیام و حذف پیام‌های قدیمی‌تر از بازه زمانی
    timestamps = _user_messages[user_id]
    timestamps.append(now)
    _user_messages[user_id] = [t for t in timestamps if now - t <= SPAM_TIME_WINDOW]

    # اگه تعداد پیام‌ها از حد مجاز بیشتر شد → بلاک
    if len(_user_messages[user_id]) > SPAM_MAX_MESSAGES:
        _banned_users[user_id] = now + SPAM_BAN_DURATION
        _user_messages[user_id].clear()
        msg = update.effective_message
        if msg:
            await msg.reply_text(
                "🚫 شما به دلیل ارسال پیام بیش از حد، به مدت ۳۰ دقیقه مسدود شدید.\n"
                "لطفاً بعداً دوباره تلاش کنید."
            )
        return True

    return False

# ایراد اصلی این تعریف button این است که ساختارش بیش از حد تو در تو (nested) است و باعث می‌شود 
# دکمه‌ها به‌صورت دلخواه در ردیف و ستون نمایش داده نشوند.
# ساختار صحیح در InlineKeyboardMarkup، باید یک لیست از ردیف‌ها باشد و هر ردیف، یک لیست از دکمه‌ها.
# یعنی: [[Button, Button], [Button], ...] و نه [[[Button], [Button]], ...] 
# بر این اساس بازنویسی صحیح:

button = [
    [InlineKeyboardButton("🌤️آب و هوا", callback_data="weather"),
     InlineKeyboardButton("🪙قیمت طلا", callback_data="gold")],
    [InlineKeyboardButton("💵قیمت ارز", callback_data="currency"),
     InlineKeyboardButton("💎ارز دیجیتال", callback_data="crypto")],
    [InlineKeyboardButton("🤖هوش مصنوعی", callback_data="ai"),
     InlineKeyboardButton("👨‍💻 ارتباط با سازنده", callback_data="contact")],
    [InlineKeyboardButton("⬅️بازگشت", callback_data="back")]
]

weather_inline_button = [
    [InlineKeyboardButton("🌤 وضعیت فعلی", callback_data="weather_current"),
     InlineKeyboardButton("📅 پیش بینی", callback_data="weather_forecast")],
    [InlineKeyboardButton("⬅️بازگشت", callback_data="back")],
]

_CITY_CHOICES = [
    "تهران", "مشهد", "اصفهان", "شیراز", "تبریز", "اهواز",
    "کرج", "قم", "کرمانشاه", "ارومیه", "رشت", "یزد",
    "کازرون", "قشم", "کیش", "مازندران", "گیلان", "بندر عباس",
]


def _build_city_keyboard(prefix: str) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for i in range(0, len(_CITY_CHOICES), 3):
        row = [
            InlineKeyboardButton(city, callback_data=f"{prefix}:{city}")
            for city in _CITY_CHOICES[i:i + 3]
        ]
        rows.append(row)
    rows.append([InlineKeyboardButton("⬅️بازگشت", callback_data="back")])
    return InlineKeyboardMarkup(rows)


def _to_persian_digits(text: str) -> str:
    return text.translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def _build_forecast_dates_keyboard() -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    today = datetime.now().date()
    row: list[InlineKeyboardButton] = []
    for offset in range(1, 5):
        target_date = today + timedelta(days=offset)
        iso_label = target_date.strftime("%Y-%m-%d")
        jdate = jdatetime.date.fromgregorian(date=target_date)
        month_names = [
            "فروردین", "اردیبهشت", "خرداد", "تیر",
            "مرداد", "شهریور", "مهر", "آبان",
            "آذر", "دی", "بهمن", "اسفند",
        ]
        day_label = _to_persian_digits(str(jdate.day))
        label = f"{day_label} {month_names[jdate.month - 1]}"
        row.append(InlineKeyboardButton(label, callback_data=f"weather_date:{iso_label}"))
    rows.append(row)
    rows.append([InlineKeyboardButton("⬅️بازگشت", callback_data="back")])
    return InlineKeyboardMarkup(rows)

reply_button = ReplyKeyboardMarkup(
    [
        ["🌤️آب و هوا", "🪙قیمت طلا"],
        ["💵قیمت ارز", "💎ارز دیجیتال"],
        ["🤖هوش مصنوعی", "👨‍💻 ارتباط با سازنده"],
        ["⬅️بازگشت"],
    ],
    resize_keyboard=True,
    is_persistent=True,
)

weather_reply_button = ReplyKeyboardMarkup(
    [
        ["🌤 وضعیت فعلی", "📅 پیش بینی"],
        ["⬅️بازگشت"],
    ],
    resize_keyboard=True,
    is_persistent=True,
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if message is None:
        return
    await message.reply_text("""🤖 به ربات هوشمند «کیارش» خوش آمدید!

من اینجا هستم تا کارهای روزمره‌ت رو سریع‌تر و راحت‌تر کنم. با کیارش می‌تونی به کلی امکانات در یک جا دسترسی داشته باشی:

🪙 قیمت طلا و سکه: مشاهده لحظه‌ای قیمت انواع طلا و سکه.

💵 قیمت ارز: مشاهده لحظه‌ای قیمت دلار، یورو و سایر ارزها.

💎 ارز دیجیتال: مشاهده لحظه‌ای قیمت بیت‌کوین، اتریوم، تتر و سایر رمز ارزها.

🧠 هوش مصنوعی: گفتگو، پرسش و پاسخ، و حل مسائل با قدرت AI.

🌤️ آب و هوا: چک کردن وضعیت جوی و پیش‌بینی هوای تمام شهرهای ایران و جهان.

👨‍💻 ارتباط با سازنده: ارتباط با سازنده ربات برای دریافت اطلاعات بیشتر.

همین حالا دکمه START رو بزن تا با هم شروع کنیم! 👇  """,
    reply_markup=InlineKeyboardMarkup(button))
    await message.reply_text("منوی اصلی 👇", reply_markup=reply_button)


async def tutorial_weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if message is None:
        return
    await message.reply_text("""🌦 راهنمای بخش هواشناسی

من می‌تونم وضعیت آب و هوای هر شهری رو بهت بگم!
فقط کافیه طبق الگوهای زیر بنویسی:

1️⃣ آب و هوای الان:
دکمه «وضعیت فعلی» رو بزن و بعد اسم شهر رو بفرست.
مثال:  Shiraz یا شیراز

2️⃣ پیش‌بینی روزهای آینده:
دکمه «پیش بینی» رو بزن و بعد اسم شهر + تاریخ رو بفرست.
مثال:  Shiraz 20 Bahman یا شیراز ۲۰ بهمن

⚠️ نکته: نام شهر رو می‌تونی فارسی یا انگلیسی بنویسی.""")

async def tutorial_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if message is None:
        return
    await message.reply_text("""🧠 بخش هوش مصنوعی کیارش

من اینجا هستم تا مثل یک دستیار هوشمند در کنارت باشم. هر سوالی داری، از مسائل درسی و برنامه‌نویسی گرفته تا مشورت برای کارهای روزمره، فقط کافیه برام بنویسی!

چه کارهایی می‌تونم انجام بدم؟

🚀 پاسخ به سوالات: هر چیزی که برات سواله رو بپرس.

💻 کمک در کدنویسی: اگر توی پروژه‌هات به مشکل خوردی، روی من حساب کن.

✍️ نوشتن متن: از ایمیل رسمی تا کپشن اینستاگرام رو برات می‌نویسم.

💡 ایده‌پردازی: برای پروژه‌ها یا کارهای شخصیت بهت ایده میدم.""")

async def contact_developer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if message is None:
        return
    await message.reply_text(
        f"سلام رفیق! 👋\n"
        f"\n"
        f"این ربات هنوز داره رشد می‌کنه و هر روز\n"
        f"قابلیت‌های جدیدی بهش اضافه میشه 🚀\n"
        f"\n"
        f"🐛 اگه جایی باگ دیدی، بهم بگو\n"
        f"💡 اگه ایده‌ای داری، خوشحال میشم بشنوم\n"
        f"\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👨‍💻 ارتباط با سازنده: {MY_ID}"
    )

async def welcome_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if message is None or not message.new_chat_members:
        return
    for member in message.new_chat_members:
        if member.is_bot:
            continue
        name = member.first_name or "دوست عزیز"
        await message.reply_text(
            f"👋 سلام {name}! به گروه خوش اومدی. "
            "برای شروع می‌تونی /start رو بزن و با امکانات ربات آشنا شو."
        )

def _is_addressed_in_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    message = update.message
    if message is None:
        return False
    if message.reply_to_message and message.reply_to_message.from_user:
        if message.reply_to_message.from_user.id == context.bot.id:
            return True
    bot_username = context.bot.username
    if bot_username and f"@{bot_username}" in message.text:
        return True
    return False


_MENU_BUTTONS = {
    "🌤️آب و هوا", "🤖هوش مصنوعی", "🪙قیمت طلا",
    "💵قیمت ارز", "💎ارز دیجیتال", "👨‍💻 ارتباط با سازنده", "⬅️بازگشت",
    "🌤 وضعیت فعلی", "📅 پیش بینی",
}


async def message_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if message is None:
        return
    if message.chat.type in ("group", "supergroup"):
        if not _is_addressed_in_group(update, context):
            return
    text = message.text or ""
    bot_username = context.bot.username
    if bot_username:
        text = text.replace(f"@{bot_username}", "").strip()

    # ── دکمه‌های منو همیشه کار کنن (بدون بررسی اسپم) ──
    if text == "🌤️آب و هوا":
        context.user_data["mode"] = "weather_menu"
        await message.reply_text(
            "یکی از گزینه‌های هواشناسی رو انتخاب کن 👇",
            reply_markup=InlineKeyboardMarkup(weather_inline_button),
        )
        await message.reply_text("منوی هواشناسی 👇", reply_markup=weather_reply_button)
        return
    if text == "🌤 وضعیت فعلی":
        context.user_data["mode"] = "weather_current"
        await message.reply_text(
            "یکی از شهرهای زیر رو انتخاب کن 👇\n"
            "اگر تو لیست نبود، اسم شهر رو انگلیسی بنویس.",
            reply_markup=_build_city_keyboard("weather_city_current"),
        )
        return
    if text == "📅 پیش بینی":
        context.user_data["mode"] = "weather_forecast"
        await message.reply_text(
            "یکی از شهرهای زیر رو انتخاب کن 👇\n"
            "اگر تو لیست نبود، اسم شهر رو انگلیسی بنویس.",
            reply_markup=_build_city_keyboard("weather_city_forecast"),
        )
        return
    if text == "🤖هوش مصنوعی":
        context.user_data["mode"] = "ai"
        await tutorial_ai(update, context)
        return
    if text == "🪙قیمت طلا":
        context.user_data["mode"] = None
        await get_gold_price(update, context)
        return
    if text == "💵قیمت ارز":
        context.user_data["mode"] = None
        await get_currency_price(update, context)
        return
    if text == "💎ارز دیجیتال":
        context.user_data["mode"] = None
        await get_crypto_price(update, context)
        return
    if text == "👨‍💻 ارتباط با سازنده":
        context.user_data["mode"] = None
        await contact_developer(update, context)
        return
    if text == "⬅️بازگشت":
        context.user_data["mode"] = None
        await start(update, context)
        return

    # ── بررسی آنتی‌اسپم فقط برای پیام‌های آزاد (نه دکمه‌ها) ──
    if await check_spam(update):
        return

    # ── هندل وضعیت آب و هوا ──
    mode = context.user_data.get("mode")
    if mode == "weather_current":
        city = text.strip()
        if not city:
            await message.reply_text("لطفاً اسم شهر رو بنویس.")
            return
        weather_info = await get_current_weather(city)
        if weather_info:
            await message.reply_text(weather_info)
        else:
            await message.reply_text("هیچ داده ای برای این شهر یافت نشد")
        return
    if mode == "weather_forecast":
        city, target_date = parse_forecast_args(text.split())
        if not city or not target_date:
            context.user_data["forecast_city"] = text.strip()
            await message.reply_text(
                "تاریخ رو از دکمه‌های زیر انتخاب کن 👇",
                reply_markup=_build_forecast_dates_keyboard(),
            )
            return
        forecast_info = await get_forecast_weather(city, target_date)
        if forecast_info:
            await message.reply_text(forecast_info)
        else:
            await message.reply_text("هیچ داده ای برای این تاریخ یافت نشد")
        return

    # ── اگه مود AI فعاله → بفرست به هوش مصنوعی ──
    if mode == "ai":
        await handle_message(update, context)
        return

    await update.message.reply_text("برای شروع یکی از دکمه‌ها را انتخاب کن یا /start بزن.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "weather":
        context.user_data["mode"] = "weather_menu"
        if query.message:
            await query.message.reply_text(
                "یکی از گزینه‌های هواشناسی رو انتخاب کن 👇",
                reply_markup=InlineKeyboardMarkup(weather_inline_button),
            )
            await query.message.reply_text("منوی هواشناسی 👇", reply_markup=weather_reply_button)
    elif data == "weather_current":
        context.user_data["mode"] = "weather_current"
        if query.message:
            await query.message.reply_text(
                "یکی از شهرهای زیر رو انتخاب کن 👇\n"
                "اگر تو لیست نبود، اسم شهر رو انگلیسی بنویس.",
                reply_markup=_build_city_keyboard("weather_city_current"),
            )
    elif data == "weather_forecast":
        context.user_data["mode"] = "weather_forecast"
        if query.message:
            await query.message.reply_text(
                "یکی از شهرهای زیر رو انتخاب کن 👇\n"
                "اگر تو لیست نبود، اسم شهر رو انگلیسی بنویس.",
                reply_markup=_build_city_keyboard("weather_city_forecast"),
            )
    elif data.startswith("weather_city_current:"):
        city = data.split(":", 1)[1]
        weather_info = await get_current_weather(city)
        if query.message:
            if weather_info:
                await query.message.reply_text(weather_info)
            else:
                await query.message.reply_text("هیچ داده ای برای این شهر یافت نشد")
    elif data.startswith("weather_city_forecast:"):
        city = data.split(":", 1)[1]
        context.user_data["forecast_city"] = city
        if query.message:
            await query.message.reply_text(
                "تاریخ رو از دکمه‌های زیر انتخاب کن 👇",
                reply_markup=_build_forecast_dates_keyboard(),
            )
    elif data.startswith("weather_date:"):
        date_str = data.split(":", 1)[1]
        city = context.user_data.get("forecast_city")
        if not city:
            if query.message:
                await query.message.reply_text("اول اسم شهر رو انتخاب کن.")
            return
        target_date = datetime.strptime(date_str, "%Y-%m-%d")
        forecast_info = await get_forecast_weather(city, target_date)
        if query.message:
            if forecast_info:
                await query.message.reply_text(forecast_info)
            else:
                await query.message.reply_text("هیچ داده ای برای این تاریخ یافت نشد")
    elif data == "ai":
        context.user_data["mode"] = "ai"
        await tutorial_ai(update, context)
    elif data == "gold":
        context.user_data["mode"] = None
        await get_gold_price(update, context)
    elif data == "currency":
        context.user_data["mode"] = None
        await get_currency_price(update, context)
    elif data == "crypto":
        context.user_data["mode"] = None
        await get_crypto_price(update, context)
    elif data == "contact":
        context.user_data["mode"] = None
        await contact_developer(update, context)
    elif data == "back":
        context.user_data["mode"] = None
        await start(update, context)


def main():
    print("Bot is running...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("tutorial_weather", tutorial_weather))
    app.add_handler(CommandHandler("weather", weather_command))
    app.add_handler(CommandHandler("forecast", forecast_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_members))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_router))
    app.add_handler(CommandHandler("contact", contact_developer))
    app.run_polling()   


if __name__ == "__main__":
    main()