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
    
    # ПУТЬ К ШРИФТУ: Убедитесь, что файл DejaVuSans.ttf лежит рядом с main.py
    font_path = "DejaVuSans.ttf" 
    
    if os.path.exists(font_path):
        pdf.add_font("DejaVu", "", font_path, uni=True)
        pdf.add_font("DejaVu", "B", font_path, uni=True) # Если есть жирный вариант, укажите его
        font_name = "DejaVu"
    else:
        # Если шрифта нет, бот выдаст ошибку в консоль, но не упадет сразу
        print(f"КРИТИЧЕСКАЯ ОШИБКА: Файл {font_path} не найден!")
        return None

    # Заголовок
    pdf.set_font(font_name, style="B", size=16)
    pdf.cell(190, 10, txt=str(title), ln=True, align='C')
    
    # Инфо
    pdf.set_font(font_name, size=10)
    pdf.cell(190, 8, txt=f"Заказчик: {user}", ln=True, align='C')
    pdf.cell(190, 8, txt=f"Дата: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}", ln=True, align='C')
    pdf.ln(10)

    # Шапка таблицы
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font(font_name, style="B", size=11)
    pdf.cell(10, 10, "№", border=1, fill=True, align='C')
    pdf.cell(95, 10, "Наименование", border=1, fill=True, align='C')
    pdf.cell(40, 10, "Кол-во", border=1, fill=True, align='C')
    pdf.cell(35, 10, "Ед.", border=1, fill=True, align='C')
    pdf.ln()

    # Данные таблицы
    pdf.set_font(font_name, size=11)
    for i, (name, unit, qty) in enumerate(rows, 1):
        # Используем str() для всех данных, чтобы избежать ошибок типов
        pdf.cell(10, 10, str(i), border=1, align='C')
        pdf.cell(95, 10, str(name), border=1)
        pdf.cell(40, 10, str(qty), border=1, align='C')
        pdf.cell(35, 10, str(unit), border=1, align='C')
        pdf.ln()

    filename = f"order_{datetime.datetime.now().strftime('%H%M%S')}.pdf"
    pdf.output(filename)
    return filename

@dp.message(Command("start"))
async def start(m: types.Message):
    kb = [[types.KeyboardButton(text="🛒 Открыть меню", web_app=WebAppInfo(url=WEBAPP_URL))]]
    await m.answer("Выберите цех и составьте заказ:", reply_markup=types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))

@dp.message(F.content_type == types.ContentType.WEB_APP_DATA)
async def web_app(m: types.Message):
    try:
        data = json.loads(m.web_app_data.data)
        loc = data.get('location', 'Цех не указан')
        items = data.get('order', [])
        user = m.from_user.full_name

        db_rows = []
        for it in items:
            save_order(user, loc, it['name'], it['qty'], it['unit'])
            db_rows.append((it['name'], it['unit'], it['qty']))

        path = create_pdf(db_rows, f"НАКЛАДНАЯ: {loc}", user)
        doc = FSInputFile(path)
        
        await m.answer_document(doc, caption=f"✅ Заказ для {loc} сохранен.")
        await bot.send_document(chat_id=GROUP_ID, document=doc, caption=f"📄 Новый заказ: {loc}\n👤 {user}")
        
        if os.path.exists(path): os.remove(path)
    except Exception as e:
        await m.answer(f"Ошибка: {e}")

async def run():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(run())


