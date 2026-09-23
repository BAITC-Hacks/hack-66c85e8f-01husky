from datetime import UTC, datetime, timedelta

import bcrypt
from jose import JWTError, jwt

from app.config import get_settings

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def create_access_token(user_id: int) -> str:
    s = get_settings()
    exp = datetime.now(UTC) + timedelta(days=s.access_token_days)
    return jwt.encode({"sub": str(user_id), "exp": exp}, s.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> int | None:
    try:
        payload = jwt.decode(token, get_settings().secret_key, algorithms=[ALGORITHM])
        return int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        return None
