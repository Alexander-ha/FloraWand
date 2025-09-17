from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import aiosqlite
import logging
import asyncio
from typing import Optional
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from aiogram import types
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime
from io import BytesIO

from create_bot import bot, dp
logger = logging.getLogger(__name__)

# class UserForm(StatesGroup):
#     waiting_for_flower = State()
#     waiting_for_water = State()
#     waiting_for_temp = State()
#     waiting_for_light = State()

start_router = Router()

# Глобальная переменная для хранения соединения с базой данных
db_connection = None

async def init_db():
    """Инициализация базы данных"""
    global db_connection
    if db_connection is None:
        db_connection = await aiosqlite.connect('flowers.db')
        await db_connection.execute('PRAGMA journal_mode=WAL')
        await db_connection.execute('PRAGMA busy_timeout=5000')

        # Создаем таблицу если она не существует
        await db_connection.execute('''
            CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        await db_connection.execute('''
            CREATE TABLE IF NOT EXISTS user_plants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            plant_id INTEGER NOT NULL,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            FOREIGN KEY (plant_id) REFERENCES plants (plant_id),
            UNIQUE(user_id, plant_id) 
        )
        ''')
        await db_connection.execute('''
            CREATE TABLE IF NOT EXISTS plants_monitor (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                plant_id INTEGER NOT NULL,
                water_lvl REAL,
                light_lvl REAL,
                temp_lvl REAL,
                measured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        #  -- Add indexes for better query performance
        await db_connection.execute('''
            CREATE INDEX IF NOT EXISTS idx_monitor_user_plant ON plants_monitor(user_id, plant_id)
        ''')
        await db_connection.execute('''
            CREATE INDEX IF NOT EXISTS idx_monitor_timestamp ON plants_monitor(measured_at)            
        ''')
        await db_connection.commit()
        logger.info("Database initiated.")

async def close_db():
    """Closing connection to database..."""
    global db_connection
    if db_connection:
        await db_connection.close()
        db_connection = None
        logger.info("Connection closed.")

@start_router.startup()
async def on_startup():
    """Starting..."""
    await init_db()

@start_router.shutdown()
async def on_shutdown():
    """Cleaning up before closing..."""
    await close_db()

async def execute_query(query, params=None):
    """Executing query...х"""
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
        logger.error(f"Error executing query: {e}")
        raise

async def fetch_one(query, params=None):
    """Fetching from database..."""
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
        logger.error(f"Error fetching data: {e}")
        raise

async def add_user(user_id: int, username: str = None):
    """Добавление нового пользователя"""
    async with aiosqlite.connect('flowers.db') as db:
        await db.execute('''
            INSERT OR IGNORE INTO users (user_id, username)
            VALUES (?, ?)
        ''', (user_id, username))
        await db.commit()

async def user_exists(user_id: int) -> bool:
    """Проверка существования пользователя"""
    async with aiosqlite.connect('flowers.db') as db:
        cursor = await db.execute('SELECT 1 FROM users WHERE user_id = ?', (user_id,))
        return await cursor.fetchone() is not None

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

async def get_user_plants(user_id: int):
    """Получение растений пользователя"""
    async with aiosqlite.connect('flowers.db') as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('''
            SELECT p.*, up.added_at 
            FROM plants_info p
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
            SELECT * FROM plants_info WHERE LOWER(plant_name) = LOWER(?)
        ''', (plant_name,))
        plant = await cursor.fetchone()
        return dict(plant) if plant else None
    
async def get_plant_by_id(plant_id: int):
    """Поиск растения по id"""
    async with aiosqlite.connect('flowers.db') as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('''
            SELECT * FROM plants_info WHERE LOWER(plant_id) = LOWER(?)
        ''', (plant_id,))
        return await cursor.fetchone()

async def search_plants_by_name(plant_name: str):
    """Поиск растений по частичному совпадению названия"""
    async with aiosqlite.connect('flowers.db') as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('''
            SELECT * FROM plants_info WHERE LOWER(plant_name) LIKE LOWER(?)
        ''', (f'%{plant_name}%',))
        return await cursor.fetchall()
    
async def get_all_plants(): #  -> List[Dict[str, Any]]
    async with aiosqlite.connect('flowers.db') as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('SELECT plant_id, plant_name FROM plants_info')
        plants = await cursor.fetchall()
        return [dict(plant) for plant in plants]

# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

def get_main_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🌿 My Plants", callback_data="my_plants"),
        InlineKeyboardButton(text="❓ What plant am I?", callback_data="start_quiz")
    )
    builder.row(
        InlineKeyboardButton(text="➕ Add Plant", callback_data="add_plant_menu")
    )
    return builder.as_markup()

