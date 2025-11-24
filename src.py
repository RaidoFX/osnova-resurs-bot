import os  # Импортируем стандартный модуль для работы с операционной системой и переменными окружения
from dotenv import load_dotenv  # Импортируем функцию для загрузки переменных окружения из файла .env

load_dotenv()  # Загружаем переменные окружения из файла .env в текущую рабочую среду

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # Получаем значение переменной окружения с API-ключом OpenAI
ASSISTANT_ID = os.getenv("ASSISTANT_ID")  # Получаем идентификатор ассистента OpenAI
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")  # Получаем токен для Telegram-бота
GIGACHAT_CREDENTIALS = os.getenv("GIGACHAT_CREDENTIALS")  # Получаем учетные данные для GigaChat
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")  # Получаем секретный ключ для сервиса Langfuse
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")  # Получаем публичный ключ для сервиса Langfuse
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST")  # Получаем адрес или домен сервиса Langfuse