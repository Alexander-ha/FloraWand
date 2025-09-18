
import aiosqlite
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from start import get_plant_by_id
from create_bot import bot, dp

api_router = Router()

@api_router.message(Command("sensor_data"))
async def handle_sensor_data(message: Message):
    """
    Обработчик данных от ESP (можно адаптировать под HTTP запросы)
    """
    try:
        text = message.text.split()
        data = {}
        
        for param in text[1:]:
            if '=' in param:
                key, value = param.split('=')
                data[key] = float(value)
        
        plant_id = int(data.get('plant_id', 0))
        temp = data.get('temp', 0)
        humidity = data.get('humidity', 0)
        light = data.get('light', 0)
        
        if plant_id and temp and humidity and light:
            success = await add_sensor_data_and_check(plant_id, temp, humidity, light)
            if success:
                await message.answer("✅ Данные получены и обработаны")
            else:
                await message.answer("❌ Ошибка обработки данных")
        else:
            await message.answer("❌ Неверный формат данных")
            
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")



async def add_sensor_data_and_check(user_id: int, plant_id: int, water: float, light: float, temp: float, humidity: float):
    """
    Добавляет данные от сенсоров и проверяет на нарушения
    """
    try:
        async with aiosqlite.connect('flowers.db') as db:
            await db.execute(
                "INSERT INTO plants_monitor (user_id, plant_id, water_lvl, light_lvl, temp_lvl, humidity_lvl) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, plant_id, water, light, temp, humidity)
            )
            
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT light_low, light_high, temp_low, temp_high, water_low, water_high, humid_low, humid_high
                FROM plants_info_new 
                WHERE p.plant_id = ?
            """, (plant_id,))
            
            plant_data = await cursor.fetchone()
            
            alerts = []
            for row in plant_data:

                if temp < row.get('water_low', 10):
                    alerts.append(f"💧 Soil moisture is too low: {temp}°C (min: {row.get('water_low', 10)}°C)")
                elif temp > row.get('water_high', 90):
                    alerts.append(f"💧 Soil moisture is too high: {temp}°C (max: {row.get('water_high', 90)}°C)")

                if temp < row.get('temp_low', 10):
                    alerts.append(f"❄️ Room temperature is too low: {temp}°C (min: {row.get('temp_low', 10)}°C)")
                elif temp > row.get('temp_high', 35):
                    alerts.append(f"🔥 Room temperature is too high: {temp}°C (max: {row.get('temp_high', 35)}°C)")
                
                if humidity < row.get('humid_low', 10):
                    alerts.append(f"🏜️ Room humidity is too low: {humidity}% (min: {row.get('humid_low', 10)}%)")
                elif humidity > row.get('humid_high', 80):
                    alerts.append(f"💦 Room humidity is too high: {humidity}% (max: {row.get('humid_high', 80)}%)")
                
                if light < row.get('light_low', 1000):
                    alerts.append(f"🌑 Need more sunlight: {light} lux (min: {row.get('light_low', 1000)} lux)")
                elif light > row.get('light_high', 1000):
                    alerts.append(f"☀️ Need less sunlight: {light} lux (max: {row.get('light_high', 40000)} lux)")
            
            await db.commit()
            
            for alert_message in alerts:
                await send_alert_to_user(user_id, alert_message, plant_id)
                
            return True
            
    except Exception as e:
        print(f"Error processing sensor data: {e}")
        return False
    


async def send_alert_to_user(user_id: int, message: str, plant_id: int):
    """
    Отправляет уведомление пользователю
    """
    try:        
        plant_name = await get_plant_by_id(plant_id)
        full_message = f"⚠️ **Внимание!**\n\n{plant_name}:\n{message}"
        
        await bot.send_message(
            chat_id=user_id,
            text=full_message,
            parse_mode="Markdown"
        )
        
        print(f"Alert sent to user {user_id}: {message}")
        
    except Exception as e:
        print(f"Error sending alert to user {user_id}: {e}")

