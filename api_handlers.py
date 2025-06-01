from fastapi import HTTPException, Header, Depends
from sqlalchemy.orm import Session
from loguru import logger
import os
from typing import List, Dict, Any
from pydantic import BaseModel
from database.database import get_db
from session import SessionManager, UserSession
from formatters import format_api_response_to_human_readable
import asyncio

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = None
    session_id: str = None
    extension_user_id: str = None

# Инициализация менеджера сессий
session_manager = SessionManager()

async def chat_endpoint(
    request: ChatRequest,
    x_extension_user_id: str = Header(...),
    db: Session = Depends(get_db)
):
    """Обработка запросов чата."""
    try:
        # Используем session_id из запроса или создаем новый
        session_id = request.session_id or session_manager.create_session()
        session = session_manager.get_session(session_id)
        
        # Если сессия не существует, создаем новую
        if session is None:
            session_id = session_manager.create_session()
            session = session_manager.get_session(session_id)
        
        # Добавляем сообщение пользователя в историю
        session.add_message("user", request.message)
        
        # Инициализируем агента, если он еще не инициализирован
        if not session.bundle or not session.flows:
            # Загружаем agents.json
            agents_json_path = os.path.join(os.path.dirname(__file__), 'agents_json', 'hh', 'agents.json')
            session.load_agents_json(agents_json_path)
            
            # Настраиваем аутентификацию HeadHunter
            session.setup_hh_auth(x_extension_user_id, db)
        
        # Выполняем запрос через модель GROQ
        result = session.execute_query(request.message)
        
        # Форматируем ответ в человекочитаемый формат
        response_text = format_api_response_to_human_readable(result, request.message)
        
        session.add_message("assistant", response_text)
        return {
            "session_id": session.session_id,
            "response": response_text
        }
            
    except Exception as e:
        logger.error(f"Ошибка в обработке запроса: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

async def clear_session(session_id: str):
    """Очистка сессии."""
    try:
        session_manager.clear_session(session_id)
        return {"status": "success", "message": "Session cleared"}
    except Exception as e:
        logger.error(f"Ошибка при очистке сессии: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 