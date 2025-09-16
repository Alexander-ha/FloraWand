from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import aiosqlite
import logging
import asyncio
from typing import Optional

logger = logging.getLogger(__name__)

class UserForm(StatesGroup):
    waiting_for_flower = State()
    waiting_for_water = State()
    waiting_for_temp = State()
    waiting_for_light = State()

start_router = Router()

# Глобальная переменная для хранения соединения с базой данных
db_connection = None

async def init_db():
    """Инициализация базы данных"""
    global db_connection
    if db_connection is None:
        db_connection = await aiosqlite.connect('pot_bot.db')
        await db_connection.execute('PRAGMA journal_mode=WAL')
        await db_connection.execute('PRAGMA busy_timeout=5000')
        
        # Создаем таблицу если она не существует
        await db_connection.execute('''
            CREATE TABLE IF NOT EXISTS user_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_nick TEXT UNIQUE NOT NULL,
                plant TEXT NOT NULL,
                water_lvl INTEGER NOT NULL,
                light_level INTEGER NOT NULL,
                temperature INTEGER NOT NULL
            )
        ''')
        await db_connection.commit()
        logger.info("База данных инициализирована")

async def close_db():
    """Закрытие соединения с базой данных"""
    global db_connection
    if db_connection:
        await db_connection.close()
        db_connection = None
        logger.info("Соединение с базой данных закрыто")

@start_router.startup()
async def on_startup():
    """Инициализация при запуске бота"""
    await init_db()

@start_router.shutdown()
async def on_shutdown():
    """Очистка при остановке бота"""
    await close_db()

async def execute_query(query, params=None):
    """Выполнение запроса к базе данных"""
    global db_connection
    if db_connection is None:
        await init_db()
    
    try:
        if params:
            result = await db_connection.execute(query, params)
        else:
            result = await db_connection.execute(query)
        await db_connection.commit()
        return result
    except Exception as e:
        logger.error(f"Ошибка при выполнении запроса: {e}")
        raise

async def fetch_one(query, params=None):
    """Получение одной записи из базы данных"""
    global db_connection
    if db_connection is None:
        await init_db()
    
    try:
        if params:
            cursor = await db_connection.execute(query, params)
        else:
            cursor = await db_connection.execute(query)
        result = await cursor.fetchone()
        await cursor.close()
        return result
    except Exception as e:
        logger.error(f"Ошибка при получении данных: {e}")
        raise

@start_router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    try:
        username = message.from_user.full_name
        user_data = await fetch_one('SELECT * FROM user_data WHERE tg_nick = ?', (username,))
        
        if user_data:
            await message.answer(f'Welcome back, {username}!\n\n'
                                'Available commands:\n'
                                '/get_user - get your data\n'
                                '/update_user - update your data\n'
                                '/delete_user - delete your account')
        else:
            await state.update_data(username=username)
            await message.answer(f"Welcome, {username}! Let's sign you up.\nEnter your flower's name:")
            await state.set_state(UserForm.waiting_for_flower)
    except Exception as e:
        logger.error(f"The error occured:: {e}")
        await message.answer("Can't connect with database. Please, try later")

@start_router.message(UserForm.waiting_for_flower)
async def process_flower(message: Message, state: FSMContext):
    await state.update_data(flower=message.text)
    await message.answer("Enter the level of water:")
    await state.set_state(UserForm.waiting_for_water)

@start_router.message(UserForm.waiting_for_water)
async def process_water(message: Message, state: FSMContext):
    try:
        water = int(message.text)
        await state.update_data(water=water)
        await message.answer("Enter the temperature:")
        await state.set_state(UserForm.waiting_for_temp)
    except ValueError:
        await message.answer("Please, enter the level of water:")

@start_router.message(UserForm.waiting_for_temp)
async def process_temp(message: Message, state: FSMContext):
    try:
        temp = int(message.text)
        await state.update_data(temp=temp)
        await message.answer("Enter the intensity of light:")
        await state.set_state(UserForm.waiting_for_light)
    except ValueError:
        await message.answer("Please, enter the level of temperature:")

@start_router.message(UserForm.waiting_for_light)
async def process_light(message: Message, state: FSMContext):
    try:
        light = int(message.text)
        user_data = await state.get_data()
        
        try:
            await execute_query(
                'INSERT INTO user_data (tg_nick, plant, water_lvl, light_level, temperature) VALUES (?, ?, ?, ?, ?)',
                (user_data['username'], user_data['flower'], user_data['water'], light, user_data['temp'])
            )
            
            await message.answer(f"User {user_data['username']} was successfully signed up!")
            await state.clear()
        except Exception as e:
            logger.error(f"Error while saving user occured: {e}")
            await message.answer("The error occured. Try later.")
    except ValueError:
        await message.answer("Please, enter the intensity of ligh:")

@start_router.message(Command('get_user'))
async def get_user_data(message: Message):
    try:
        username = message.from_user.full_name
        user_data = await fetch_one('SELECT * FROM user_data WHERE tg_nick = ?', (username,))
        
        if user_data:
            await message.answer(f"Your data:\n"
                                f"Flower: {user_data[2]}\n"
                                f"Water level: {user_data[3]}\n"
                                f" Light level: {user_data[4]}\n"
                                f"Temperature: {user_data[5]}")
        else:
            await message.answer("You're not signed up. Type /start to begin.")
    except Exception as e:
        logger.error(f"The error occured while receiving data: {e}")
        await message.answer("The error occured.")

@start_router.message(Command('update_user'))
async def update_user_data(message: Message):
    args = message.text.split()
    if len(args) < 4:
        await message.answer("Format: /update_user <water> <light> <temperature>")
        return
    
    try:
        username = message.from_user.full_name
        water = int(args[1])
        light = int(args[2])
        temp = int(args[3])
        
        try:
            await execute_query(
                'UPDATE user_data SET water_lvl = ?, light_level = ?, temperature = ? WHERE tg_nick = ?',
                (water, light, temp, username)
            )
            await message.answer(f"User  {username} data is updated!")
        except Exception as e:
            logger.error(f"Error while updating data: {e}")
            await message.answer("The error occured. Please try later")
    except (ValueError, IndexError):
        await message.answer("Error in data! Incorrect")

@start_router.message(Command('delete_user'))
async def delete_user(message: Message):
    try:
        username = message.from_user.full_name
        await execute_query('DELETE FROM user_data WHERE tg_nick = ?', (username,))
        await message.answer(f"User {username} is deleted.")
    except Exception as e:
        logger.error(f"Error: {e}")
        await message.answer("The error occured. Please try later")