from typing import Dict, Any
import json
from loguru import logger
from langchain_community.chat_models.gigachat import GigaChat
from config import GIGACHAT_CREDENTIALS

def format_api_response_to_human_readable(result: Dict[str, Any], query: str) -> str:
    """Преобразует JSON-ответ от API в человекочитаемый формат."""
    system_prompt = """Вы - ИИ-ассистент, который помогает пользователям взаимодействовать с API HeadHunter.
Ваша задача - преобразовать технический JSON-ответ от API в понятный для человека текст.

Правила форматирования:
1. Используйте простой и понятный язык
2. Структурируйте информацию в виде списков или параграфов
3. Выделяйте важную информацию (зарплату, требования, обязанности)
4. Отвечайте на исходный запрос пользователя, используя полученные данные
5. Если в ответе есть ошибка, объясните её простыми словами

Не просто перечисляйте данные, а составьте связный ответ на вопрос пользователя.
"""

    result_json = json.dumps(result, ensure_ascii=False)
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Запрос пользователя: {query}\n\nJSON-ответ от API: {result_json}\n\nПожалуйста, преобразуйте этот JSON в человекочитаемый ответ на запрос пользователя."}
    ]
    
    try:
        giga = GigaChat(credentials=GIGACHAT_CREDENTIALS, verify_ssl_certs=False)
        
        response = giga.chat(messages)
        
        if response and hasattr(response, 'content'):
            return response.content
        else:
            logger.error(f"Неожиданный формат ответа от GigaChat API: {response}")
            return "Не удалось преобразовать ответ в человекочитаемый формат."
    except Exception as e:
        logger.error(f"Ошибка при форматировании ответа: {str(e)}", exc_info=True)
        return f"Произошла ошибка при форматировании ответа: {str(e)}" 