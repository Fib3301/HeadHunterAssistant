from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.orm import Session
import httpx
import secrets
from urllib.parse import urlencode
from loguru import logger
from fastapi.responses import HTMLResponse
import uuid

from database.database import get_db
from database.models import UserToken, EmployerInfo
from database.encryption import encrypt_token, decrypt_token
from config import HH_CLIENT_ID, HH_CLIENT_SECRET

router = APIRouter()

# URL для авторизации
AUTH_URL = "https://hh.ru/oauth/authorize"
TOKEN_URL = "https://hh.ru/oauth/token"
REDIRECT_URI = "http://localhost:8000/auth/callback"

@router.get("/auth/login")
async def login(x_extension_user_id: str = Header(...)):
    """Генерирует URL для авторизации через HH.ru"""
    try:
        # Создаем state, который содержит и случайное значение, и extension_user_id
        random_state = secrets.token_urlsafe(16)
        state = f"{random_state}|{x_extension_user_id}"
        
        params = {
            "response_type": "code",
            "client_id": HH_CLIENT_ID,
            "state": state,
            "redirect_uri": REDIRECT_URI
        }
        auth_url = f"{AUTH_URL}?{urlencode(params)}"
        logger.info(f"Сгенерирован URL для авторизации: {auth_url[:50]}...")
        return {"auth_url": auth_url}
    except Exception as e:
        logger.error(f"Ошибка при генерации URL авторизации: {e}")
        raise HTTPException(status_code=500, detail="Ошибка при генерации URL авторизации")

