import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
import datetime
import time
import logging
import requests
import uuid

# Конфигурация
GROUP_ID = 231406471
TOKEN = "vk1.a.PzHqqXxe88F9IRrh_TKb-CXcpTtV5ue4W9ppsUvXcea1C2EWHmYUIZMNr9W42MlplRCxP6F-OsuBCWPFqvZvLmpXEG2gUkq0foxJME1ZAiF3Yv3pnk8xixS7zPyfXQwzhvBHwFVlRY7N_dPTultrjOLsUJ6HrKaTN5mSeubN4owooj0uznCT8FazgsF9vweGkWpWcewfE8ewqMPBlGbL4g"
VK_EDU_LINK = "https://vk.com/vkedu"
GIGACHAT_API_KEY = "ZDE3ZmYyYjEtODkyYi00OGFjLTlmMjctYjM1YjNkMjliZGEwOjM5NmVhYTk0LWE1NDQtNDA0MC04ZjY4LTI3MjUwYzk3MTBhNQ=="

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("VK_Education_Bot")

# База знаний (FAQ) - основные вопросы о VK Education
FAQ = {
    "Кто может участвовать?": "Школьники, студенты бакалавриата, специалитета, магистратуры и аспирантуры всех вузов России, а также научные руководители и преподаватели.",
    "Можно выбрать несколько задач?": "Да, можно выбрать неограниченное количество задач.",
    "Где использовать решения?": "В практической части выпускных квалификационных работ, курсовых, НИР и домашних заданий.",
    "Как получить данные?": "Выбери задачу, пройди регистрацию — и получишь доступ к материалам.",
    "Будут сертификаты?": "Да, при выполнении всех условий задачи.",
    "Будут оценки?": "Нет, но эксперты дадут рецензию на хорошие решения.",
    "Откуда задачи?": "Исследовательские задачи с актуальным бизнес-контекстом от VK.",
    "Кому задать вопрос?": "Экспертам на вебинарах или на обучающей платформе.",
    "Нет подходящей задачи?": "Следи за обновлениями в банке задач VK."
}

# Список нецензурных слов (фильтр)
PROFANITY_FILTER = [
    "бля", "хуй", "пизд", "еба", "хуе", "хуя", "ебал", "залуп", "мудак", "гандон",
    "шлюх", "долбоеб", "сука", "пидор", "член", "вагин", "пенис", "анус", "срак",
    "жопа", "ссать", "перд", "дрист", "елда", "мразь", "ублюдок", "падл", "бляд",
    "оху", "ебан", "ебу", "ебн", "писе", "попк", "сучк", "трах", "выеб", "вздроч",
    "гондон", "дроч", "заеб", "конч", "лох", "манда", "мудил", "педр", "пезд",
    "соси", "сперм", "суч", "хер", "хуи", "шмар"
]

def create_keyboard():
    """Создает интерактивную клавиатуру с вопросами"""
    keyboard = VkKeyboard(inline=True)
    questions = list(FAQ.keys())
    
    for i, question in enumerate(questions):
        keyboard.add_button(question, color=VkKeyboardColor.PRIMARY)
        if (i + 1) % 2 == 0 and i < len(questions) - 1:
            keyboard.add_line()
    
    keyboard.add_line()
    keyboard.add_button("Другой вопрос", color=VkKeyboardColor.SECONDARY)
    return keyboard.get_keyboard()

# Глобальные переменные для управления токеном GigaChat
access_token = None
token_expire_time = 0

def get_gigachat_token():
    """Получаем новый токен доступа для GigaChat API"""
    global access_token, token_expire_time
    
    url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    
    payload = {
        'scope': 'GIGACHAT_API_PERS'
    }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json',
        'RqUID': str(uuid.uuid4()),
        'Authorization': f'Basic {GIGACHAT_API_KEY}'
    }
    
    try:
        # Отключаем проверку SSL для этого запроса
        response = requests.post(
            url, 
            headers=headers, 
            data=payload, 
            timeout=10,
            verify=False  # ОТКЛЮЧАЕМ ПРОВЕРКУ SSL
        )
        
        if response.status_code == 200:
            data = response.json()
            access_token = data['access_token']
            token_expire_time = time.time() + 25 * 60
            logger.info("Токен GigaChat успешно получен")
            return True
        else:
            logger.error(f"Ошибка получения токена: {response.status_code}, {response.text}")
            return False
    except Exception as e:
        logger.error(f"Ошибка при получении токена: {str(e)}")
        return False

def contains_profanity(text):
    """Проверяет текст на наличие нецензурной лексики"""
    text_lower = text.lower()
    for word in PROFANITY_FILTER:
        if word in text_lower:
            return True
    return False

