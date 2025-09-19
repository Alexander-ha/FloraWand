import os
import asyncio
from create_bot import bot, dp
from handlers.start import start_router
from handlers.notifications import check_plant_conditions_by_mac  # Импортируем нужную функцию
import threading
from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

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
                print("Updating database structure to allow NULL for plant_id...")
                
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
                
                # Копируем данные
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

# Глобальная переменная для хранения loop бота
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

@app_flask.route("/data", methods=['POST'])
def receive_data():
    try:
        data = request.form
        macadress = data.get('MacAdress')
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

        print(f"Received data: Address: {macadress}, Temp={temp_lvl}, Hum={humidity_lvl}, HI={heat_index}, Lux1={lux1}, Lux2={lux2}, moisture={water_lvl}")
        
        try:
            # Получаем все записи для этого MAC-адреса
            results = db.session.execute(
                text('SELECT user_id, plant_id FROM users_wands WHERE wand_id = :macadress'),
                {'macadress': macadress}
            ).fetchall()
            
            if not results:
                print(f"No wand found with macadress: {macadress}")
                return "Wand not found", 404
            
            # Обрабатываем каждую запись
            for result in results:
                user_id, plant_id = result[0], result[1]
                print(f"Found user_id: {user_id}, plant_id: {plant_id}")
                
                # Если plant_id равен NULL, пропускаем сохранение данных
                if plant_id is None:
                    print(f"Skipping data save for user {user_id} - plant not assigned")
                    continue
                    
                # Сохраняем данные для этого пользователя и растения
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
            
            # Вызываем проверку условий для этого MAC-адреса
            global bot_loop
            if bot_loop is not None:
                # Запускаем проверку условий в loop бота
                asyncio.run_coroutine_threadsafe(
                    check_plant_conditions_by_mac(macadress), 
                    bot_loop
                )
                print("Started condition check for the plant")
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
        
@app_flask.route("/data")
def get_data():
    return "Data received"

async def check_sensor_data_periodically():
    while True:
        try:
            from handlers.notifications import check_all_plants_conditions
            await check_all_plants_conditions()
            await asyncio.sleep(500)
        except Exception as e:
            print(f"Error in periodic check: {e}")
            await asyncio.sleep(60)

async def telegram_bot():
    global bot_loop
    bot_loop = asyncio.get_event_loop()
    asyncio.create_task(check_sensor_data_periodically())
    
    dp.include_router(start_router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

def run_flask():
    global flask_loop
    flask_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(flask_loop)
    
    with app_flask.app_context():
        update_database_structure()
        db.create_all()
    
    app_flask.run(host='0.0.0.0', port=80, debug=False, use_reloader=False)

if __name__ == "__main__":
    print("\nStarting...")
    
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    try:
        asyncio.run(telegram_bot())
    except KeyboardInterrupt:
        print("Bot stopped")