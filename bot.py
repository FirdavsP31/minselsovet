from aiogram import Bot, Dispatcher, types, F
from aiogram.types import WebAppInfo, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
import asyncio
from threading import Thread
from urllib.parse import quote

TOKEN = '7881985630:AAFk01LFjqYO067yA1o5Vqjbzaz_ejFR4xc'
bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    first_name = quote(message.from_user.first_name)
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="Открыть чат",
                    web_app=WebAppInfo(
                        url=f"https://d114-84-54-73-72.ngrok-free.app/?tg_user_id={message.from_user.id}&first_name={first_name}"
                    )
                )
            ]
        ],
        resize_keyboard=True
    )

    await message.answer(
        f"Привет, {message.from_user.first_name}!\n"
        "Нажми кнопку ниже, чтобы открыть чат:",
        reply_markup=keyboard
    )

async def start_bot():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(start_bot())