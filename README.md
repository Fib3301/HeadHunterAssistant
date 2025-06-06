![Демонстрация работы ассистента hh](1.gif)

# HH-AI-Agent

## Введение

Современный рынок труда характеризуется высокой динамикой и обострением конкуренции за квалифицированных специалистов. Разработанная интеллектуальная система автоматического скрининга резюме представляет собой комплексное решение, сочетающее технологии обработки естественного языка с глубоким пониманием специфики российского рекрутинга.

Система была разработана в ответ на ограничения существующих платформ, таких как HeadHunter, которые демонстрируют недостаточную эффективность в точном подборе кандидатов. В качестве базовой модели используется Sber GigaChat 2 Max, что обеспечивает превосходную обработку русскоязычных текстов и расширенное контекстное окно.

Архитектура системы основана на концепции интеллектуальных агентов с использованием API HeadHunter, что позволяет:
- Автоматизировать скрининг резюме
- Управлять воронкой найма
- Генерировать ответы соискателям
- Сохранять контроль над решениями за рекрутером

Практические результаты внедрения показали сокращение времени обработки откликов в 3-8 раз при сохранении высокой точности отбора. Система выступает в роли интеллектуального ассистента рекрутера, беря на себя рутинные операции и позволяя специалисту сосредоточиться на стратегических задачах.

AI-ассистент для работы с API HeadHunter, использующий GigaChat для обработки запросов. Система включает в себя бэкенд-сервис и Chrome расширение для удобного взаимодействия с API HeadHunter прямо из браузера.

## Описание

Проект представляет собой бэкенд-сервис и Chrome расширение, которые помогают автоматизировать работу с API HeadHunter. Основные возможности:

- Анализ резюме кандидатов
- Генерация приглашений на собеседование
- Генерация сообщений об отказе
- Управление вакансиями
- Работа с откликами
- Интеграция с браузером через Chrome расширение

## Технологии

- Python 3.8+
- FastAPI
- PostgreSQL
- GigaChat API
- HeadHunter API
- SQLAlchemy

## Установка

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd python-ai-agent
```

2. Создайте виртуальное окружение:
```bash
python -m venv .venv
source .venv/bin/activate  # для Linux/Mac
# или
.venv\Scripts\activate  # для Windows
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Создайте файл .env и добавьте необходимые переменные окружения:
```env
# GigaChat credentials
GIGACHAT_CREDENTIALS=your_gigachat_credentials_here

# HeadHunter API credentials
HH_CLIENT_ID=your_hh_client_id_here
HH_CLIENT_SECRET=your_hh_client_secret_here

# Database configuration
DATABASE_URL=postgresql://user:password@localhost:5432/hh_agent

# Encryption key (будет сгенерирован автоматически при первом запуске)
ENCRYPTION_KEY=your_encryption_key_here
```

## Запуск

1. Запустите сервер:
```bash
python main.py
```

Сервер будет доступен по адресу: http://localhost:8000

## API Endpoints

- `GET /` - Проверка работоспособности сервера
- `POST /chat` - Основной эндпоинт для взаимодействия с AI
- `POST /clear_session` - Очистка сессии
- `GET /health` - Проверка здоровья сервера

## Структура проекта

```
python-ai-agent/
├── api/                    # API роуты
├── database/              # Модели и настройки базы данных
├── python/               # Основной код приложения
│   └── agentsjson/      # Интеграция с HeadHunter API
├── chrome_extension/    # Chrome расширение для интеграции с браузером
│   ├── manifest.json    # Конфигурация расширения
│   ├── sidepanel.html   # Интерфейс боковой панели
│   ├── sidepanel.js     # Логика боковой панели
│   ├── background.js    # Фоновые процессы
│   └── styles.css       # Стили расширения
├── main.py              # Точка входа приложения
├── config.py            # Конфигурация
├── formatters.py        # Форматирование ответов
├── session.py           # Управление сессиями
└── requirements.txt     # Зависимости проекта
```
