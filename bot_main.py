import torch  # Импорт всех необходимых библиотек
from diffusers import StableDiffusionPipeline
from telebot import types, telebot
import os
from dotenv import load_dotenv
import re
import queue
import threading
import time


messages = [  # Перечень сообщений, отправляемых ботом
    "👋 Здравствуйте! Это Text2ART - бот для генерации изображений по текстовому запросу\n"  # 0
    "\n"
    "Давайте попробуем что-нибудь сгенерировать. Для начала выберите, в каком стиле Вы хотите сгенерировать изображение",

    "По всем вопросам или предложениям Вы можете обратиться к администрации бота\n"  # 1
    "\n"
    "~@Chedrok\n"
    "~@Dust_mi",

    "🔧 Теперь укажите уровень проработки изображения\n"  # 2
    "(больше шагов -> проработаннее, медленнее генерация)",

    "Выберите формат изображения:"  # 3
]


load_dotenv()  # Загрузка информации из файлов виртуального окружения
token = os.getenv('TOKEN')  # Передача выгруженной информации в токен бота


# Инициализация глобальных переменных
style = ""
model_id = ""
sampling_steps = 0
user_prompt = ""
height = 0
width = 0

# Передача API токена в основной модуль Telegram-бота
bot = telebot.TeleBot(token)

# Переменная записи значений пользователя, находящегося в очереди
request_queue = queue.Queue()
processing_queue = False  # Установка флага очереди


@bot.message_handler(commands=['start'])  # Декоратор обработки команды /start
def start_message(message):
    markup = types.InlineKeyboardMarkup()  # Переменная для работы с Inline кнопками

    btn1 = types.InlineKeyboardButton(  # Настройка первой Inline кнопки
        text="🌄 Реализм",
        callback_data="Реализм"
    )

    btn2 = types.InlineKeyboardButton(  # Настройка второй Inline кнопки
        text="🖌️ Рисунок",
        callback_data="рисунок"
    )

    btn3 = types.InlineKeyboardButton(  # Настройка третьей Inline кнопки
        text="Помощь/предложения",
        callback_data="помощь"
    )

    markup.add(btn1)  # Передача значений кнопок в переменную markup
    markup.add(btn2)
    markup.add(btn3)

    bot.send_message(message.from_user.id,
                     # Отправка сообщения из переменной messages с подписанными Inline кнопками
                     text=messages[0], reply_markup=markup)


