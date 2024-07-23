from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler
import logging
import requests
import json
import wikipedia
from attractions_data import attractions_data

# Настройка логгирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Стартовое состояние разговора
START, ASK_COUNTRY, ASK_CITY, CHOOSE_SEARCH_METHOD, WIKIPEDIA_INFO, RAPIDAPI_INFO, CHOOSE_ROUTE, CHOOSE_ROUTE_BACK, END_CONVERSATION = range(9)

# Функция начала диалога
def start(update, context):
    context.user_data.clear()  # Очищаем данные пользователя
    reply_keyboard = [['Начать путешествие']]
    update.message.reply_text(
        "Привет! Я могу помочь тебе узнать о достопримечательностях городов. "
        "Давай начнем. В какой стране ты хочешь узнать о городе?",
        reply_markup=ReplyKeyboardRemove()
    )
    update.message.reply_text(
        "Нажми 'Начать путешествие', чтобы завершить разговор.",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return ASK_COUNTRY

# Функция завершения диалога
def end_conversation(update, context):
    user = update.message.from_user
    logger.info("User %s ended the conversation.", user.first_name)
    update.message.reply_text(
        'До новых встреч! Если захочешь узнать о достопримечательностях, просто напиши /start.',
        reply_markup=ReplyKeyboardRemove()
    )
    context.user_data.clear()
    return ConversationHandler.END

# Функция обработки страны
def ask_country(update, context):
    user_country = update.message.text
    context.user_data['country'] = user_country
    update.message.reply_text(
        f"Отлично! Теперь укажи, пожалуйста, город в стране {user_country}."
    )
    return ASK_CITY

# Функция обработки города и выбора метода поиска
def ask_city(update, context):
    user_city = update.message.text
    context.user_data['city'] = user_city
    reply_keyboard = [['РапидAPI', 'Википедия'], ['Изменить страну']]
    update.message.reply_text(
        f"Спасибо! Ты выбрал город {user_city}. Каким методом поиска ты хочешь воспользоваться?",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return CHOOSE_SEARCH_METHOD

# Функция обработки выбора метода поиска
def choose_search_method(update, context):
    user_choice = update.message.text
    if user_choice == 'РапидAPI':
        return rapidapi_info(update, context)
    elif user_choice == 'Википедия':
        return wikipedia_info(update, context)
    elif user_choice == 'Изменить страну':
        return start(update, context)  # Перезапускаем бота
    else:
        update.message.reply_text("Пожалуйста, выбери один из предложенных вариантов.")
        return CHOOSE_SEARCH_METHOD

# Функция для получения основной информации о городе из Википедии 
def wikipedia_info(update, context):
    user_city = context.user_data['city']
    try:
        wiki_page = wikipedia.page(user_city)
        summary = wiki_page.summary[:500]
        reply_keyboard = [['Маршрут 1', 'Маршрут 2'], ['Изменить страну']]
        update.message.reply_text(f"Основная информация о городе {user_city}:\n\n{summary}\n\nТеперь выбери маршрут достопримечательностей:",
                                  reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
        return CHOOSE_ROUTE
    except wikipedia.exceptions.PageError:
        update.message.reply_text(f"Информация о городе {user_city} не найдена.")
        return choose_search_method(update, context)

# Функция для вывода информации о достопримечательностях через RapidAPI
def rapidapi_info(update, context):
    user_city = context.user_data['city']
    user_country = context.user_data['country']

    # Заменяем пробелы в названии города на "+" для правильного запроса
    city_name = user_city.replace(' ', '+')

    # Запрос к RapidAPI (замените на реальные данные)
    url = "https://rapidapi.com"  # Замените на URL API RapidAPI
    headers = {
        'X-RapidAPI-Key': "df14899cb6msh2d95385e7ac5746p16e75cjsnaebb4ed134e2",  # Замените на свой ключ RapidAPI
        'X-RapidAPI-Host': "YOUR_RAPIDAPI_HOST"  # Замените на хост RapidAPI
    }
    querystring = {"q": city_name, "location": f"{city_name},{user_country}"}
    response = requests.request("GET", url, headers=headers, params=querystring)

    # Обработка ответа RapidAPI
    if response.status_code == 200:
        data = json.loads(response.text)
        attractions = data.get('attractions', [])

        if attractions:
            message = f"Достопримечательности в городе {user_city}:\n\n"
            for attraction in attractions:
                message += f"{attraction['name']}: {attraction['description']}\n\n"
            update.message.reply_text(message)
        else:
            update.message.reply_text(f"Извините, информация о достопримечательностях в {user_city} не найдена.")
    else:
        update.message.reply_text(f"Произошла ошибка при получении данных от RapidAPI.")
    reply_keyboard = [['Изменить страну']]
    update.message.reply_text(
        "Каким методом поиска ты хочешь воспользоваться?",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return CHOOSE_SEARCH_METHOD

# Функция для выбора маршрута достопримечательностей
def choose_route(update, context):
    route_choice = update.message.text
    city_key = f"{context.user_data['city']}, {context.user_data['country']}"
    attractions = attractions_data.get(city_key, [])
    if not attractions:
        update.message.reply_text("Извините, информация о достопримечательностях данного города временно недоступна.")
        return choose_search_method(update, context)

    message = f"Ты выбрал {route_choice}.\n\nМаршрут достопримечательностей:\n\n"
    if route_choice == 'Маршрут 1':
        route_attractions = attractions[:2]
    elif route_choice == 'Маршрут 2':
        route_attractions = attractions[2:4]
    elif route_choice == 'Изменить страну':
        return start(update, context)  # Перезапускаем бота
    else:
        update.message.reply_text("Пожалуйста, выбери один из предложенных маршрутов или изменить страну:")
        return CHOOSE_ROUTE

    for i, attraction in enumerate(route_attractions, start=1):
        message += f"{i}. {attraction['name']}: {attraction['description']}\n"

    reply_keyboard = [['Вернуться назад'], ['Изменить страну']]
    update.message.reply_text(message, reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
    return CHOOSE_ROUTE_BACK

# Функция для возврата к выбору маршрута достопримечательностей
def back_to_choose_route(update, context):
    city_key = f"{context.user_data['city']}, {context.user_data['country']}"
    attractions = attractions_data.get(city_key, [])
    if not attractions:
        update.message.reply_text("Извините, информация о достопримечательностях данного города временно недоступна.")
        return choose_search_method(update, context)

    reply_keyboard = [['Маршрут 1', 'Маршрут 2'], ['Изменить страну']]
    update.message.reply_text(
        "Выбери маршрут достопримечательностей или изменить страну:",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return CHOOSE_ROUTE

def cancel(update, context):
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    update.message.reply_text(
        'До новых встреч! Если захочешь узнать о достопримечательностях, просто напиши /start.',
        reply_markup=ReplyKeyboardRemove()
    )
    context.user_data.clear()
    return ConversationHandler.END

# Функция для обработки неизвестных команд
def unknown(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Извините, я не понимаю эту команду.")

# Функция для обработки всех сообщений от пользователя
def handle_message(update, context):
    update.message.reply_text("Извините, я не могу обработать ваш запрос. Пожалуйста, используйте кнопки для взаимодействия.")

# Функция main, запускающая бота
def main():
    # Инициализация бота
    updater = Updater(token='какой то токен)', use_context=True)
    dp = updater.dispatcher

    # Определение состояний и переходов между ними
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],

        states={
            ASK_COUNTRY: [MessageHandler(Filters.text & ~Filters.command, ask_country)],
            ASK_CITY: [MessageHandler(Filters.text & ~Filters.command, ask_city)],
            CHOOSE_SEARCH_METHOD: [MessageHandler(Filters.text & ~Filters.command, choose_search_method)],
            WIKIPEDIA_INFO: [MessageHandler(Filters.text & ~Filters.command, wikipedia_info)],
            RAPIDAPI_INFO: [MessageHandler(Filters.text & ~Filters.command, rapidapi_info)],
            CHOOSE_ROUTE: [MessageHandler(Filters.text & ~Filters.command, choose_route)],
            CHOOSE_ROUTE_BACK: [MessageHandler(Filters.text & ~Filters.command, back_to_choose_route)],
            END_CONVERSATION: [MessageHandler(Filters.text('Начать путешествие'), end_conversation)]
        },

        fallbacks=[CommandHandler('cancel', cancel)]
    )

    dp.add_handler(conv_handler)
    dp.add_handler(MessageHandler(Filters.command, unknown))
    dp.add_handler(MessageHandler(Filters.text, handle_message))

    # Запуск бота
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
