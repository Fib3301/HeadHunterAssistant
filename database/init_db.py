from database.database import engine
from database.models import Base
from loguru import logger

def init_db():
    try:
        # Создаем все таблицы
        Base.metadata.create_all(bind=engine)
        logger.info("База данных успешно инициализирована")
    except Exception as e:
        logger.error(f"Ошибка при инициализации базы данных: {e}")
        raise

if __name__ == "__main__":
    init_db() 