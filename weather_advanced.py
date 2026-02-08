import os
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from datetime import datetime, timezone
from collections import defaultdict
from date import parse_forecast_args

    
load_dotenv()


TOKEN = os.getenv("API_TELEGRAM")
API_KEY = os.getenv("API_WEATHER")
BASE_URL_current_weather = os.getenv("BASE_URL_current_weather")
BASE_URL_forecast_weather = os.getenv("BASE_URL_forecast_weather")




async def get_current_weather(city: str):
    try:
        
        base_url = BASE_URL_current_weather
        complete_url = f'{base_url}?q={city}&appid={API_KEY}&units=metric&lang=fa'
        response = requests.get(complete_url)
        response.raise_for_status()
        data = response.json()
        if data['cod'] != '404':
            main= data['main']
            weather = data['weather'][0]
            temp = main['temp']
            humidity = main['humidity']
            wind_speed = data['wind']['speed']
            pressure = main['pressure']
            fells_like = main['feels_like']
            uv_index = data.get('uvi', 'نامشخص')
            description = weather['description']
            city = data['name']            # روش اول: استفاده از \n دستی (تمیزترین روش برای تلگرام)
            return (
                f"🌤 وضعیت آب و هوای {city}:\n\n"
                f"📝 توضیحات: {description}"
                f"🌡 دما: {temp}°C\n"
                f"💧 رطوبت: {humidity}%\n"
                f"🌬 فشار: {pressure} hPa\n"
                f"🌡 حساسیت آب و هوا: {fells_like}°C\n"
                f"🌬 سرعت باد: {wind_speed} m/s\n"
                f"🌡 میزان uv: {uv_index}\n"
                
            )

    except Exception as e:
        print(f"Error: {e}")
    return None




async def get_forecast_weather(city: str, target_date: datetime):
    try:
        base_url = BASE_URL_forecast_weather
        complete_url = f'{base_url}?q={city}&appid={API_KEY}&units=metric&lang=fa'
        response = requests.get(complete_url)
        response.raise_for_status()
        data = response.json()
        if data.get('cod') == '404':
            return "  دوباره تلاش کنید هیچ داده ای برای این شهر یافت نشد" 
        items = data.get("list", [])
        if not items:
            return "هیچ داده ای برای این شهر یافت نشد"
        target_str = target_date.strftime("%Y-%m-%d")
        day_items = [item for item in items if item.get("dt_txt", "").startswith(target_str)]
        if not day_items:
            return "برای این تاریخ پیش بینی در دسترس نیست (فقط چند روز آینده)."
        temps = [item["main"]["temp"] for item in day_items]
        hums = [item["main"]["humidity"] for item in day_items]
        winds = [item["wind"]["speed"] for item in day_items]
        pressures = [item["main"]["pressure"] for item in day_items]
        best_item = min(
            day_items,
            key=lambda item: abs(
                datetime.fromtimestamp(item["dt"], tz=timezone.utc).hour - 12
            ),
        )
        description = best_item["weather"][0]["description"]
        city_name = data["city"]["name"]
        return (
            f"🌤 پیش بینی آب و هوای {city_name} برای {target_str}:\n\n"
            f"📝 توضیحات غالب: {description}"
            f"🌡 حداقل/حداکثر دما: {min(temps)}°C / {max(temps)}°C\n"
            f"💧 رطوبت میانگین: {sum(hums) // len(hums)}%\n"
            f"🌬 سرعت باد میانگین: {sum(winds) / len(winds):.1f} m/s\n"
            f"🌬 فشار میانگین: {sum(pressures) // len(pressures)} hPa\n"
            
        )

    except Exception as e:
        print(f"Error: {e}")
    return None



async def weather_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("لطفا نام شهر را بعد از دستور /weather مثل /weather تهران  وارد کنید")
        return
    city = context.args[0]
    weather_info = await get_current_weather(city)
    if weather_info:
        await update.message.reply_text(weather_info)
    else:
        await update.message.reply_text("هیچ داده ای برای این شهر یافت نشد")


async def forecast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    city, target_date = parse_forecast_args(context.args)
    if not city or not target_date:
        await update.message.reply_text(
            "فرمت درست: /forecast شهر روز ماه\n"
            "مثال: /forecast شیراز ۱۹ بهمن"
        )
        return
    forecast_info = await get_forecast_weather(city, target_date)
    if forecast_info:
        await update.message.reply_text(forecast_info)
    else:
        await update.message.reply_text("هیچ داده ای برای این تاریخ یافت نشد")






def main():
    app = Application.builder().token(TOKEN).build()
    print("Bot is running...")
    app.add_handler(CommandHandler("weather", weather_command))
    app.add_handler(CommandHandler("forecast", forecast_command))
    app.run_polling()

if __name__ == "__main__":
    main()
