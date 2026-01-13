import os
import json
import sqlite3
import datetime
import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import WebAppInfo, FSInputFile
from PIL import Image, ImageDraw, ImageFont

# Загрузка настроек
load_dotenv()
API_TOKEN = '8241341995:AAGC0lw8M-qeg9OpipC25qU90oPubvwqQF4'
GROUP_ID = -1003399244861  # ID вашей группы (с -100)
WEBAPP_URL = 'https://alnino18.github.io/salad-app/' # Ссылка на index.html

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('orders.db')
    cur = conn.cursor()
    # Создаем таблицу, если её нет
    cur.execute('''CREATE TABLE IF NOT EXISTS orders 
                   (id INTEGER PRIMARY KEY, user_name TEXT, location TEXT, 
                    salad TEXT, value TEXT, unit TEXT, date TEXT)''')
    
    # Проверка: если колонка location вдруг отсутствует (в старой базе), добавляем её
    cur.execute("PRAGMA table_info(orders)")
    columns = [column[1] for column in cur.fetchall()]
    if 'location' not in columns:
        cur.execute("ALTER TABLE orders ADD COLUMN location TEXT")
        print("База данных успешно обновлена: добавлена колонка location")
    
    conn.commit()
    conn.close()

def save_order(user_name, location, salad, value, unit):
    conn = sqlite3.connect('orders.db')
    cur = conn.cursor()
    date_today = datetime.date.today().strftime("%d.%m.%Y")
    cur.execute("INSERT INTO orders (user_name, location, salad, value, unit, date) VALUES (?, ?, ?, ?, ?, ?)",
                (user_name, location, salad, value, unit, date_today))
    conn.commit()
    conn.close()

# --- ГЕНЕРАЦИЯ ТАБЛИЦЫ В JPG ---
def create_table_invoice(rows, title, subtitle):
    date_str = datetime.date.today().strftime("%d.%m.%Y %H:%M")
    img_name = f"invoice_{datetime.datetime.now().strftime('%H%M%S')}.jpg"
    
    # Настройки таблицы
    margin = 40
    col_widths = [50, 300, 100, 100] # №, Салат, Кол-во, Ед. изм.
    row_height = 40
    header_height = 180
    width = sum(col_widths) + (margin * 2)
    height = header_height + (len(rows) + 1) * row_height + margin

    img = Image.new('RGB', (width, int(height)), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    try:
        f_bold = ImageFont.truetype("arial.ttf", 28)
        f_reg = ImageFont.truetype("arial.ttf", 22)
        f_small = ImageFont.truetype("arial.ttf", 18)
    except:
        f_bold = f_reg = f_small = ImageFont.load_default()

    # Шапка документа
    draw.text((margin, 30), title, fill=(0, 0, 0), font=f_bold)
    draw.text((margin, 75), f"Отправитель: {subtitle}", fill=(60, 60, 60), font=f_reg)
    draw.text((margin, 110), f"Дата: {date_str}", fill=(100, 100, 100), font=f_small)

    # Рисуем таблицу
    curr_y = header_height
    headers = ["№", "Наименование салата", "Кол-во", "Ед."]
    
    # Отрисовка заголовков таблицы
    curr_x = margin
    for i, h_text in enumerate(headers):
        draw.rectangle([curr_x, curr_y, curr_x + col_widths[i], curr_y + row_height], outline=(0,0,0), width=2)
        draw.text((curr_x + 5, curr_y + 8), h_text, fill=(0,0,0), font=f_small)
        curr_x += col_widths[i]

    # Отрисовка строк с данными
    curr_y += row_height
    for idx, (name, unit, qty) in enumerate(rows, 1):
        curr_x = margin
        row_data = [str(idx), name, str(qty), unit]
        for i, val in enumerate(row_data):
            draw.rectangle([curr_x, curr_y, curr_x + col_widths[i], curr_y + row_height], outline=(0,0,0), width=1)
            draw.text((curr_x + 5, curr_y + 8), val, fill=(0,0,0), font=f_reg)
            curr_x += col_widths[i]
        curr_y += row_height

    img.save(img_name)
    return img_name

# --- ХЕНДЛЕРЫ ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    markup = types.ReplyKeyboardMarkup(keyboard=[
        [types.KeyboardButton(text="🥗 ОФОРМИТЬ ЗАКАЗ", web_app=WebAppInfo(url=WEBAPP_URL))]
    ], resize_keyboard=True)
    await message.answer("Выберите цех и салаты в меню:", reply_markup=markup)

@dp.message(F.content_type == types.ContentType.WEB_APP_DATA)
async def handle_webapp_data(message: types.Message):
    try:
        raw_data = json.loads(message.web_app_data.data)
        location = raw_data.get('location', 'Не указан')
        order_items = raw_data.get('order', [])
        user_name = message.from_user.full_name
        
        db_rows = []
        for item in order_items:
            save_order(user_name, location, item['name'], item['qty'], item['unit'])
            db_rows.append((item['name'], item['unit'], item['qty']))
        
        img_path = create_table_invoice(db_rows, f"ЗАКАЗ: {location}", user_name)
        
        await message.answer_photo(FSInputFile(img_path), caption=f"✅ Заказ для {location} отправлен.")
        await bot.send_photo(chat_id=GROUP_ID, photo=FSInputFile(img_path), caption=f"🔔 Новый заказ: {location}")
        
        if os.path.exists(img_path): os.remove(img_path)
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

