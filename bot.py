import threading
from fastapi import FastAPI, HTTPException
from bs4 import BeautifulSoup
import httpx
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import uvicorn
from decouple import config
from config import BOT_TOKEN

# Инициализация FastAPI приложения
fastapi_app = FastAPI()
BASE_URL = "https://www.wildberries.ru"

@fastapi_app.get("/trees/")
def get_christmas_trees():
    url = "https://www.wildberries.ru/catalog/0/search.aspx?search=новогодняя+ёлка"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    response = httpx.get(url, headers=headers)

    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Не удалось получить данные")

    soup = BeautifulSoup(response.content, "html.parser")
    tree_items = soup.select(".product-card")

    trees_data = []
    for item in tree_items[:10]:
        title = item.select_one(".goods-name").get_text(strip=True) if item.select_one(".goods-name") else "Не указано"
        price = item.select_one(".lower-price").get_text(strip=True) if item.select_one(".lower-price") else "Цена неизвестна"
        link = BASE_URL + item.select_one("a")["href"] if item.select_one("a") else "Нет ссылки"
        trees_data.append({"title": title, "price": price, "link": link})

    return {"trees": trees_data}

# URL FastAPI сервера для получения данных
API_URL = "http://127.0.0.1:8888/trees/"

# Telegram Bot функции
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await update.message.reply_text(f"Привет, {user.first_name}! Напиши /trees, чтобы получить список новогодних елок с Wildberries.")

async def get_trees(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Загружаю данные о новогодних елках...")

    try:
        response = httpx.get(API_URL)
        data = response.json()

        if "trees" in data:
            text = "🎄 Новогодние елки на Wildberries:\n\n"
            for tree in data["trees"]:
                text += f"🔹 *{tree['title']}*\n"
                text += f"💰 Цена: {tree['price']}\n"
                text += f"[Ссылка на товар]({tree['link']})\n\n"
        else:
            text = "Упс! Не удалось получить данные."

        await update.message.reply_text(text, parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text("Произошла ошибка при получении данных.")

def run_telegram_bot():
    telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()  # Замените токен
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CommandHandler("trees", get_trees))

    telegram_app.run_polling()

def start_fastapi():
    uvicorn.run(fastapi_app, host="127.0.0.1", port=8888)


if __name__ == "__main__":
    # Запускаем FastAPI в отдельном потоке
    fastapi_thread = threading.Thread(target=start_fastapi, daemon=True)
    fastapi_thread.start()

    # Запускаем Telegram Bot в основном потоке
    run_telegram_bot()
