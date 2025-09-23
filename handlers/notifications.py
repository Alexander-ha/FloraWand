import aiosqlite
from create_bot import bot, logger
from datetime import datetime, timedelta
from handlers.db_queries import get_wand_users, user_has_wand, is_notify_on
from handlers.menus import get_main_menu

async def check_plant_conditions_by_mac(mac_address: str):
    """
    Проверяет условия для всех растений, связанных с палочкой по MAC-адресу
    и отправляет уведомления при необходимости
    """
    try:
        wand_users = await get_wand_users(mac_address)
        if not wand_users:
            logger.error(f"No registered wand found with MAC: {mac_address}")
            return
        
        for user_id, plant_id in wand_users:
            if plant_id is None:
                continue
                
            latest_data = await get_latest_plant_data(user_id, plant_id)
            if not latest_data:
                logger.info(f"No data found for plant {plant_id} of user {user_id}")
                continue
            
            plant_info = await get_plant_info(plant_id)
            if not plant_info:
                logger.error(f"No plant info found for plant ID: {plant_id}")
                continue
            
            alerts = await check_plant_conditions(latest_data, plant_info)
            
            if alerts:
                await send_alerts_to_user(user_id, alerts, plant_id)
    except Exception as e:
        logger.error(f"Error checking plant conditions for MAC {mac_address}: {e}")


async def get_wand_info_by_mac(mac_address: str):
    """Получает информацию о палочке по MAC-адресу"""
    try:
        async with aiosqlite.connect('flowers.db') as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT user_id, plant_id FROM users_wands WHERE wand_id = ?", 
                (mac_address,)
            )
            result = await cursor.fetchone()
            return dict(result) if result else None
    except Exception as e:
        logger.error(f"Error getting wand info: {e}")
        return None

async def get_latest_plant_data(user_id: int, plant_id: int):
    """Получает последние данные о растении"""
    try:
        async with aiosqlite.connect('flowers.db') as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('''
                SELECT * FROM plants_monitor_final 
                WHERE user_id = ? AND plant_id = ?
                ORDER BY measured_at DESC 
                LIMIT 1
            ''', (user_id, plant_id))
            result = await cursor.fetchone()
            return dict(result) if result else None
    except Exception as e:
        logger.error(f"Error getting plant data: {e}")
        return None

async def get_plant_info(plant_id: int):
    """Получает информацию о растении из plants_info_new"""
    try:
        async with aiosqlite.connect('flowers.db') as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM plants_info_new WHERE plant_id = ?", 
                (plant_id,)
            )
            result = await cursor.fetchone()
            return dict(result) if result else None
    except Exception as e:
        logger.error(f"Error getting plant info: {e}")
        return None

async def check_plant_conditions(latest_data: dict, plant_info: dict):
    """Проверяет условия для растения и возвращает список предупреждений"""
    alerts = []
    
    water = latest_data.get('water_lvl')
    if water is not None:
        water_low = plant_info.get('water_low', 10)
        water_high = plant_info.get('water_high', 90)
        
        if water < water_low:
            alerts.append(f"💧 Soil moisture is too low: {water}% (min: {water_low}%)")
        elif water > water_high:
            alerts.append(f"💧 Soil moisture is too high: {water}% (max: {water_high}%)")

    temp = latest_data.get('temp_lvl')
    if temp is not None:
        temp_low = plant_info.get('temp_low', 10)
        temp_high = plant_info.get('temp_high', 35)
        
        if temp < temp_low:
            alerts.append(f"❄️ Room temperature is too low: {temp}°C (min: {temp_low}°C)")
        elif temp > temp_high:
            alerts.append(f"🔥 Room temperature is too high: {temp}°C (max: {temp_high}°C)")
    
    humidity = latest_data.get('humidity_lvl')
    if humidity is not None:
        humid_low = plant_info.get('humid_low', 10)
        humid_high = plant_info.get('humid_high', 80)
        
        if humidity < humid_low:
            alerts.append(f"🏜️ Room humidity is too low: {humidity}% (min: {humid_low}%)")
        elif humidity > humid_high:
            alerts.append(f"💦 Room humidity is too high: {humidity}% (max: {humid_high}%)")
    
    light = latest_data.get('light_lvl')
    if light is not None:
        light_low = plant_info.get('light_low', 1000)
        light_high = plant_info.get('light_high', 40000)
        
        if light < light_low:
            alerts.append(f"🌑 Need more sunlight: {light} lux (min: {light_low} lux)")
        elif light > light_high:
            alerts.append(f"☀️ Need less sunlight: {light} lux (max: {light_high} lux)")
    
    return alerts