@router.get("/auth/callback")
async def callback(code: str, state: str, db: Session = Depends(get_db)):
    """Обрабатывает callback от HH.ru и сохраняет токены"""
    try:
        logger.info("Получен callback от HH.ru")
        logger.debug(f"Code: {code[:5]}...{code[-5:]}")
        logger.debug(f"State: {state}")

        # Получаем extension_user_id из state
        if '|' not in state:
            logger.error("Некорректный формат state")
            raise HTTPException(status_code=400, detail="Некорректный формат state")
            
        extension_user_id = state.split('|')[1]
        if not extension_user_id:
            logger.error("extension_user_id не найден в state")
            raise HTTPException(status_code=400, detail="Отсутствует extension_user_id")
            
        logger.info(f"Получен extension_user_id: {extension_user_id}")

        async with httpx.AsyncClient() as client:
            # Получаем токены
            token_response = await client.post(
                TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "client_id": HH_CLIENT_ID,
                    "client_secret": HH_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": REDIRECT_URI
                }
            )
            
            if token_response.status_code != 200:
                error_detail = token_response.text
                logger.error(f"Ошибка при получении токенов: {error_detail}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Ошибка при получении токенов: {error_detail}"
                )
                
            data = token_response.json()
            access_token = data["access_token"]
            refresh_token = data["refresh_token"]
            logger.info("Токены успешно получены")
            
            # Получаем информацию о пользователе
            user_response = await client.get(
                "https://api.hh.ru/me",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if user_response.status_code != 200:
                error_detail = user_response.text
                logger.error(f"Ошибка при получении информации о пользователе: {error_detail}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Ошибка при получении информации о пользователе: {error_detail}"
                )
                
            user_data = user_response.json()
            user_id = str(user_data["id"])
            logger.info(f"Получена информация о пользователе: {user_id}")
            
            # Создаем новую запись токена
            db_token = UserToken(
                id=str(uuid.uuid4()),
                user_id=user_id,
                extension_user_id=extension_user_id,
                encrypted_access_token=encrypt_token(access_token),
                encrypted_refresh_token=encrypt_token(refresh_token)
            )
            
            # Проверяем существующие токены для данного extension_user_id
            existing_token = db.query(UserToken).filter(
                UserToken.extension_user_id == extension_user_id
            ).first()
            
            if existing_token:
                # Обновляем существующую запись
                existing_token.user_id = user_id
                existing_token.encrypted_access_token = encrypt_token(access_token)
                existing_token.encrypted_refresh_token = encrypt_token(refresh_token)
                logger.info(f"Обновлены токены для пользователя {user_id} (extension_user_id: {extension_user_id})")
            else:
                # Создаем новую запись
                db.add(db_token)
                logger.info(f"Создана новая запись токенов для пользователя {user_id} (extension_user_id: {extension_user_id})")

            # Сохраняем информацию о работодателе
            if "employer" in user_data and "manager" in user_data:
                employer_info = EmployerInfo(
                    id=str(uuid.uuid4()),
                    extension_user_id=extension_user_id,
                    employer_id=str(user_data["employer"]["id"]),
                    employer_name=user_data["employer"]["name"],
                    manager_id=str(user_data["manager"]["id"]),
                    manager_email=user_data.get("email")
                )

                # Проверяем существующую информацию о работодателе
                existing_employer = db.query(EmployerInfo).filter(
                    EmployerInfo.extension_user_id == extension_user_id
                ).first()

                if existing_employer:
                    # Обновляем существующую запись
                    existing_employer.employer_id = str(user_data["employer"]["id"])
                    existing_employer.employer_name = user_data["employer"]["name"]
                    existing_employer.manager_id = str(user_data["manager"]["id"])
                    existing_employer.manager_email = user_data.get("email")
                    logger.info(f"Обновлена информация о работодателе для extension_user_id: {extension_user_id}")
                else:
                    # Создаем новую запись
                    db.add(employer_info)
                    logger.info(f"Создана новая запись информации о работодателе для extension_user_id: {extension_user_id}")
                
            db.commit()
            
            # Возвращаем HTML-страницу с JavaScript для закрытия окна
            return HTMLResponse("""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Авторизация успешна</title>
                    <script>
                        window.onload = function() {
                            if (window.opener) {
                                window.opener.postMessage('auth_success', '*');
                            }
                            window.close();
                        };
                    </script>
                </head>
                <body>
                    <h1>Авторизация успешна</h1>
                    <p>Окно закроется автоматически...</p>
                </body>
                </html>
            """)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Неожиданная ошибка при обработке callback: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")

@router.get("/auth/check")
async def check_auth(x_extension_user_id: str = Header(...), db: Session = Depends(get_db)):
    """Проверяет состояние авторизации пользователя"""
    try:
        # Получаем токен для конкретного extension_user_id
        user_token = db.query(UserToken).filter(
            UserToken.extension_user_id == x_extension_user_id
        ).first()
        
        if not user_token:
            logger.info(f"Токен не найден для extension_user_id: {x_extension_user_id}")
            return {"is_authenticated": False}
            
        # Проверяем валидность токена
        async with httpx.AsyncClient() as client:
            try:
                # Пробуем получить информацию о пользователе
                response = await client.get(
                    "https://api.hh.ru/me",
                    headers={"Authorization": f"Bearer {decrypt_token(user_token.encrypted_access_token)}"}
                )
                
                if response.status_code == 200:
                    logger.info(f"Токен валиден для extension_user_id: {x_extension_user_id}")
                    return {"is_authenticated": True}
                elif response.status_code == 403:
                    # Если токен истек, пробуем обновить его
                    logger.info(f"Токен истек для extension_user_id: {x_extension_user_id}, пробуем обновить")
                    refresh_response = await client.post(
                        TOKEN_URL,
                        data={
                            "grant_type": "refresh_token",
                            "client_id": HH_CLIENT_ID,
                            "client_secret": HH_CLIENT_SECRET,
                            "refresh_token": decrypt_token(user_token.encrypted_refresh_token)
                        }
                    )
                    
                    if refresh_response.status_code == 200:
                        # Обновляем токены в базе
                        new_tokens = refresh_response.json()
                        user_token.encrypted_access_token = encrypt_token(new_tokens["access_token"])
                        user_token.encrypted_refresh_token = encrypt_token(new_tokens["refresh_token"])
                        db.commit()
                        logger.info(f"Токены успешно обновлены для extension_user_id: {x_extension_user_id}")
                        return {"is_authenticated": True}
                    else:
                        logger.error(f"Ошибка при обновлении токена для extension_user_id: {x_extension_user_id}")
                        db.delete(user_token)
                        db.commit()
                        return {"is_authenticated": False}
                else:
                    logger.error(f"Неожиданный статус ответа для extension_user_id: {x_extension_user_id}")
                    db.delete(user_token)
                    db.commit()
                    return {"is_authenticated": False}
                    
            except Exception as e:
                logger.error(f"Ошибка при проверке токена для extension_user_id: {x_extension_user_id}: {e}")
                db.delete(user_token)
                db.commit()
                return {"is_authenticated": False}
                
    except Exception as e:
        logger.error(f"Ошибка при проверке авторизации: {e}")
        return {"is_authenticated": False} 