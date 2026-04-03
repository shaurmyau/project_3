import logging
from datetime import datetime, date
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from bot.services.user_service import UserService
from bot.keyboards.reply_keyboards import (
    get_gender_keyboard, 
    get_search_gender_keyboard,
    get_cancel_keyboard
)
from bot.states.registration_states import *

logger = logging.getLogger(__name__)

async def registration_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Начало регистрации
    """
    await update.message.reply_text(
        "Давайте создадим вашу анкету! 📝\n\n"
        "Сначала укажите ваш пол:",
        reply_markup=get_gender_keyboard()
    )
    
    return ASK_GENDER

async def ask_gender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Получение пола пользователя
    """
    gender_map = {
        "Мужской": "male",
        "Женский": "female",
        "Другой": "other"
    }
    
    gender_text = update.message.text
    
    if gender_text not in gender_map:
        await update.message.reply_text(
            "Пожалуйста, выберите пол из предложенных вариантов:",
            reply_markup=get_gender_keyboard()
        )
        return ASK_GENDER
    
    context.user_data['gender'] = gender_map[gender_text]
    
    await update.message.reply_text(
        "Теперь укажите вашу дату рождения в формате ДД.ММ.ГГГГ\n"
        "Например: 15.05.1995",
        reply_markup=get_cancel_keyboard()
    )
    
    return ASK_AGE

async def ask_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Получение даты рождения
    """
    if update.message.text == "Отмена":
        return await cancel_registration(update, context)
    
    try:
        birth_date_str = update.message.text
        birth_date = datetime.strptime(birth_date_str, "%d.%m.%Y").date()
        
        # Проверяем возраст
        today = date.today()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        
        if age < 18:
            await update.message.reply_text(
                "❌ Извините, бот предназначен для пользователей старше 18 лет.",
                reply_markup=ReplyKeyboardRemove()
            )
            return ConversationHandler.END
        elif age > 100:
            await update.message.reply_text(
                "Пожалуйста, укажите корректную дату рождения.",
                reply_markup=get_cancel_keyboard()
            )
            return ASK_AGE
        
        context.user_data['birth_date'] = birth_date
        context.user_data['age'] = age
        
        await update.message.reply_text(
            f"Ваш возраст: {age} лет ✅\n\n"
            "В каком городе вы находитесь?",
            reply_markup=get_cancel_keyboard()
        )
        
        return ASK_CITY
        
    except ValueError:
        await update.message.reply_text(
            "Неверный формат даты. Пожалуйста, используйте формат ДД.ММ.ГГГГ\n"
            "Например: 15.05.1995",
            reply_markup=get_cancel_keyboard()
        )
        return ASK_AGE

async def ask_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Получение города
    """
    if update.message.text == "Отмена":
        return await cancel_registration(update, context)
    
    city = update.message.text.strip()
    
    if len(city) < 2:
        await update.message.reply_text(
            "Пожалуйста, укажите корректное название города.",
            reply_markup=get_cancel_keyboard()
        )
        return ASK_CITY
    
    context.user_data['city'] = city
    
    await update.message.reply_text(
        "Расскажите немного о себе. Что вы любите, чем увлекаетесь?\n"
        "Это поможет другим пользователям узнать вас лучше. (максимум 500 символов)",
        reply_markup=get_cancel_keyboard()
    )
    
    return ASK_BIO

async def ask_bio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Получение описания
    """
    if update.message.text == "Отмена":
        return await cancel_registration(update, context)
    
    bio = update.message.text.strip()
    
    if len(bio) > 500:
        await update.message.reply_text(
            "Описание слишком длинное. Пожалуйста, сократите до 500 символов.",
            reply_markup=get_cancel_keyboard()
        )
        return ASK_BIO
    
    context.user_data['bio'] = bio
    
    await update.message.reply_text(
        "Теперь добавьте фото. Отправьте одно фото для вашей анкеты.\n"
        "Позже вы сможете добавить больше фотографий.",
        reply_markup=get_cancel_keyboard()
    )
    
    return ASK_PHOTO

async def ask_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Получение фото
    """
    if update.message.text == "Отмена":
        return await cancel_registration(update, context)
    
    if not update.message.photo:
        await update.message.reply_text(
            "Пожалуйста, отправьте фото.\n"
            "Вы можете отправить обычное фото, а не файл.",
            reply_markup=get_cancel_keyboard()
        )
        return ASK_PHOTO
    
    # Получаем file_id самого качественного фото
    photo = update.message.photo[-1]
    context.user_data['photo_file_id'] = photo.file_id
    
    await update.message.reply_text(
        "Фото сохранено! 📸\n\n"
        "Теперь укажите, кого вы хотите искать:",
        reply_markup=get_search_gender_keyboard()
    )
    
    return ASK_SEARCH_GENDER

