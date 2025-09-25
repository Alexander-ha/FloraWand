from aiogram import Router
from aiogram.filters import Command
import aiosqlite
import logging
from aiogram import types

from create_bot import bot, dp
from handlers.quiz import user_quiz_state

from handlers.db_queries import *
from handlers.menus import get_main_menu
from handlers.menus import *

logger = logging.getLogger(__name__)
start_router = Router()

@start_router.startup()
async def init_db():
    async with aiosqlite.connect('flowers.db') as db:
        await db.execute('PRAGMA journal_mode=WAL')
        await db.execute('PRAGMA busy_timeout=5000')


        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        await db.execute('''
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
        await db.execute('''
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
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users_wands (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                plant_id INTEGER,
                wand_id TEXT NOT NULL,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                FOREIGN KEY (plant_id) REFERENCES plants_info_new (plant_id)
            )
        ''')
        await db.execute('''
            CREATE INDEX IF NOT EXISTS idx_monitor_user_plant ON plants_monitor_final (user_id, plant_id)
        ''')
        await db.execute('''
            CREATE INDEX IF NOT EXISTS idx_monitor_timestamp ON plants_monitor_final (measured_at)            
        ''')
        await db.execute('''
            CREATE INDEX IF NOT EXISTS idx_wand_id ON users_wands (wand_id)
        ''')

        # care_description = [
        #     "🌱 Dieffenbachia — a decorative tropical plant with large variegated leaves in green and cream patterns.\n👉 Keep it in bright, indirect light, water regularly, and avoid cold drafts.",
        #     "🌵 Cactus — a slow-growing succulent with spines that stores water in its stem.\n👉 Keep it in bright sunlight and water only when the soil is completely dry.",
        #     "🌿 Ficus — an evergreen tree with elegant drooping branches and glossy leaves.\n👉 Place it in bright, indirect light and avoid sudden changes in conditions to prevent leaf drop.",
        #     "🍃 Monstera — a tropical climbing plant with large leaves featuring iconic splits and holes.\n👉 Water moderately and provide partial shade to protect it from direct sunburn.",
        #     "🌸 Orchid — a delicate orchid known as the “dancing lady” for its clusters of small, fluttering flowers.\n👉 Give it bright, filtered light, water when the top of the potting mix is dry, and ensure good air circulation."]
        
        # for i, plant in enumerate(care_description):
        #     query = f'''
        #         UPDATE plants_info_new SET care_description = ? WHERE plant_id = ?
        #     '''
        #     await db.execute(query, (plant, i+1))

        # veggies_care_desc = ["🥒 Cucumber — vining vegetable with crisp fruits; loves warmth, moisture, and lots of light.\n👉 Keep soil consistently moist (but not waterlogged), provide plenty of air circulation to prevent fungal diseases, and support vines (trellis) so fruits don’t touch soil. Use full sun or strong grow lights especially in less sunny periods.", 
        #                      "🍅 Tomato — fruiting plant needing good day-night temperature difference for best yields.\n👉 Ensure warm days and cooler nights (but not too cold), remove lower leaves for airflow, stake or cage the plants so branches don’t break, and feed with fertilizer especially when flowering begins. Avoid letting soil dry out.",
        #                      "🌶 Pepper — loves heat; sensitive to cold dips.\n👉 Keep night temperatures above ~18-20°C, avoid cold drafts; use mulch to conserve soil moisture and warmth; ensure good light especially during fruiting; pick off early blossoms if plant is too small or weak to support fruit to focus energy on vegetative growth first."]

        # query = "insert into plants_info_new (plant_name, care_description, light_low, light_high, temp_low, temp_high, water_low, water_high, humid_low, humid_high) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        # await db.execute(query, ("Cucumber", veggies_care_desc[0], 5000, 12000, 20, 26, 60, 80, 60, 75 ))
        # await db.execute(query, ("Tomato", veggies_care_desc[1],  6000, 15000, 18, 25, 55, 75, 55, 70 ))
        # await db.execute(query, ("Pepper", veggies_care_desc[2], 4000, 10000, 20, 28, 60, 75, 60, 70 ))
        await db.commit()
        logger.info("Database initiated.")



@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user = message.from_user
    welcome_text = f"""
    🌿 Welcome back to Flora Wand Bot, {user.first_name}!

    I can help you:
    • Add plants to your collection
    • Monitor water, light, humidity and room temperature levels
    • Get care instructions
    • Find the perfect plant for you
    """

    await add_user(user.id, user.username)
    has_wand = await user_has_wand(user.id)
    if not has_wand:
        welcome_text = f"""
        🌿 Welcome to Flora Wand Bot, {user.first_name}!

        I can help you:
        • Add plants to your collection
        • Monitor water, light, humidity and room temperature levels
        • Get care instructions
        • Find the perfect plant for you
        """
        welcome_text += '\n\n🔮➕ You have a new wand! Check out "My Wands" menu.'
        await register_user_wand(user.id, "30:83:98:B2:D4:0D")

    has_wand = await user_has_wand(user.id)
    notify_on = await is_notify_on(user.id)

    # if not has_wand:
        # welcome_text += "\n\n⚠️ Please register your wand first to access all features!"
    
    await message.answer(welcome_text, reply_markup= get_main_menu(has_wand, notify_on), parse_mode=None)

    
@dp.message(Command("menu"))
async def cmd_menu(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_quiz_state:
        del user_quiz_state[user_id]
    await message.answer("Main menu:", reply_markup= get_main_menu(await user_has_wand(user_id), await is_notify_on(user_id)), parse_mode=None)


@dp.message(Command("remove_wand"))
async def cmd_remove_wand(message: types.Message):
    """Удаление палочки у пользователя"""
    user_id = message.from_user.id
    parts = message.text.split()
    
    if len(parts) < 2:
        await message.answer(
            "Please specify the wand ID to remove.\n\n"
            "Usage: /remove_wand <wand_id>",
            parse_mode=None
        )
        return
    try:
        wand_id = parts[1]
            
        async with aiosqlite.connect('flowers.db') as db:
            await db.execute(
                    "DELETE FROM users_wands WHERE user_id = ? AND wand_id = ?",
                    (user_id, wand_id)
                )
            await db.commit()
            
        await message.answer(f"Wand {wand_id} successfully removed from your account.", parse_mode=None)
    except ValueError:
        await message.answer("Please, specify wand ID: /remove_wand <wand_id>", parse_mode=None)
        return
    

@dp.message(Command("register_wand"))
async def cmd_register_wand(message: types.Message):
    """Обработчик команды регистрации новой палочки"""
    user_id = message.from_user.id
    parts = message.text.split()
    
    if len(parts) < 2:
        await message.answer(
            "Please specify the wand ID after the command.\n\n"
            "Usage: /register_wand <wand_id> [plant_id]\n\n"
            "You can optionally specify a plant ID to link the wand to a specific plant.", 
            parse_mode=None
        )
        return
    
    wand_id = parts[1]
    
    # Проверяем формат MAC-адреса
    if not is_valid_mac_address(wand_id):
        await message.answer(
            "Invalid MAC address format. Please use format like: 30:83:98:B2:D4:0D\n"
            "The MAC address should contain 6 pairs of hex digits separated by colons or hyphens.",
            parse_mode=None
        )
        return
    
    plant_id = None
    
    if len(parts) >= 3:
        try:
            plant_id = int(parts[2])
            user_plants = await get_user_plants(user_id)
            user_plant_ids = [plant['plant_id'] for plant in user_plants]
            if plant_id not in user_plant_ids:
                await message.answer(
                    "The specified plant is not in your collection. "
                    "Registering wand without plant association.",
                    parse_mode=None
                )
                plant_id = None
        except ValueError:
            await message.answer(
                "Invalid plant ID. Registering wand without plant association.",
                parse_mode=None
            )
            plant_id = None
    
    try:
        success = await register_user_wand(user_id, wand_id, plant_id)
        if success:
            if plant_id:
                plant = await get_plant_by_id(plant_id)
                await message.answer(
                    f"✅ Wand {wand_id} successfully registered for '{plant['plant_name']}'!",
                    parse_mode=None
                )
            else:
                await message.answer(
                    f"✅ Wand {wand_id} successfully registered! "
                    "You can link it to a plant later using /link_wand command.",
                    parse_mode=None
                )
            await message.answer("Main menu:", reply_markup= get_main_menu(True, await is_notify_on(user_id)), parse_mode=None)
        else:
            await message.answer("❌ Error registering the wand.", parse_mode=None)
    except ValueError as e:
        await message.answer(str(e), parse_mode=None)

@dp.message(Command("link_wand"))
async def cmd_link_wand(message: types.Message):
    """Привязка палочки к растению"""
    user_id = message.from_user.id
    parts = message.text.split()
    
    if len(parts) < 3:
        await message.answer(
            "Please specify both wand ID and plant ID.\n\n"
            "Usage: /link_wand <wand_id> <plant_id>", parse_mode = None
        )
        return
    wand_id = parts[1]
    try:
        plant_id = int(parts[2])
    except ValueError:
        await message.answer("Invalid plant ID. Please specify a numeric plant ID.", parse_mode=None)
        return
    wand_owner = await get_wand_owner(wand_id)
    wand_owners = [x for xs in wand_owner for x in xs]
    print(f"User was found {user_id}")
    if user_id not in wand_owners:
        await message.answer("This wand is not registered to your account.", parse_mode=None)
        return
    user_plants = await get_user_plants(user_id)
    user_plant_ids = [plant['plant_id'] for plant in user_plants]
    if plant_id not in user_plant_ids:
        await message.answer("The specified plant is not in your collection.", parse_mode=None)
        return
    async with aiosqlite.connect('flowers.db') as db:
        await db.execute(
            "UPDATE users_wands SET plant_id = ? WHERE wand_id = ? AND user_id = ?",
            (plant_id, wand_id, user_id)
        )
        await db.commit()
    
    plant = await get_plant_by_id(plant_id)
    await message.answer(
        f"✅ Wand {wand_id} successfully linked to '{plant['plant_name']}'!", parse_mode=None
    )


@dp.message(Command("my_wands"))
async def cmd_my_wands(message: types.Message):
    """Обработчик команды просмотра зарегистрированных палочек"""
    builder = InlineKeyboardBuilder()
    user_id = message.from_user.id
    wands = await get_user_wands(user_id)
    
    if not wands:
        await message.answer("You don't have any registered wands.", parse_mode=None)
        return
    
    wands_text = "Your registered wands:\n\n"
    for wand in wands:
        registered_date = wand['registered_at'].split()[0] 
        plant_info = f"Linked to: {wand['plant_name']}" if wand['plant_id'] else "Not linked to any plant"
        wands_text += (
            f"• Wand: {wand['wand_id']}\n"
            f"  {plant_info}\n"
            f"  Registered: {registered_date}\n\n"
        )
        builder.row(
            InlineKeyboardButton(text=wands_text, reply_markup=get_wand_control_menu(user_id, wand['wand_id']), parse_mode=None),
        )
    
    return builder.as_markup()