async def get_user_plants_menu(user_id: int) -> InlineKeyboardMarkup:
    plants = await get_user_plants(user_id)
    builder = InlineKeyboardBuilder()
    
    for plant in plants:
        builder.row(
            InlineKeyboardButton(
                text=f"🌱 {plant['plant_name']}", 
                callback_data=f"plant_detail_{plant['plant_id']}"
            )
        )
    builder.row(
        InlineKeyboardButton(text="⬅️ Back to Main Menu", callback_data="main_menu")
    )
    return builder.as_markup()
    
async def get_add_plant_menu() -> InlineKeyboardMarkup:
    plants = await get_all_plants()
    builder = InlineKeyboardBuilder()
    
    for plant in plants:
        builder.row(
            InlineKeyboardButton(
                text=f"➕ {plant['plant_name']}", 
                callback_data=f"add_plant_{plant['plant_id']}"
            )
        )
    builder.row(
        InlineKeyboardButton(text="⬅️ Back to Main Menu", callback_data="main_menu")
    )
    
    return builder.as_markup()

def get_plant_actions_menu(user_id: int, plant_id: int = None) -> InlineKeyboardMarkup:
    """
    Компактное меню с действиями для растения (2 кнопки в ряду)
    """
    builder = InlineKeyboardBuilder()
    
    # Первый ряд: две кнопки показателей
    builder.row(
        InlineKeyboardButton(
            text="📊 All time measurements", 
            callback_data=f"stats_all_{user_id}_{plant_id}" if plant_id else "stats_all"
        ),
        InlineKeyboardButton(
            text="📈 Right now measurements", 
            callback_data=f"stats_now_{user_id}_{plant_id}" if plant_id else "stats_now"
        )
    )
    # Второй ряд: уход
    builder.row(
        InlineKeyboardButton(
            text="🌱 Care description", 
            callback_data=f"care_info_{plant_id}" if plant_id else "care_info"
        )
    )
    # Третий ряд: главное меню
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Back to Main Menu", 
            callback_data="main_menu"
        )
    )
    return builder.as_markup()

# Обработчики команд
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user = message.from_user
    await add_user(user.id, user.username)
    
    welcome_text = f"""
    🌿 Welcome to Flora Wand Bot, {user.first_name}!

    I can help you:
    • Add plants to your collection
    • Monitor water, light, humidity and room temperature levels
    • Get care instructions
    • Find the perfect plant for you

    Choose an option from the menu below:
    """
    await message.answer(welcome_text, reply_markup=get_main_menu())

