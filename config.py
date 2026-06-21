import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "8998750960:AAGh4UYLx8ltYNdskZgl9hum0JDQuBaq9Fk")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:postgres@localhost/documentbot_db")
CHANNEL_ID = os.getenv("CHANNEL_ID", "https://t.me/ZuzuKidss")
CLICK_MERCHANT_ID = os.getenv("CLICK_MERCHANT_ID", "")
CLICK_SECRET_KEY = os.getenv("CLICK_SECRET_KEY", "")
FREE_DOCS_LIMIT = 3
SUBSCRIPTION_PRICE = 49900
ADMIN_IDS = [5065038035]