from telegram import ReplyKeyboardMarkup, KeyboardButton

def get_gender_keyboard():
    """Клавиатура для выбора пола"""
    keyboard = [
        [KeyboardButton("Мужской"), KeyboardButton("Женский")],
        [KeyboardButton("Другой")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

def get_search_gender_keyboard():
    """Клавиатура для выбора пола для поиска"""
    keyboard = [
        [KeyboardButton("Мужской"), KeyboardButton("Женский")],
        [KeyboardButton("Любой")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

def get_cancel_keyboard():
    """Клавиатура с кнопкой отмены"""
    keyboard = [[KeyboardButton("Отмена")]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_main_keyboard():
    """Главная клавиатура после регистрации"""
    keyboard = [
        [KeyboardButton("👤 Моя анкета"), KeyboardButton("🔍 Смотреть анкеты")],
        [KeyboardButton("💬 Чаты"), KeyboardButton("⚙️ Настройки")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)