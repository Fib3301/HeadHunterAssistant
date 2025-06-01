import uvicorn
from fastapi import FastAPI, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from dotenv import load_dotenv
from database.database import engine, Base, get_db
from api.auth import router as auth_router
from api_handlers import chat_endpoint, clear_session, ChatRequest
from config import GIGACHAT_CREDENTIALS, HH_CLIENT_ID, HH_CLIENT_SECRET
from sqlalchemy.orm import Session

# Загрузка переменных окружения
load_dotenv()
logger.info("Проверка переменных окружения...")

# Проверка наличия необходимых переменных окружения
required_env_vars = {
    "GIGACHAT_CREDENTIALS": GIGACHAT_CREDENTIALS,
    "HH_CLIENT_ID": HH_CLIENT_ID,
    "HH_CLIENT_SECRET": HH_CLIENT_SECRET
}

# Проверяем наличие всех необходимых переменных окружения
for var_name, var_value in required_env_vars.items():
    if not var_value:
        logger.error(f"Отсутствует обязательная переменная окружения: {var_name}")
        raise ValueError(f"Необходимо установить {var_name} в файле .env")
    logger.info(f"Переменная {var_name} успешно загружена")

# Инициализация базы данных
try:
    logger.info("Инициализация базы данных...")
    Base.metadata.create_all(bind=engine)
    logger.info("База данных успешно инициализирована")
except Exception as e:
    logger.error(f"Ошибка при инициализации базы данных: {e}")
    raise

# Инициализация FastAPI приложения
app = FastAPI()

# Настройка CORS для расширения Chrome
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутер авторизации
app.include_router(auth_router)

@app.get("/")
async def root():
    return {"status": "ok", "message": "Server is running"}

@app.options("/chat")
async def options_chat():
    return {"status": "ok"}

@app.post("/chat")
async def chat(
    request: ChatRequest,
    x_extension_user_id: str = Header(...),
    db: Session = Depends(get_db)
):
    return await chat_endpoint(request, x_extension_user_id, db)

@app.post("/clear_session")
async def clear(session_id: str):
    return await clear_session(session_id)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 