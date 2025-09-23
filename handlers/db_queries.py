import aiosqlite
import pandas as pd
import logging
import re
logger = logging.getLogger(__name__)

async def user_has_wand(user_id: int) -> bool:
    """Проверка наличия палочек у пользователя"""
    async with aiosqlite.connect('flowers.db') as db:
        cursor = await db.execute(
            'SELECT 1 FROM users_wands WHERE user_id = ?', 
            (user_id,)
        )
        return await cursor.fetchone() is not None
    
async def user_exists(user_id: int) -> bool:
    """Проверка существования пользователя"""
    async with aiosqlite.connect('flowers.db') as db:
        cursor = await db.execute('SELECT 1 FROM users WHERE user_id = ?', (user_id,))
        return await cursor.fetchone() is not None
    

async def add_user(user_id: int, username: str = None):
    """Добавление нового пользователя"""
    async with aiosqlite.connect('flowers.db') as db:
        await db.execute('''
            INSERT OR IGNORE INTO users (user_id, username)
            VALUES (?, ?)
        ''', (user_id, username))
        await db.commit()

async def add_plant_to_user(user_id: int, plant_id: int):
    """Добавление растения пользователю"""
    async with aiosqlite.connect('flowers.db') as db:
        try:
            await db.execute('''
                INSERT INTO user_plants (user_id, plant_id)
                VALUES (?, ?)
            ''', (user_id, plant_id))
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            # Растение уже добавлено
            return False

async def is_valid_mac_address(mac_address: str) -> bool:
    """Проверяет, является ли строка валидным MAC-адресом"""
    pattern = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'
    return re.match(pattern, mac_address) is not None

async def register_user_wand(user_id: int, wand_id: str, plant_id: int = None):
    """Регистрация новой палочки для пользователя"""
    if not await is_valid_mac_address(wand_id):
        raise ValueError("Invalid MAC address format")
    
    async with aiosqlite.connect('flowers.db') as db:
        try:
            cursor = await db.execute(
                "SELECT 1 FROM users_wands WHERE user_id = ? AND wand_id = ?",
                (user_id, wand_id)
            )
            existing = await cursor.fetchone()
            
            if existing:
                await db.execute(
                    "UPDATE users_wands SET plant_id = ? WHERE user_id = ? AND wand_id = ?",
                    (plant_id, user_id, wand_id)
                )
            else:
                await db.execute('''
                    INSERT INTO users_wands (user_id, plant_id, wand_id)
                    VALUES (?, ?, ?)
                ''', (user_id, plant_id, wand_id))
            
            await db.commit()
            return True
        except Exception as e:
            logger.error(f"Error registering wand: {e}")
            return False


async def get_user_plants(user_id: int):
    """Получение растений пользователя"""
    async with aiosqlite.connect('flowers.db') as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('''
            SELECT p.*, up.added_at 
            FROM plants_info_new p
            JOIN user_plants up ON p.plant_id = up.plant_id
            WHERE up.user_id = ?
            ORDER BY up.added_at DESC
        ''', (user_id,))
        return await cursor.fetchall()

async def get_plant_by_name(plant_name: str):
    """Поиск растения по названию"""
    async with aiosqlite.connect('flowers.db') as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('''
            SELECT * FROM plants_info_new WHERE LOWER(plant_name) = LOWER(?)
        ''', (plant_name,))
        plant = await cursor.fetchone()
        return dict(plant) if plant else None
    
async def get_plant_by_id(plant_id: int):
    """Поиск растения по id"""
    async with aiosqlite.connect('flowers.db') as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('''
            SELECT * FROM plants_info_new WHERE LOWER(plant_id) = LOWER(?)
        ''', (plant_id,))
        return await cursor.fetchone()

async def search_plants_by_name(plant_name: str):
    """Поиск растений по частичному совпадению названия"""
    async with aiosqlite.connect('flowers.db') as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('''
            SELECT * FROM plants_info_new WHERE LOWER(plant_name) LIKE LOWER(?)
        ''', (f'%{plant_name}%',))
        return await cursor.fetchall()
    
