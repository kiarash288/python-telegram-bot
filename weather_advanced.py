import os
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from datetime import datetime
from date import parse_forecast_args

    
load_dotenv()


TOKEN = os.getenv("API_TELEGRAM")
API_KEY = os.getenv("NEW_API_WEATHER") or os.getenv("API_WEATHER")
BASE_URL_current_weather = os.getenv("NEW_BASE_URL_current_weather") or os.getenv("BASE_URL_current_weather")
BASE_URL_forecast_weather = os.getenv("NEW_BASE_URL_forecast_weather") or os.getenv("BASE_URL_forecast_weather")


def _normalize_base_url(base_url: str, kind: str) -> str:
    if not base_url:
        if kind == "current":
            return "https://api.weatherapi.com/v1/current.json"
        return "https://api.weatherapi.com/v1/forecast.json"
    if "weatherapi.com/docs" in base_url:
        if kind == "current":
            return "https://api.weatherapi.com/v1/current.json"
        return "https://api.weatherapi.com/v1/forecast.json"
    return base_url


_CITY_ALIASES = {
    "تهران": "Tehran",
    "مشهد": "Mashhad",
    "اصفهان": "Isfahan",
    "شیراز": "Shiraz",
    "تبریز": "Tabriz",
    "اهواز": "Ahvaz",
    "کرج": "Karaj",
    "قم": "Qom",
    "کرمانشاه": "Kermanshah",
    "ارومیه": "Urmia",
    "رشت": "Rasht",
    "زاهدان": "Zahedan",
    "یزد": "Yazd",
    "کرمان": "Kerman",
    "همدان": "Hamedan",
    "قزوین": "Qazvin",
    "سنندج": "Sanandaj",
    "بندرعباس": "Bandar Abbas",
    "بندر عباس": "Bandar Abbas",
    "کازرون": "Kazerun",
    "ساری": "Sari",
    "گرگان": "Gorgan",
    "بوشهر": "Bushehr",
    "خرم آباد": "Khorramabad",
    "خرم‌آباد": "Khorramabad",
    "کیش": "Kish",
    "قشم": "Qeshm",
    "مازندران": "Mazandaran",
    "گیلان": "Gilan",
    "کاشان": "Kashan",
    "اراک": "Arak",
}


def _normalize_city_name(city: str) -> str:
    if not city:
        return city
    cleaned = city.strip()
    return _CITY_ALIASES.get(cleaned, cleaned)




async def get_current_weather(city: str):
    try:
        
        base_url = _normalize_base_url(BASE_URL_current_weather, "current")
        normalized_city = _normalize_city_name(city)
        complete_url = f"{base_url}?key={API_KEY}&q={normalized_city}&aqi=no&lang=fa"
        response = requests.get(complete_url)
        response.raise_for_status()
        data = response.json()
        if "error" in data:
            return data["error"].get("message", "هیچ داده ای برای این شهر یافت نشد")
        location = data["location"]
        current = data["current"]
        condition = current["condition"]["text"]
        temp = current["temp_c"]
        humidity = current["humidity"]
        wind_speed = current["wind_kph"]
        pressure = current["pressure_mb"]
        fells_like = current["feelslike_c"]
        uv_index = current.get("uv", "نامشخص")
        cloud = current.get("cloud", "نامشخص")
        visibility = current.get("vis_km", "نامشخص")
        precip = current.get("precip_mm", "نامشخص")
        gust = current.get("gust_kph", "نامشخص")
        last_updated = current.get("last_updated", "نامشخص")
        city = location["name"]
        return (
            f"🌤 وضعیت آب و هوای {city}:\n"
            f"📝 توضیحات: {condition}\n"
            f"🌡 دما: {temp}°C\n"
            f"💧 رطوبت: {humidity}%\n"
            f"🌬 فشار: {pressure} mb\n"
            f"🌡 حساسیت آب و هوا: {fells_like}°C\n"
            f"🌬 سرعت باد: {wind_speed} km/h\n"
            f"🌪 تندباد: {gust} km/h\n"
            f"☁️ پوشش ابر: {cloud}%\n"
            f"👁 دید افقی: {visibility} km\n"
            f"🌧 بارش: {precip} mm\n"
            f"🔆 شاخص UV: {uv_index}\n"
            f"🌅 طلوع: {last_updated}\n"
            f"🌇 غروب: {last_updated}\n"
            
        )

    except Exception as e:
        print(f"Error: {e}")
    return None




async def get_forecast_weather(city: str, target_date: datetime):
    try:
        base_url = _normalize_base_url(BASE_URL_forecast_weather, "forecast")
        normalized_city = _normalize_city_name(city)
        complete_url = f"{base_url}?key={API_KEY}&q={normalized_city}&days=10&aqi=no&alerts=no&lang=fa"
        response = requests.get(complete_url)
        response.raise_for_status()
        data = response.json()
        if "error" in data:
            return data["error"].get("message", "هیچ داده ای برای این شهر یافت نشد")
        forecast_days = data.get("forecast", {}).get("forecastday", [])
        if not forecast_days:
            return "هیچ داده ای برای این شهر یافت نشد"
        target_str = target_date.strftime("%Y-%m-%d")
        day_data = next((item for item in forecast_days if item.get("date") == target_str), None)
        if not day_data:
            return "برای این تاریخ پیش بینی در دسترس نیست (فقط چند روز آینده)."
        day = day_data["day"]
        astro = day_data.get("astro", {})
        description = day["condition"]["text"]
        city_name = data.get("location", {}).get("name", city)
        return (
            f"🌤 پیش بینی آب و هوای {city_name} برای {target_str}:\n"
            f"📝 توضیحات غالب: {description}\n"
            f"🌡 حداقل/حداکثر دما: {day['mintemp_c']}°C / {day['maxtemp_c']}°C\n"
            f"🌡 دمای میانگین: {day['avgtemp_c']}°C\n"
            f"💧 رطوبت میانگین: {day['avghumidity']}%\n"
            f"🌬 بیشترین سرعت باد: {day['maxwind_kph']} km/h\n"
            f"🌧 احتمال بارش: {day.get('daily_chance_of_rain', 'نامشخص')}%\n"
            f"🌧 مجموع بارش: {day.get('totalprecip_mm', 'نامشخص')} mm\n"
            f"👁 دید افقی میانگین: {day.get('avgvis_km', 'نامشخص')} km\n"
            f"🔆 شاخص UV: {day.get('uv', 'نامشخص')}\n"
            f"🌅 طلوع: {astro.get('sunrise', 'نامشخص')} | 🌇 غروب: {astro.get('sunset', 'نامشخص')}\n"
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
