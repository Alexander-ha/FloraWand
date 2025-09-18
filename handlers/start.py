from aiogram import Router
from aiogram.filters import Command
import aiosqlite
import logging
from typing import Optional
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from aiogram import types
import matplotlib.pyplot as plt
import pandas as pd
from datetime import timedelta
from io import BytesIO
import matplotlib.dates as mdates

from create_bot import bot, dp

logger = logging.getLogger(__name__)
start_router = Router()
user_quiz_state = {}
db_connection = None

async def init_db():
    global db_connection
    if db_connection is None:
        db_connection = await aiosqlite.connect('flowers.db')
        await db_connection.execute('PRAGMA journal_mode=WAL')
        await db_connection.execute('PRAGMA busy_timeout=5000')


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
            CREATE TABLE IF NOT EXISTS plants_monitor_final (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                plant_id INTEGER NOT NULL,
                water_lvl REAL,
                light_lvl REAL,
                temp_lvl REAL,
                measured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await db_connection.execute('''
            CREATE INDEX IF NOT EXISTS idx_monitor_user_plant ON plants_monitor_final (user_id, plant_id)
        ''')
        await db_connection.execute('''
            CREATE INDEX IF NOT EXISTS idx_monitor_timestamp ON plants_monitor_final (measured_at)            
        ''')
        # care_description = [
        #     "\n🌱 Dieffenbachia — a decorative tropical plant with large variegated leaves in green and cream patterns.\n👉 Keep it in bright, indirect light, water regularly, and avoid cold drafts.",
        #     "\n🌵 Cactus — a slow-growing succulent with spines that stores water in its stem.\n👉 Keep it in bright sunlight and water only when the soil is completely dry.",
        #     "\n🌿 Ficus — an evergreen tree with elegant drooping branches and glossy leaves.\n👉 Place it in bright, indirect light and avoid sudden changes in conditions to prevent leaf drop.",
        #     "\n🍃 Monstera — a tropical climbing plant with large leaves featuring iconic splits and holes.\n👉 Water moderately and provide partial shade to protect it from direct sunburn.",
        #     "\n🌸 Orchid — a delicate orchid known as the “dancing lady” for its clusters of small, fluttering flowers.\n👉 Give it bright, filtered light, water when the top of the potting mix is dry, and ensure good air circulation."]
        # for i, plant in enumerate(care_description):
        #     query = f'''
        #         UPDATE plants_info SET care_description = ? WHERE plant_id = ?
        #     '''
        #     await db_connection.execute(query, (plant, i+1))
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

# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
# DATABASE QUERIES

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
                query += f"DESC LIMIT {cnt}" # !!!!!!! выдает самую старую запись пока, надо самую новую
            cursor = await db.execute(query, (plant_id, user_id))  
            rows = await cursor.fetchall()
            if not rows:
                return None
            df = pd.DataFrame(rows, columns=['water_lvl', 'temp_lvl', 'light_lvl', 'humidity_lvl', 'measured_at'])
            df['measured_at'] = pd.to_datetime(df['measured_at'])
            df.set_index('measured_at', inplace=True)
            
            # Убеждаемся, что индекс имеет правильный тип
            if not isinstance(df.index, pd.DatetimeIndex):
                df.index = pd.to_datetime(df.index)
            return df
    except Exception as e:
        print(f"Error fetching plant stats: {e}")
        return None

# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# MENU FUNCTIONS

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
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="📊 Dashboard", 
            callback_data=f"stats_all_{user_id}_{plant_id}" if plant_id else "stats_all"
        ),
        InlineKeyboardButton(
            text="📈 Current state", 
            callback_data=f"stats_now_{user_id}_{plant_id}" if plant_id else "stats_now"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🌱 Care description", 
            callback_data=f"care_info_{plant_id}" if plant_id else "care_info"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Back to my plants", 
            callback_data="my_plants"
        ),
        InlineKeyboardButton(
            text="⬅️ Back to Main Menu", 
            callback_data="main_menu"
        )
    )
    return builder.as_markup()

