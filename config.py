import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = '6927833396:AAFmCFnWQiaQGUug457Lv6BvbTVs6P9mp5k'
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///testing.db')

ADMIN_IDS = [707889443, 000000000]  #Telegram ID админов
