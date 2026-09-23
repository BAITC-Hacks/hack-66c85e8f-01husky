"""Idempotent dev seed: admin user, participants, directions. `uv run python -m app.seed`."""

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Direction, Participant, User
from app.models.enums import UserRole
from app.security import hash_password

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin123"

DIRECTIONS = ["Финансы", "Кадры", "ИТ", "Юридическое", "Закупки", "Производство", "Другое"]

# Participants of the sample recording "Совещание №1" (АО «Самрук-Қазына Ондеу»).
PARTICIPANTS = [
    ("Асхат Ерланович", "askhat@example.com", "Заместитель председателя правления"),
    ("Гульмира Сериковна", "gulmira@example.com", "Директор департамента промышленной политики"),
    ("Тимур Болатович", "timur@example.com", "Директор департамента инвестиций"),
    (
        "Айнур Каировна",
        "ainur@example.com",
        "Руководитель управления взаимодействия с подрядчиками",
    ),
    (
        "Нурлан Сагатович",
        "nurlan@example.com",
        "Руководитель службы охраны труда и промбезопасности",
    ),
]


def run() -> None:
    with SessionLocal() as db:
        admin = db.scalar(select(User).where(User.email == ADMIN_EMAIL))
        if not admin:
            admin = User(
                email=ADMIN_EMAIL,
                password_hash=hash_password(ADMIN_PASSWORD),
                name="Администратор",
                role=UserRole.admin,
            )
            db.add(admin)
        for name in DIRECTIONS:
            if not db.scalar(select(Direction).where(Direction.name == name)):
                db.add(Direction(name=name))
        for name, email, position in PARTICIPANTS:
            if not db.scalar(select(Participant).where(Participant.email == email)):
                db.add(Participant(name=name, email=email, position=position))
        db.commit()
    print(
        f"seed ok: {ADMIN_EMAIL} / {ADMIN_PASSWORD}, {len(PARTICIPANTS)} participants, {len(DIRECTIONS)} directions"
    )


if __name__ == "__main__":
    run()
