
import logging
from typing import Optional
from aiogram.types import BufferedInputFile
from aiogram import types
import matplotlib.pyplot as plt
import pandas as pd
from datetime import timedelta
from io import BytesIO
import matplotlib.dates as mdates

from create_bot import bot, dp
from handlers.db_queries import get_plant_stats_from_db, get_plant_by_id
logger = logging.getLogger(__name__)



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
        time_range: '1h', '24h', '7d', '30d', 'all', 'auto'
    """
    try:
        df = await get_plant_stats_from_db(user_id, plant_id)
        
        if df is None or df.empty:
            await callback.message.answer("📊 No statistics data available for this plant.", parse_mode=None)
            return 
        
        # Фильтруем данные по временному диапазону
        now = pd.Timestamp.now()
        if time_range == '1h':
            filtered_df = df[df.index >= now - timedelta(hours=1)]
            title_suffix = ' (1 hour)'
        elif time_range == '24h':
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
            await callback.message.answer("📊 No statistics data available for this period.", parse_mode=None)
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
            \t• Soil moisture level: {df['water_lvl'].values[0]}%
            \t• Temperature: {df['temp_lvl'].values[0]}°C
            \t• Sunlight: {df['light_lvl'].values[0]} lux
            \t• Humidity: {df['humidity_lvl'].values[0]} %
        """
    return stats_text

async def show_care_info(plant_id: int):
    plant = await get_plant_by_id(plant_id)
    care_text = f"{plant['care_description']}\n\n\t💧 gather watering info and give advice\n☀️ gather watering info and give advice\n🌡️ gather watering info and give advice"
    return care_text