def is_closed_question(question):
    """Определяет, является ли вопрос закрытым (да/нет)"""
    closed_keywords = [
        "можно ли", "возможно ли", "есть ли", "будет ли", "имеется ли", 
        "существует ли", "доступно ли", "разрешено ли", "допустимо ли",
        "можно?", "разрешено?", "будет?", "есть?", "доступно?", "допустимо?"
    ]
    
    question_lower = question.lower()
    return any(keyword in question_lower for keyword in closed_keywords)

def ask_gigachat(question):
    """Отправляем запрос к GigaChat API с использованием токена"""
    global access_token, token_expire_time
    
    if not access_token or time.time() > token_expire_time:
        if not get_gigachat_token():
            return "Сервис временно недоступен. Попробуйте позже."
    
    url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }
    
    messages = [
        {
            "role": "system",
            "content": (
                "Ты помощник для проектов VK Education. Отвечай кратко (1-2 предложения), "
                "используя только информацию с официального сайта VK Education. "
                "Будь дружелюбным и полезным. Если вопрос не связан с образовательными проектами VK, "
                "вежливо предложи посетить официальный сайт VK Education. "
                "Не упоминай, что ты ИИ-модель. Используй эмодзи для выразительности."
            )
        },
        {
            "role": "user",
            "content": question
        }
    ]
    
    data = {
        "model": "GigaChat",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 200
    }
    
    try:
        # Отключаем проверку SSL для этого запроса
        response = requests.post(
            url, 
            headers=headers, 
            json=data, 
            timeout=15,
            verify=False  # ОТКЛЮЧАЕМ ПРОВЕРКУ SSL
        )
        
        if response.status_code == 401:
            logger.warning("Токен недействителен. Пробуем обновить...")
            if get_gigachat_token():
                headers['Authorization'] = f'Bearer {access_token}'
                response = requests.post(
                    url, 
                    headers=headers, 
                    json=data, 
                    timeout=15,
                    verify=False  # ОТКЛЮЧАЕМ ПРОВЕРКУ SSL
                )
            else:
                return "Ошибка авторизации. Попробуйте позже."
        
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        else:
            logger.error(f"Ошибка API GigaChat: {response.status_code}, {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        logger.warning("Таймаут при запросе к GigaChat API")
        return None
    except Exception as e:
        logger.error(f"Ошибка запроса к GigaChat: {str(e)}")
        return None

def get_answer(question):
    """Генерирует ответ на вопрос пользователя"""
    if contains_profanity(question):
        return "⚠️ Пожалуйста, соблюдайте правила общения. Недопустимо использовать нецензурную лексику."
    
    if is_closed_question(question):
        positive_keywords = ["можно", "возможно", "есть", "будет", "разрешено", "доступно", "допустимо"]
        question_lower = question.lower()
        if any(keyword in question_lower for keyword in positive_keywords):
            return "✅ Да."
        else:
            return "❌ Нет."
    
    if question in FAQ:
        return FAQ[question]
    
    question_lower = question.lower()
    for key, answer in FAQ.items():
        if question_lower in key.lower():
            return answer
    
    giga_response = ask_gigachat(question)
    if giga_response:
        return giga_response
    
    return f"🤔 Я не нашел ответ на ваш вопрос. Посетите официальный сайт VK Education для получения информации: {VK_EDU_LINK}"

def main():
    vk_session = vk_api.VkApi(token=TOKEN)
    vk = vk_session.get_api()
    longpoll = VkBotLongPoll(vk_session, GROUP_ID)
    
    logger.info("Бот VK Education запущен!")
    logger.info("Ожидание сообщений...")
    
    if not get_gigachat_token():
        logger.error("Не удалось получить токен GigaChat при запуске. Бот будет работать без GigaChat.")
    
    keyboard = create_keyboard()
    
    for event in longpoll.listen():
        if event.type == VkBotEventType.MESSAGE_NEW:
            msg = event.object.message
            user_id = msg['from_id']
            text = msg['text']
            current_time = datetime.datetime.now().strftime("%H:%M:%S")
            
            logger.info(f"[{current_time}] Сообщение от {user_id}: {text}")
            
            if text.lower() in ["помощь", "меню", "клавиатура", "start"]:
                vk.messages.send(
                    user_id=user_id,
                    message="👋 Привет! Я бот VK Education. Выберите вопрос из меню:",
                    keyboard=keyboard,
                    random_id=0
                )
                continue
            
            if text == "Другой вопрос":
                response = "❓ Задайте ваш вопрос текстом, и я постараюсь помочь!"
                vk.messages.send(
                    user_id=user_id,
                    message=response,
                    keyboard=keyboard,
                    random_id=0
                )
                continue
            
            response = get_answer(text)
            
            vk.messages.send(
                user_id=user_id,
                message=response,
                keyboard=keyboard,
                random_id=0
            )
            logger.info(f"[{current_time}] Отправлен ответ")

if __name__ == '__main__':
    main()
