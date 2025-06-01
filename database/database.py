from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os
from dotenv import load_dotenv
from loguru import logger

# Загрузка переменных окружения
load_dotenv()

# Получаем URL базы данных
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:0112@localhost:5432/hh_agent")
logger.info(f"Используется URL базы данных: {DATABASE_URL}")

# Создаем движок SQLAlchemy
engine = create_engine(DATABASE_URL)

# Создаем фабрику сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Создаем базовый класс для моделей
Base = declarative_base()

def get_db():
    """Функция-генератор для получения сессии базы данных"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 