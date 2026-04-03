from sqlalchemy import Column, Integer, String, Date, Text, DECIMAL, Boolean, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base

class Profile(Base):
    """Модель анкеты пользователя"""
    __tablename__ = 'profiles'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    gender = Column(String(16))
    birth_date = Column(Date)
    city = Column(String(128))
    latitude = Column(DECIMAL(10, 8))
    longitude = Column(DECIMAL(11, 8))
    bio = Column(Text)
    search_gender = Column(String(16))
    search_age_min = Column(Integer)
    search_age_max = Column(Integer)
    search_distance_km = Column(Integer, default=50)
    is_completed = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", backref="profile")
    
    def __repr__(self):
        return f"<Profile(user_id={self.user_id}, is_completed={self.is_completed})>"