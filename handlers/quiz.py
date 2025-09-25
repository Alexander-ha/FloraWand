
import logging
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from aiogram import types
from create_bot import bot, dp
from handlers.db_queries import get_plant_by_name

logger = logging.getLogger(__name__)
user_quiz_state = {}

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
    
    recommendation = ('Cactus', 'https://shorturl.at/L4sbi')
    for score_range, rec in PLANT_RECOMMENDATIONS.items():
        if score_range[0] <= score <= score_range[1]:
            recommendation = rec
            break
    plant = await get_plant_by_name(recommendation[0])
    text = f"""
        🎉 Quiz Completed! Recommended plant for you: \n{plant['care_description']}\n
        Would you like to add this plant to your collection?
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Add to My Plants", callback_data=f"add_plant_{plant['plant_id']}"),
        InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="main_menu")
    )
    
    await bot.send_photo(chat_id=user_id, photo=recommendation[1], caption=text, reply_markup=builder.as_markup())
    
    if user_id in user_quiz_state:
        del user_quiz_state[user_id]


QUIZ_QUESTIONS = [
    {
        'question': "What's your plant care style?",
        'options': ['🌵 Minimal, I almost never water', '🌿 Sometimes I forget, but I try', '🌸 I love caring, I check every detail'],
        'scores': [1, 2, 3]
    },
    {
        'question': "What's the usual temperature at home?",
        'options': ['☀️ Hot, above 24°C', '🌤 Moderate, 20-24°C', '❄️ Cool, below 20°C'],
        'scores': [1, 2, 3]
    },
    {
        'question': "What kind of light do you have?",
        'options': ['🌞 Very bright, direct sunlight', '🌥 Medium, soft light', '🌑 Shade or artificial light'],
        'scores': [1, 2, 3]
    },
    {
        'question': "How do you feel about humidity?",
        'options': ['💨 I like dry air', "💧 I'm fine with medium humidity", "🌊 I prefer when it's humid and fresh"],
        'scores': [1, 2, 3]
    },
    {
        'question': "What kind of plant appearance do you prefer?",
        'options': ['🏜️ Desert-style (succulents, cacti)', '🍃 Lush green foliage', '💐 Colorful blooming flowers'],
        'scores': [1, 2, 3]
    },
    {
        'question': "Why do you want a plant?",
        'options': ['😎 Just to look nice without much care', '🏡 For coziness and greenery', '💖 To care for it like a "green friend"'],
        'scores': [1, 2, 3]
    }
]

PLANT_RECOMMENDATIONS = {
    (6, 8): ('Cactus', 'https://shorturl.at/L4sbi'),
    (9, 10): ('Kalanchoe', 'https://tinyurl.com/4s37ubek'),
    (11, 12): ('Ficus', 'https://shorturl.at/7d8je'),
    (13, 14): ('Monstera', 'https://tinyurl.com/55w83a8r'),
    (15, 16): ('Dieffenbachia', 'https://tinyurl.com/232ew2x4'),
    (17, 18): ('Orchid', 'https://tinyurl.com/2csh8xje')
}
