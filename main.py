import requests
import time
from collections import defaultdict
from dotenv import load_dotenv
import os
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
load_dotenv()
from weather_advanced import weather_command, forecast_command
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
«وضعیت» + اسم شهر
مثال:  /weather شیراز

2️⃣ پیش‌بینی روزهای آینده:
«پیشبینی» + اسم شهر + تاریخ
مثال:  /forecast شیراز ۲۰ بهمن

⚠️ نکته: لطفاً نام شهر و تاریخ رو دقیق وارد کن.""")

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
        f"👤 ارتباط با سازنده: {MY_ID}"
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
        context.user_data["mode"] = None
        await tutorial_weather(update, context)
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

    # ── اگه مود AI فعاله → بفرست به هوش مصنوعی ──
    mode = context.user_data.get("mode")
    if mode == "ai":
        await handle_message(update, context)
        return

    await update.message.reply_text("برای شروع یکی از دکمه‌ها را انتخاب کن یا /start بزن.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "weather":
        context.user_data["mode"] = None
        await tutorial_weather(update, context)
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