@dp.message(Command("menu"))
async def cmd_menu(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_quiz_state:
        del user_quiz_state[user_id]
    await message.answer("Main menu:", reply_markup=get_main_menu())





# Примеры функций-заглушек для обработки действий
async def show_all_time_stats(callback: types.CallbackQuery, user_id: int, plant_id: int):
    """Показать показатели за все время"""
    plant = await get_plant_by_id(plant_id)
    chat_id = callback.message.chat.id

    # Получаем данные из БД 
    stats_data = await get_plant_stats_from_db(user_id, plant_id)

    # Создаем фигуру с несколькими subplots
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 10))
    fig.suptitle(f'🌿 Plant Statistics\n{plant["plant_name"]}', fontsize=16)
    
    # График температуры
    ax1.plot(stats_data['measured_at'], stats_data['temp_lvl'], 'r-o', linewidth=2)
    ax1.set_title('🌡️ Temperature')
    ax1.set_ylabel('°C')
    ax1.grid(True, alpha=0.3)
    ax1.tick_params(axis='x', rotation=45)
    
    # График влажности
    ax2.plot(stats_data['measured_at'], stats_data['water_lvl'], 'b-s', linewidth=2)
    ax2.set_title('💧 Humidity')
    ax2.set_ylabel('%')
    ax2.grid(True, alpha=0.3)
    ax2.tick_params(axis='x', rotation=45)
    
    # График освещенности
    ax3.bar(stats_data['measured_at'], stats_data['light_level'], color='orange', alpha=0.7)
    ax3.set_title('☀️ Light Level')
    ax3.set_ylabel('Lux')
    ax3.grid(True, alpha=0.3)
    ax3.tick_params(axis='x', rotation=45)
    
    # График полива
    # ax4.scatter(stats_data['watering_dates'], 
    #            [1] * len(stats_data['watering_dates']), 
    #            color='blue', s=100)
    # ax4.set_title('🚰 Watering Events')
    # ax4.set_yticks([])
    # ax4.tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    
    # Сохраняем и отправляем
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    plt.close()
    
    await bot.send_photo(
        chat_id=chat_id,
        photo=BufferedInputFile(buf.getvalue(), filename='plant_stats.png'),
        caption="📊 Detailed plant statistics"
    )
    

async def get_plant_stats_from_db(user_id: int, plant_id: int):
    query = """
        SELECT 
            measured_at,
            temp_lvl,
            humidity_lvl,
            light_lvl,
            water_lvl
        FROM plants_monitor 
        WHERE plant_id = ? AND user_id = ?
        ORDER BY measured_at ASC
        """
    # add AND measured_at >= ? to WHERE to collect data from a certain timestamp
    df = pd.read_sql_query(query, db_connection, params=(user_id, plant_id))
    return df 


async def show_current_stats(callback: types.CallbackQuery, user_id: int, plant_id: int):
    """Показать текущие показатели"""
    plant = await get_plant_by_id(plant_id)
    stats_text = f"""
        📈 Current state of your {plant['plant_name']}:

        • Temperature: {plant['temp_lvl']}°C
        • Soil moisture level: {plant['water_lvl']}%
        • Sunlight: {plant['light_lvl']} lux
        • Overall state: Excellent 🌟
        """
    return stats_text

async def show_care_info(callback: types.CallbackQuery, plant_id: int):
    """Показать информацию об уходе"""
    plant = await get_plant_by_id(plant_id)
    care_text = f"""
        🌱 Уход за {plant['plant_name']}:

        {plant['care_instructions']}

        💧 gather watering info and give advice
        ☀️ gather watering info and give advice
        🌡️ gather watering info and give advice
        """
    return care_text


# Обработчик callback запросов
@dp.callback_query()
async def handle_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    data = callback.data
    
    if data == "main_menu":
        await callback.message.answer("Main menu:", reply_markup=get_main_menu())
        await callback.answer()
    
    elif data == "my_plants":
        plants = await get_user_plants(user_id)
        if plants:
            plants_list = "\n".join([f"🌱 {plant['plant_name']}" for plant in plants])
            text = f"Your plants:\n{plants_list}"
        else:
            text = "You don't have any plants yet. Add some from the main menu!"
        
        await callback.message.answer(text, reply_markup=await get_user_plants_menu(user_id))
        await callback.answer()
    
    elif data == "add_plant_menu":
        await callback.message.answer("Choose a plant to add:", reply_markup=await get_add_plant_menu())
        await callback.answer()
    
    elif data.startswith("add_plant_"):
        plant_id = int(data.split("_")[2])
        success = await add_plant_to_user(user_id, plant_id)
        if success:
            await callback.message.answer("Plant added successfully! ✅ 🌿")
        else:
            await callback.message.answer("This plant is already in your collection! ⚠️")
        await callback.answer()
    
    elif data.startswith("plant_detail_"):
        plant_id = int(data.split("_")[2])
        plant = await get_plant_by_id(plant_id)
        if plant:
            await callback.message.answer("Here are your options: ", reply_markup=get_plant_actions_menu(user_id, plant_id))
        else:
            await callback.message.answer("Plant not found")
        await callback.answer()

    elif data.startswith("stats_all_"):
        plant_id = int(data.split("_")[3])
        await show_all_time_stats(callback, user_id, plant_id)
        await callback.answer(reply_markup=get_plant_actions_menu(user_id, plant_id))

    elif data.startswith("stats_now_"):
        plant_id = int(data.split("_")[3])
        stats_text = await show_current_stats(callback, user_id, plant_id)
        await callback.message.answer(stats_text, reply_markup=get_plant_actions_menu(user_id, plant_id))
        await callback.answer()

    elif data.startswith("care_info_"):
        plant_id = int(data.split("_")[2])
        care_text = await show_care_info(callback, plant_id)
        await callback.message.answer(care_text, reply_markup=get_plant_actions_menu(user_id, plant_id))
        await callback.answer()

    elif data == "start_quiz":
        user_quiz_state[user_id] = {'current_question': 0, 'score': 0}
        await ask_quiz_question(callback.message, user_id)
        await callback.answer()
    
    elif data.startswith("quiz_answer_"):
        if user_id not in user_quiz_state:
            await callback.answer("Quiz not started")
            return
        
        answer_index = int(data.split("_")[2])
        current_state = user_quiz_state[user_id]
        current_question = current_state['current_question']
        
        if current_question < len(QUIZ_QUESTIONS):
            question_data = QUIZ_QUESTIONS[current_question]
            current_state['score'] += question_data['scores'][answer_index]
            current_state['current_question'] += 1
            
            if current_state['current_question'] < len(QUIZ_QUESTIONS):
                await ask_quiz_question(callback.message, user_id)
            else:
                await show_quiz_results(callback.message, user_id)
        
        await callback.answer()

