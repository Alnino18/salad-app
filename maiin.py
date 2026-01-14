import os
import json
import sqlite3
import datetime
import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import WebAppInfo, FSInputFile
from fpdf import FPDF

load_dotenv()
API_TOKEN = '8241341995:AAGC0lw8M-qeg9OpipC25qU90oPubvwqQF4'
GROUP_ID = -1003399244861  # ID вашей группы (с -100)
WEBAPP_URL = 'https://alnino18.github.io/salad-app/' # Ссылка на index.html

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Инициализация БД
def init_db():
    conn = sqlite3.connect('orders.db')
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS orders 
                   (id INTEGER PRIMARY KEY, user_name TEXT, location TEXT, 
                    salad TEXT, value TEXT, unit TEXT, date TEXT)''')
    # Проверка колонки location
    cur.execute("PRAGMA table_info(orders)")
    if 'location' not in [col[1] for col in cur.fetchall()]:
        cur.execute("ALTER TABLE orders ADD COLUMN location TEXT")
    conn.commit()
    conn.close()

def save_order(user, loc, salad, val, unit):
    conn = sqlite3.connect('orders.db')
    cur = conn.cursor()
    dt = datetime.date.today().strftime("%d.%m.%Y")
    cur.execute("INSERT INTO orders (user_name, location, salad, value, unit, date) VALUES (?, ?, ?, ?, ?, ?)",
                (user, loc, salad, val, unit, dt))
    conn.commit()
    conn.close()

# Генерация PDF
def create_pdf(rows, title, user):
    pdf = FPDF()
    pdf.add_page()
    
    # Подключаем шрифт (обязательно положите DejaVuSans.ttf в папку)
    pdf.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)
    pdf.add_font("DejaVu", "B", "DejaVuSans.ttf", uni=True)
    
    # 1. Добавляем прозрачный логотип
    if os.path.exists("logo.png"):
        pdf.image("logo.png", x=10, y=10, w=25)

    # 2. Заголовок (смещен вправо от лого)
    pdf.set_font("DejaVu", "B", 20)
    pdf.set_text_color(40, 40, 40)
    pdf.cell(10) # Отступ от логотипа
    pdf.cell(160, 15, txt="НАКЛАДНАЯ", ln=True, align='L')
    
    pdf.set_font("DejaVu", "", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(30)
    pdf.cell(160, 5, txt=f"Локация: {loc} | Создал: {user}", ln=True, align='L')
    pdf.cell(30)
    pdf.cell(160, 5, txt=f"Дата: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}", ln=True, align='L')
    pdf.ln(20)

    # 3. Таблица в стиле Minimalist
    # Заголовки
    pdf.set_font("DejaVu", "B", 11)
    pdf.set_text_color(255, 255, 255)
    pdf.set_fill_color(255, 69, 0) # Оранжевый акцент
    
    pdf.cell(10, 12, "№", border=0, fill=True, align='C')
    pdf.cell(110, 12, " Наименование товара", border=0, fill=True)
    pdf.cell(35, 12, "Кол-во", border=0, fill=True, align='C')
    pdf.cell(35, 12, "Ед. изм.", border=0, fill=True, align='C')
    pdf.ln()

    # Строки товаров
    pdf.set_font("DejaVu", "", 10)
    pdf.set_text_color(50, 50, 50)
    
    fill = False
    for i, (name, unit, qty) in enumerate(rows, 1):
        # Зебра-эффект (светло-серые строки)
        if fill: pdf.set_fill_color(248, 248, 248)
        else: pdf.set_fill_color(255, 255, 255)
        
        pdf.cell(10, 10, str(i), border='B', fill=True, align='C')
        pdf.cell(110, 10, f" {name}", border='B', fill=True)
        pdf.cell(35, 10, str(qty), border='B', fill=True, align='C')
        pdf.cell(35, 10, unit, border='B', fill=True, align='C')
        pdf.ln()
        fill = not fill

    # Подпись
    #pdf.ln(15)
    #pdf.set_font("DejaVu", "", 10)
    #pdf.cell(190, 10, "__________________________", ln=True, align='R')
    #pdf.cell(190, 5, "Подпись ответственного лица", ln=True, align='R')

    filename = f"order_{datetime.datetime.now().strftime('%H%M%S')}.pdf"
    pdf.output(filename)
    return filename

@dp.message(Command("start"))
async def start(m: types.Message):
    kb = [[types.KeyboardButton(text="🛒 Открыть меню", web_app=WebAppInfo(url=WEBAPP_URL))]]
    await m.answer("Выберите точку и составьте заказ:", reply_markup=types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))

@dp.message(F.content_type == types.ContentType.WEB_APP_DATA)
async def web_app(m: types.Message):
    try:
        data = json.loads(m.web_app_data.data)
        loc = data.get('location', 'Точка не указан')
        items = data.get('order', [])
        user = m.from_user.full_name

        db_rows = []
        for it in items:
            save_order(user, loc, it['name'], it['qty'], it['unit'])
            db_rows.append((it['name'], it['unit'], it['qty']))

        path = create_pdf(db_rows, f"НАКЛАДНАЯ: {loc}", user)
        doc = FSInputFile(path)
        
        #await m.answer_document(doc, caption=f"✅ Заказ для {loc} сохранен.")
        await bot.send_document(chat_id=GROUP_ID, document=doc, caption=f"📄 Новый заказ: {loc}\n👤 {user}")
        
        if os.path.exists(path): os.remove(path)
    except Exception as e:
        await m.answer(f"Ошибка: {e}")

async def run():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(run())