def get_time_range_menu(user_id: int, plant_id: int) -> InlineKeyboardMarkup:
    """
    Создает меню для выбора временного диапазона графиков
    """
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="📊 24 hours", callback_data=f"graph_24h_{user_id}_{plant_id}"),
        InlineKeyboardButton(text="📈 7 days", callback_data=f"graph_7d_{user_id}_{plant_id}"),
        InlineKeyboardButton(text="📅 30 days", callback_data=f"graph_30d_{user_id}_{plant_id}")
    )
    
    builder.row(
        InlineKeyboardButton(text="🕰️ All time", callback_data=f"graph_all_{user_id}_{plant_id}"),
        InlineKeyboardButton(text="🌿 Auto", callback_data=f"graph_auto_{user_id}_{plant_id}")
    )
    
    builder.row(
        InlineKeyboardButton(text="⬅️ Back to options", callback_data=f"plant_detail_{plant_id}")
    )
    
    return builder.as_markup()

# ***************************************************************************************************************************************************************************************************************************************
# STATISTICS HANDLERS
def format_datetime_axis(ax, timestamps: pd.Series, rotation: int = 45):
    if timestamps.empty:
        return
    
    time_range = timestamps.max() - timestamps.min()
    
    if time_range <= timedelta(hours=12):
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
    elif time_range <= timedelta(days=1):
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
    elif time_range <= timedelta(days=7):
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m %H:%M'))
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
    elif time_range <= timedelta(days=30):
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=2))
    elif time_range <= timedelta(days=90):
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
        ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
    else:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
    
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=rotation, ha='right')

async def create_time_range_graph(callback: types.CallbackQuery, user_id: int, plant_id: int, time_range: str = 'auto') -> Optional[BytesIO]:
    """
    Создает график для определенного временного диапазона
    
    Args:
        time_range: '24h', '7d', '30d', 'all', 'auto'
    """
    try:
        df = await get_plant_stats_from_db(user_id, plant_id)
        
        if df is None or df.empty:
            await callback.message.answer("📊 No statistics data available for this period.")
            return 
        
        # Фильтруем данные по временному диапазону
        now = pd.Timestamp.now()
        
        if time_range == '24h':
            filtered_df = df[df.index >= now - timedelta(hours=24)]
            title_suffix = ' (24 hours)'
        elif time_range == '7d':
            filtered_df = df[df.index >= now - timedelta(days=7)]
            title_suffix = ' (7 days)'
        elif time_range == '30d':
            filtered_df = df[df.index >= now - timedelta(days=30)]
            title_suffix = ' (30 days)'
        else:
            filtered_df = df
            title_suffix = ' (all time)'
        
        if filtered_df.empty:
            return None
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 10))
        fig.suptitle(f'Plant Statistics{title_suffix}', fontsize=16)
        
        ax1.plot(filtered_df.index, filtered_df['temp_lvl'], marker='o', color="red", linewidth=3)
        ax1.set_title('Temperature')
        ax1.set_ylabel('°C')
        ax1.grid(True, alpha=0.3)
        
        ax2.plot(filtered_df.index, filtered_df['water_lvl'], marker='o', color="blue", linewidth=3)
        ax2.set_title('Soil moisture')
        ax2.set_ylabel('%')
        ax2.grid(True, alpha=0.3)
        
        ax3.plot(filtered_df.index, filtered_df['light_lvl'], marker='o', color="orange", linewidth=3)
        ax3.set_title('Light')
        ax3.set_ylabel('Lux')
        ax3.grid(True, alpha=0.3)
        
        ax4.plot(filtered_df.index, filtered_df['humidity_lvl'], marker='o', color="gray", linewidth=3)
        ax4.set_title('Air humidity')
        ax4.set_ylabel('%')
        ax4.grid(True, alpha=0.3)
    
        
        format_datetime_axis(ax1, pd.Series(filtered_df.index))
        format_datetime_axis(ax2, pd.Series(filtered_df.index))
        format_datetime_axis(ax3, pd.Series(filtered_df.index))
        format_datetime_axis(ax4, pd.Series(filtered_df.index))
        
        plt.tight_layout()

        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        plt.close()

        await bot.send_photo(
        chat_id=callback.message.chat.id,
        photo=BufferedInputFile(buf.getvalue(), filename='plant_stats.png'),
        caption="📊 Detailed plant statistics"
    )
        
    except Exception as e:
        print(f"Error creating time range graph: {e}")
        return None


