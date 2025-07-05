import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
import requests
import time
import random
import datetime

GROUP_ID = 231406471
TOKEN = "vk1.a.PzHqqXxe88F9IRrh_TKb-CXcpTtV5ue4W9ppsUvXcea1C2EWHmYUIZMNr9W42MlplRCxP6F-OsuBCWPFqvZvLmpXEG2gUkq0foxJME1ZAiF3Yv3pnk8xixS7zPyfXQwzhvBHwFVlRY7N_dPTultrjOLsUJ6HrKaTN5mSeubN4owooj0uznCT8FazgsF9vweGkWpWcewfE8ewqMPBlGbL4g"
VK_EDU_LINK = "https://vk.com/vkedu"

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

def create_keyboard():
    keyboard = VkKeyboard(inline=True)
    questions = list(FAQ.keys())
    
    for i, question in enumerate(questions):
        keyboard.add_button(question, color=VkKeyboardColor.PRIMARY)
        if (i + 1) % 2 == 0 and i < len(questions) - 1:
            keyboard.add_line()
    
    keyboard.add_line()
    keyboard.add_button("Другой вопрос", color=VkKeyboardColor.SECONDARY)
    return keyboard.get_keyboard()

def google_search(question):
    try:
        query = f"{question} site:vk.com OR site:education.vk.com"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7'
        }
        
        time.sleep(1.5)
        response = requests.get(
            "https://www.google.com/search",
            params={'q': query, 'num': 3, 'hl': 'ru'},
            headers=headers
        )
        
        if "detected unusual traffic" in response.text:
            search_url = f"https://www.google.com/search?q={query}"
            return f"🔍 Для просмотра результатов перейдите по ссылке:\n{search_url}"
        
        results = []
        start = 0
        while len(results) < 3:
            start_idx = response.text.find('href="/url?q=', start)
            if start_idx == -1:
                break
            
            end_idx = response.text.find('&', start_idx + 14)
            if end_idx == -1:
                break
                
            url = response.text[start_idx + 14:end_idx]
            if url.startswith('http'):
                # Декодируем URL
                url = requests.utils.unquote(url)
                results.append(url)
            
            start = end_idx
        
        if results:
            return "🔍 Вот что я нашел:\n" + "\n".join(results[:3]) + f"\n\nТакже посетите: {VK_EDU_LINK}"
        
        return f"🔍 По вашему запросу ничего не найдено.\nРекомендую посетить: {VK_EDU_LINK}"
    
    except Exception as e:
        return f"🔍 Для поиска информации посетите:\n{VK_EDU_LINK}/search?q={question}"

def hybrid_search(question):
    for key in FAQ.keys():
        if question.lower() in key.lower():
            return FAQ[key]
    
    return google_search(question)

def main():
    vk_session = vk_api.VkApi(token=TOKEN)
    vk = vk_session.get_api()
    longpoll = VkBotLongPoll(vk_session, GROUP_ID)
    
    print("Бот запущен! Ожидание сообщений...")
    print("Для вызова меню отправьте: помощь, меню или клавиатура")
    print("Тестовый поиск:", hybrid_search("проекты для студентов"))
    
    for event in longpoll.listen():
        if event.type == VkBotEventType.MESSAGE_NEW:
            msg = event.object.message
            user_id = msg['from_id']
            text = msg['text']
            current_time = datetime.datetime.now().strftime("%H:%M:%S")
            print(f"[{current_time}] Сообщение от {user_id}: {text}")
            
            if text.lower() in ["помощь", "меню", "клавиатура", "start"]:
                vk.messages.send(
                    user_id=user_id,
                    message="Выберите вопрос из меню:",
                    keyboard=create_keyboard(),
                    random_id=0
                )
                continue
            
            if text in FAQ:
                vk.messages.send(
                    user_id=user_id,
                    message=FAQ[text],
                    keyboard=create_keyboard(),
                    random_id=0
                )
                continue
            
            if text == "Другой вопрос":
                response = "Задайте ваш вопрос текстом!"
            elif any(kw in text.lower() for kw in ["можно ли", "возможно ли", "есть ли", "будет ли"]):
                response = "Да." if any(kw in text.lower() for kw in ["можно", "возможно", "есть", "будет"]) else "Нет."
            else:
                response = hybrid_search(text)
            
            vk.messages.send(
                user_id=user_id,
                message=response,
                keyboard=create_keyboard(),
                random_id=0
            )
            print(f"[{current_time}] Отправлен ответ")

if __name__ == '__main__':
    main()
