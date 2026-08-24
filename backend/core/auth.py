from datetime import datetime, timezone, timedelta

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request

from core.config import JWT_SECRET, JWT_ALGO, ADMIN_EMAIL
from core.db import get_db, SupabaseDatabase


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_jwt(user_id: str) -> str:
    from core.config import require_jwt_secret
    require_jwt_secret()
    return jwt.encode(
        {"user_id": user_id, "exp": datetime.now(timezone.utc) + timedelta(days=7)},
        JWT_SECRET,
        algorithm=JWT_ALGO,
    )


def is_configured_admin_email(email: str) -> bool:
    return bool(ADMIN_EMAIL and email.lower() == ADMIN_EMAIL.lower())


def compute_premium(user) -> bool:
    if user.premium_manual:
        return True
    if not user.premium_until:
        return False
    try:
        return datetime.fromisoformat(user.premium_until) > datetime.now(timezone.utc)
    except ValueError:
        return False


async def get_current_user(request: Request, db: SupabaseDatabase = Depends(get_db)):
    from schemas.users import User
    token = request.cookies.get("session_token") or request.query_params.get("auth")
    auth = request.headers.get("Authorization")
    if not token and auth and auth.startswith("Bearer "):
        token = auth.split(" ", 1)[1]
    if not token:
        raise HTTPException(status_code=401, detail="Non autenticato")
    from core.config import require_jwt_secret
    require_jwt_secret()
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Token non valido") from exc
    user_doc = await db.users.find_one({"user_id": payload["user_id"]})
    if not user_doc:
        raise HTTPException(status_code=401, detail="Utente non trovato")
    return User(**user_doc)


async def require_premium(user=Depends(get_current_user)):
    if not compute_premium(user):
        raise HTTPException(status_code=402, detail="Funzione Premium: attiva l'abbonamento per usare la generazione AI.")
    return user


async def require_admin(user=Depends(get_current_user)):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Accesso riservato agli admin")
    return user
