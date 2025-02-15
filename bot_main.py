import torch
from diffusers import StableDiffusionPipeline
from telebot import types, telebot
import os
from dotenv import load_dotenv
import re
import queue
import threading
import time


messages = [
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


load_dotenv()
token = os.getenv('TOKEN')

style = ""
model_id = ""
sampling_steps = 0
user_prompt = ""
height = 0
width = 0

bot = telebot.TeleBot(token)

request_queue = queue.Queue()
processing_queue = False


@bot.message_handler(commands=['start'])
def start_message(message):
    markup = types.InlineKeyboardMarkup()

    btn1 = types.InlineKeyboardButton(
        text="🌄 Реализм",
        callback_data="Реализм"
    )

    btn2 = types.InlineKeyboardButton(
        text="🖌️ Рисунок",
        callback_data="рисунок"
    )

    btn3 = types.InlineKeyboardButton(
        text="Помощь/предложения",
        callback_data="помощь"
    )

    markup.add(btn1)
    markup.add(btn2)
    markup.add(btn3)

    bot.send_message(message.from_user.id,
                     text=messages[0], reply_markup=markup)


@bot.callback_query_handler(func=lambda call: True)
def inline_start_btn(call):
    global model_id, sampling_steps, width, height

    if call.data == "помощь":
        bot.send_message(call.message.chat.id, messages[1])

    elif call.data == "Реализм":
        model_id = "SG161222/Realistic_Vision_V5.0_noVAE"
        bot.send_message(call.message.chat.id, "Что Вы хотите сгенерировать?\n"
                         "✅ Используйте только буквы латинского алфавита\n"
                         "\n"
                         "❌ При попытке генерации NSFW контента будет отправлено пустое изображение")
        bot.register_next_step_handler(call.message, get_prompt)

    elif call.data == "рисунок":
        model_id = "dreamlike-art/dreamlike-anime-1.0"
        bot.send_message(call.message.chat.id, "Что Вы хотите сгенерировать?\n"
                         "✅ Используйте только буквы латинского алфавита\n"
                         "\n"
                         "❌ При попытке генерации NSFW контента будет отправлено пустое изображение")
        bot.register_next_step_handler(call.message, get_prompt)

    elif call.data in ["20", "50", "75", "100"]:
        sampling_steps = int(call.data)
        scale(call)

    elif call.data == "vert":
        width = 512
        height = 912
        model_name = "рисунок" if model_id == "dreamlike-art/dreamlike-anime-1.0" else "реализм" if model_id == "SG161222/Realistic_Vision_V5.0_noVAE" else model_id

        bot.send_message(
            call.message.chat.id,
            text=f"Генерация изображения происходит по данным параметрам:\n"
            f"Ширина: {width}\n"
            f"Высота: {height}\n"
            f"Запрос: {user_prompt}\n"
            f"Количество шагов проработки: {sampling_steps}\n"
            f"Модель: {model_name}"
        )

        pipe = StableDiffusionPipeline.from_pretrained(
            model_id, torch_dtype=torch.float16).to("cuda")
        set_size_and_generate(pipe, call)

    elif call.data == "horizon":
        width = 912
        height = 512
        model_name = "рисунок" if model_id == "dreamlike-art/dreamlike-anime-1.0" else "реализм" if model_id == "SG161222/Realistic_Vision_V5.0_noVAE" else model_id

        bot.send_message(
            call.message.chat.id,
            text=f"Генерация изображения происходит по данным параметрам:\n"
            f"Ширина: {width}\n"
            f"Высота: {height}\n"
            f"Запрос: {user_prompt}\n"
            f"Количество шагов проработки: {sampling_steps}\n"
            f"Модель: {model_name}"
        )

        pipe = StableDiffusionPipeline.from_pretrained(
            model_id, torch_dtype=torch.float16).to("cuda")
        set_size_and_generate(pipe, call)

    elif call.data == "square":
        width = 512
        height = 512
        model_name = "рисунок" if model_id == "dreamlike-art/dreamlike-anime-1.0" else "реализм" if model_id == "SG161222/Realistic_Vision_V5.0_noVAE" else model_id

        bot.send_message(
            call.message.chat.id,
            text=f"Генерация изображения происходит по данным параметрам:\n"
            f"Ширина: {width}\n"
            f"Высота: {height}\n"
            f"Запрос: {user_prompt}\n"
            f"Количество шагов проработки: {sampling_steps}\n"
            f"Модель: {model_name}"
        )

        pipe = StableDiffusionPipeline.from_pretrained(
            model_id, torch_dtype=torch.float16).to("cuda")
        set_size_and_generate(pipe, call)


def get_prompt(message):
    global user_prompt
    user_prompt = message.text.strip()

    if not re.match(r'^[A-Za-z ]+$', user_prompt):
        bot.send_message(
            message.chat.id, "Повторите запрос, используя только буквы латинского алфавита")
        bot.register_next_step_handler(message, get_prompt)
    else:
        sampling_steps_message(message)


def sampling_steps_message(message):
    markup = types.InlineKeyboardMarkup()

    btn1 = types.InlineKeyboardButton(
        text="20",
        callback_data="20"
    )

    btn2 = types.InlineKeyboardButton(
        text="50",
        callback_data="50"
    )

    btn3 = types.InlineKeyboardButton(
        text="75",
        callback_data="75"
    )

    btn4 = types.InlineKeyboardButton(
        text="100",
        callback_data="100"
    )

    markup.add(btn1)
    markup.add(btn2)
    markup.add(btn3)
    markup.add(btn4)

    bot.send_message(message.chat.id,
                     text=messages[2], reply_markup=markup)


def scale(call):
    markup = types.InlineKeyboardMarkup()

    btn1 = types.InlineKeyboardButton(
        text="↕️ Вертикально",
        callback_data="vert"
    )
    btn2 = types.InlineKeyboardButton(
        text="↔️ Горизонтально",
        callback_data="horizon"
    )
    btn3 = types.InlineKeyboardButton(
        text="⏹️ Квадрат",
        callback_data="square"
    )

    markup.add(btn1)
    markup.add(btn2)
    markup.add(btn3)

    bot.send_message(call.from_user.id, text=messages[3], reply_markup=markup)


def set_size_and_generate(pipe, call):
    global width, height

    if call.data == "vert":
        width, height = 512, 912

    elif call.data == "horizon":
        width, height = 912, 512

    elif call.data == "square":
        width, height = 512, 512

    request_queue.put((pipe, user_prompt, height, width, sampling_steps, call))

    if not processing_queue:
        process_queue()


def process_queue():
    global processing_queue
    if not processing_queue and not request_queue.empty():
        processing_queue = True
        pipe, user_prompt, height, width, sampling_steps, call = request_queue.get()
        threading.Thread(target=generate_image_from_text, args=(
            pipe, user_prompt, height, width, sampling_steps, call)).start()


def generate_image_from_text(pipe, user_prompt, height, width, sampling_steps, call):
    global processing_queue

    output_dir = r"C:\\Users\\Mari\\Downloads\\text2art\\outputs"
    save_path = os.path.join(output_dir, f"{user_prompt}.png")

    bot.send_message(call.message.chat.id, "Генерация изображения...")

    with torch.amp.autocast(device_type="cuda"):
        image = pipe(
            user_prompt, num_inference_steps=sampling_steps, width=width, height=height).images[0]
    image.save(save_path)
    with open(save_path, "rb") as photo:
        bot.send_photo(call.message.chat.id, photo)

    time.sleep(10)
    torch.cuda.empty_cache()

    processing_queue = False
    process_queue()


bot.polling(none_stop=True)