# Декоратор обработки запросовов от Inline кнопок
@bot.callback_query_handler(func=lambda call: True)
def inline_start_btn(call):
    # Инициализация глобальных переменных
    global model_id, sampling_steps, width, height

    if call.data == "помощь":
        # Отправка сообщения с помощью/предложениями
        bot.send_message(call.message.chat.id, messages[1])

    elif call.data == "Реализм":
        # Выбор реалистичной модели для генерации
        model_id = "SG161222/Realistic_Vision_V5.0_noVAE"
        bot.send_message(call.message.chat.id, "Что Вы хотите сгенерировать?\n"
                         "✅ Вводите запрос на английском языке")  # Отправка сообщения пользователю
        # Запись только следующего значения, введёенного пользователем, в функцию get_prompt
        bot.register_next_step_handler(call.message, get_prompt)

    elif call.data == "рисунок":
        # Выбор рисованной модели для генерации
        model_id = "dreamlike-art/dreamlike-anime-1.0"
        bot.send_message(call.message.chat.id, "Что Вы хотите сгенерировать?\n"
                         "✅ Вводите запрос на английском языке")  # Отправка сообщения пользователю
        # Запись только следующего значения, введёенного пользователем, в функцию get_prompt
        bot.register_next_step_handler(call.message, get_prompt)

    elif call.data in ["20", "50", "75", "100"]:
        # Выбор количества шагов шумоподавления
        sampling_steps = int(call.data)
        scale(call)

    elif call.data == "vert":  # Выбор формата изображения
        width = 512
        height = 912
        # Запись названия модели в зависимости от выбора пользователя
        model_name = "рисунок" if model_id == "dreamlike-art/dreamlike-anime-1.0" else "реализм" if model_id == "SG161222/Realistic_Vision_V5.0_noVAE" else model_id

        bot.send_message(  # Отправка сообщения, содержащего все выбранные пользователем  параметры
            call.message.chat.id,
            text=f"Генерация изображения происходит по данным параметрам:\n"
            f"Ширина: {width}\n"
            f"Высота: {height}\n"
            f"Запрос: {user_prompt}\n"
            f"Количество шагов проработки: {sampling_steps}\n"
            f"Модель: {model_name}"
        )

        pipe = StableDiffusionPipeline.from_pretrained(
            # Установка и инициализация модели изображения для последующей генерации
            model_id, torch_dtype=torch.float16).to("cuda")
        set_size_and_generate(pipe, call)

    elif call.data == "horizon":  # Выбор формата изображения
        width = 912
        height = 512
        # Запись названия модели в зависимости от выбора пользователя
        model_name = "рисунок" if model_id == "dreamlike-art/dreamlike-anime-1.0" else "реализм" if model_id == "SG161222/Realistic_Vision_V5.0_noVAE" else model_id

        bot.send_message(  # Отправка сообщения, содержащего все выбранные пользователем  параметры
            call.message.chat.id,
            text=f"Генерация изображения происходит по данным параметрам:\n"
            f"Ширина: {width}\n"
            f"Высота: {height}\n"
            f"Запрос: {user_prompt}\n"
            f"Количество шагов проработки: {sampling_steps}\n"
            f"Модель: {model_name}"
        )

        pipe = StableDiffusionPipeline.from_pretrained(
            # Установка и инициализация модели изображения для последующей генерации
            model_id, torch_dtype=torch.float16).to("cuda")
        set_size_and_generate(pipe, call)

    elif call.data == "square":  # Выбор формата изображения
        width = 512
        height = 512
        # Запись названия модели в зависимости от выбора пользователя
        model_name = "рисунок" if model_id == "dreamlike-art/dreamlike-anime-1.0" else "реализм" if model_id == "SG161222/Realistic_Vision_V5.0_noVAE" else model_id

        bot.send_message(  # Отправка сообщения, содержащего все выбранные пользователем  параметры
            call.message.chat.id,
            text=f"Генерация изображения происходит по данным параметрам:\n"
            f"Ширина: {width}\n"
            f"Высота: {height}\n"
            f"Запрос: {user_prompt}\n"
            f"Количество шагов проработки: {sampling_steps}\n"
            f"Модель: {model_name}"
        )

        pipe = StableDiffusionPipeline.from_pretrained(
            # Установка и инициализация модели изображения для последующей генерации
            model_id, torch_dtype=torch.float16).to("cuda")
        set_size_and_generate(pipe, call)


def get_prompt(message):  # Функция по обработке текстового запроса пользователя
    global user_prompt
    user_prompt = message.text.strip()  # Запись сообщения в переменную

    # Проверка на корректность содержания сообщения
    if not re.match(r'^[A-Za-z ]+$', user_prompt):
        bot.send_message(
            # Отправка сообщения, если запрос некорректен
            message.chat.id, "Повторите запрос на английском языке")
        # Повторное принятие последующего значения
        bot.register_next_step_handler(message, get_prompt)
    else:
        sampling_steps_message(message)  # Переход к следующей функции


