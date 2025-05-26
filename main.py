import telebot
import json

TOKEN = '7891817489:AAEcB8G2fkErx8OWlB4WHGaWOeDeBNKxv-k'
bot = telebot.TeleBot(TOKEN)

SPECIALTIES = {
    'Программирование': ['Python', 'JavaScript', 'Java', 'C++'],
    'Системное администрирование': ['Linux', 'Windows Server', 'Docker', 'Kubernetes'],
    'Маркетинг': ['SEO', 'SMM', 'Google Analytics', 'Email Marketing']
}

USER_STATES = {}

STATE_NAME = 'name'
STATE_AGE = 'age'
STATE_EXPERIENCE = 'experience'
STATE_SPECIALTY = 'specialty'
STATE_SKILLS = 'skills'


def get_experience_buttons():
    markup = telebot.types.InlineKeyboardMarkup()
    for exp in ['Нет опыта', '1-3 года', '3-5 лет', 'Более 5 лет']:
        markup.add(telebot.types.InlineKeyboardButton(text=exp, callback_data=f'exp_{exp}'))
    return markup


def get_cancel_button():
    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add('Отмена')
    return markup


def reset_user_state(chat_id):
    if chat_id in USER_STATES:
        del USER_STATES[chat_id]
    try:
        with open(f'resume_{chat_id}.json', 'w') as f:
            json.dump({}, f)
    except Exception:
        pass


@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    reset_user_state(chat_id)
    bot.send_message(chat_id, "Добро пожаловать! Я помогу вам составить резюме.\n"
                              "Для начала давайте соберём ваши данные.\n"
                              "Введите ваше имя:", reply_markup=get_cancel_button())
    USER_STATES[chat_id] = {'step': STATE_NAME}

@bot.message_handler(func=lambda m: m.text == 'Отмена')
def cancel(message):
    chat_id = message.chat.id
    reset_user_state(chat_id)
    bot.send_message(chat_id, "Заполнение анкеты отменено.", reply_markup=telebot.types.ReplyKeyboardRemove())

@bot.message_handler(content_types=['text'])
def handle_text(message):
    chat_id = message.chat.id
    user_data = USER_STATES.get(chat_id)

    if not user_data:
        bot.send_message(chat_id, "Неизвестная команда. Воспользуйтесь /start.")
        return

    text = message.text.strip()

    if user_data['step'] == STATE_NAME:
        user_data['name'] = text
        bot.send_message(chat_id, "Введите ваш возраст:")
        user_data['step'] = STATE_AGE

    elif user_data['step'] == STATE_AGE:
        if not text.isdigit() or int(text) < 14 or int(text) > 100:
            bot.send_message(chat_id, "Пожалуйста, введите корректный возраст (число от 14 до 100).")
            return
        user_data['age'] = int(text)
        bot.send_message(chat_id, "Выберите опыт работы:", reply_markup=get_experience_buttons())
        user_data['step'] = STATE_EXPERIENCE

    elif user_data['step'] == STATE_SPECIALTY:
        if text not in SPECIALTIES:
            bot.send_message(chat_id, "Выберите специальность из предложенных.")
            return
        user_data.setdefault('specialties', []).append(text)
        bot.send_message(chat_id, "Добавить ещё специальность? (да/нет)")

    elif user_data['step'] == STATE_SPECIALTY + '_confirm':
        if text.lower() == 'да':
            bot.send_message(chat_id, "Выберите специальность:", reply_markup=generate_specialty_buttons())
        elif text.lower() == 'нет':
            bot.send_message(chat_id, "Теперь выберите навыки, которые у вас есть:")
            user_data['step'] = STATE_SKILLS
            bot.send_message(chat_id, "Выберите навыки:",
                             reply_markup=generate_skill_buttons(user_data.get('specialties', [])))
        else:
            bot.send_message(chat_id, "Введите 'да' или 'нет'.")

    elif user_data['step'] == STATE_SKILLS:
        bot.send_message(chat_id, "Спасибо! Ваше резюме готово.")
        save_resume(chat_id, user_data)
        reset_user_state(chat_id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('exp_'))
def process_experience(call):
    chat_id = call.message.chat.id
    user_data = USER_STATES.get(chat_id)
    if user_data and user_data['step'] == STATE_EXPERIENCE:
        user_data['experience'] = call.data[4:]
        bot.send_message(chat_id, "Выберите специальность:", reply_markup=generate_specialty_buttons())
        user_data['step'] = STATE_SPECIALTY


def generate_specialty_buttons():
    markup = telebot.types.InlineKeyboardMarkup()
    for spec in SPECIALTIES:
        markup.add(telebot.types.InlineKeyboardButton(spec, callback_data=f'spec_{spec}'))
    return markup


@bot.callback_query_handler(func=lambda call: call.data.startswith('spec_'))
def process_specialty(call):
    chat_id = call.message.chat.id
    user_data = USER_STATES.get(chat_id)
    if user_data and user_data['step'] == STATE_SPECIALTY:
        specialty = call.data[5:]
        user_data.setdefault('specialties', []).append(specialty)
        bot.send_message(chat_id, "Добавить ещё одну специальность? (да/нет)",
                         reply_markup=telebot.types.ReplyKeyboardRemove())
        user_data['step'] = STATE_SPECIALTY + '_confirm'


def generate_skill_buttons(specialties):
    skills = set()
    for spec in specialties:
        skills.update(SPECIALTIES.get(spec, []))
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    buttons = [telebot.types.InlineKeyboardButton(skill, callback_data=f'skill_{skill}') for skill in skills]
    markup.add(*buttons)
    return markup


@bot.callback_query_handler(func=lambda call: call.data.startswith('skill_'))
def process_skill(call):
    chat_id = call.message.chat.id
    user_data = USER_STATES.get(chat_id)
    if user_data and user_data['step'] == STATE_SKILLS:
        skill = call.data[6:]
        user_data.setdefault('skills', []).append(skill)


def save_resume(chat_id, data):
    filename = f'resume_{chat_id}.json'
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump({
            'name': data.get('name'),
            'age': data.get('age'),
            'experience': data.get('experience'),
            'specialties': data.get('specialties', []),
            'skills': data.get('skills', [])
        }, f, ensure_ascii=False, indent=4)
    bot.send_document(chat_id, open(filename, 'rb'))


@bot.message_handler(func=lambda message: True)
def unknown_command(message):
    bot.send_message(message.chat.id, "Неизвестная команда. Попробуйте использовать /start.")


print("Бот запущен...")
bot.polling(none_stop=True)