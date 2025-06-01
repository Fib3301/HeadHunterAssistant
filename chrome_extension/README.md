# HH AI Agent Chrome Extension

Это расширение Chrome для взаимодействия с AI агентом для поиска работы.

## Установка

1. Запустите сервер:
```bash
python main.py
```

2. Установите расширение в Chrome:
   - Откройте Chrome и перейдите в `chrome://extensions/`
   - Включите "Режим разработчика" (Developer mode)
   - Нажмите "Загрузить распакованное" (Load unpacked)
   - Выберите папку `chrome_extension`

## Использование

1. Нажмите на иконку расширения в панели инструментов Chrome
2. Введите ваше сообщение в поле ввода
3. Нажмите "Отправить" или клавишу Enter
4. Дождитесь ответа от AI агента

## Структура проекта

```
chrome_extension/
├── manifest.json
├── popup.html
├── popup.js
└── images/
    ├── icon16.png
    ├── icon48.png
    └── icon128.png
```

## Требования

- Chrome версии 88 или выше
- Запущенный сервер на `http://localhost:5000` 