import uuid
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Response

from core.auth import (
    compute_premium, create_jwt, get_current_user,
    hash_password, is_configured_admin_email, verify_password,
)
from core.config import (
    ADMIN_EMAIL, ADMIN_PASSWORD, MOCK_DATA, MOCK_USER_EMAIL, MOCK_USER_PASSWORD,
    SUPABASE_ANON_KEY, SUPABASE_URL, utc_now,
)
from core.db import db, get_db, supabase_auth_client, SupabaseDatabase
from schemas.users import LoginInput, RegisterInput, SupabaseSessionInput, User

router = APIRouter()


async def seed_mock_data() -> None:
    existing = await db.users.find_one({"email": MOCK_USER_EMAIL})
    if existing:
        return
    user_id = "user_demo_tomeforge"
    await db.users.insert_one({
        "user_id": user_id, "email": MOCK_USER_EMAIL, "name": "Evocatore Demo",
        "picture": None, "auth_provider": "email", "password_hash": hash_password(MOCK_USER_PASSWORD),
        "is_admin": True, "premium_manual": True, "created_at": utc_now(),
    })
    await db.cards.insert_one({
        "id": "card_demo_flame", "user_id": user_id, "type": "spell",
        "custom_type": None, "name": "Fiamma del Primo Tomo",
        "description": "Una scintilla arcana per provare il grimorio.",
        "story": "La prima carta apparve tra le ceneri di un antico laboratorio.",
        "language": "it", "attributes": {"livello": "2", "scuola": "Invocazione", "danno": "2d6 fuoco"},
        "artwork_path": None, "frame": "gold",
        "back": {"style": "classic", "color": "#7f1d1d", "emblem": "flame", "motto": "Audentes fortuna iuvat"},
        "created_at": utc_now(), "updated_at": utc_now(),
    })


@router.get("/health")
async def health() -> dict:
    from core.config import configuration_status
    status = configuration_status()
    return {"status": "ok" if status["supabase"] and status["jwt"] else "degraded", "services": status}


@router.post("/auth/register")
async def register(body: RegisterInput, db: SupabaseDatabase = Depends(get_db)):
    existing = await db.users.find_one({"email": body.email.lower()})
    if not existing:
        pass
    else:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Email già registrata")
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    is_configured_admin = is_configured_admin_email(body.email)
    document = {
        "user_id": user_id, "email": body.email.lower(), "name": body.name,
        "picture": None, "auth_provider": "email", "password_hash": hash_password(body.password),
        "is_admin": is_configured_admin, "premium_manual": is_configured_admin, "created_at": utc_now(),
    }
    await db.users.insert_one(document)
    user = User(**document)
    return {"token": create_jwt(user_id), "user": {**user.model_dump(), "is_premium": compute_premium(user)}}


@router.post("/auth/login")
async def login(body: LoginInput, db: SupabaseDatabase = Depends(get_db)):
    from fastapi import HTTPException
    document = await db.users.find_one({"email": body.email.lower()})
    if not document or not document.get("password_hash") or not verify_password(body.password, document["password_hash"]):
        raise HTTPException(status_code=401, detail="Credenziali non valide")
    user = User(**document)
    return {"token": create_jwt(user.user_id), "user": {**user.model_dump(), "is_premium": compute_premium(user)}}


@router.get("/auth/me")
async def auth_me(user: User = Depends(get_current_user)):
    return {**user.model_dump(), "is_premium": compute_premium(user)}


@router.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("session_token", path="/")
    return {"ok": True}


@router.get("/auth/google/start")
async def google_start(redirect_to: str):
    """Start Google OAuth using the app's Supabase Auth provider."""
    from fastapi import HTTPException
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise HTTPException(status_code=503, detail="Supabase Auth non configurato")
    auth_url = f"{SUPABASE_URL.rstrip('/')}/auth/v1/authorize?{urlencode({
        'provider': 'google',
        'redirect_to': redirect_to,
    })}"
    return {"url": auth_url}


@router.post("/auth/supabase-session")
async def supabase_session(body: SupabaseSessionInput, db: SupabaseDatabase = Depends(get_db)):
    """Exchange a verified Supabase OAuth token for TomeForge's session token."""
    from fastapi import HTTPException
    try:
        external_user = supabase_auth_client().auth.get_user(body.access_token).user
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Sessione Supabase non valida") from exc
    if not external_user or not external_user.email:
        raise HTTPException(status_code=401, detail="L'account Google non contiene un'email verificata")
    email = external_user.email.lower()
    metadata = external_user.user_metadata or {}
    is_configured_admin = is_configured_admin_email(email)
    existing = await db.users.find_one({"email": email})
    if existing:
        user_id = existing["user_id"]
        await db.users.update_one({"user_id": user_id}, {"$set": {
            "name": metadata.get("full_name") or metadata.get("name") or existing.get("name") or email,
            "picture": metadata.get("avatar_url") or existing.get("picture"),
            "auth_provider": "google",
            "supabase_auth_id": external_user.id,
            **({"is_admin": True, "premium_manual": True} if is_configured_admin else {}),
        }})
        existing.update({
            "supabase_auth_id": external_user.id,
            "auth_provider": "google",
            **({"is_admin": True, "premium_manual": True} if is_configured_admin else {}),
        })
    else:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        existing = {
            "user_id": user_id, "email": email,
            "name": metadata.get("full_name") or metadata.get("name") or email,
            "picture": metadata.get("avatar_url"), "auth_provider": "google",
            "supabase_auth_id": external_user.id, "is_admin": is_configured_admin,
            "premium_manual": is_configured_admin, "created_at": utc_now(),
        }
        await db.users.insert_one(existing)
    user = User(**existing)
    return {"token": create_jwt(user_id), "user": {**user.model_dump(), "is_premium": compute_premium(user)}}
