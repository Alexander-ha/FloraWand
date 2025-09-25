import logging
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from create_bot import bot, dp
from aiogram import types
from aiogram import Router, types
import shared_vars
from queue import Queue
from threading import Thread


from handlers.quiz import *
from handlers.menus import *
from handlers.db_queries import *
from create_bot import bot, dp
from handlers.statistics import *

menus_router = Router()


SENTINEL = object()


logger = logging.getLogger(__name__)

def watering_menu(has_wand: bool = True, notify_on: bool = True) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
            InlineKeyboardButton(text="➕ Add Plant", callback_data="add_plant_menu"),
            InlineKeyboardButton(text="❓ What plant am I?", callback_data="start_quiz")
        )
    if has_wand:
        builder.row(
            InlineKeyboardButton(text="🌿 My Plants", callback_data="my_plants"),
            InlineKeyboardButton(text="📋 My Wands", callback_data="my_wands")
        )

    else:
        builder.row(
            InlineKeyboardButton(text="🌿 My Plants", callback_data="my_plants"),
            InlineKeyboardButton(text="🪄 Register Wand", callback_data="register_wand_info")
        )
    builder.row(
            InlineKeyboardButton(text="💦 Water my plants", callback_data="water_callback"),
        )

    if notify_on:
        builder.row(InlineKeyboardButton(text="📴 Alerts OFF", callback_data="notify_on_off"))
    else:
        builder.row(InlineKeyboardButton(text="📳 Alerts ON", callback_data="notify_on_off"))

    return builder.as_markup()


def get_main_menu(has_wand: bool = True, notify_on: bool = True) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
            InlineKeyboardButton(text="➕ Add Plant", callback_data="add_plant_menu"),
            InlineKeyboardButton(text="❓ What plant am I?", callback_data="start_quiz")
        )
    if has_wand:
        builder.row(
            InlineKeyboardButton(text="🌿 My Plants", callback_data="my_plants"),
            InlineKeyboardButton(text="📋 My Wands", callback_data="my_wands")
        )
    else:
        builder.row(
            InlineKeyboardButton(text="🌿 My Plants", callback_data="my_plants"),
            InlineKeyboardButton(text="🪄 Register Wand", callback_data="register_wand_info")
        )
    if notify_on:
        builder.row(InlineKeyboardButton(text="📴 Alerts OFF", callback_data="notify_on_off"))
    else:
        builder.row(InlineKeyboardButton(text="📳 Alerts ON", callback_data="notify_on_off"))

    return builder.as_markup()

async def get_wand_plants_menu(user_id: int, wand_id: str) -> InlineKeyboardMarkup:
    plants = await get_wand_plants(user_id, wand_id)
    builder = InlineKeyboardBuilder()
    
    for plant in plants:
        builder.row(
            InlineKeyboardButton(
                text=f"🌱 {plant['plant_name']}", 
                callback_data=f"plant_detail_{plant['plant_id']}"
            )
        )
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Back to Wand Menu", 
            callback_data=f"select_wand_{user_id}_{wand_id}"
        )
    )
    return builder.as_markup()


async def get_wand_users_menu(user_id: int, wand_id: str) -> InlineKeyboardMarkup:
    users = await get_wand_users(wand_id)  
    builder = InlineKeyboardBuilder()
    
    for user in users:
        builder.row(
            InlineKeyboardButton(
                text=f"👤 User: {user}",
                callback_data=f"get_user_{user}"
            )
        )
    builder.row(
        InlineKeyboardButton(text="⬅️ Back to Wand Menu", callback_data=f"select_wand_{user_id}_{wand_id}")
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

async def get_wand_control_menu(user_id: int, wand_id: str) -> InlineKeyboardMarkup:
    """
    Создает меню для управления wand'ом
    """
    
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="🌵 Connected plants", callback_data=f"connected_plants_{wand_id}_{user_id}"),
        InlineKeyboardButton(text="🧒 Connected users", callback_data=f"connected_users_{wand_id}_{user_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="🔮 Link wand", callback_data=f"link_wand_{wand_id}"),
        InlineKeyboardButton(text="🗑️ Delete wand", callback_data=f"remove_wand_{wand_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Back to wands", callback_data="my_wands"),
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Back to main menu", callback_data="main_menu")
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
        ),
        InlineKeyboardButton(
            text="🌱 Care description", 
            callback_data=f"care_info_{plant_id}" if plant_id else "care_info"
        ),
    )
    builder.row(
        
        InlineKeyboardButton(
            text="🗑️ Delete plant", 
            callback_data=f"remove_plant_{plant_id}" if plant_id else "remove_plant"
        ),
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
        InlineKeyboardButton(text="📅 1 hour", callback_data=f"graph_1h_{user_id}_{plant_id}"),
        InlineKeyboardButton(text="📊 24 hours", callback_data=f"graph_24h_{user_id}_{plant_id}"),
        InlineKeyboardButton(text="📈 7 days", callback_data=f"graph_7d_{user_id}_{plant_id}"),
    )
    
    builder.row(
        InlineKeyboardButton(text="📅 30 days", callback_data=f"graph_30d_{user_id}_{plant_id}"),
        InlineKeyboardButton(text="🕰️ All time", callback_data=f"graph_all_{user_id}_{plant_id}"),
        InlineKeyboardButton(text="🌿 Auto", callback_data=f"graph_auto_{user_id}_{plant_id}")
    )
    
    builder.row(
        InlineKeyboardButton(text="⬅️ Back to options", callback_data=f"plant_detail_{plant_id}")
    )
    
    return builder.as_markup()

