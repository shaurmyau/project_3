import logging
from sqlalchemy.exc import IntegrityError
from bot.models.database import db_session
from bot.models.user import User
from bot.models.profile import Profile

logger = logging.getLogger(__name__)

class UserService:
    """Сервис для работы с пользователями"""
    
    @staticmethod
    def get_or_create_user(telegram_id: int, username: str = None, 
                           first_name: str = None, last_name: str = None) -> User:
        """
        Получить или создать пользователя
        
        Args:
            telegram_id: ID пользователя в Telegram
            username: Username пользователя
            first_name: Имя пользователя
            last_name: Фамилия пользователя
            
        Returns:
            User: Объект пользователя
        """
        try:
            user = db_session.query(User).filter_by(telegram_id=telegram_id).first()
            
            if user:
                # Обновляем данные если изменились
                updated = False
                if username and user.username != username:
                    user.username = username
                    updated = True
                if first_name and user.first_name != first_name:
                    user.first_name = first_name
                    updated = True
                if last_name and user.last_name != last_name:
                    user.last_name = last_name
                    updated = True
                
                if updated:
                    db_session.commit()
                    logger.info(f"Updated user {telegram_id}")
            else:
                # Создаем нового пользователя
                user = User(
                    telegram_id=telegram_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name
                )
                db_session.add(user)
                db_session.commit()
                logger.info(f"Created new user {telegram_id}")
            
            return user
            
        except IntegrityError as e:
            db_session.rollback()
            logger.error(f"Error creating user {telegram_id}: {e}")
            raise
        except Exception as e:
            db_session.rollback()
            logger.error(f"Unexpected error in get_or_create_user: {e}")
            raise
    
    @staticmethod
    def get_user_by_telegram_id(telegram_id: int) -> User:
        """Получить пользователя по Telegram ID"""
        return db_session.query(User).filter_by(telegram_id=telegram_id).first()
    
    @staticmethod
    def get_user_profile(user_id: int) -> Profile:
        """Получить профиль пользователя"""
        return db_session.query(Profile).filter_by(user_id=user_id).first()
    
    @staticmethod
    def is_user_registered(telegram_id: int) -> bool:
        """
        Проверить, зарегистрирован ли пользователь (имеет ли заполненную анкету)
        
        Args:
            telegram_id: ID пользователя в Telegram
            
        Returns:
            bool: True если пользователь зарегистрирован, False в противном случае
        """
        user = UserService.get_user_by_telegram_id(telegram_id)
        if not user:
            return False
        
        profile = UserService.get_user_profile(user.id)
        return profile is not None and profile.is_completed
    
    @staticmethod
    def update_user_activity(telegram_id: int):
        """Обновить время последней активности пользователя"""
        user = UserService.get_user_by_telegram_id(telegram_id)
        if user:
            user.updated_at = func.now()
            db_session.commit()