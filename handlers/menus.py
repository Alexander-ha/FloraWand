import logging
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from create_bot import bot, dp
from aiogram import types

from handlers.quiz import *
from handlers.menus import *
from handlers.db_queries import *
from create_bot import bot, dp
from handlers.statistics import *

logger = logging.getLogger(__name__)

def get_main_menu(has_wand: bool = True, notify_on: bool = True) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
            InlineKeyboardButton(text="🌿 My Plants", callback_data="my_plants"),
            InlineKeyboardButton(text="❓ What plant am I?", callback_data="start_quiz")
        )
    if has_wand:
        builder.row(
            InlineKeyboardButton(text="➕ Add Plant", callback_data="add_plant_menu"),
            InlineKeyboardButton(text="📋 My Wands", callback_data="my_wands")
        )
    else:
        builder.row(
            InlineKeyboardButton(text="➕ Add Plant", callback_data="add_plant_menu"),
            InlineKeyboardButton(text="🪄 Register Wand", callback_data="register_wand_info")
        )
    if notify_on:
        builder.row(InlineKeyboardButton(text="📴 Alerts OFF", callback_data="notify_on_off"))
    else:
        builder.row(InlineKeyboardButton(text="📳 Alerts ON", callback_data="notify_on_off"))

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




@dp.callback_query()
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
    
    elif data.startswith("add_plant_"):
        plant_id = int(data.split("_")[2])
        success = await add_plant_to_user(user_id, plant_id)
        if success:
            await callback.message.answer("Plant added successfully! ✅ 🌿", parse_mode=None)
        else:
            await callback.message.answer("This plant is already in your collection! ⚠️", parse_mode=None)
    
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
            await callback.message.answer(wands_text, parse_mode=None)

    elif data == "notify_on_off":
        await change_notify(user_id)

    await callback.answer()
