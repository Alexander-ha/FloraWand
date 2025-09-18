# import asyncio
# from create_bot import bot, dp
# from handlers.start import start_router
# from handlers.monitor import add_sensor_data_and_check
# from flask import Flask, request
# import threading
# from flask_sqlalchemy import SQLAlchemy

# app_flask = Flask(__name__)
# flask_loop = None



# db_name = 'flowers.db'
# app_flask.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_name
# app_flask.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
# # this variable, db, will be used for all SQLAlchemy commands

# db = SQLAlchemy()
# db.init_app(app_flask)

# # @app_flask._got_first_request
# # def create_tables():
# #     db.create_all()

# class PlantsMonitorFinal(db.Model):
#     __tablename__ = 'plants_monitor_final'
    
#     id = db.Column(db.Integer, primary_key=True, autoincrement=True)
#     user_id = db.Column(db.Integer, nullable=False)
#     plant_id = db.Column(db.Integer, nullable=False)
#     water_lvl = db.Column(db.Float)
#     light_lvl = db.Column(db.Float)
#     temp_lvl = db.Column(db.Float)
#     humidity_lvl = db.Column(db.Float)
#     measured_at = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())

#     def __init__(self, user_id, plant_id, water_lvl=None, light_lvl=None, temp_lvl=None, humidity_lvl=None, measured_at=None):
#         self.user_id = user_id
#         self.plant_id = plant_id
#         self.water_lvl = water_lvl
#         self.light_lvl = light_lvl
#         self.temp_lvl = temp_lvl
#         self.humidity_lvl = humidity_lvl
#         self.measured_at = measured_at

        
        

# @app_flask.route("/")
# def index():
#     return "Hello world"

# @app_flask.route("/data", methods=['POST'])
# def receive_data():
#     try:
#         macadress = request.form.get('MacAdress')
#         temp_lvl = request.form.get('temperature')
#         humidity_lvl = request.form.get('humidity')
#         heat_index = request.form.get('heat_index')
#         lux1 = request.form.get('lux1')
#         lux2 = request.form.get('lux2')
#         water_lvl = request.form.get('moisture')
#         light_lvl = max(float(lux1), float(lux2))
#         light_lvl = max(float(lux1), float(lux2))

#         print(f"Received data: Address: {macadress}, Temp={temp_lvl}, Hum={humidity_lvl}, HI={heat_index}, Lux1={lux1}, Lux2={lux2}, moisture={water_lvl}")
        
#         # "SELECT user_id, plant_id from users_wands WHERE wand_id = ?", (macadress,)
#         user_id = 683777507
#         plant_id = 2

#         record = PlantsMonitorFinal(user_id, plant_id, water_lvl, light_lvl, temp_lvl, humidity_lvl)
#         db.session.add(record)
#         db.session.commit()
#         print("send data in database-----------------------------------------------------------")
#         # Создаем задачу в основном loop
#         future = asyncio.run_coroutine_threadsafe(
#             add_sensor_data_and_check(
#                 macadress, 
#                 float(water_lvl) if water_lvl else 0.0, 
#                 float(light_lvl) if light_lvl else 0.0, 
#                 float(temp_lvl) if temp_lvl else 0.0, 
#                 float(humidity_lvl) if humidity_lvl else 0.0
#             ), 
#             flask_loop
#         )
#         # Не ждем результат сразу, чтобы не блокировать Flask
#         # Можно добавить callback для обработки результата
#         future.add_done_callback(lambda f: print("Data processing completed") if not f.exception() else print(f"Error: {f.exception()}"))

#         return "Data received successfully", 200
#     except Exception as e:
#         print(f"Error receiving data: {e}")
#         return "Error", 400


# @app_flask.route("/data")
# def get_data():
#     return "Data received"

# async def telegram_bot():
#     dp.include_router(start_router)
#     await bot.delete_webhook(drop_pending_updates=True)
#     await dp.start_polling(bot)

# def run_flask():
#     global flask_loop
#     flask_loop = asyncio.new_event_loop()
#     asyncio.set_event_loop(flask_loop)
#     app_flask.run(host='0.0.0.0', port=80, debug=False, threaded=True)


#     # with app_flask.app_context():
#     #     db.create_all()

# def run_telegram_bot():
#     asyncio.run(telegram_bot())

# if __name__ == "__main__":
#     print("\nStarting...")
    
#     novy_thread = threading.Thread(target=run_flask)
#     novy_thread.daemon = True
#     novy_thread.start()

#     with app_flask.app_context():
#         db.create_all()

#     run_telegram_bot()



import asyncio
from create_bot import bot, dp
from handlers.start import start_router
from handlers.monitor import add_sensor_data_and_check
from flask import Flask, request
import threading
from flask_sqlalchemy import SQLAlchemy

app_flask = Flask(__name__)
flask_loop = None

db_name = 'flowers.db'
app_flask.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_name
app_flask.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Отключаем уведомления
db = SQLAlchemy(app_flask)  # Инициализируем с приложением

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
        
        # Проверяем и преобразуем данные
        try:
            light_lvl = max(float(lux1 or 0), float(lux2 or 0))
        except (TypeError, ValueError):
            light_lvl = 0.0

        print(f"Received data: Address: {macadress}, Temp={temp_lvl}, Hum={humidity_lvl}, HI={heat_index}, Lux1={lux1}, Lux2={lux2}, moisture={water_lvl}")
        
        user_id = 683777507  # Замените на реальные данные
        plant_id = 2

        # Создаем и сохраняем запись
        record = PlantsMonitorFinal(
            user_id=user_id,
            plant_id=plant_id,
            water_lvl=float(water_lvl),
            light_lvl=light_lvl,
            temp_lvl=float(temp_lvl),
            humidity_lvl=float(humidity_lvl) 
        )
        
        db.session.add(record)
        db.session.commit()  
        print("Data saved to database-----------------------------------------------------------")

        # Асинхронная обработка
        if flask_loop:
            asyncio.run_coroutine_threadsafe(
                add_sensor_data_and_check(
                    macadress, 
                    float(water_lvl),
                    light_lvl, 
                    float(temp_lvl),
                    float(humidity_lvl)
                ), 
                flask_loop
            )

        return "Data received successfully", 200

    except Exception as e:
        db.session.rollback()  # Откат при ошибке
        print(f"Error receiving data: {str(e)}")
        return "Error", 400

@app_flask.route("/data")
def get_data():
    return "Data received"

async def telegram_bot():
    dp.include_router(start_router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

def run_flask():
    global flask_loop
    flask_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(flask_loop)
    
    with app_flask.app_context():
        db.create_all()  # Создаем таблицы здесь
    
    app_flask.run(host='0.0.0.0', port=80, debug=False, use_reloader=False)

if __name__ == "__main__":
    print("\nStarting...")
    
    # Создаем и запускаем Flask в отдельном потоке
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Запускаем бота в основном потоке
    try:
        asyncio.run(telegram_bot())
    except KeyboardInterrupt:
        print("Bot stopped")