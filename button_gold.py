from dotenv import load_dotenv
import os
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
import requests

update = Update

load_dotenv()

TOKEN = os.getenv("API_TELEGRAM")


async def start (update: Update, context: ContextTypes.DEFAULT_TYPE):

    keyboard = [
        [InlineKeyboardButton("طلا", callback_data="gold")],
        [InlineKeyboardButton("ارز دیجیتال", callback_data="crypto")],
        [InlineKeyboardButton("بازگشت", callback_data="back")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        await update.callback_query.message.edit_text("Please select an option", reply_markup=reply_markup)
    else:
        await update.message.reply_text("Please select an option", reply_markup=reply_markup)


async def get_gold_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    api_key = os.getenv("API_GOLD")
    url = f'https://BrsApi.ir/Api/Market/Gold_Currency.php?key={api_key}'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36'
    }
    lines = []
    response = requests.get(url, headers=headers)
    data =  response.json()
    gold = data.get('gold', [])
    if gold:
        lines.append("💰 قیمت طلا:")
        for item in gold:
            name = item.get('name', '')
            price = item.get('price', 0)
            change = item.get('change', 0)
            unit = item.get('unit', '')
            price_text = f"{price} {unit}"
            lines.append(f"{name}: {price_text} {change}")

    currency = data.get('currency', [])
    usd_items = []
    for item in currency:
        name = str(item.get('name', ''))
        code = str(item.get('code', ''))
        if "دلار" in name or "USD" in name.upper() or "DOLLAR" in name.upper() or code.upper() == "USD":
            usd_items.append(item)

    if usd_items:
        lines.append("")
        lines.append("💵 نرخ دلار:")
        for item in usd_items:
            name = item.get('name', 'دلار')
            price = item.get('price', 0)
            change = item.get('change', 0)
            unit = item.get('unit', '')
            price_text = f"{price} {unit}"
            lines.append(f"{name}: {price_text} {change}")
    elif currency and not usd_items:
        lines.append("")
        lines.append("💵 نرخ دلار در این API پیدا نشد.")

    if not lines:
        lines.append("هیچ داده‌ای دریافت نشد.")

    target = update.callback_query.message if update.callback_query else update.message
    await target.reply_text('\n'.join(lines))



async def get_crypto_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = 'https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,tether&vs_currencies=usd'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    lines = []
    response = requests.get(url, headers=headers)
    data = await response.json()
    crypto = data['bitcoin']
    for item in crypto:
        name = item.get('name','')
        price = item.get('price',0)
        change = item.get('change',0)
        unit = item.get('unit','')
        price_text = f"{price} {unit}"
        lines.append(f"{name}: {price_text} {change}")
    await update.callback_query.message.reply_text('\n'.join(lines))

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()
    if data == "gold":
        await get_gold_price(update, context)
        
    elif data == "crypto":
        await get_crypto_price(update, context)
    elif data == "back":
        await start(update, context)
    
    
    






def main():
    print('bot is running ')
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(button))
    application.run_polling()


if __name__ == "__main__":
    main()