async def send_alerts_to_user(user_id, alerts, plant_id):
    """Отправляет уведомления пользователю"""
    notify_on = await is_notify_on(user_id)
    try:
        if notify_on == 1:
            plant_name = await get_plant_name_by_id(plant_id)
            
            alert_text = "\n".join(alerts)
            full_message = f"⚠️ **Alert for {plant_name}!**\n\n{alert_text}"
            
            await bot.send_message(
                chat_id=user_id,
                text=full_message,
                parse_mode="Markdown",
                reply_markup=get_main_menu(await user_has_wand(user_id), await is_notify_on(user_id))
            )
            
            logger.info(f"Alerts sent to user {user_id} for plant {plant_id}")
        
    except Exception as e:
        logger.error(f"Error sending alerts to user {user_id}: {e}")

async def get_plant_name_by_id(plant_id):
    """Получает название растения по ID"""
    try:
        async with aiosqlite.connect('flowers.db') as db:
            cursor = await db.execute(
                "SELECT plant_name FROM plants_info_new WHERE plant_id = ?", 
                (plant_id,)
            )
            plant = await cursor.fetchone()
            return plant[0] if plant else f"Plant #{plant_id}"
    except Exception as e:
        logger.error(f"Error getting plant name: {e}")
        return f"Plant #{plant_id}"

async def check_all_plants_conditions():
    """Проверяет условия для всех растений и отправляет уведомления"""
    try:
        async with aiosqlite.connect('flowers.db') as db:
            cursor = await db.execute("""
                SELECT pmf.*, pin.* 
                FROM plants_monitor_final pmf
                INNER JOIN (
                    SELECT plant_id, user_id, MAX(measured_at) as latest_time 
                    FROM plants_monitor_final 
                    GROUP BY plant_id, user_id
                ) latest ON pmf.plant_id = latest.plant_id AND pmf.user_id = latest.user_id AND pmf.measured_at = latest.latest_time
                JOIN plants_info_new pin ON pmf.plant_id = pin.plant_id
            """)
            
            plants_data = await cursor.fetchall()
            
            if not plants_data:
                logger.info("No plant data found for monitoring")
                return
            
            columns = [description[0] for description in cursor.description]
            
            for plant_row in plants_data:
                plant_data = dict(zip(columns, plant_row))
                
                latest_data = {
                    'water_lvl': plant_data.get('water_lvl'),
                    'temp_lvl': plant_data.get('temp_lvl'),
                    'humidity_lvl': plant_data.get('humidity_lvl'),
                    'light_lvl': plant_data.get('light_lvl')
                }
                
                plant_info = {
                    'water_low': plant_data.get('water_low', 10),
                    'water_high': plant_data.get('water_high', 90),
                    'temp_low': plant_data.get('temp_low', 10),
                    'temp_high': plant_data.get('temp_high', 35),
                    'humid_low': plant_data.get('humid_low', 10),
                    'humid_high': plant_data.get('humid_high', 80),
                    'light_low': plant_data.get('light_low', 1000),
                    'light_high': plant_data.get('light_high', 40000)
                }
                
                alerts = await check_plant_conditions(latest_data, plant_info)
                
                if alerts:
                    await send_alerts_to_user(
                        plant_data['user_id'], 
                        alerts, 
                        plant_data['plant_id']
                    )
                    
    except Exception as e:
        logger.error(f"Error checking plant conditions: {e}")
