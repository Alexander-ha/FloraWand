import aiosqlite
import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class AsyncDB_Access():
    def __init__(self, db_path: str = 'pot_bot.db', max_retries: int = 3, retry_delay: float = 0.1):
        self.db_path = db_path
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    async def _execute_with_retry(self, func, *args, **kwargs):
        """Выполняет функцию с повторными попытками при блокировке базы данных"""
        for attempt in range(self.max_retries):
            try:
                return await func(*args, **kwargs)
            except aiosqlite.OperationalError as e:
                if "database is locked" in str(e) and attempt < self.max_retries - 1:
                    logger.warning(f"База данных заблокирована, попытка {attempt + 1}/{self.max_retries}")
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                else:
                    raise
        return None

    async def add_user(self, user_name, flower, init_water, init_temp, init_light):
        async def _add_user():
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('PRAGMA journal_mode=WAL')
                await db.execute('PRAGMA busy_timeout=3000')
                await db.execute(
                    'INSERT OR IGNORE INTO user_data (tg_nick, plant, water_lvl, light_level, temperature) VALUES (?, ?, ?, ?, ?)', 
                    (user_name, flower, init_water, init_light, init_temp)
                )
                await db.commit()
        
        await self._execute_with_retry(_add_user)

    async def set_user_data(self, user_name, water_lvl, light_level, temperature):
        async def _set_user_data():
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('PRAGMA journal_mode=WAL')
                await db.execute('PRAGMA busy_timeout=3000')
                await db.execute(
                    'UPDATE user_data SET water_lvl = ?, light_level = ?, temperature = ? WHERE tg_nick = ?',
                    (water_lvl, light_level, temperature, user_name)
                )
                await db.commit()
        
        await self._execute_with_retry(_set_user_data)

    async def get_user_data(self, user_name) -> Optional[tuple]:
        async def _get_user_data():
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('PRAGMA journal_mode=WAL')
                await db.execute('PRAGMA busy_timeout=3000')
                async with db.execute('SELECT * FROM user_data WHERE tg_nick = ?', (user_name,)) as cursor:
                    return await cursor.fetchone()
        
        return await self._execute_with_retry(_get_user_data)

    async def delete_user(self, user_name):
        async def _delete_user():
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('PRAGMA journal_mode=WAL')
                await db.execute('PRAGMA busy_timeout=3000')
                await db.execute('DELETE FROM user_data WHERE tg_nick = ?', (user_name,))
                await db.commit()
        
        await self._execute_with_retry(_delete_user)

    async def create_table_if_not_exists(self):
        """Создает таблицу если она не существует"""
        async def _create_table():
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS user_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tg_nick TEXT UNIQUE NOT NULL,
                        plant TEXT NOT NULL,
                        water_lvl INTEGER NOT NULL,
                        light_level INTEGER NOT NULL,
                        temperature INTEGER NOT NULL
                    )
                ''')
                await db.commit()
        
        await self._execute_with_retry(_create_table)