from pydantic import BaseModel
from agentsjson.core.models.auth import OAuth2AuthConfig
from typing import ClassVar, Dict, Optional
from functools import lru_cache
import requests
import logging
import json
import os
from datetime import datetime
import re
from langchain_community.chat_models.gigachat import GigaChat
from config import GIGACHAT_CREDENTIALS

# Настройка логирования
logger = logging.getLogger(__name__)

class HHAuthConfig(OAuth2AuthConfig):
    """
    Расширенная конфигурация аутентификации для HeadHunter API.
    Добавляет поле employer_id к базовой OAuth2 конфигурации.
    """
    employer_id: Optional[str] = None

class Executor(BaseModel):
    """
    Executor class for HeadHunter API operations.
    
    Authentication is handled via HHAuthConfig which should include:
    - token: The OAuth 2.0 access token
    - refresh_token: The OAuth 2.0 refresh token (optional)
    - employer_id: The HeadHunter employer ID
    """
    
    BASE_URL: ClassVar[str] = "https://api.hh.ru"
    
    @staticmethod
    def _handle_api_error(response: requests.Response, operation: str) -> None:
        """
        Обрабатывает ошибки API HeadHunter.
        
        Args:
            response: Ответ от API
            operation: Название операции, которая вызвала ошибку
        """
        if response.status_code != 200:
            try:
                error_data = response.json()
                if 'errors' in error_data:
                    errors = error_data['errors']
                    error_messages = []
                    for error in errors:
                        if 'value' in error and 'type' in error:
                            error_messages.append(f"Параметр '{error['value']}': {error['type']}")
                    if error_messages:
                        raise Exception(f"Ошибка при {operation}: {'; '.join(error_messages)}")
            except json.JSONDecodeError:
                pass
            raise Exception(f"Ошибка при {operation}: {response.status_code} - {response.text}")

    @staticmethod
    @lru_cache(maxsize=100)
    def _get_session(token: str) -> requests.Session:
        """
        Creates a session with HeadHunter API using OAuth2 token.
        This function is cached with LRU policy.
        """
        session = requests.Session()
        session.headers.update({
            "Authorization": f"Bearer {token}",
            "User-Agent": "HH-AI-Agent/1.0",
            "Accept": "application/json"
        })
        return session

    @staticmethod
    def _get_hh_session(auth_config: HHAuthConfig) -> requests.Session:
        """
        Creates or retrieves a cached HeadHunter API session using OAuth2 credentials.
        
        Args:
            auth_config: HHAuthConfig containing the required OAuth2 credentials
        
        Returns:
            HeadHunter API session instance
        """
        return Executor._get_session(auth_config.token)

    @staticmethod
    def hh_get_current_user_info(auth_config: HHAuthConfig, **kwargs):
        """
        Получает информацию о текущем авторизованном пользователе
        
        Args:
            auth_config: HHAuthConfig с токеном доступа
            **kwargs: Дополнительные параметры запроса
        
        Returns:
            Dict: Информация о текущем пользователе
        """
        session = Executor._get_hh_session(auth_config)
        url = f"{Executor.BASE_URL}/me"
        
        # Логируем URL и параметры запроса
        logger.info(f"Выполняется запрос GET: {url}")
        logger.info(f"Параметры запроса: {kwargs}")
        
        response = session.get(url)
        Executor._handle_api_error(response, "получении информации о пользователе")
        
        logger.info(f"Запрос успешно выполнен: {url}")
        return response.json()
    
    @staticmethod
    def hh_get_active_vacancy_list(auth_config: HHAuthConfig, parameters: Dict = None, **kwargs):
        """
        Получает список опубликованных вакансий работодателя
        
        Args:
            auth_config: HHAuthConfig с токеном доступа
            parameters: Параметры запроса (page, per_page, manager_id, text, area, resume_id, order_by)
            **kwargs: Дополнительные параметры запроса
        
        Returns:
            Dict: Список опубликованных вакансий
        """
        session = Executor._get_hh_session(auth_config)
        
        # Получаем employer_id из auth_config
        employer_id = auth_config.employer_id
        if not employer_id:
            logger.error("employer_id не указан в конфигурации аутентификации")
            raise Exception("employer_id не указан в конфигурации аутентификации")
        
        # Формируем URL для запроса
        url = f"{Executor.BASE_URL}/employers/{employer_id}/vacancies/active"
        
        # Логируем URL и параметры запроса
        logger.info(f"Выполняется запрос GET: {url}")
        logger.info(f"Параметры запроса: {parameters}")
        
        # Выполняем запрос с параметрами
        response = session.get(url, params=parameters)
        Executor._handle_api_error(response, "получении списка вакансий")
        
        logger.info(f"Запрос успешно выполнен: {url}")
        return response.json()
    
    @staticmethod
    def hh_get_vacancy(auth_config: HHAuthConfig, parameters: Dict = None, **kwargs):
        """
        Получает подробную информацию о конкретной вакансии по её идентификатору
        
        Args:
            auth_config: HHAuthConfig с токеном доступа
            parameters: Параметры запроса (vacancy_id)
            **kwargs: Дополнительные параметры запроса
        
        Returns:
            Dict: Подробная информация о вакансии
        """
        session = Executor._get_hh_session(auth_config)
        
        # Получаем vacancy_id из параметров
        vacancy_id = parameters.get('vacancy_id')
        if not vacancy_id:
            logger.error("vacancy_id не указан в параметрах запроса")
            raise Exception("vacancy_id не указан в параметрах запроса")
        
        # Формируем URL для запроса
        url = f"{Executor.BASE_URL}/vacancies/{vacancy_id}"
        
        # Логируем URL и параметры запроса
        logger.info(f"Выполняется запрос GET: {url}")
        logger.info(f"Параметры запроса: {parameters}")
        
        # Выполняем запрос
        response = session.get(url)
        Executor._handle_api_error(response, "получении информации о вакансии")
        
        logger.info(f"Запрос успешно выполнен: {url}")
        return response.json()

    @staticmethod
    def hh_get_negotiations_list(auth_config: HHAuthConfig, parameters: Dict = None, **kwargs):
        """
        Получает список откликов/приглашений по вакансии
        
        Args:
            auth_config: HHAuthConfig с токеном доступа
            parameters: Параметры запроса:
                - vacancy_id: ID вакансии (обязательный)
                - order_by: Тип сортировки
                - page: Номер страницы (по умолчанию 0)
                - per_page: Количество элементов на странице (по умолчанию 20)
                - salary_from: Нижняя граница желаемой ЗП
                - salary_to: Верхняя граница желаемой ЗП
                - age_from: Нижняя граница возраста
                - age_to: Верхняя граница возраста
                - experience: Опыт работы
                - education_level: Уровень образования
                - area: Регион
                - search_text: Поисковая строка
                и другие параметры фильтрации
            **kwargs: Дополнительные параметры запроса
        
        Returns:
            Dict: Список откликов с информацией о резюме
        """
        session = Executor._get_hh_session(auth_config)
        
        # Формируем URL для запроса
        url = f"{Executor.BASE_URL}/negotiations/response"
        
        # Выполняем запрос
        response = session.get(url, params=parameters)
        Executor._handle_api_error(response, "получении списка откликов")
        
        # Получаем данные ответа
        data = response.json()
        
        # Создаем директорию для сохранения данных, если она не существует
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
        os.makedirs(data_dir, exist_ok=True)
        
        # Формируем имя файла с текущей датой и временем
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = os.path.join(data_dir, f'negotiations_{timestamp}.json')
        
        # Сохраняем данные в JSON файл
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Данные сохранены в файл: {filename}")
        logger.info(f"Запрос успешно выполнен: {url}")
        return data

    @staticmethod
    def hh_get_resume(auth_config: HHAuthConfig, parameters: Dict = None, **kwargs):
        """
        Получает информацию о конкретном резюме по его идентификатору
        
        Args:
            auth_config: HHAuthConfig с токеном доступа
            parameters: Параметры запроса:
                - resume_id: ID резюме (обязательный) или список ID резюме
                - with_negotiations_history: Добавить историю откликов
                - with_creds: Добавить учетные данные
                - with_job_search_status: Добавить статус поиска работы
            **kwargs: Дополнительные параметры запроса
        
        Returns:
            List[Dict]: Список с информацией о резюме
        """
        session = Executor._get_hh_session(auth_config)
        
        # Получаем resume_id из параметров
        resume_id = parameters.get('resume_id')
        if not resume_id:
            logger.error("resume_id не указан в параметрах запроса")
            raise Exception("resume_id не указан в параметрах запроса")
        
        result = []
        
        # Если передан список ID резюме
        if isinstance(resume_id, list):
            for rid in resume_id:
                # Формируем URL для запроса
                url = f"{Executor.BASE_URL}/resumes/{rid}"
                
                # Логируем URL и параметры запроса
                logger.info(f"Выполняется запрос GET: {url}")
                logger.info(f"Параметры запроса: {parameters}")
                
                # Выполняем запрос
                response = session.get(url, params=parameters)
                try:
                    Executor._handle_api_error(response, f"получении информации о резюме {rid}")
                    # Добавляем информацию о резюме в результат
                    result.append(response.json())
                    logger.info(f"Запрос успешно выполнен: {url}")
                except Exception as e:
                    logger.error(f"Ошибка при получении информации о резюме {rid}: {str(e)}")
                    continue
        else:
            # Формируем URL для запроса
            url = f"{Executor.BASE_URL}/resumes/{resume_id}"
            
            # Логируем URL и параметры запроса
            logger.info(f"Выполняется запрос GET: {url}")
            logger.info(f"Параметры запроса: {parameters}")
            
            # Выполняем запрос
            response = session.get(url, params=parameters)
            Executor._handle_api_error(response, "получении информации о резюме")
            
            # Добавляем информацию о резюме в результат
            result.append(response.json())
            logger.info(f"Запрос успешно выполнен: {url}")
        
        return result

    def get_negotiations_and_change_state_flow(self, search_text: str, new_state: str, salary_from: int = None, 
        salary_to: int = None, experience: str = None, education_level: str = None, 
        age_from: int = None, age_to: int = None) -> dict:
        """
        Получение списка откликов/приглашений по вакансии и изменение их состояния.
        
        Args:
            search_text (str): Название вакансии для поиска
            new_state (str): Новое состояние отклика (response/invitation/discard/hidden)
            salary_from (int, optional): Нижняя граница желаемой заработной платы
            salary_to (int, optional): Верхняя граница желаемой заработной платы
            experience (str, optional): Опыт работы
            education_level (str, optional): Уровень образования
            age_from (int, optional): Нижняя граница возраста соискателя в годах
            age_to (int, optional): Верхняя граница возраста соискателя в годах
            
        Returns:
            dict: Результат изменения состояния отклика
        """
        # Поиск вакансии
        vacancy_result = self.search_vacancy(search_text)
        if not vacancy_result.get("items"):
            return {"error": "Вакансия не найдена"}
            
        vacancy_id = vacancy_result["items"][0]["id"]
        
        # Получение списка откликов
        negotiations_params = {
            "vacancy_id": vacancy_id
        }
        if salary_from:
            negotiations_params["salary_from"] = salary_from
        if salary_to:
            negotiations_params["salary_to"] = salary_to
        if experience:
            negotiations_params["experience"] = experience
        if education_level:
            negotiations_params["education_level"] = education_level
        if age_from:
            negotiations_params["age_from"] = age_from
        if age_to:
            negotiations_params["age_to"] = age_to
            
        negotiations_result = self.get_negotiations(**negotiations_params)
        if not negotiations_result.get("items"):
            return {"error": "Отклики не найдены"}
            
        # Изменение состояния первого отклика
        first_negotiation = negotiations_result["items"][0]
        state_change_result = self.change_negotiation_state(
            collection_name=first_negotiation["collection_name"],
            nid=first_negotiation["id"],
            parameters={
                "collection_name": first_negotiation["collection_name"],
                "nid": first_negotiation["id"],
                "new_state": new_state
            }
        )
        
        return {
            "search_result": vacancy_result,
            "negotiations": negotiations_result,
            "state_change": state_change_result
        } 

    @staticmethod
    def hh_change_negotiation_state(auth_config: HHAuthConfig, parameters: Dict = None, **kwargs):
        """
        Изменяет состояние конкретного отклика/приглашения
        
        Args:
            auth_config: HHAuthConfig с токеном доступа
            parameters: Параметры запроса:
                - negotiation_id: ID отклика (обязательный)
                - new_state: Новое состояние (response/invitation/discard/hidden)
            **kwargs: Дополнительные параметры запроса
        
        Returns:
            Dict: Результат изменения состояния
        """
        session = Executor._get_hh_session(auth_config)
        
        # Получаем необходимые параметры
        negotiation_id = parameters.get('negotiation_id')
        new_state = parameters.get('new_state')
        
        if not negotiation_id or not new_state:
            logger.error("Не указаны обязательные параметры: negotiation_id, new_state")
            raise Exception("Не указаны обязательные параметры: negotiation_id, new_state")
        
        # Формируем URL для запроса
        url = f"{Executor.BASE_URL}/negotiations/{negotiation_id}"
        
        # Формируем данные для запроса
        data = {
            "state": new_state
        }
        
        # Логируем URL и параметры запроса
        logger.info(f"Выполняется запрос PUT: {url}")
        logger.info(f"Данные запроса: {data}")
        
        # Выполняем запрос
        response = session.put(url, json=data)
        Executor._handle_api_error(response, "изменении состояния отклика")
        
        logger.info(f"Запрос успешно выполнен: {url}")
        return response.json()

    @staticmethod
    def hh_analyze_resume(auth_config: HHAuthConfig, parameters: Dict = None, **kwargs):
        """
        Анализирует резюме кандидата и принимает решение о приглашении или отказе с помощью GigaChat
        """
        try:
            # Получаем данные резюме из параметров
            resume_data = parameters.get('resume_data')
            if not resume_data:
                raise Exception("Данные резюме не предоставлены")

            # Формируем промпт для GigaChat
            prompt = f"""Проанализируйте следующее резюме и дайте рекомендацию о приглашении на собеседование или отказе.
            Укажите основные причины вашего решения.

            Резюме:
            {json.dumps(resume_data, ensure_ascii=False, indent=2)}

            Пожалуйста, предоставьте анализ в следующем формате:
            1. Общая оценка кандидата
            2. Сильные стороны
            3. Слабые стороны
            4. Рекомендация (пригласить/отказать)
            5. Обоснование решения
            """

            # Создаем клиент GigaChat
            giga = GigaChat(credentials=GIGACHAT_CREDENTIALS, verify_ssl_certs=False)

            # Отправляем запрос к GigaChat
            response = giga.chat([{"role": "user", "content": prompt}])

            if not response or not hasattr(response, 'content'):
                raise Exception("Получен пустой ответ от GigaChat API")

            return {
                "analysis": response.content,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Ошибка при анализе резюме через GigaChat: {str(e)}")
            raise

    def analyze_resume_and_respond_flow(self, search_text: str, analysis_criteria: str) -> dict:
        """
        Анализирует резюме кандидата и автоматически принимает решение о приглашении или отказе.
        
        Args:
            search_text (str): Название вакансии для поиска
            analysis_criteria (str): Критерии для анализа резюме
            
        Returns:
            dict: Результат анализа и изменения состояния отклика
        """
        # Поиск вакансии
        vacancy_result = self.search_vacancy(search_text)
        if not vacancy_result.get("items"):
            return {"error": "Вакансия не найдена"}
            
        vacancy_id = vacancy_result["items"][0]["id"]
        
        # Получение списка откликов
        negotiations_result = self.get_negotiations(vacancy_id=vacancy_id)
        if not negotiations_result.get("items"):
            return {"error": "Отклики не найдены"}
            
        # Получение информации о резюме
        resume_id = negotiations_result["items"][0]["resume"]["id"]
        resume_result = self.get_resume(resume_id=resume_id)
        
        # Анализ резюме
        analysis_result = self.hh_analyze_resume(
            parameters={
                "resume_data": resume_result[0],
                "analysis_criteria": analysis_criteria
            }
        )
        
        # Проверяем, что результат анализа содержит should_invite и это boolean
        if not isinstance(analysis_result.get("should_invite"), bool):
            logger.error(f"Некорректный результат анализа: {analysis_result}")
            return {"error": "Некорректный результат анализа резюме"}
        
        # Изменение состояния отклика
        new_state = "invitation" if analysis_result["should_invite"] else "discard"
        state_change_result = self.change_negotiation_state(
            negotiation_id=negotiations_result["items"][0]["id"],
            new_state=new_state
        )
        
        return {
            "search_result": vacancy_result,
            "negotiations": negotiations_result,
            "resume_analysis": analysis_result,
            "state_change": state_change_result
        } 

    @staticmethod
    def hh_generate_rejection_message(auth_config: HHAuthConfig, parameters: Dict = None, **kwargs):
        """
        Генерирует текст сообщения об отказе с помощью GigaChat
        """
        try:
            # Получаем параметры из запроса
            resume_data = parameters.get('resume_data')
            rejection_reason = parameters.get('rejection_reason')
            message_tone = parameters.get('message_tone', 'professional')

            if not resume_data or not rejection_reason:
                raise Exception("Необходимые параметры не предоставлены")

            # Формируем промпт для GigaChat
            prompt = f"""Сгенерируйте вежливое сообщение об отказе кандидату на основе следующей информации:

            Резюме кандидата:
            {json.dumps(resume_data, ensure_ascii=False, indent=2)}

            Причина отказа: {rejection_reason}
            Тон сообщения: {message_tone}

            Требования к сообщению:
            1. Вежливый и профессиональный тон
            2. Конструктивная обратная связь
            3. Благодарность за интерес к вакансии
            4. Пожелания успехов в поиске работы
            """

            # Создаем клиент GigaChat
            giga = GigaChat(credentials=GIGACHAT_CREDENTIALS, verify_ssl_certs=False)

            # Отправляем запрос к GigaChat
            response = giga.chat([{"role": "user", "content": prompt}])

            if not response or not hasattr(response, 'content'):
                raise Exception("Получен пустой ответ от GigaChat API")

            return {
                "message": response.content,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Ошибка при генерации сообщения об отказе через GigaChat: {str(e)}")
            raise

    def generate_rejection_message_flow(self, search_text: str, rejection_reason: str, message_tone: str = "professional") -> dict:
        """
        Генерирует персонализированное сообщение отказа и отправляет его кандидату.
        
        Args:
            search_text (str): Название вакансии для поиска
            rejection_reason (str): Причина отказа
            message_tone (str): Тон сообщения (formal/friendly/professional)
            
        Returns:
            dict: Результат генерации сообщения и изменения состояния отклика
        """
        # Поиск вакансии
        vacancy_result = self.search_vacancy(search_text)
        if not vacancy_result.get("items"):
            return {"error": "Вакансия не найдена"}
            
        vacancy_id = vacancy_result["items"][0]["id"]
        
        # Получение списка откликов
        negotiations_result = self.get_negotiations(vacancy_id=vacancy_id)
        if not negotiations_result.get("items"):
            return {"error": "Отклики не найдены"}
            
        # Получение информации о резюме
        resume_id = negotiations_result["items"][0]["resume"]["id"]
        resume_result = self.get_resume(resume_id=resume_id)
        
        # Генерация сообщения отказа
        message_result = self.hh_generate_rejection_message(
            parameters={
                "resume_data": resume_result[0],
                "rejection_reason": rejection_reason,
                "message_tone": message_tone
            }
        )
        
        # Проверяем, что сообщение сгенерировано
        if not message_result.get("message"):
            logger.error("Не удалось сгенерировать сообщение отказа")
            return {"error": "Не удалось сгенерировать сообщение отказа"}
        
        # Изменение состояния отклика с сообщением
        state_change_result = self.change_negotiation_state(
            negotiation_id=negotiations_result["items"][0]["id"],
            new_state="discard",
            message=message_result["message"]
        )
        
        return {
            "search_result": vacancy_result,
            "negotiations": negotiations_result,
            "generated_message": message_result,
            "state_change": state_change_result
        } 

    @staticmethod
    def hh_generate_invitation_message(auth_config: HHAuthConfig, parameters: Dict = None, **kwargs):
        """
        Генерирует текст приглашения на собеседование с помощью GigaChat
        """
        try:
            # Получаем параметры из запроса
            resume_data = parameters.get('resume_data')
            interview_details = parameters.get('interview_details')
            message_tone = parameters.get('message_tone', 'professional')

            if not resume_data or not interview_details:
                raise Exception("Необходимые параметры не предоставлены")

            # Формируем промпт для GigaChat
            prompt = f"""Сгенерируйте приглашение на собеседование на основе следующей информации:

            Резюме кандидата:
            {json.dumps(resume_data, ensure_ascii=False, indent=2)}

            Детали собеседования: {interview_details}
            Тон сообщения: {message_tone}

            Требования к сообщению:
            1. Профессиональный и дружелюбный тон
            2. Четкое описание деталей собеседования
            3. Выражение заинтересованности в кандидате
            4. Контактная информация для связи
            """

            # Создаем клиент GigaChat
            giga = GigaChat(credentials=GIGACHAT_CREDENTIALS, verify_ssl_certs=False)

            # Отправляем запрос к GigaChat
            response = giga.chat([{"role": "user", "content": prompt}])

            if not response or not hasattr(response, 'content'):
                raise Exception("Получен пустой ответ от GigaChat API")

            return {
                "message": response.content,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Ошибка при генерации приглашения через GigaChat: {str(e)}")
            raise

    def generate_invitation_message_flow(self, search_text: str, interview_details: str, message_tone: str = "professional") -> dict:
        """
        Генерирует персонализированное приглашение на собеседование и отправляет его кандидату.
        
        Args:
            search_text (str): Название вакансии для поиска
            interview_details (str): Детали собеседования
            message_tone (str): Тон сообщения (formal/friendly/professional)
            
        Returns:
            dict: Результат генерации сообщения и изменения состояния отклика
        """
        # Поиск вакансии
        vacancy_result = self.search_vacancy(search_text)
        if not vacancy_result.get("items"):
            return {"error": "Вакансия не найдена"}
            
        vacancy_id = vacancy_result["items"][0]["id"]
        
        # Получение списка откликов
        negotiations_result = self.get_negotiations(vacancy_id=vacancy_id)
        if not negotiations_result.get("items"):
            return {"error": "Отклики не найдены"}
            
        # Получение информации о резюме
        resume_id = negotiations_result["items"][0]["resume"]["id"]
        resume_result = self.get_resume(resume_id=resume_id)
        
        # Генерация сообщения приглашения
        message_result = self.hh_generate_invitation_message(
            parameters={
                "resume_data": resume_result[0],
                "interview_details": interview_details,
                "message_tone": message_tone
            }
        )
        
        # Проверяем, что сообщение сгенерировано
        if not message_result.get("message"):
            logger.error("Не удалось сгенерировать сообщение приглашения")
            return {"error": "Не удалось сгенерировать сообщение приглашения"}
        
        # Изменение состояния отклика с сообщением
        state_change_result = self.change_negotiation_state(
            negotiation_id=negotiations_result["items"][0]["id"],
            new_state="invitation",
            message=message_result["message"]
        )
        
        return {
            "search_result": vacancy_result,
            "negotiations": negotiations_result,
            "generated_message": message_result,
            "state_change": state_change_result
        } 