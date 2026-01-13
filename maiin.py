import os
import json
import sqlite3
import datetime
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import WebAppInfo, FSInputFile
from PIL import Image, ImageDraw, ImageFont

# --- НАСТРОЙКИ (Замените на свои или используйте .env) ---
API_TOKEN = '8241341995:AAGC0lw8M-qeg9OpipC25qU90oPubvwqQF4'
GROUP_ID = -1003399244861  # ID вашей группы (с -100)
WEBAPP_URL = 'https://alnino18.github.io/salad-app/' # Ссылка на index.html

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('orders.db')
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS orders 
                   (id INTEGER PRIMARY KEY, user_name TEXT, salad TEXT, value TEXT, unit TEXT, date TEXT)''')
    conn.commit()
    conn.close()

def save_order(user_name, salad, value, unit):
    conn = sqlite3.connect('orders.db')
    cur = conn.cursor()
    date_today = datetime.date.today().strftime("%d.%m.%Y")
    cur.execute("INSERT INTO orders (user_name, salad, value, unit, date) VALUES (?, ?, ?, ?, ?)",
                (user_name, salad, value, unit, date_today))
    conn.commit()
    conn.close()

# --- ГЕНЕРАЦИЯ ИЗОБРАЖЕНИЯ НАКЛАДНОЙ ---
def create_jpg_invoice(rows, title):
    date_str = datetime.date.today().strftime("%d.%m.%Y")
    img_name = f"invoice_{datetime.datetime.now().strftime('%H%M%S')}.jpg"
    
    # Расчет высоты картинки в зависимости от кол-ва строк
    width = 650
    height = 160 + (len(rows) * 45)
    img = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    try:
        # Убедитесь, что arial.ttf лежит в той же папке на сервере!
        font = ImageFont.truetype("arial.ttf", 24)
        header_font = ImageFont.truetype("arial.ttf", 32)
    except:
        font = ImageFont.load_default()
        header_font = ImageFont.load_default()

    draw.text((40, 40), f"{title}", fill=(0, 0, 0), font=header_font)
    draw.text((40, 85), f"Дата: {date_str}", fill=(100, 100, 100), font=font)
    
    y = 140
    for i, (salad, unit, total) in enumerate(rows, 1):
        draw.text((40, y), f"{i}. {salad} — {total} {unit}", fill=(0, 0, 0), font=font)
        y += 45
    
    img.save(img_name)
    return img_name

# --- ОБРАБОТЧИКИ КОМАНД ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    # Кнопка для открытия вашего HTML Mini App
    markup = types.ReplyKeyboardMarkup(keyboard=[
        [types.KeyboardButton(text="🥗 ЗАКАЗАТЬ САЛАТЫ", web_app=WebAppInfo(url=WEBAPP_URL))]
    ], resize_keyboard=True)
    
    await message.answer(
        "Привет! Нажми на кнопку ниже, чтобы выбрать салаты в меню.",
        reply_markup=markup
    )

@dp.message(F.content_type == types.ContentType.WEB_APP_DATA)
async def handle_webapp_data(message: types.Message):
    user_name = message.from_user.full_name
    # Получаем JSON из нашего HTML (того самого index.html)
    try:
        data = json.loads(message.web_app_data.data)
        
        order_items = []
        for item in data:
            save_order(user_name, item['salad'], item['value'], item['unit'])
            order_items.append((item['salad'], item['unit'], item['value']))
        
        # Создаем картинку для подтверждения
        img_path = create_jpg_invoice(order_items, f"ЗАКАЗ: {user_name}")
        
        # Отправляем пользователю в ЛС
        await message.answer_photo(FSInputFile(img_path), caption="✅ Ваш заказ принят!")
        
        # Отправляем копию в ГРУППУ ЦЕХА
        try:
            await bot.send_photo(
                chat_id=GROUP_ID, 
                photo=FSInputFile(img_path), 
                caption=f"🔔 Новый заказ от {user_name}"
            )
        except Exception as e:
            await message.answer(f"⚠️ Ошибка отправки в группу: {e}")
            
    except Exception as e:
        await message.answer(f"❌ Ошибка обработки: {e}")

@dp.message(Command("invoice"))
async def manual_invoice(message: types.Message):
    # Формируем итоговую накладную за весь день
    date_today = datetime.date.today().strftime("%d.%m.%Y")
    conn = sqlite3.connect('orders.db')
    cur = conn.cursor()
    cur.execute("SELECT salad, unit, SUM(value) FROM orders WHERE date=? GROUP BY salad, unit", (date_today,))
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return await message.answer("Сегодня еще никто ничего не заказывал.")
    
    img_path = create_jpg_invoice(rows, "ИТОГО НА СЕГОДНЯ")
    await bot.send_photo(chat_id=GROUP_ID, photo=FSInputFile(img_path), caption=f"📊 Сводная накладная на {date_today}")
    await message.answer("✅ Итоговая накладная отправлена в группу.")

# --- ЗАПУСК ---
async def main():
    init_db()
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())