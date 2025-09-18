
import aiosqlite
from aiogram import Bot
from aiogram.types import Message
from aiogram.filters import Command
from handlers.start import get_plant_by_id
from create_bot import bot
from create_bot import logger

async def add_sensor_data_and_check(wand_id: str, water: float, light: float,  temp: float, humidity: float):
    """
    Добавляет данные от сенсоров и проверяет на нарушения
    """
    try:
        logger.log(1, "we are entering")
        async with aiosqlite.connect('flowers.db') as db:
            cursor = await db.execute(
                "SELECT user_id, plant_id from users_wands WHERE wand_id = ?", (wand_id,)
            )
            wand = await cursor.fetchone()
            if wand:  
                user_id, plant_id = wand[0], wand[1]
            else:
                print(f"Wand with id {wand_id} not found")
                user_id, plant_id = None, None

            assert user_id == 683777507 and plant_id == 2

            
            # await db.execute(
            #     "INSERT INTO plants_monitor_final (user_id, plant_id, water_lvl, light_lvl, temp_lvl, humidity_lvl) VALUES (?, ?, ?, ?, ?, ?)",
            #     (user_id, plant_id, water, light, temp, humidity)
            # )
            
          
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT *
                FROM plants_info_new 
                WHERE plant_id = ?
            """, (plant_id,))
            
            plant_data = await cursor.fetchone()
            row = dict(plant_data)
            alerts = []
  
            if water < row.get('water_low', 10):
                alerts.append(f"💧 Soil moisture is too low: {water}°C (min: {row.get('water_low', 10)}°C)")
            elif water > row.get('water_high', 90):
                alerts.append(f"💧 Soil moisture is too high: {water}°C (max: {row.get('water_high', 90)}°C)")

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
                # plant_name = await get_plant_by_id(plant_id)
                # full_message = f"⚠️ **Alert!**\n\n{plant_name}:\n{alert_message}"
                
                # await bot.send_message(
                #     chat_id=user_id,
                #     text=full_message,
                #     parse_mode="Markdown"
                # )
        
                        
    except Exception as e:
        print(f"Error processing sensor data: {e}")
    


async def send_alert_to_user(user_id: int, message: str, plant_id: int):
    """
    Отправляет уведомление пользователю
    """
    try:        
        plant_name = await get_plant_by_id(plant_id)
        full_message = f"⚠️ **Alert!**\n\n{plant_name}:\n{message}"
        
        await bot.send_message(
            chat_id=user_id,
            text=full_message,
            parse_mode="Markdown"
        )
        
        print(f"Alert sent to user {user_id}: {message}")
        
    except Exception as e:
        print(f"Error sending alert to user {user_id}: {e}")

