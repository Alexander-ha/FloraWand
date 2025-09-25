import os
import asyncio
from create_bot import bot, dp
from handlers.start import start_router
from handlers.menus import menus_router
from handlers.notifications import check_plant_conditions_by_mac  
import threading
from asyncio import Queue
import requests
from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
import concurrent.futures
import logging 
import shared_vars
from shared_vars import bot_pipeline

SENTINEL = object()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('pipeline.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

class Pipeline:
    def __init__(self):
        self.queue = Queue()
        self.logger = logging.getLogger('pipeline')

    async def get_message(self, name):
        self.logger.info(f"{name}: waiting for message")
        message = await self.queue.get()
        self.logger.info(f"{name}: got message: {message}")
        return message

    async def set_message(self, message, name):
        self.logger.info(f"{name}: setting message: {message}")
        await self.queue.put(message)
        self.logger.info(f"{name}: message set successfully")

def update_database_structure():
    """Обновляет структуру базы данных чтобы разрешить NULL для plant_id"""
    try:
        with app_flask.app_context():
            result = db.session.execute(text('''
                PRAGMA table_info(plants_monitor_final)
            ''')).fetchall()
            
            plant_id_column = None
            for column in result:
                if column[1] == 'plant_id':
                    plant_id_column = column
                    break
            
            if plant_id_column and plant_id_column[3] == 1:  
                db.session.execute(text('''
                    CREATE TABLE plants_monitor_final_temp (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        plant_id INTEGER,
                        water_lvl REAL,
                        light_lvl REAL,
                        temp_lvl REAL,
                        humidity_lvl REAL,
                        measured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                '''))
                
                db.session.execute(text('''
                    INSERT INTO plants_monitor_final_temp 
                    SELECT id, user_id, plant_id, water_lvl, light_lvl, temp_lvl, humidity_lvl, measured_at 
                    FROM plants_monitor_final
                '''))
                
                db.session.execute(text('DROP TABLE plants_monitor_final'))
                db.session.execute(text('ALTER TABLE plants_monitor_final_temp RENAME TO plants_monitor_final'))
                
                db.session.execute(text('''
                    CREATE INDEX IF NOT EXISTS idx_monitor_user_plant ON plants_monitor_final (user_id, plant_id)
                '''))
                db.session.execute(text('''
                    CREATE INDEX IF NOT EXISTS idx_monitor_timestamp ON plants_monitor_final (measured_at)
                '''))
                
                db.session.commit()
                print("Database structure updated successfully")
                
    except Exception as e:
        print(f"Error updating database structure: {e}")
        db.session.rollback()  

app_flask = Flask(__name__)
flask_loop = None

basedir = os.path.abspath(os.path.dirname(__file__))
app_flask.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "flowers.db")}'
app_flask.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app_flask)

bot_loop = None

class PlantsMonitorFinal(db.Model):
    __tablename__ = 'plants_monitor_final'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, nullable=False)
    plant_id = db.Column(db.Integer, nullable=False)
    water_lvl = db.Column(db.Float)
    light_lvl = db.Column(db.Float)
    temp_lvl = db.Column(db.Float)
    humidity_lvl = db.Column(db.Float)
    measured_at = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())

    def __init__(self, user_id, plant_id, water_lvl=None, light_lvl=None, temp_lvl=None, humidity_lvl=None):
        self.user_id = user_id
        self.plant_id = plant_id
        self.water_lvl = water_lvl
        self.light_lvl = light_lvl
        self.temp_lvl = temp_lvl
        self.humidity_lvl = humidity_lvl

@app_flask.route("/")
def index():
    return "Hello world"

@app_flask.route("/water_command", methods=['POST'])
def handle_water_command():
    """Эндпоинт для приема команд полива от бота"""
    try:
        data = request.get_json()
        logger.info(f"Flask received water command: {data}")
        
        user_id = data.get('user_id', 'unknown')
        command = data.get('command', 'unknown')
        
        print(f"🚀 WATER COMMAND RECEIVED FROM USER {user_id}: {command}")
        try:
            result = db.session.execute(
                text('SELECT w.wand_id, w.ip_address FROM users_wands w WHERE w.user_id = :user_id'),
                {'user_id': user_id}
            ).fetchone()
            
            if result:
                wand_id, ip_address = result[0], result[1]
                if ip_address:
                    print(f"Found device IP: {ip_address} for user {user_id}")
                    
                    device_url = f"http://{ip_address}/water"
                    try:
                        response = requests.post(
                            device_url,
                            json={'command': command, 'duration': 3000},
                            timeout=5
                        )
                        if response.status_code == 200:
                            print(f"Water command successfully sent to device {ip_address}")
                        else:
                            print(f"Device returned error: {response.status_code}")
                    except requests.exceptions.RequestException as e:
                        print(f"Error sending command to device {ip_address}: {e}")
                else:
                    print(f"No IP address found for user {user_id}")
            else:
                print(f"No device found for user {user_id}")
        except Exception as e:
            print(f"Database error when searching for device IP: {e}")


        
        return {
            "status": "success",
            "message": f"Water command received for user {user_id}",
            "command": command
        }, 200
        
    except Exception as e:
        logger.error(f"Error handling water command: {e}")
        return {"status": "error", "message": str(e)}, 400

