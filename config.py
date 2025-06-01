import os
from dotenv import load_dotenv
from loguru import logger
import sys

logger.remove()  
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="DEBUG"
)

env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
logger.info(f"Загрузка переменных окружения из файла: {env_path}")
# Загружаем из .env файла
load_dotenv(env_path)

GIGACHAT_CREDENTIALS = os.getenv("GIGACHAT_CREDENTIALS")

# Параметры авторизации HH.ru
HH_CLIENT_ID = os.getenv("HH_CLIENT_ID")
HH_CLIENT_SECRET = os.getenv("HH_CLIENT_SECRET")

# Проверка наличия всех необходимых переменных окружения
if not all([GIGACHAT_CREDENTIALS, HH_CLIENT_ID, HH_CLIENT_SECRET]):
    missing_vars = []
    if not GIGACHAT_CREDENTIALS:
        missing_vars.append("GIGACHAT_CREDENTIALS")
    if not HH_CLIENT_ID:
        missing_vars.append("HH_CLIENT_ID")
    if not HH_CLIENT_SECRET:
        missing_vars.append("HH_CLIENT_SECRET")
    
    logger.error(f"Отсутствуют необходимые переменные окружения: {', '.join(missing_vars)}")
    raise ValueError(f"Необходимо установить {', '.join(missing_vars)} в файле .env")

logger.info("Переменные окружения успешно загружены")