async def get_all_plants(): #  -> List[Dict[str, Any]]
    async with aiosqlite.connect('flowers.db') as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('SELECT plant_id, plant_name FROM plants_info_new')
        plants = await cursor.fetchall()
        return [dict(plant) for plant in plants]

async def get_plant_stats_from_db(user_id: int, plant_id: int, cnt: int=-1):
    try:
        async with aiosqlite.connect('flowers.db') as db:
            query = """
                SELECT water_lvl, temp_lvl, light_lvl, humidity_lvl, measured_at
                FROM plants_monitor_final
                WHERE plant_id = ? AND user_id = ?
                ORDER BY measured_at
            """
            if cnt > 0:
                query += f"DESC LIMIT {cnt}"
            cursor = await db.execute(query, (plant_id, user_id))  
            rows = await cursor.fetchall()
            if not rows:
                return None
            df = pd.DataFrame(rows, columns=['water_lvl', 'temp_lvl', 'light_lvl', 'humidity_lvl', 'measured_at'])
            df['measured_at'] = pd.to_datetime(df['measured_at'])
            df.set_index('measured_at', inplace=True)
            
            if not isinstance(df.index, pd.DatetimeIndex):
                df.index = pd.to_datetime(df.index)
            return df
    except Exception as e:
        print(f"Error fetching plant stats: {e}")
        return None

async def get_user_wands(user_id: int):
    """Получение всех палочек пользователя"""
    async with aiosqlite.connect('flowers.db') as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('''
            SELECT uw.wand_id, uw.plant_id, uw.registered_at, 
                   COALESCE(pin.plant_name, 'Not linked') as plant_name
            FROM users_wands uw
            LEFT JOIN plants_info_new pin ON uw.plant_id = pin.plant_id
            WHERE uw.user_id = ?
        ''', (user_id,))
        wands = await cursor.fetchall()
        return [dict(wand) for wand in wands]
    

async def get_wand_users(wand_id: str):
    """Получение всех пользователей, связанных с палочкой"""
    async with aiosqlite.connect('flowers.db') as db:
        cursor = await db.execute(
            "SELECT user_id, plant_id FROM users_wands WHERE wand_id = ?", 
            (wand_id,)
        )
        return await cursor.fetchall()

async def get_wand_owner(wand_id: str):
    """Получение владельца палочки по её ID"""
    async with aiosqlite.connect('flowers.db') as db:
        cursor = await db.execute(
            "SELECT user_id FROM users_wands WHERE wand_id = ?", 
            (wand_id,)
        )
        result = await cursor.fetchall()
        print(f"{result}")
        return result if result else (None, None)
    
async def del_user(user_id: int):
    async with aiosqlite.connect('flowers.db') as db:
        await db.execute('''
            DELETE FROM user_plants WHERE user_id = ?
        ''', (user_id, ))
        await db.execute('''
            DELETE FROM users_wands WHERE user_id = ?
        ''', (user_id, ))
        await db.execute('''
            DELETE FROM plants_monitor_final WHERE user_id = ?
        ''', (user_id, ))
        await db.commit()

async def del_plant(user_id: int, plant_id: int):
    async with aiosqlite.connect('flowers.db') as db:
        await db.execute('''
            DELETE FROM user_plants WHERE user_id = ? and plant_id = ?
        ''', (user_id, plant_id))
        await db.execute('''
            DELETE FROM users_wands WHERE user_id = ? and plant_id = ?
        ''', (user_id, plant_id))
        await db.execute('''
            DELETE FROM plants_monitor_final WHERE user_id = ? and plant_id = ?
        ''', (user_id, plant_id))
        await db.commit()

async def del_wand(user_id: int, wand_id: int):
    async with aiosqlite.connect('flowers.db') as db:
        await db.execute('''
            DELETE FROM users_wands WHERE user_id = ? and wand_id = ?
        ''', (user_id, wand_id))
        await db.commit()