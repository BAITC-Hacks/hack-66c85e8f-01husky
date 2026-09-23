from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Direction(Base):
    __tablename__ = "directions"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
