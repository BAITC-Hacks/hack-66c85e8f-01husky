from datetime import datetime

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.enums import Locale, UserRole


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), default=UserRole.user)
    locale: Mapped[Locale] = mapped_column(Enum(Locale, name="locale"), default=Locale.ru)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
