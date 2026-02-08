import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)

# ایمپورت کردن کلاسی که ساختیم
from main_ai import AIAgent

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# تنظیمات لاگ (برای اینکه بفهمیم چی به چیه)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ساخت یک نمونه از هوش مصنوعی (بیرون توابع که فقط یکبار ساخته بشه)
print("Loading AI Model...")
ai_brain = AIAgent()
print("AI Model Loaded!")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام! من به مدل Llama 3 متصل هستم. هر سوالی داری بپرس!"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    این هندلر پیام کاربر رو میگیره، میده به فایل ai_engine و جواب رو پس میده
    """
    user_text = update.message.text
    user_id = update.effective_user.id
    
    # ۱. اعلام وضعیت تایپ کردن (که کاربر بفهمه داریم فکر میکنیم)
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    try:
        # ۲. ارسال پیام به کلاس هوش مصنوعی
        # (چون تابع chat رو async تعریف کردیم، اینجا await میذاریم)
        response = await ai_brain.chat(user_id=user_id, user_message=user_text)
        
        # ۳. ارسال جواب به کاربر
        await update.message.reply_text(response)
        
    except Exception as e:
        logging.error(f"Error in AI generation: {e}")
        await update.message.reply_text("متاسفانه مشکلی در ارتباط با مغز هوش مصنوعی پیش آمد. 🤕")

def main():
    if not TOKEN:
        print("Error: BOT_TOKEN not found!")
        return

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    
    # فیلتر: همه پیام‌های متنی به جز دستورات (مثل /start)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot is polling...")
    app.run_polling()

if __name__ == "__main__":
    main()