@app_flask.route("/data", methods=['POST'])
def receive_data():
    try:
        data = request.form
        macadress = data.get('MacAdress')
        ip_address = data.get('ip_address')
        temp_lvl = data.get('temperature')
        humidity_lvl = data.get('humidity')
        heat_index = data.get('heat_index')
        lux1 = data.get('lux1')
        lux2 = data.get('lux2')
        water_lvl = data.get('moisture')
        
        try:
            light_lvl = max(float(lux1 or 0), float(lux2 or 0))
        except (TypeError, ValueError):
            light_lvl = 0.0

        print(f"Received data: Address: {macadress}, IP: {ip_address}, Temp={temp_lvl}, Hum={humidity_lvl}, HI={heat_index}, Lux1={lux1}, Lux2={lux2}, moisture={water_lvl}")
        try:
            db.session.execute(
                text('UPDATE users_wands SET ip_address = :ip_address WHERE wand_id = :macadress'),
                {'ip_address': ip_address, 'macadress': macadress}
            )
            db.session.commit()
            print(f"Updated IP address for wand {macadress}: {ip_address}")
        except Exception as e:
            print(f"Error updating IP address: {e}")
            db.session.rollback()
        
        try:
            results = db.session.execute(
                text('SELECT user_id, plant_id FROM users_wands WHERE wand_id = :macadress'),
                {'macadress': macadress}
            ).fetchall()
            
            if not results:
                print(f"No wand found with macadress: {macadress}")
                return "Wand not found", 404
            
            for result in results:
                user_id, plant_id = result[0], result[1]
                print(f"Found user_id: {user_id}, plant_id: {plant_id}")
                
                if plant_id is None:
                    print(f"Skipping data save for user {user_id} - plant not assigned")
                    continue
                    
                record = PlantsMonitorFinal(
                    user_id=user_id,
                    plant_id=plant_id,
                    water_lvl=float(water_lvl) if water_lvl else None,
                    light_lvl=light_lvl,
                    temp_lvl=float(temp_lvl) if temp_lvl else None,
                    humidity_lvl=float(humidity_lvl) if humidity_lvl else None
                )
                db.session.add(record)
                print(f"Data saved for user {user_id}, plant {plant_id}")
                
            db.session.commit()
            print("Data saved to database-----------------------------------------------------------")
            
            global bot_loop
            if bot_loop is not None:
                try:
                    asyncio.run_coroutine_threadsafe(
                        check_plant_conditions_by_mac(macadress), 
                        bot_loop
                    )
                    print("Started condition check for the plant")
                except Exception as e:
                    print(f"Error starting condition check: {e}")
            else:
                print("Bot loop is not available")

            return "Data received successfully", 200
                
        except Exception as e:
            db.session.rollback()
            print(f"Database error: {e}")
            return "Database error", 500

    except Exception as e:
        db.session.rollback()
        print(f"Error receiving data: {str(e)}")
        return "Error", 400

async def pipeline_consumer(pipeline):
    consumer_logger = logging.getLogger('pipeline.consumer')
    consumer_logger.info("Pipeline consumer started")
    
    while True:
        try:
            consumer_logger.info("Waiting for message...")
            message = await pipeline.get_message("Consumer")
            consumer_logger.info(f"Consumer received message: {message}")
            
            if message == SENTINEL:
                consumer_logger.info("Received SENTINEL, stopping consumer")
                break
                
            consumer_logger.info(f"Sending to Flask: {message}")
            await send_message_to_flask(message, consumer_logger)
            consumer_logger.info("Message sent to Flask successfully")
            
        except Exception as e:
            consumer_logger.error(f"Error in pipeline consumer: {e}")
            await asyncio.sleep(1)

async def send_message_to_flask(message, logger):
    """Отправляет сообщение в Flask эндпоинт"""
    try:
        flask_url = "http://localhost:80/water_command"
        
        logger.info(f"Sending message to Flask: {message}")
        
        response = await asyncio.get_event_loop().run_in_executor(
            None, 
            lambda: requests.post(
                flask_url,
                json=message,
                timeout=10
            )
        )
        
        logger.info(f"Flask response status: {response.status_code}")
        
        if response.status_code == 200:
            logger.info(f"Flask accepted message: {response.json()}")
        else:
            logger.error(f"Flask returned error: {response.status_code} - {response.text}")
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending to Flask: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")

@app_flask.route("/data")
def get_data():
    return "Data received"

async def check_sensor_data_periodically():
    while True:
        try:
            from handlers.notifications import check_all_plants_conditions
            await check_all_plants_conditions()
            await asyncio.sleep(60)
        except Exception as e:
            print(f"Error in periodic check: {e}")
            await asyncio.sleep(60)

def run_telegram_bot(pipeline):
    logger.info("=== BOT STARTING ===")
    logger.info(f"Bot token: {bot.token is not None}")
    logger.info(f"Routers count: {len(dp.sub_routers)}")
    
    logger.info(f"Middlewares: {dp.message.middleware._middlewares}")
    try:
        asyncio.run(telegram_bot(pipeline))
    except Exception as e:
        logger.error(f"Bot error: {e}")

async def telegram_bot(pipeline):
    global bot_loop
    shared_vars.bot_pipeline = pipeline
    
    logger.info(f"Pipeline initialized: {shared_vars.bot_pipeline is not None}")
    bot_loop = asyncio.get_event_loop()

    dp.include_router(start_router)
    dp.include_router(menus_router)

    asyncio.create_task(pipeline_consumer(pipeline))
    asyncio.create_task(check_sensor_data_periodically())
    
    logger.info("Starting bot...")
    
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Webhook deleted, starting polling...")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Polling error: {e}")

def run_flask(pipeline):
    global flask_loop
    flask_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(flask_loop)
    
    with app_flask.app_context():
        update_database_structure()
        db.create_all()
    
    app_flask.run(host='0.0.0.0', port=80, debug=False, use_reloader=False)

if __name__ == "__main__":
    print("\nStarting...")
    pipeline = Pipeline()

    flask_thread = threading.Thread(target=run_flask, args=(pipeline,), daemon=True)
    flask_thread.start()
    
    import time
    time.sleep(2)
    
    run_telegram_bot(pipeline)