async def get_plants_selection_menu(user_id: int, wand_id: str) -> InlineKeyboardMarkup:
    """Меню для выбора растения"""
    user_plants = await get_user_plants(user_id)
    builder = InlineKeyboardBuilder()
    
    for plant in user_plants:
        builder.row(
            InlineKeyboardButton(
                text=f"🌱 {plant['plant_name']} (ID: {plant['plant_id']})",
                callback_data=f"select_plant_for_wand_{wand_id}_{plant['plant_id']}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_link_wand")
    )
    
    return builder.as_markup()


async def get_wands(user_id: int) -> InlineKeyboardMarkup:
    """Create menu for selecting a wand"""
    builder = InlineKeyboardBuilder()
    wands = await get_user_wands(user_id)

    if not wands:
        builder.row(
            InlineKeyboardButton(text="🪄 Register New Wand", callback_data="register_wand_info")
        )
        builder.row(
            InlineKeyboardButton(text="⬅️ Back to Main Menu", callback_data="main_menu")
        )
        return builder.as_markup()

    for wand in wands:
        plant_name = wand['plant_name'] if wand['plant_name'] else "Not linked"
        button_text = f"🪄 {wand['wand_id']} - {plant_name}"
        
        builder.row(
            InlineKeyboardButton(text=button_text, callback_data=f"select_wand_{user_id}_{wand['wand_id']}")
        )
    
    builder.row(
        InlineKeyboardButton(text="➕ Register New Wand", callback_data="register_wand_info")
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Back to Main Menu", callback_data="main_menu")
    )
    
    return builder.as_markup()

