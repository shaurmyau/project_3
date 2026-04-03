#!/usr/bin/env python3
from telegram import Update
import logging
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters
)
from config import config
from bot.handlers.start import start_command, handle_registration_confirmation
from bot.handlers.registration import (
    registration_start,
    ask_gender,
    ask_age,
    ask_city,
    ask_bio,
    ask_photo,
    ask_search_gender,
    ask_search_age_min,
    ask_search_age_max,
    ask_search_distance,
    cancel_registration
)
from bot.states.registration_states import *
from bot.models.database import init_db

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO if not config.DEBUG else logging.DEBUG
)

logger = logging.getLogger(__name__)

def main() -> None:
    """Запуск бота"""
    # Инициализация базы данных
    init_db()
    logger.info("Database initialized")
    
    # Создание приложения
    application = Application.builder().token(config.BOT_TOKEN).build()
    
    # Регистрация обработчика регистрации
    registration_handler = ConversationHandler(
        entry_points=[
            CommandHandler('register', registration_start),
            MessageHandler(
                filters.Regex('^✅ Да, начать регистрацию$'),
                registration_start
            )
        ],
        states={
            ASK_GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_gender)],
            ASK_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_age)],
            ASK_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_city)],
            ASK_BIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_bio)],
            ASK_PHOTO: [MessageHandler(filters.PHOTO | filters.TEXT & ~filters.COMMAND, ask_photo)],
            ASK_SEARCH_GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_search_gender)],
            ASK_SEARCH_AGE_MIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_search_age_min)],
            ASK_SEARCH_AGE_MAX: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_search_age_max)],
            ASK_SEARCH_DISTANCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_search_distance)],
        },
        fallbacks=[
            CommandHandler('cancel', cancel_registration),
            MessageHandler(filters.Regex('^Отмена$'), cancel_registration)
        ],
        name="registration_conversation",
        persistent=False
    )
    
    application.add_handler(registration_handler)
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(
        MessageHandler(
            filters.Regex('^(✅ Да, начать регистрацию|❌ Нет, позже)$'),
            handle_registration_confirmation
        )
    )
    
    # Запуск бота
    logger.info("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()