async def ask_search_gender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Получение предпочтений по полу для поиска
    """
    if update.message.text == "Отмена":
        return await cancel_registration(update, context)
    
    gender_map = {
        "Мужской": "male",
        "Женский": "female",
        "Любой": "any"
    }
    
    search_gender_text = update.message.text
    
    if search_gender_text not in gender_map:
        await update.message.reply_text(
            "Пожалуйста, выберите из предложенных вариантов:",
            reply_markup=get_search_gender_keyboard()
        )
        return ASK_SEARCH_GENDER
    
    context.user_data['search_gender'] = gender_map[search_gender_text]
    
    await update.message.reply_text(
        "Укажите минимальный возраст партнера (от 18 до 100):",
        reply_markup=get_cancel_keyboard()
    )
    
    return ASK_SEARCH_AGE_MIN

async def ask_search_age_min(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Получение минимального возраста для поиска
    """
    if update.message.text == "Отмена":
        return await cancel_registration(update, context)
    
    try:
        age_min = int(update.message.text)
        
        if age_min < 18 or age_min > 100:
            await update.message.reply_text(
                "Пожалуйста, укажите возраст от 18 до 100 лет.",
                reply_markup=get_cancel_keyboard()
            )
            return ASK_SEARCH_AGE_MIN
        
        context.user_data['search_age_min'] = age_min
        
        await update.message.reply_text(
            "Укажите максимальный возраст партнера:",
            reply_markup=get_cancel_keyboard()
        )
        
        return ASK_SEARCH_AGE_MAX
        
    except ValueError:
        await update.message.reply_text(
            "Пожалуйста, введите число.",
            reply_markup=get_cancel_keyboard()
        )
        return ASK_SEARCH_AGE_MIN

async def ask_search_age_max(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Получение максимального возраста для поиска
    """
    if update.message.text == "Отмена":
        return await cancel_registration(update, context)
    
    try:
        age_max = int(update.message.text)
        age_min = context.user_data.get('search_age_min')
        
        if age_max < age_min:
            await update.message.reply_text(
                f"Максимальный возраст должен быть не меньше {age_min} лет.",
                reply_markup=get_cancel_keyboard()
            )
            return ASK_SEARCH_AGE_MAX
        
        if age_max > 100:
            await update.message.reply_text(
                "Максимальный возраст не может превышать 100 лет.",
                reply_markup=get_cancel_keyboard()
            )
            return ASK_SEARCH_AGE_MAX
        
        context.user_data['search_age_max'] = age_max
        
        await update.message.reply_text(
            "Укажите максимальное расстояние для поиска (в километрах, от 1 до 500):",
            reply_markup=get_cancel_keyboard()
        )
        
        return ASK_SEARCH_DISTANCE
        
    except ValueError:
        await update.message.reply_text(
            "Пожалуйста, введите число.",
            reply_markup=get_cancel_keyboard()
        )
        return ASK_SEARCH_AGE_MAX

async def ask_search_distance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Получение расстояния для поиска
    """
    if update.message.text == "Отмена":
        return await cancel_registration(update, context)
    
    try:
        distance = int(update.message.text)
        
        if distance < 1 or distance > 500:
            await update.message.reply_text(
                "Пожалуйста, укажите расстояние от 1 до 500 км.",
                reply_markup=get_cancel_keyboard()
            )
            return ASK_SEARCH_DISTANCE
        
        context.user_data['search_distance'] = distance
        
        # Сохраняем анкету в базу данных
        await save_profile(update, context)
        
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text(
            "Пожалуйста, введите число.",
            reply_markup=get_cancel_keyboard()
        )
        return ASK_SEARCH_DISTANCE

async def save_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Сохранение анкеты в базу данных
    """
    from bot.models.database import db_session
    from bot.models.user import User
    from bot.models.profile import Profile
    
    user_data = context.user_data
    
    # Получаем пользователя
    user = UserService.get_user_by_telegram_id(user_data['telegram_id'])
    
    # Создаем профиль
    profile = Profile(
        user_id=user.id,
        gender=user_data['gender'],
        birth_date=user_data['birth_date'],
        city=user_data['city'],
        bio=user_data['bio'],
        search_gender=user_data['search_gender'],
        search_age_min=user_data['search_age_min'],
        search_age_max=user_data['search_age_max'],
        search_distance_km=user_data['search_distance'],
        is_completed=True
    )
    
    db_session.add(profile)
    db_session.commit()
    
    # Здесь нужно будет сохранить фото в отдельную таблицу photos
    # Пока сохраняем только file_id в context
    
    # Поздравляем с регистрацией
    from bot.keyboards.reply_keyboards import get_main_keyboard
    
    await update.message.reply_text(
        "🎉 Поздравляем! Ваша анкета успешно создана!\n\n"
        "Теперь вы можете:\n"
        "• Просматривать анкеты других пользователей\n"
        "• Ставить лайки и находить пару\n"
        "• Общаться в чатах\n\n"
        "Используйте кнопки меню для навигации:",
        reply_markup=get_main_keyboard()
    )
    
    # Очищаем данные пользователя
    context.user_data.clear()

async def cancel_registration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Отмена регистрации
    """
    await update.message.reply_text(
        "Регистрация отменена.\n"
        "Вы можете начать регистрацию позже с помощью команды /register",
        reply_markup=ReplyKeyboardRemove()
    )
    
    context.user_data.clear()
    return ConversationHandler.END