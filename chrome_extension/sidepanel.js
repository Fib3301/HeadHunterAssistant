document.addEventListener('DOMContentLoaded', () => {
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');
    let currentSessionId = null;
    let extensionUserId = null;

    // Проверяем, что marked.js загружен
    if (typeof marked === 'undefined') {
        console.error('marked.js не загружен!');
        return;
    }

    // Настройка marked.js
    marked.setOptions({
        breaks: true,
        gfm: true,
        sanitize: true,
        smartLists: true,
        smartypants: true
    });

    // Функция для автоматического изменения размера текстового поля
    function autoResizeTextarea() {
        userInput.style.height = 'auto';
        userInput.style.height = (userInput.scrollHeight) + 'px';
    }

    // Функция для сохранения данных в хранилище
    function saveData() {
        const messages = Array.from(chatMessages.children).map(message => {
            const contentDiv = message.querySelector('.message-content');
            const isUser = message.classList.contains('user');
            // Сохраняем оригинальный текст с разметкой
            const text = contentDiv ? contentDiv.getAttribute('data-original-text') || contentDiv.textContent : message.textContent;
            return {
                text: text,
                isUser: isUser,
                isMarkdown: !isUser
            };
        });
        chrome.storage.local.set({ 
            chatHistory: messages,
            sessionId: currentSessionId
        });
    }

    // Функция для загрузки данных из хранилища
    function loadData() {
        chrome.storage.local.get(['chatHistory', 'sessionId'], (result) => {
            if (result.sessionId) {
                currentSessionId = result.sessionId;
            }
            if (result.chatHistory) {
                result.chatHistory.forEach(msg => {
                    addMessage(msg.text, msg.isUser, msg.isMarkdown);
                });
            } else {
                // Если истории нет, показываем приветственное сообщение
                addMessage('Привет! Я ваш AI ассистент для работы с HeadHunter. Чем могу помочь?', false, true);
            }
        });
    }

    // Функция для добавления сообщения в чат
    function addMessage(text, isUser = false, isMarkdown = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isUser ? 'user' : 'assistant'}`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = isUser ? 'message-content' : 'message-content markdown-content';
        
        if (isUser) {
            contentDiv.textContent = text;
        } else {
            // Сохраняем оригинальный текст с разметкой
            contentDiv.setAttribute('data-original-text', text);
            contentDiv.innerHTML = marked.parse(text);
        }
        
        messageDiv.appendChild(contentDiv);
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        saveData();
        return messageDiv;
    }

    // Функция для получения истории сообщений
    function getMessageHistory() {
        return Array.from(chatMessages.children).map(message => {
            const contentDiv = message.querySelector('.message-content');
            // Используем оригинальный текст с разметкой
            return {
                role: message.classList.contains('user') ? 'user' : 'assistant',
                content: contentDiv ? contentDiv.getAttribute('data-original-text') || contentDiv.textContent : message.textContent
            };
        });
    }

    // Функция для генерации уникального ID
    function generateUUID() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            const r = Math.random() * 16 | 0;
            const v = c === 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }

    // Функция для получения или создания ID расширения
    async function getOrCreateExtensionUserId() {
        return new Promise((resolve) => {
            chrome.storage.local.get(['extensionUserId'], async (result) => {
                if (result.extensionUserId) {
                    extensionUserId = result.extensionUserId;
                } else {
                    extensionUserId = generateUUID();
                    await chrome.storage.local.set({ extensionUserId });
                }
                resolve(extensionUserId);
            });
        });
    }

    // Функция для проверки состояния авторизации
    async function checkAuthState() {
        try {
            const response = await fetch('http://localhost:8000/auth/check', {
                headers: {
                    'X-Extension-User-Id': extensionUserId
                }
            });
            const data = await response.json();
            updateAuthUI(data.is_authenticated);
            return data.is_authenticated;
        } catch (error) {
            console.error('Ошибка при проверке состояния авторизации:', error);
            updateAuthUI(false);
            return false;
        }
    }

    // Функция для отправки сообщения на сервер
    async function sendMessageToServer(message) {
        try {
            const messageHistory = getMessageHistory();
            console.log('Отправка запроса на сервер:', {
                message,
                history: messageHistory,
                session_id: currentSessionId
            });

            const response = await fetch('http://localhost:8000/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Extension-User-Id': extensionUserId
                },
                body: JSON.stringify({ 
                    message: message,
                    history: messageHistory,
                    session_id: currentSessionId || undefined
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                console.error('Ошибка сервера:', errorData);
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            console.log('Получен ответ от сервера:', data);
            
            currentSessionId = data.session_id;
            saveData();
            return data.response;
        } catch (error) {
            console.error('Ошибка при отправке сообщения:', error);
            throw error;
        }
    }

    // Функция для отправки сообщения
    async function sendMessage() {
        const message = userInput.value.trim();
        if (!message) return;

        // Добавляем сообщение пользователя
        addMessage(message, true, false);
        userInput.value = '';
        autoResizeTextarea(); // Сбрасываем размер поля ввода

        try {
            // Показываем индикатор загрузки
            const loadingMessageDiv = document.createElement('div');
            loadingMessageDiv.className = 'message assistant';
            const loadingDots = document.createElement('div');
            loadingDots.className = 'loading-dots';
            for (let i = 0; i < 3; i++) {
                const dot = document.createElement('span');
                loadingDots.appendChild(dot);
            }
            loadingMessageDiv.appendChild(loadingDots);
            chatMessages.appendChild(loadingMessageDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
            
            // Отправляем сообщение на сервер и получаем ответ
            const response = await sendMessageToServer(message);
            
            // Удаляем индикатор загрузки
            loadingMessageDiv.remove();
            
            // Добавляем ответ от сервера
            addMessage(response, false, true);
        } catch (error) {
            // Удаляем индикатор загрузки в случае ошибки
            const lastMessage = chatMessages.lastChild;
            if (lastMessage && lastMessage.querySelector('.loading-dots')) {
                lastMessage.remove();
            }
            addMessage('Произошла ошибка при отправке сообщения. Пожалуйста, попробуйте позже.', false, false);
        }
    }

    // Обработчики событий
    sendButton.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Обработчик для автоматического изменения размера текстового поля
    userInput.addEventListener('input', autoResizeTextarea);

    // Функция для обновления UI в зависимости от состояния авторизации
    function updateAuthUI(isAuthenticated) {
        const authButton = document.getElementById('auth-button');
        if (isAuthenticated) {
            authButton.textContent = 'Выход';
            authButton.disabled = false;
            authButton.style.backgroundColor = '#d6001c';
            authButton.onclick = async () => {
                try {
                    const response = await fetch('http://localhost:8000/auth/logout', {
                        method: 'POST',
                        headers: {
                            'X-Extension-User-Id': extensionUserId
                        }
                    });
                    if (response.ok) {
                        updateAuthUI(false);
                    }
                } catch (error) {
                    console.error('Ошибка при выходе:', error);
                }
            };
        } else {
            authButton.textContent = 'Войти через HH.ru';
            authButton.disabled = false;
            authButton.style.backgroundColor = '#d6001c';
            authButton.onclick = async () => {
                try {
                    const response = await fetch('http://localhost:8000/auth/login', {
                        method: 'GET',
                        headers: {
                            'X-Extension-User-Id': extensionUserId
                        }
                    });
                    
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    
                    const data = await response.json();
                    console.log('Получен URL авторизации:', data);
                    
                    // Открываем окно авторизации
                    const authWindow = window.open(
                        data.auth_url,
                        'HH Auth',
                        'width=600,height=700,menubar=no,toolbar=no,location=no,status=no'
                    );
                    
                    // Добавляем обработчик сообщений от окна авторизации
                    window.addEventListener('message', function(event) {
                        if (event.data === 'auth_success') {
                            checkAuthState();
                        }
                    });
                } catch (error) {
                    console.error('Ошибка при авторизации:', error);
                }
            };
        }
    }

    // Инициализация расширения
    async function initializeExtension() {
        await getOrCreateExtensionUserId();
        loadData();
        checkAuthState();
    }

    // Обработка состояния боковой панели
    chrome.sidePanel.setOptions({
        enabled: true,
        path: 'sidepanel.html'
    });

    // Запускаем инициализацию
    initializeExtension();
}); 