import requests
from dotenv import load_dotenv
import os
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
load_dotenv()
from weather_advanced import weather_command, forecast_command
from bot_ai import handle_message
from main_ai import AIAgent
from button_gold import get_gold_price
BOT_TOKEN = os.getenv("API_TELEGRAM")

# ایراد اصلی این تعریف button این است که ساختارش بیش از حد تو در تو (nested) است و باعث می‌شود 
# دکمه‌ها به‌صورت دلخواه در ردیف و ستون نمایش داده نشوند.
# ساختار صحیح در InlineKeyboardMarkup، باید یک لیست از ردیف‌ها باشد و هر ردیف، یک لیست از دکمه‌ها.
# یعنی: [[Button, Button], [Button], ...] و نه [[[Button], [Button]], ...] 
# بر این اساس بازنویسی صحیح:

button = [
    [InlineKeyboardButton("🌤️آب و هوا", callback_data="weather"),
     InlineKeyboardButton("💰قیمت طلا و دلار", callback_data="gold")],
    [InlineKeyboardButton("🤖هوش مصنوعی", callback_data="ai"),
     InlineKeyboardButton("⬅️بازگشت", callback_data="back")]
]

reply_button = ReplyKeyboardMarkup(
    [
        ["🌤️آب و هوا", "💰قیمت طلا و دلار"],
        ["🤖هوش مصنوعی", "⬅️بازگشت"],
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

💰 استعلام قیمت‌ها: مشاهده لحظه‌ای قیمت دلار، یورو و انواع طلا و سکه.

🧠 هوش مصنوعی: گفتگو، پرسش و پاسخ، و حل مسائل با قدرت AI.

🌤️ آب و هوا: چک کردن وضعیت جوی و پیش‌بینی هوای تمام شهرهای ایران و جهان.

همین حالا دکمه START رو بزن تا با هم شروع کنیم! 👇  """,
    reply_markup=InlineKeyboardMarkup(button))
    await message.reply_text("منوی اصلی 👇", reply_markup=reply_button)


async def tutorial_weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if message is None:
        return
    await message.reply_text("برای اینکه بدونی وضعیت جوی چطوره، فقط کافیه طبق الگوهای زیر از من بپرسی:\n\n📍 مشاهده دمای فعلی: کافیه بنویسی «دمای» و بعد اسم شهرت رو وارد کنی. مثال: / دمای شیراز\n\n📅 مشاهده وضعیت در یک روز خاص: اسم شهر رو بنویس و بعدش تاریخی که می‌خوای رو بگو. مثال: / دمای شیراز ۱۸ بهمن")

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


async def message_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = context.user_data.get("mode")
    if mode == "ai":
        await handle_message(update, context)
        return
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
    if text == "🌤️آب و هوا":
        context.user_data["mode"] = None
        await tutorial_weather(update, context)
        return
    if text == "🤖هوش مصنوعی":
        context.user_data["mode"] = "ai"
        await tutorial_ai(update, context)
        return
    if text == "💰قیمت طلا و دلار":
        context.user_data["mode"] = None
        await get_gold_price(update, context)
        return
    if text == "⬅️بازگشت":
        context.user_data["mode"] = None
        await start(update, context)
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
    app.run_polling()   


if __name__ == "__main__":
    main()