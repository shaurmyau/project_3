import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from bot.services.user_service import UserService
from bot.keyboards.reply_keyboards import get_main_keyboard, get_cancel_keyboard

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик команды /start
    
    Args:
        update: Объект обновления от Telegram
        context: Контекст обработчика
    """
    user = update.effective_user
    
    # Сохраняем данные пользователя в контексте для регистрации
    context.user_data['telegram_id'] = user.id
    context.user_data['username'] = user.username
    context.user_data['first_name'] = user.first_name
    context.user_data['last_name'] = user.last_name
    
    # Получаем или создаем пользователя в БД
    db_user = UserService.get_or_create_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    # Проверяем, зарегистрирован ли пользователь
    is_registered = UserService.is_user_registered(user.id)
    
    if is_registered:
        # Пользователь уже зарегистрирован
        welcome_text = (
            f"С возвращением, {user.first_name}! 👋\n\n"
            f"Вы уже зарегистрированы в нашем дейтинг-боте.\n"
            f"Используйте кнопки меню для навигации:"
        )
        await update.message.reply_text(
            welcome_text,
            reply_markup=get_main_keyboard()
        )
    else:
        # Новый пользователь - начинаем регистрацию
        welcome_text = (
            f"Привет, {user.first_name}! 👋\n\n"
            f"Добро пожаловать в дейтинг-бот!\n\n"
            f"Для начала работы нам нужно создать вашу анкету. "
            f"Это займет всего пару минут.\n\n"
            f"Готовы начать регистрацию?"
        )
        
        keyboard = [
            ["✅ Да, начать регистрацию"],
            ["❌ Нет, позже"]
        ]
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        )
        
        # Сохраняем состояние ожидания ответа о начале регистрации
        context.user_data['awaiting_registration_confirmation'] = True

async def handle_registration_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик подтверждения начала регистрации
    """
    user_response = update.message.text
    user = update.effective_user
    
    if user_response == "✅ Да, начать регистрацию":
        # Переходим к регистрации
        from bot.handlers.registration import registration_start
        await registration_start(update, context)
    elif user_response == "❌ Нет, позже":
        await update.message.reply_text(
            "Хорошо! Вы всегда можете начать регистрацию позже с помощью команды /register",
            reply_markup=ReplyKeyboardRemove()
        )
        context.user_data.pop('awaiting_registration_confirmation', None)
    else:
        await update.message.reply_text(
            "Пожалуйста, используйте кнопки для выбора.",
            reply_markup=ReplyKeyboardMarkup(
                [["✅ Да, начать регистрацию"], ["❌ Нет, позже"]],
                resize_keyboard=True,
                one_time_keyboard=True
            )
        )