async def show_current_stats(callback: types.CallbackQuery, user_id: int, plant_id: int):
    plant = await get_plant_by_id(plant_id)
    df = await get_plant_stats_from_db(user_id, plant_id, cnt=1)

    if df is None or df.empty:
        stats_text = "📊 No statistics data available for this plant."
    else:
        stats_text = f"""
        📈 Current state of your {plant['plant_name']}:
            • Soil moisture level: {df['water_lvl'].values[0]}%
            • Temperature: {df['temp_lvl'].values[0]}°C
            • Sunlight: {df['light_lvl'].values[0]} lux
            • Humidity: {df['humidity_lvl'].values[0]} %
        """
    return stats_text

async def show_care_info(plant_id: int):
    plant = await get_plant_by_id(plant_id)
    care_text = f"{plant['care_description']}\n\n\t💧 gather watering info and give advice\n☀️ gather watering info and give advice\n🌡️ gather watering info and give advice"
    return care_text

#++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# COMMAND HANDLERS

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
    
# ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
# CALLBACK QUERIES HANDLERS

@dp.callback_query()
async def handle_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    data = callback.data
    if data == "main_menu":
        await callback.message.answer("Main menu:", reply_markup=get_main_menu())
        # await callback.answer()
    
    elif data == "my_plants":
        plants = await get_user_plants(user_id)
        if plants:
            text = f"Your plants:\n"
        else:
            text = "You don't have any plants yet. Add some from the main menu!"
        
        await callback.message.answer(text, reply_markup=await get_user_plants_menu(user_id))
        # await callback.answer()
    
    elif data == "add_plant_menu":
        await callback.message.answer("Choose a plant to add:", reply_markup=await get_add_plant_menu())
        # await callback.answer()
    
    elif data.startswith("add_plant_"):
        plant_id = int(data.split("_")[2])
        success = await add_plant_to_user(user_id, plant_id)
        if success:
            await callback.message.answer("Plant added successfully! ✅ 🌿")
        else:
            await callback.message.answer("This plant is already in your collection! ⚠️")
        # await callback.answer()
    
    elif data.startswith("plant_detail_"):
        plant_id = int(data.split("_")[2])
        plant = await get_plant_by_id(plant_id)
        if plant:
            await callback.message.answer("Here are your options: ", reply_markup=get_plant_actions_menu(user_id, plant_id))
        else:
            await callback.message.answer("Plant not found")
        # await callback.answer()

    elif data.startswith("stats_all_"):
        plant_id = int(data.split("_")[3])
        # await show_all_time_stats(callback, user_id, plant_id)
        await callback.message.answer("Select time period", reply_markup=get_time_range_menu(user_id, plant_id))
        # await callback.answer()

    elif data.startswith("stats_now_"):
        plant_id = int(data.split("_")[3])
        stats_text = await show_current_stats(callback, user_id, plant_id)
        await callback.message.answer(stats_text, reply_markup=get_plant_actions_menu(user_id, plant_id))
        # await callback.answer()

    elif data.startswith("care_info_"):
        plant_id = int(data.split("_")[2])
        care_text = await show_care_info(plant_id)
        await callback.message.answer(care_text, reply_markup=get_plant_actions_menu(user_id, plant_id))
        # await callback.answer()

    elif data == "start_quiz":
        user_quiz_state[user_id] = {'current_question': 0, 'score': 0}
        await ask_quiz_question(callback.message, user_id)
        # await callback.answer()
    
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

    elif  data.startswith("graph_"):
        plant_id = int(data.split("_")[3])
        await create_time_range_graph(callback, user_id, plant_id, data.split("_")[1])
        await callback.message.answer("Other time period?", reply_markup=get_time_range_menu(user_id, plant_id))

    await callback.answer()

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
# QUIZ HANDLERS
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
    
    recommendation = ("Cactus", "low-maintenance")
    for score_range, rec in PLANT_RECOMMENDATIONS.items():
        if score_range[0] <= score <= score_range[1]:
            recommendation = rec
            break
    plant = await get_plant_by_name(recommendation[0])
    text = f"""
        🎉 Quiz Completed!

        🌿 Recommended plant for you: {' - '.join(recommendation)}
        {plant['care_description']}
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