# Функции квиза
async def ask_quiz_question(message: types.Message, user_id: int):
    current_state = user_quiz_state[user_id]
    question_index = current_state['current_question']
    question_data = QUIZ_QUESTIONS[question_index]
    
    builder = InlineKeyboardBuilder()
    for i, option in enumerate(question_data['options']):
        builder.row(InlineKeyboardButton(text=option, callback_data=f"quiz_answer_{i}"))
    
    builder.row(InlineKeyboardButton(text="❌ Cancel Quiz", callback_data="main_menu"))
    
    await message.answer(
        f"Question {question_index + 1}/{len(QUIZ_QUESTIONS)}:\n\n{question_data['question']}",
        reply_markup=builder.as_markup()
    )

async def show_quiz_results(message: types.Message, user_id: int):
    score = user_quiz_state[user_id]['score']
    
    recommendation = ("Snake Plant", "неприхотливое растение")
    for score_range, rec in PLANT_RECOMMENDATIONS.items():
        if score_range[0] <= score <= score_range[1]:
            recommendation = rec
            break
    
    text = f"""
        🎉 Quiz Completed!

        Your score: {score}/9

        🌿 Recommended plant for you:
        {' - '.join(recommendation)}

        Would you like to add this plant to your collection?
    """
    rec_plant = await get_plant_by_name(recommendation[0])
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Add to My Plants", callback_data=f"add_plant_{rec_plant['plant_id']}"),
        InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="main_menu")
    )
    
    await message.answer(text, reply_markup=builder.as_markup())
    
    if user_id in user_quiz_state:
        del user_quiz_state[user_id]


# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

# Quiz questions and answers
QUIZ_QUESTIONS = [
    {
        'question': 'How often can you water your plants?',
        'options': ['Daily', '2-3 times a week', 'Once a week', 'Once two weeks'],
        'scores': [3, 2, 1, 0]
    },
    {
        'question': 'How much sunlight can you provide for your plant?',
        'options': ['Lots of direct sunlight', 'Scatterred sunlight', 'Partial shade', 'Darkness'],
        'scores': [3, 2, 1, 0]
    },
    {
        'question': 'What level of care can you provide?',
        'options': ['Easy care', 'Moderate care', 'Complex care', 'Not important'],
        'scores': [0, 1, 2, 0]
    }
]

PLANT_RECOMMENDATIONS = {
    (0, 3): ('Dieffenbachia', 'low-maintenance'),
    (4, 6): ('Cactus', 'medium-meintenance'),
    (7, 9): ('Monstera', 'high-maintenance')
}

user_quiz_state = {}