# Выбор количества шагов шумоподавления для генерации
def sampling_steps_message(message):
    markup = types.InlineKeyboardMarkup()  # Переменная для работы с Inline кнопками

    btn1 = types.InlineKeyboardButton(  # Настройка первой Inline кнопки
        text="20",
        callback_data="20"
    )

    btn2 = types.InlineKeyboardButton(  # Настройка второй Inline кнопки
        text="50",
        callback_data="50"
    )

    btn3 = types.InlineKeyboardButton(  # Настройка третьей Inline кнопки
        text="75",
        callback_data="75"
    )

    btn4 = types.InlineKeyboardButton(  # Настройка четвертой Inline кнопки
        text="100",
        callback_data="100"
    )

    markup.add(btn1)  # Передача значений Inline кнопок в переменную markup
    markup.add(btn2)
    markup.add(btn3)
    markup.add(btn4)

    bot.send_message(message.chat.id,
                     # Отправка сообщения с Inline кнопками
                     text=messages[2], reply_markup=markup)


def scale(call):  # Выбор формата изображения
    markup = types.InlineKeyboardMarkup()  # Переменная для работы с Inline кнопками

    btn1 = types.InlineKeyboardButton(  # Настройка первой Inline кнопки
        text="↕️ Вертикально",
        callback_data="vert"
    )
    btn2 = types.InlineKeyboardButton(  # Настройка второй Inline кнопки
        text="↔️ Горизонтально",
        callback_data="horizon"
    )
    btn3 = types.InlineKeyboardButton(  # Настройка третьей Inline кнопки
        text="⏹️ Квадрат",
        callback_data="square"
    )

    markup.add(btn1)  # Передача значений Inline кнопок в переменную markup
    markup.add(btn2)
    markup.add(btn3)

    # Отправка сообщения с Inline кнопками
    bot.send_message(call.from_user.id, text=messages[3], reply_markup=markup)


# Функция вторичной записи формата изображения
def set_size_and_generate(pipe, call):
    global width, height  # Инициализация глобальных переменных

    if call.data == "vert":  # Выбор формата изображения
        width, height = 512, 912

    elif call.data == "horizon":  # Выбор формата изображения
        width, height = 912, 512

    elif call.data == "square":  # Выбор формата изображения
        width, height = 512, 512

    # Запись всех значений, выбранных пользователем, в переменную очереди
    request_queue.put((pipe, user_prompt, height, width, sampling_steps, call))

    if not processing_queue:  # Запуск функции если это не было совершенно раньше, позволяет избежать возможных отключений
        process_queue()


def process_queue():
    global processing_queue
    # Если в переменную очереди для генерации что-то записано и флаг установлен False, значит генератор изображений свободен
    if not processing_queue and not request_queue.empty():
        processing_queue = True  # Установка флага True
        # Выгрузка значений из переменной, отвечающей за очередь
        pipe, user_prompt, height, width, sampling_steps, call = request_queue.get()
        threading.Thread(target=generate_image_from_text, args=(
            # Запуск генерации изображения в отдельном ядре
            pipe, user_prompt, height, width, sampling_steps, call)).start()


def generate_image_from_text(pipe, user_prompt, height, width, sampling_steps, call):
    global processing_queue

    # Путь для сохранения изображений
    output_dir = r"C:\\Users\\Mari\\Downloads\\text2art\\outputs"
    # Создание пути с названием изображения
    save_path = os.path.join(output_dir, f"{user_prompt}.png")

    # Вывод сообщения пользователю
    bot.send_message(call.message.chat.id, "Генерация изображения...")

    with torch.amp.autocast(device_type="cuda"):  # Использование ПО CUDA
        image = pipe(
            # Генерация изображения
            user_prompt, num_inference_steps=sampling_steps, width=width, height=height).images[0]
    image.save(save_path)  # Сохранение изображения
    with open(save_path, "rb") as photo:  # Выгрузка сохранённого изображения
        # Отправка изображения пользователю
        bot.send_photo(call.message.chat.id, photo)

    # !0 секундный таймер задержка, для избежания проблем с нехваткой видеопамяти
    time.sleep(10)
    torch.cuda.empty_cache()  # Очистка кэш файлов для генерации изображений

    # Установка отрицательного флага, что означает, что генерация завершена и можно начинать следующую
    processing_queue = False
    process_queue()  # Запуск функции обработчика очереди


bot.polling(none_stop=True)  # Запуск бота
