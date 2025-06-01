from datetime import datetime, timedelta
import uuid
from typing import Dict, Optional, List
from loguru import logger
from sqlalchemy.orm import Session
from database.models import UserToken, EmployerInfo
from database.encryption import decrypt_token
import json
import os
import yaml
from agentsjson.core.models import Flow
from agentsjson.core.models.bundle import Bundle
from agentsjson.core.models.auth import AuthType, OAuth2AuthConfig
from agentsjson.integrations.hh.tools import HHAuthConfig
import agentsjson.core as core
from agentsjson.core.executor import execute_flows
from agentsjson.core import ToolFormat
from langchain_community.chat_models.gigachat import GigaChat
from config import GIGACHAT_CREDENTIALS

# Системный промпт для AI
SYSTEM_PROMPT = """Вы - ИИ-ассистент, который помогает пользователям взаимодействовать с API HeadHunter.
Ваша задача - помогать пользователям управлять вакансиями, откликами и другими функциями работодателя на HeadHunter.

Правила:
1. Отвечайте на русском языке
2. Используйте простой и понятный язык
3. Если запрос НЕ связан с HeadHunter (например, общие вопросы, вопросы о других сервисах и т.д.), 
   вы ДОЛЖНЫ ответить на вопрос напрямую, БЕЗ использования API. В этом случае просто верните текстовый ответ.
4. При работе с API HeadHunter используйте только предоставленные инструменты
5. Всегда проверяйте наличие необходимых данных перед выполнением операций
6. В случае ошибок, объясняйте их простыми словами

ВАЖНО: Используйте API HeadHunter ТОЛЬКО для запросов, связанных с вакансиями, работодателями и другими функциями HeadHunter.
Для всех остальных запросов давайте прямые текстовые ответы."""

class UserSession:
    def __init__(self, session_id: str):
        """Инициализация сессии пользователя."""
        self.session_id = session_id
        self.chat_history: List[Dict[str, str]] = []
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.bundle = None
        self.flows = None
        self.hh_tokens = None
        self.hh_auth = None
        self.extension_user_id = None

    def add_message(self, role: str, content: str):
        """Добавляет сообщение в историю чата."""
        self.chat_history.append({"role": role, "content": content})
        self.last_activity = datetime.now()
        if len(self.chat_history) > 10:
            self.chat_history = [self.chat_history[0]] + self.chat_history[-9:]

    def update_history(self, history: List[dict]):
        """Обновляет историю чата новыми сообщениями."""
        self.chat_history = [{
            "role": "system",
            "content": SYSTEM_PROMPT
        }]
        for msg in history:
            self.add_message(msg.role, msg.content)

    def setup_hh_auth(self, extension_user_id: str, db: Session) -> None:
        """Настройка OAuth2 аутентификации HeadHunter из базы данных."""
        user_token = db.query(UserToken).filter(
            UserToken.extension_user_id == extension_user_id
        ).first()
        
        if not user_token:
            raise ValueError(f"Токен не найден для extension_user_id: {extension_user_id}")
        
        employer_info = db.query(EmployerInfo).filter(
            EmployerInfo.extension_user_id == extension_user_id
        ).first()
        
        if not employer_info:
            raise ValueError(f"Информация о работодателе не найдена для extension_user_id: {extension_user_id}")
        
        self.hh_tokens = {
            'access_token': decrypt_token(user_token.encrypted_access_token),
            'refresh_token': decrypt_token(user_token.encrypted_refresh_token),
            'employer_id': employer_info.employer_id
        }
        logger.info("Учетные данные API HeadHunter успешно загружены из базы данных")

    def load_agents_json(self, agents_json_path: str) -> None:
        """Загрузка файла agents.json и OpenAPI спецификации."""
        try:
            with open(agents_json_path, 'r') as f:
                agents_json_content = json.load(f)
            
            openapi_path = os.path.join(os.path.dirname(agents_json_path), 'openapi.yaml')
            with open(openapi_path, 'r') as f:
                openapi_content = yaml.safe_load(f)
            
            bundle_data = {
                "agentsJson": agents_json_content,
                "openapi": openapi_content,
                "operations": {}
            }
            
            self.bundle = Bundle.model_validate(bundle_data)
            self.flows = self.bundle.agentsJson.flows
            logger.info("agents.json и OpenAPI спецификация успешно загружены")
        except Exception as e:
            logger.error(f"Ошибка загрузки agents.json: {str(e)}")
            raise

    def execute_query(self, query: str, flow_hint: Optional[List[str]] = None) -> Dict:
        """Выполнение запроса на естественном языке к API HeadHunter."""
        try:
            if not self.bundle or not self.flows:
                raise Exception("Агент не инициализирован")

            flows = self.flows
            if flow_hint:
                flows = [f for f in self.flows if f.name in flow_hint]

            giga = GigaChat(credentials=GIGACHAT_CREDENTIALS, verify_ssl_certs=False)

            try:
                response = giga.chat(
                    messages=self.chat_history + [{"role": "user", "content": query}],
                    tools=core.flows_tools(flows, format=ToolFormat.OPENAI),
                    temperature=0.7
                )
            except Exception as e:
                logger.error(f"Ошибка при вызове GigaChat API: {str(e)}", exc_info=True)
                raise Exception(f"Ошибка при вызове GigaChat API: {str(e)}")

            if not response or not hasattr(response, 'content'):
                raise Exception("Получен пустой ответ от GigaChat API")

            message = response
            
            # Если получен текстовый ответ без вызовов инструментов
            if not hasattr(message, 'tool_calls') or not message.tool_calls:
                logger.info("Получен текстовый ответ от модели")
                response_content = message.content
                self.add_message("assistant", response_content)
                return {"text_response": response_content}

            auth = HHAuthConfig(
                type=AuthType.OAUTH2,
                token=self.hh_tokens['access_token'],
                refresh_token=self.hh_tokens.get('refresh_token'),
                scopes=set(),
                employer_id=self.hh_tokens.get('employer_id')
            )

            try:
                result = execute_flows(
                    response,
                    format=ToolFormat.OPENAI,
                    bundle=self.bundle,
                    flows=flows,
                    auth=auth
                )
                return result
            except Exception as e:
                logger.error(f"Ошибка при выполнении flows: {str(e)}", exc_info=True)
                raise Exception(f"Ошибка при выполнении flows: {str(e)}")

        except Exception as e:
            logger.error(f"Ошибка при выполнении запроса: {str(e)}", exc_info=True)
            raise

class SessionManager:
    """Класс для управления пользовательскими сессиями."""
    def __init__(self):
        """Инициализация менеджера сессий."""
        self.sessions: Dict[str, UserSession] = {}
        self.session_timeout = timedelta(hours=24)

    def create_session(self) -> str:
        """Создает новую пользовательскую сессию."""
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = UserSession(session_id)
        return session_id

    def get_session(self, session_id: str) -> Optional[UserSession]:
        """Получает существующую сессию по её идентификатору."""
        session = self.sessions.get(session_id)
        if session and datetime.now() - session.last_activity < self.session_timeout:
            session.last_activity = datetime.now()
            return session
        return None

    def clear_session(self, session_id: str):
        """Удаляет сессию из системы."""
        if session_id in self.sessions:
            del self.sessions[session_id] 