@menus_router.callback_query()
async def handle_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    data = callback.data
    if data == "main_menu":
        await callback.message.answer("Main menu:", reply_markup=get_main_menu(await user_has_wand(user_id), await is_notify_on(user_id)), parse_mode=None)
    
    elif data == "my_plants":
        plants = await get_user_plants(user_id)
        if plants:
            text = f"Your plants:\n"
        else:
            text = "You don't have any plants yet. Add some from the main menu!"
        
        await callback.message.answer(text, reply_markup=await get_user_plants_menu(user_id), parse_mode=None)
    
    elif data == "add_plant_menu":
        await callback.message.answer("Choose a plant to add:", reply_markup=await get_add_plant_menu(), parse_mode=None)

    elif data == "water_callback":
        message = {"user_id": user_id, "command": "water"}
        logger.info(f"User {user_id} pressed water button, sending message to pipeline: {message}")
        try:
            if shared_vars.bot_pipeline:
                await shared_vars.bot_pipeline.set_message(message, "Producer")
                logger.info(f"Message {message} successfully sent to pipeline by user {user_id}")
                await callback.answer("Watering command sent! 💦")
            else:
                logger.error("bot_pipeline is not initialized")
                await callback.answer("System error: pipeline not available ❌")
        except Exception as e:
            logger.error(f"Error sending message to pipeline: {e}")
            await callback.answer("Error sending command ❌")
    
    elif data.startswith("add_plant_"):
        plant_id = int(data.split("_")[2])
        success = await add_plant_to_user(user_id, plant_id)
        if success:
            await callback.message.answer("Plant added successfully! ✅ 🌿", parse_mode=None)
        else:
            await callback.message.answer("This plant is already in your collection! ⚠️", parse_mode=None)

    elif data.startswith("link_wand_"):
        wand_id = data.split("_")[2]
        
        user_plants = await get_user_plants(user_id)
        if not user_plants:
            await callback.message.answer("You don't have any plants yet.", parse_mode=None)
            return
        
        await callback.message.answer(
            "Select a plant to link to this wand:",
            reply_markup=await get_plants_selection_menu(user_id, wand_id),
            parse_mode=None
        )

    elif data.startswith("remove_wand_"):
        wand_id = data.split("_")[2]
        try:
            async with aiosqlite.connect('flowers.db') as db:
                await db.execute(
                        "DELETE FROM users_wands WHERE user_id = ? AND wand_id = ?",
                        (user_id, wand_id)
                    )
                await db.commit()
            
            await callback.message.answer(
                "Wand was successfully deleted.",
                parse_mode=None
            )
        except:
            await callback.message.answer(
                "Can't find any wands with such number",
                parse_mode=None
            )

    elif data.startswith("remove_plant_"):
        plant_id = int(data.split("_")[2])
        try:
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
            
            await callback.message.answer(
                "Plant was successfully deleted.",
                parse_mode=None
            )
        except:
            await callback.message.answer(
                "Error deleting plant info.",
                parse_mode=None
            )

    elif data.startswith("select_plant_for_wand_"):
        parts = data.split("_")
        wand_id = parts[4]
        plant_id = int(parts[5])
        
        async with aiosqlite.connect('flowers.db') as db:
            await db.execute(
                "UPDATE users_wands SET plant_id = ? WHERE wand_id = ? AND user_id = ?",
                (plant_id, wand_id, user_id)
            )
            await db.commit()
        
        plant = await get_plant_by_id(plant_id)
        await callback.message.answer(
            f"✅ Wand {wand_id} successfully linked to '{plant['plant_name']}'!", 
            parse_mode=None
        )

    elif data == "cancel_link_wand":
        await callback.message.answer("Linking operation cancelled.", parse_mode=None)

    elif data.startswith("get_user_"):
            await callback.message.answer("This info is currently closed", parse_mode=None)

    elif data.startswith("plant_detail_"):
        plant_id = int(data.split("_")[2])
        plant = await get_plant_by_id(plant_id)
        if plant:
            await callback.message.answer("Here are your options: ", reply_markup=get_plant_actions_menu(user_id, plant_id), parse_mode=None)
        else:
            await callback.message.answer("Plant not found", parse_mode=None)

    elif data.startswith("stats_all_"):
        plant_id = int(data.split("_")[3])
        await callback.message.answer("Select time period", reply_markup=get_time_range_menu(user_id, plant_id), parse_mode=None)

    elif data.startswith("stats_now_"):
        plant_id = int(data.split("_")[3])
        stats_text = await show_current_stats(callback, user_id, plant_id)
        await callback.message.answer(stats_text, reply_markup=get_plant_actions_menu(user_id, plant_id), parse_mode=None)

    elif data.startswith("care_info_"):
        plant_id = int(data.split("_")[2])
        care_text = await show_care_info(plant_id)
        await callback.message.answer(care_text, reply_markup=get_plant_actions_menu(user_id, plant_id), parse_mode=None)
    
    elif data.startswith("connected_plants_"):
        wand_id = data.split("_")[2]
        user_id = data.split("_")[3]
        await callback.message.answer("Here are the plants, connected to your wand", reply_markup=await get_wand_plants_menu(user_id, wand_id), parse_mode=None)

    elif data.startswith("connected_users_"):
        wand_id = data.split("_")[2]
        user_id = data.split("_")[3]
        await callback.message.answer("Here are the users, connected to your wand", reply_markup=await get_wand_users_menu(user_id, wand_id), parse_mode=None)


    elif data == "start_quiz":
        user_quiz_state[user_id] = {'current_question': 0, 'score': 0}
        await ask_quiz_question(callback.message, user_id)
    
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

    elif data.startswith("select_wand_"):
        user_id = data.split("_")[2]
        wand_id = data.split("_")[3]
        await callback.message.answer("Your wand information: "+ wand_id, 
            reply_markup=await get_wand_control_menu(user_id, wand_id), 
            parse_mode=None
        )

    elif  data.startswith("graph_"):
        plant_id = int(data.split("_")[3])
        await create_time_range_graph(callback, user_id, plant_id, time_range=data.split("_")[1])
        await callback.message.answer("Other time period?", reply_markup=get_time_range_menu(user_id, plant_id), parse_mode=None)

    elif data == "register_wand_info":
        user_plants = await get_user_plants(user_id)
        plants_text = "To register a wand, use the command:\n/register_wand wand_id plant_id\n\n"
        plants_text += "Your plants:\n"
        for plant in user_plants:
            plants_text += f"ID {plant['plant_id']} - {plant['plant_name']}\n"
            
        await callback.message.answer(plants_text, parse_mode=None)
                
    elif data == "my_wands":
        wands = await get_user_wands(user_id)
        if not wands:
            await callback.message.answer("You don't have any registered wands.", parse_mode=None)
        else:
            wands_text = "Your registered wands:\n\n"
            for wand in wands:
                registered_date = wand['registered_at'].split()[0]
                wands_text += (
                    f"• Wand: {wand['wand_id']}\n"
                    f"  Plant: {wand['plant_name']} (ID: {wand['plant_id']})\n"
                    f"  Registered: {registered_date}\n\n"
                )
            await callback.message.answer(wands_text, reply_markup=await get_wands(user_id), parse_mode=None)

    elif data == "notify_on_off":
        await change_notify(user_id)
    await callback.answer()
