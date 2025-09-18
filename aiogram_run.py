import asyncio
from create_bot import bot, dp, scheduler
from handlers.start import start_router
from flask import Flask, request
import threading

app_flask = Flask(__name__)

@app_flask.route("/")
def index():
    return "Hello world"

@app_flask.route("/data", methods=['POST'])
def receive_data():
    try:
        temperature = request.form.get('temperature')
        humidity = request.form.get('humidity')
        heat_index = request.form.get('heat_index')
        lux1 = request.form.get('lux1')
        lux2 = request.form.get('lux2')
        
        print(f"Received data: Temp={temperature}, Hum={humidity}, HI={heat_index}, Lux1={lux1}, Lux2={lux2}")
        return "Data received successfully", 200
    except Exception as e:
        print(f"Error receiving data: {e}")
        return "Error", 400



@app_flask.route("/data")
def get_data():
    return "Data received"

async def telegram_bot():
    dp.include_router(start_router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

def run_flask():
    app_flask.run(host='0.0.0.0', port=80, debug=False, threaded=True)

def run_telegram_bot():
    asyncio.run(telegram_bot())

if __name__ == "__main__":
    print("\nStarting...")
    
    novy_thread = threading.Thread(target=run_flask)
    novy_thread.daemon = True
    novy_thread.start()
    
    run_telegram_bot()
