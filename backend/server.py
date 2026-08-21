import base64
import asyncio
import io
import json
import logging
import os
import uuid
import copy
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, List, Literal, Optional
from urllib.parse import urlencode

import bcrypt
import jwt
import stripe
import requests
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI, File, Header, HTTPException, Query, Request, Response, UploadFile
from openai import AsyncOpenAI
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from starlette.middleware.cors import CORSMiddleware
from supabase import Client, create_client
from spell_library import (
    extract_spell_records,
    merge_spell_records,
    search_spell_records,
    spell_to_card_payload,
)
from reference_library import (
    CARD_TYPE_BY_REFERENCE_TYPE,
    REFERENCE_TYPES,
    extract_reference_records,
    merge_reference_records,
    reference_to_card_payload,
    search_reference_records,
)

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("tomeforge")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
MOCK_DATA = os.getenv("MOCK_DATA", "").lower() in {"1", "true", "yes"}
MOCK_USER_EMAIL = "demo@example.com"
MOCK_USER_PASSWORD = "tomeforge-demo"
SUPABASE_STORAGE_BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "tomeforge-assets")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_TEXT_MODEL = os.getenv("OPENAI_TEXT_MODEL", "gpt-4o-mini")
OPENAI_IMAGE_MODEL = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1")
# Artwork cleanup is an optional, per-generation feature. Deployments can disable
# it entirely with ARTWORK_CLEANUP_ENABLED=false to avoid the extra edit pass.
ARTWORK_CLEANUP_ENABLED = os.getenv("ARTWORK_CLEANUP_ENABLED", "true").lower() not in {"0", "false", "no", "off"}
ARTWORK_CLEANUP_MODEL = os.getenv("ARTWORK_CLEANUP_MODEL", OPENAI_IMAGE_MODEL)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_TEXT_MODEL = os.getenv("GEMINI_TEXT_MODEL", "gemini-3.6-flash")
SEGMIND_API_KEY = os.getenv("SEGMIND_API_KEY")
SEGMIND_IMAGE_MODEL = os.getenv("SEGMIND_IMAGE_MODEL", "flux-dev")
JWT_SECRET = os.getenv("JWT_SECRET") or os.getenv("SESSION_SECRET")
JWT_ALGO = "HS256"
PREMIUM_LOOKUP_KEY = "premium_monthly"
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
SPELL_PDF_DIRECTORY = ROOT_DIR.parent / "attached_assets"
REFERENCE_MANUAL_FILENAMES = (
    "Manuale_del_giocatore__1787259882002.pdf",
    "Guida_onnicomprensiva_di_Xanathar__1787259928030.pdf",
    "Calderone-Omnicomprensivo-di-TASHA_1787259976040.pdf",
    "724962906-D-D-5e-Manuale-Del-Dungeon-Master_1787282954664.pdf",
)
OCR_ONLY_REFERENCE_MANUAL_FILENAMES = frozenset({
    "724962906-D-D-5e-Manuale-Del-Dungeon-Master_1787282954664.pdf",
})
OCR_REQUIRED_REFERENCE_PREFIXES = (
    "Manuale_del_giocatore",
    "Calderone-Omnicomprensivo",
)

MIME_TYPES = {
    "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
    "gif": "image/gif", "webp": "image/webp",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def configuration_status() -> dict:
    return {
        "supabase": bool(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY) or MOCK_DATA,
        "supabase_auth": bool(SUPABASE_ANON_KEY) or MOCK_DATA,
        "openai": bool(OPENAI_API_KEY) or MOCK_DATA,
        "gemini": bool(GEMINI_API_KEY) or MOCK_DATA,
        "segmind": bool(SEGMIND_API_KEY) or MOCK_DATA,
        "jwt": bool(JWT_SECRET),
        "stripe": bool(stripe.api_key),
    }


def require_jwt_secret() -> None:
    if not JWT_SECRET:
        raise HTTPException(status_code=503, detail="JWT_SECRET o SESSION_SECRET non configurato")


class SupabaseCursor:
    def __init__(self, collection: "SupabaseCollection", query: dict, projection: Optional[dict]):
        self.collection = collection
        self.query = query
        self.projection = projection
        self.order_field: Optional[str] = None
        self.order_desc = False

    def sort(self, field: str, direction: int) -> "SupabaseCursor":
        self.order_field = field
        self.order_desc = direction < 0
        return self

    async def to_list(self, limit: int) -> list[dict]:
        client = self.collection.client
        statement = client.table(self.collection.name).select("*")
        statement = self.collection.apply_filters(statement, self.query)
        if self.order_field:
            statement = statement.order(self.order_field, desc=self.order_desc)
        result = statement.limit(limit).execute()
        return [self.collection.apply_projection(row, self.projection) for row in (result.data or [])]


class UpdateResult:
    def __init__(self, count: int):
        self.matched_count = count
        self.deleted_count = count


class MemoryCursor:
    def __init__(self, rows: list[dict], projection: Optional[dict]):
        self.rows = rows
        self.projection = projection

    def sort(self, field: str, direction: int) -> "MemoryCursor":
        self.rows.sort(key=lambda row: row.get(field, ""), reverse=direction < 0)
        return self

    async def to_list(self, limit: int) -> list[dict]:
        return [
            {key: value for key, value in row.items() if not self.projection or self.projection.get(key, 1) != 0}
            for row in self.rows[:limit]
        ]


class MemoryCollection:
    def __init__(self):
        self.rows: list[dict] = []

    @staticmethod
    def matches(row: dict, query: dict) -> bool:
        for field, value in query.items():
            if isinstance(value, dict) and "$ne" in value:
                if row.get(field) == value["$ne"]:
                    return False
            elif row.get(field) != value:
                return False
        return True

    async def find_one(self, query: dict, projection: Optional[dict] = None) -> Optional[dict]:
        for row in self.rows:
            if self.matches(row, query):
                result = copy.deepcopy(row)
                return {key: value for key, value in result.items() if not projection or projection.get(key, 1) != 0}
        return None

    async def insert_one(self, document: dict) -> None:
        self.rows.append(copy.deepcopy(document))

    async def update_one(self, query: dict, update: dict) -> UpdateResult:
        changes = update.get("$set", update)
        count = 0
        for row in self.rows:
            if self.matches(row, query):
                row.update(copy.deepcopy(changes))
                count += 1
        return UpdateResult(count)

    async def delete_one(self, query: dict) -> UpdateResult:
        for index, row in enumerate(self.rows):
            if self.matches(row, query):
                self.rows.pop(index)
                return UpdateResult(1)
        return UpdateResult(0)

    def find(self, query: dict, projection: Optional[dict] = None) -> MemoryCursor:
        return MemoryCursor(
            [copy.deepcopy(row) for row in self.rows if self.matches(row, query)],
            projection,
        )


class SupabaseCollection:
    def __init__(self, database: "SupabaseDatabase", name: str):
        self.database = database
        self.name = name

    @property
    def client(self) -> Client:
        return self.database.client

    @staticmethod
    def apply_projection(row: dict, projection: Optional[dict]) -> dict:
        if not projection:
            return row
        return {key: value for key, value in row.items() if projection.get(key, 1) != 0}

    @staticmethod
    def apply_filters(statement: Any, query: dict) -> Any:
        for field, value in query.items():
            if isinstance(value, dict):
                if "$ne" in value:
                    statement = statement.neq(field, value["$ne"])
                else:
                    raise HTTPException(status_code=400, detail=f"Filtro non supportato: {field}")
            else:
                statement = statement.eq(field, value)
        return statement

    async def find_one(self, query: dict, projection: Optional[dict] = None) -> Optional[dict]:
        statement = self.apply_filters(self.client.table(self.name).select("*"), query)
        result = statement.limit(1).execute()
        if not result.data:
            return None
        return self.apply_projection(result.data[0], projection)

    async def insert_one(self, document: dict) -> None:
        self.client.table(self.name).insert(document).execute()

    async def update_one(self, query: dict, update: dict) -> UpdateResult:
        changes = update.get("$set", update)
        statement = self.apply_filters(self.client.table(self.name).update(changes), query)
        result = statement.execute()
        return UpdateResult(len(result.data or []))

    async def delete_one(self, query: dict) -> UpdateResult:
        statement = self.apply_filters(self.client.table(self.name).delete(), query)
        result = statement.execute()
        return UpdateResult(len(result.data or []))

    def find(self, query: dict, projection: Optional[dict] = None) -> SupabaseCursor:
        return SupabaseCursor(self, query, projection)


class SupabaseDatabase:
    def __init__(self):
        self._client: Optional[Client] = None
        self._memory: dict[str, MemoryCollection] = {}

    @property
    def configured(self) -> bool:
        return bool(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY) or MOCK_DATA

    @property
    def client(self) -> Client:
        if MOCK_DATA:
            raise HTTPException(status_code=503, detail="Supabase client non disponibile in modalità mock")
        if not self.configured:
            raise HTTPException(status_code=503, detail="Supabase non configurato: aggiungi SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY")
        if self._client is None:
            self._client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        return self._client

    def __getattr__(self, name: str) -> SupabaseCollection:
        if MOCK_DATA:
            if name not in self._memory:
                self._memory[name] = MemoryCollection()
            return self._memory[name]
        return SupabaseCollection(self, name)


db = SupabaseDatabase()
MOCK_OBJECTS: dict[str, tuple[bytes, str]] = {}


def require_openai() -> AsyncOpenAI:
    api_key = (OPENAI_API_KEY or "").strip()
    if not api_key:
        raise HTTPException(status_code=503, detail="OpenAI non configurato: aggiungi OPENAI_API_KEY")
    return AsyncOpenAI(api_key=api_key, timeout=120.0)


def require_segmind() -> str:
    api_key = (SEGMIND_API_KEY or "").strip()
    if not api_key:
        raise HTTPException(status_code=503, detail="Segmind non configurato: aggiungi SEGMIND_API_KEY")
    return api_key


def require_gemini() -> str:
    api_key = (GEMINI_API_KEY or "").strip()
    if not api_key:
        raise HTTPException(status_code=503, detail="Gemini non configurato: aggiungi GEMINI_API_KEY")
    return api_key


def supabase_auth_client() -> Client:
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise HTTPException(status_code=503, detail="Supabase Auth non configurato: aggiungi SUPABASE_URL e SUPABASE_ANON_KEY")
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


def put_object(path: str, data: bytes, content_type: str) -> str:
    if MOCK_DATA:
        MOCK_OBJECTS[path] = (data, content_type)
        return path
    try:
        db.client.storage.from_(SUPABASE_STORAGE_BUCKET).upload(
            path, data, {"content-type": content_type, "upsert": "false"}
        )
        return path
    except Exception as exc:
        logger.exception("Supabase Storage upload failed")
        raise HTTPException(status_code=502, detail=f"Caricamento su Supabase Storage fallito: {exc}") from exc


def get_object(path: str) -> bytes:
    if MOCK_DATA:
        if path not in MOCK_OBJECTS:
            raise HTTPException(status_code=404, detail="File mock non trovato")
        return MOCK_OBJECTS[path][0]
    try:
        return db.client.storage.from_(SUPABASE_STORAGE_BUCKET).download(path)
    except Exception as exc:
        logger.exception("Supabase Storage download failed")
        raise HTTPException(status_code=404, detail="File non trovato nello storage") from exc


class CardBack(BaseModel):
    style: str = "classic"
    color: str = "#7f1d1d"
    emblem: str = "flame"
    motto: str = ""


class CardAppearance(BaseModel):
    title_effect: Literal[
        "gold", "silver", "rainbow", "crimson", "azure",
        "violet", "emerald", "copper", "rose", "arctic",
        "onyx", "amber", "ruby",
    ] = "gold"
    title_shadow: bool = True
    description_opacity: float = Field(default=0.64, ge=0.3, le=0.9)
    text_panel_color: str = "#05080a"
    text_color: str = "#f5f1df"
    front_background_start: str = "#151311"
    front_background_end: str = "#151311"
    front_background_gradient: bool = False
    title_custom_color_enabled: bool = False
    title_custom_color: str = "#f8d764"
    frame_custom_color_enabled: bool = False
    frame_custom_color: str = "#d4af37"


class Card(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    type: str
    custom_type: Optional[str] = None
    name: str = ""
    description: str = ""
    story: str = ""
    language: str = "it"
    attributes: dict = Field(default_factory=dict)
    artwork_path: Optional[str] = None
    frame: str = "gold"
    appearance: CardAppearance = Field(default_factory=CardAppearance)
    back: CardBack = Field(default_factory=CardBack)
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)


class CardCreate(BaseModel):
    type: str
    custom_type: Optional[str] = None
    name: str = ""
    description: str = ""
    story: str = ""
    language: str = "it"
    attributes: dict = Field(default_factory=dict)
    artwork_path: Optional[str] = None
    frame: str = "gold"
    appearance: Optional[CardAppearance] = None
    back: Optional[CardBack] = None


class CardUpdate(BaseModel):
    type: Optional[str] = None
    custom_type: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    story: Optional[str] = None
    language: Optional[str] = None
    attributes: Optional[dict] = None
    artwork_path: Optional[str] = None
    frame: Optional[str] = None
    appearance: Optional[CardAppearance] = None
    back: Optional[CardBack] = None


class RegisterInput(BaseModel):
    email: EmailStr
    password: str
    name: str


class LoginInput(BaseModel):
    email: EmailStr
    password: str


class SupabaseSessionInput(BaseModel):
    access_token: str


class GenerateContentInput(BaseModel):
    type: str
    custom_type: Optional[str] = None
    prompt: str
    language: str = "it"


class SpellImportResult(BaseModel):
    imported: int
    updated: int
    flagged_for_review: int
    skipped: int


class ReferenceImportInput(BaseModel):
    filenames: list[str] = Field(default_factory=list)
    start_page: int = Field(default=5, ge=1)
    end_page: Optional[int] = Field(default=None, ge=1)
    use_ai_ocr: bool = False
    external_processing_confirmed: bool = False


class ReferenceImportResult(BaseModel):
    imported: int
    updated: int
    flagged_for_review: int
    skipped: int
    sources: list[dict]


class ReferenceReviewInput(BaseModel):
    review_status: Literal["pending", "verified", "needs_review"]
    review_notes: str = Field(default="", max_length=3000)


class GenerateImageInput(BaseModel):
    prompt: str
    type: Optional[str] = None
    cleanup: bool = False


class User(BaseModel):
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    auth_provider: str = "email"
    is_admin: bool = False
    premium_manual: bool = False
    premium_until: Optional[str] = None
    supabase_auth_id: Optional[str] = None


app = FastAPI(title="TomeForge API")
api_router = APIRouter(prefix="/api")


@app.on_event("startup")
async def startup() -> None:
    status = configuration_status()
    logger.info("TomeForge configuration: %s", status)
    if MOCK_DATA:
        await seed_mock_data()
        logger.warning("TomeForge is running with MOCK_DATA=true; no external data is used.")
    if not db.configured:
        logger.warning("Supabase is not configured; protected data endpoints will return 503.")
        return
    if ADMIN_EMAIL and ADMIN_PASSWORD:
        existing = await db.users.find_one({"email": ADMIN_EMAIL.lower()})
        payload = {
            "user_id": f"user_{uuid.uuid4().hex[:12]}",
            "email": ADMIN_EMAIL.lower(),
            "name": "Custode del Tomo",
            "picture": None,
            "auth_provider": "email",
            "password_hash": hash_password(ADMIN_PASSWORD),
            "is_admin": True,
            "premium_manual": True,
            "created_at": utc_now(),
        }
        if existing:
            await db.users.update_one({"email": ADMIN_EMAIL.lower()}, {"$set": {"is_admin": True, "premium_manual": True}})
        else:
            await db.users.insert_one(payload)


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


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_jwt(user_id: str) -> str:
    require_jwt_secret()
    return jwt.encode({"user_id": user_id, "exp": datetime.now(timezone.utc) + timedelta(days=7)}, JWT_SECRET, algorithm=JWT_ALGO)


async def get_current_user(request: Request) -> User:
    token = request.cookies.get("session_token") or request.query_params.get("auth")
    auth = request.headers.get("Authorization")
    if not token and auth and auth.startswith("Bearer "):
        token = auth.split(" ", 1)[1]
    if not token:
        raise HTTPException(status_code=401, detail="Non autenticato")
    require_jwt_secret()
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Token non valido") from exc
    user_doc = await db.users.find_one({"user_id": payload["user_id"]})
    if not user_doc:
        raise HTTPException(status_code=401, detail="Utente non trovato")
    return User(**user_doc)


def compute_premium(user: User) -> bool:
    if user.premium_manual:
        return True
    if not user.premium_until:
        return False
    try:
        return datetime.fromisoformat(user.premium_until) > datetime.now(timezone.utc)
    except ValueError:
        return False


def is_configured_admin_email(email: str) -> bool:
    return bool(ADMIN_EMAIL and email.lower() == ADMIN_EMAIL.lower())


async def require_premium(user: User = Depends(get_current_user)) -> User:
    if not compute_premium(user):
        raise HTTPException(status_code=402, detail="Funzione Premium: attiva l'abbonamento per usare la generazione AI.")
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Accesso riservato agli admin")
    return user


@api_router.get("/health")
async def health() -> dict:
    status = configuration_status()
    return {"status": "ok" if status["supabase"] and status["jwt"] else "degraded", "services": status}


@api_router.post("/auth/register")
async def register(body: RegisterInput):
    existing = await db.users.find_one({"email": body.email.lower()})
    if existing:
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


@api_router.post("/auth/login")
async def login(body: LoginInput):
    document = await db.users.find_one({"email": body.email.lower()})
    if not document or not document.get("password_hash") or not verify_password(body.password, document["password_hash"]):
        raise HTTPException(status_code=401, detail="Credenziali non valide")
    user = User(**document)
    return {"token": create_jwt(user.user_id), "user": {**user.model_dump(), "is_premium": compute_premium(user)}}


@api_router.get("/auth/me")
async def auth_me(user: User = Depends(get_current_user)):
    return {**user.model_dump(), "is_premium": compute_premium(user)}


@api_router.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("session_token", path="/")
    return {"ok": True}


@api_router.get("/auth/google/start")
async def google_start(redirect_to: str):
    """Start Google OAuth using the app's Supabase Auth provider."""
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise HTTPException(status_code=503, detail="Supabase Auth non configurato")

    # Build an implicit-flow URL deliberately. The server-side Supabase client
    # generates a PKCE verifier that cannot be recovered by the browser callback,
    # leaving users returned to the login screen without a usable session token.
    auth_url = f"{SUPABASE_URL.rstrip('/')}/auth/v1/authorize?{urlencode({
        'provider': 'google',
        'redirect_to': redirect_to,
    })}"
    return {"url": auth_url}


@api_router.post("/auth/supabase-session")
async def supabase_session(body: SupabaseSessionInput):
    """Exchange a verified Supabase OAuth token for TomeForge's session token."""
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


TYPE_LABELS = {
    "spell": "Magia/Incantesimo", "class": "Classe", "race": "Razza", "weapon": "Arma",
    "armor": "Armatura/Scudo", "item": "Oggetto/Equipaggiamento",
    "feat": "Talento", "monster": "Mostro/Nemico", "character": "Personaggio", "custom": "Tipo personalizzato",
}
TYPE_SCHEMAS = {
    "spell": '"attributes": {"livello": "", "scuola": "", "azione": "", "tempo_lancio": "", "gittata": "", "area": "", "componenti": "", "durata": "", "concentrazione": "", "danno": "", "effetto": ""}',
    "class": '"attributes": {"dado_vita": "", "abilita_primaria": "", "tiri_salvezza": "", "competenze": "", "caratteristiche": []}',
    "race": '"attributes": {"bonus_caratteristiche": "", "velocita": "", "taglia": "", "linguaggi": "", "tratti": []}',
    "weapon": '"attributes": {"danno": "", "tipo_danno": "", "proprieta": "", "peso": "", "costo": "", "categoria": ""}',
    "armor": '"attributes": {"classe_armatura": "", "forza_minima": "", "svantaggio_furtivita": "", "peso": "", "costo": "", "categoria": ""}',
    "item": '"attributes": {"categoria": "", "costo": "", "peso": "", "proprieta": "", "rarita": "", "sintonia": ""}',
    "feat": '"attributes": {"prerequisito": "", "benefici": []}',
    "monster": '"attributes": {"classe_armatura": "", "punti_ferita": "", "velocita": "", "for": "", "des": "", "cos": "", "int": "", "sag": "", "car": "", "azioni": [{"nome": "", "descrizione": ""}]}',
    "character": '"attributes": {"classe": "", "razza": "", "livello": "", "for": "", "des": "", "cos": "", "int": "", "sag": "", "car": "", "slot_incantesimi": []}',
    "custom": '"attributes": {}',
}
LANGUAGES = {"it": "Italiano", "en": "English", "es": "Spanish", "de": "German"}


def parse_ai_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`").removeprefix("json").strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("OpenAI did not return JSON")
    return json.loads(text[start:end + 1])


async def private_spell_records(user_id: str) -> list[dict]:
    """Load only one owner's catalogue; no unauthenticated route calls this."""
    collection = getattr(db, "private_spells", None)
    if collection is None:
        return []
    try:
        return await collection.find({"user_id": user_id}).to_list(3000)
    except Exception as exc:
        # Existing installations can receive the code before the SQL schema is
        # applied. Keep AI generation usable and leave a clear server-side cue.
        if "private_spells" in str(exc):
            logger.warning("Private spell catalogue schema is not available yet")
            return []
        raise


async def find_private_spell(user_id: str, query: str) -> Optional[dict]:
    matches = search_spell_records(await private_spell_records(user_id), query, limit=1)
    return matches[0] if matches else None


async def import_private_spell_pdfs(user_id: str) -> SpellImportResult:
    """Import supplied PDFs into a single private owner's catalogue."""
    pdf_paths = sorted(SPELL_PDF_DIRECTORY.glob("*.pdf"))
    if not pdf_paths:
        raise HTTPException(status_code=404, detail="Nessun PDF degli incantesimi è disponibile per l'importazione")

    extracted_groups = await asyncio.gather(
        *(asyncio.to_thread(extract_spell_records, path) for path in pdf_paths)
    )
    records = merge_spell_records(record for group in extracted_groups for record in group)
    imported = updated = flagged = skipped = 0
    collection = getattr(db, "private_spells", None)
    if collection is None:
        raise HTTPException(status_code=503, detail="Catalogo privato non disponibile")

    for record in records:
        if not record.get("name") or not record.get("description"):
            skipped += 1
            continue
        existing = await collection.find_one({
            "user_id": user_id,
            "normalized_name": record["normalized_name"],
        })
        payload = {
            **record,
            "user_id": user_id,
            "updated_at": utc_now(),
        }
        if existing:
            await collection.update_one({"id": existing["id"], "user_id": user_id}, {"$set": payload})
            updated += 1
        else:
            payload.update({"id": str(uuid.uuid4()), "imported_at": utc_now()})
            await collection.insert_one(payload)
            imported += 1
        flagged += bool(record.get("review_flags"))
    return SpellImportResult(
        imported=imported,
        updated=updated,
        flagged_for_review=flagged,
        skipped=skipped,
    )


def spell_summary(spell: dict) -> dict:
    """A compact result for the picker; full description is detail-only."""
    return {
        "id": spell["id"],
        "name": spell["name"],
        "level": spell.get("level", ""),
        "school": spell.get("school", ""),
        "classes": spell.get("classes", []),
        "casting_time": spell.get("casting_time", ""),
        "range": spell.get("range", ""),
        "needs_review": bool(spell.get("review_flags")),
    }


@api_router.get("/spells")
async def search_private_spells(
    q: str = Query("", max_length=120),
    review_only: bool = False,
    user: User = Depends(get_current_user),
):
    records = search_spell_records(await private_spell_records(user.user_id), q)
    if review_only:
        records = [record for record in records if record.get("review_flags")]
    return {"spells": [spell_summary(record) for record in records]}


@api_router.post("/spells/import", response_model=SpellImportResult)
async def import_private_spells(user: User = Depends(require_admin)):
    """Admin-only local import; it never copies the PDF binaries to storage."""
    try:
        return await import_private_spell_pdfs(user.user_id)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Private spell PDF import failed")
        raise HTTPException(status_code=502, detail="Importazione del Grimorio non riuscita") from exc


@api_router.get("/spells/{spell_id}")
async def get_private_spell(spell_id: str, user: User = Depends(get_current_user)):
    spell = await db.private_spells.find_one({"id": spell_id, "user_id": user.user_id})
    if not spell:
        raise HTTPException(status_code=404, detail="Incantesimo non trovato nel tuo Grimorio")
    return spell


@api_router.post("/spells/{spell_id}/apply")
async def apply_private_spell(spell_id: str, user: User = Depends(get_current_user)):
    spell = await db.private_spells.find_one({"id": spell_id, "user_id": user.user_id})
    if not spell:
        raise HTTPException(status_code=404, detail="Incantesimo non trovato nel tuo Grimorio")
    return {**spell_to_card_payload(spell), "spell_id": spell["id"]}


def available_reference_manuals() -> dict[str, Path]:
    """Whitelist supplied local manuals; callers can never select arbitrary paths."""
    return {
        filename: SPELL_PDF_DIRECTORY / filename
        for filename in REFERENCE_MANUAL_FILENAMES
        if (SPELL_PDF_DIRECTORY / filename).is_file()
    }


def manual_requires_ocr(filename: str) -> bool:
    """Keep the import path and picker metadata consistent for scanned manuals."""
    return (
        filename in OCR_ONLY_REFERENCE_MANUAL_FILENAMES
        or filename.startswith(OCR_REQUIRED_REFERENCE_PREFIXES)
    )


def gemini_ocr_manual_page(page: Any, page_number: int) -> str:
    """Transcribe a private scanned page without persisting the page image."""
    pixmap = page.get_pixmap(matrix=__import__("fitz").Matrix(1.45, 1.45), alpha=False)
    image_b64 = base64.b64encode(pixmap.tobytes("png")).decode("ascii")
    prompt = (
        "Trascrivi fedelmente questa pagina di un manuale di gioco in italiano. "
        "Mantieni titoli in MAIUSCOLO, paragrafi e tabelle leggibili. Non riassumere, "
        "non inventare testo, non aggiungere commenti: restituisci solo la trascrizione."
    )
    try:
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_TEXT_MODEL}:generateContent",
            headers={"x-goog-api-key": require_gemini(), "Content-Type": "application/json"},
            json={
                "contents": [{"parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": "image/png", "data": image_b64}},
                ]}],
                "generationConfig": {"temperature": 0, "maxOutputTokens": 8192},
            },
            timeout=(15, 180),
        )
        response.raise_for_status()
    except requests.HTTPError as exc:
        status_code = getattr(exc.response, "status_code", None)
        logger.warning("OCR Gemini non disponibile per pagina %s (HTTP %s)", page_number, status_code or "errore")
        # Let the extractor retain the page number for a future, explicitly
        # confirmed retry instead of discarding the rest of the import batch.
        return ""
    except requests.RequestException as exc:
        logger.warning("OCR Gemini non raggiungibile per pagina %s: %s", page_number, exc)
        return ""
    try:
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("risposta JSON non oggetto")
        candidates = payload.get("candidates")
        candidate = candidates[0] if isinstance(candidates, list) and candidates else {}
        if not isinstance(candidate, dict):
            raise ValueError("candidato OCR non valido")
        content = candidate.get("content")
        parts = content.get("parts") if isinstance(content, dict) else []
        if not isinstance(parts, list):
            raise ValueError("parti OCR non valide")
        transcription = "\n".join(
            part.get("text", "") for part in parts if isinstance(part, dict) and part.get("text")
        ).strip()
        if transcription:
            return transcription
        finish_reason = candidate.get("finishReason", "sconosciuto")
        logger.warning("OCR Gemini senza testo per pagina %s (motivo: %s)", page_number, finish_reason)
    except (ValueError, TypeError, IndexError, AttributeError) as exc:
        logger.warning("OCR Gemini ha restituito una risposta non leggibile per pagina %s: %s", page_number, exc)
    # Returning an empty value lets the extractor mark only this page for
    # review instead of abandoning the whole user-confirmed batch.
    return ""


async def private_reference_records(user_id: str) -> list[dict]:
    """Load a user's non-spell manual facts only; the source PDFs stay local."""
    collection = getattr(db, "private_reference_records", None)
    if collection is None:
        return []
    try:
        return await collection.find({"user_id": user_id}).to_list(8000)
    except Exception as exc:
        if "private_reference_records" in str(exc):
            logger.warning("Private reference catalogue schema is not available yet")
            return []
        raise


async def find_private_reference(user_id: str, query: str, card_type: Optional[str] = None) -> Optional[dict]:
    records = await private_reference_records(user_id)
    matches = search_reference_records(records, query, limit=20)
    if card_type:
        matches = [record for record in matches if CARD_TYPE_BY_REFERENCE_TYPE.get(record.get("reference_type")) == card_type]
    return matches[0] if matches else None


async def import_private_reference_manuals(user_id: str, body: ReferenceImportInput) -> ReferenceImportResult:
    """Idempotently import selected supplied manuals without uploading their PDFs."""
    manuals = available_reference_manuals()
    requested = body.filenames or list(manuals)
    unknown = sorted(set(requested) - set(manuals))
    if unknown:
        raise HTTPException(status_code=400, detail="Uno o più manuali richiesti non sono disponibili localmente")
    if body.end_page and body.end_page < body.start_page:
        raise HTTPException(status_code=400, detail="L'intervallo di pagine non è valido")
    if body.use_ai_ocr:
        if not body.external_processing_confirmed:
            raise HTTPException(
                status_code=400,
                detail="Conferma esplicitamente l'invio delle sole pagine selezionate a Gemini per l'OCR",
            )
        if len(requested) != 1:
            raise HTTPException(status_code=400, detail="L'OCR può elaborare un solo manuale per volta")
        if body.end_page is None:
            raise HTTPException(
                status_code=400,
                detail="Per l'OCR seleziona un piccolo intervallo di pagine (massimo 12) così l'importazione resta verificabile",
            )
        if body.end_page - body.start_page + 1 > 12:
            raise HTTPException(status_code=400, detail="L'OCR Gemini è limitato a 12 pagine per importazione")

    all_records: list[dict] = []
    source_reports: list[dict] = []
    ocr_callback = gemini_ocr_manual_page if body.use_ai_ocr else None
    for filename in requested:
        report = await asyncio.to_thread(
            extract_reference_records,
            manuals[filename],
            ocr_callback,
            body.start_page,
            body.end_page,
            manual_requires_ocr(filename),
        )
        all_records.extend(report.records)
        source_reports.append({
            "filename": filename,
            "pages_read": report.pages_read,
            "pages_needing_ocr": report.pages_needing_ocr,
            "records_detected": len(report.records),
        })

    collection = getattr(db, "private_reference_records", None)
    if collection is None:
        raise HTTPException(status_code=503, detail="Biblioteca privata non disponibile: applica prima la migrazione SQL")

    imported = updated = flagged = skipped = 0
    for record in merge_reference_records(all_records):
        if not record.get("name") or not record.get("full_text"):
            skipped += 1
            continue
        existing = await collection.find_one({
            "user_id": user_id,
            "reference_type": record["reference_type"],
            "normalized_name": record["normalized_name"],
        })
        owned_record_id = uuid.uuid5(uuid.NAMESPACE_URL, f"{user_id}:{record['id']}").hex
        payload = {
            **record,
            # Source-derived IDs are stable inside a source page but must not
            # collide when two separate owners import the same manual.
            "id": f"ref_{owned_record_id}",
            "user_id": user_id,
            "review_status": "needs_review" if record.get("review_flags") else "pending",
            "review_notes": "",
            "updated_at": utc_now(),
        }
        if existing:
            # Human verification must survive a repeatable import.
            payload["review_status"] = existing.get("review_status", payload["review_status"])
            payload["review_notes"] = existing.get("review_notes", "")
            await collection.update_one({"id": existing["id"], "user_id": user_id}, {"$set": payload})
            updated += 1
        else:
            payload["imported_at"] = utc_now()
            await collection.insert_one(payload)
            imported += 1
        flagged += bool(record.get("review_flags"))
    return ReferenceImportResult(
        imported=imported,
        updated=updated,
        flagged_for_review=flagged,
        skipped=skipped,
        sources=source_reports,
    )


def reference_summary(record: dict) -> dict:
    return {
        "id": record["id"],
        "name": record["name"],
        "reference_type": record.get("reference_type", "other"),
        "attributes": record.get("attributes", {}),
        "source_refs": record.get("source_refs", []),
        "needs_review": bool(record.get("review_flags")) or record.get("review_status") == "needs_review",
    }


@api_router.get("/library/manuals")
async def private_library_manuals(user: User = Depends(require_premium)):
    """Return local import metadata only, never the manual files or page text."""
    records = await private_reference_records(user.user_id)
    manuals = []
    for filename, path in available_reference_manuals().items():
        source_records = [
            record for record in records
            if any(ref.get("filename") == filename for ref in record.get("source_refs", []))
        ]
        try:
            import fitz
            document = fitz.open(path)
            page_count = len(document)
            document.close()
        except Exception:
            page_count = None
        manuals.append({
            "filename": filename,
            "page_count": page_count,
            "imported_records": len(source_records),
            "requires_ocr": manual_requires_ocr(filename),
        })
    return {"manuals": manuals, "ocr_batch_limit": 12}


@api_router.get("/library")
async def search_private_library(
    q: str = Query("", max_length=120),
    types: str = Query("", max_length=200),
    review_only: bool = False,
    user: User = Depends(get_current_user),
):
    requested_types = {value.strip() for value in types.split(",") if value.strip()}
    if requested_types - set(REFERENCE_TYPES):
        raise HTTPException(status_code=400, detail="Tipo di contenuto non valido")
    records = search_reference_records(await private_reference_records(user.user_id), q, limit=40)
    if requested_types:
        records = [record for record in records if record.get("reference_type") in requested_types]
    if review_only:
        records = [record for record in records if record.get("review_flags") or record.get("review_status") == "needs_review"]
    return {"records": [reference_summary(record) for record in records]}


@api_router.post("/library/import", response_model=ReferenceImportResult)
async def import_private_library(body: ReferenceImportInput, user: User = Depends(require_premium)):
    """Per-account, resumable import. OCR is explicit because it calls Gemini."""
    try:
        return await import_private_reference_manuals(user.user_id, body)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Private manual import failed")
        raise HTTPException(status_code=502, detail="Importazione della biblioteca privata non riuscita") from exc


@api_router.get("/library/{reference_id}")
async def get_private_reference(reference_id: str, user: User = Depends(get_current_user)):
    record = await db.private_reference_records.find_one({"id": reference_id, "user_id": user.user_id})
    if not record:
        raise HTTPException(status_code=404, detail="Contenuto non trovato nella tua biblioteca privata")
    return record


@api_router.post("/library/{reference_id}/apply")
async def apply_private_reference(reference_id: str, user: User = Depends(get_current_user)):
    record = await db.private_reference_records.find_one({"id": reference_id, "user_id": user.user_id})
    if not record:
        raise HTTPException(status_code=404, detail="Contenuto non trovato nella tua biblioteca privata")
    return {**reference_to_card_payload(record), "reference_id": record["id"]}


@api_router.patch("/library/{reference_id}/review")
async def review_private_reference(
    reference_id: str,
    body: ReferenceReviewInput,
    user: User = Depends(require_admin),
):
    record = await db.private_reference_records.find_one({"id": reference_id, "user_id": user.user_id})
    if not record:
        raise HTTPException(status_code=404, detail="Contenuto non trovato nella tua biblioteca privata")
    await db.private_reference_records.update_one(
        {"id": reference_id, "user_id": user.user_id},
        {"$set": {**body.model_dump(), "updated_at": utc_now()}},
    )
    return {"ok": True, "id": reference_id, **body.model_dump()}


@api_router.post("/ai/generate-content")
async def generate_content(body: GenerateContentInput, user: User = Depends(require_premium)):
    if MOCK_DATA:
        return {
            "name": "Eco della Luna (Demo)",
            "description": f"Una creazione simulata per: {body.prompt}.",
            "story": "Il testo dimostrativo appare senza chiamare OpenAI.",
            "attributes": {"livello": "2", "scuola": "Illusione", "azione": "1 azione", "danno": "2d6 psichico"},
        }
    if body.type == "spell":
        spell = await find_private_spell(user.user_id, body.prompt)
        if spell:
            return spell_to_card_payload(spell)
    reference = await find_private_reference(user.user_id, body.prompt, body.type)
    if reference:
        return reference_to_card_payload(reference)
    language = LANGUAGES.get(body.language, "Italiano")
    type_label = body.custom_type if body.type == "custom" and body.custom_type else TYPE_LABELS.get(body.type, body.type)
    prompt = (
        f"Create a balanced Dungeons & Dragons 5e {type_label} card in {language} from: {body.prompt}. "
        f"Return only valid JSON with name, description (maximum 3 sentences), story (maximum 4 sentences), and {TYPE_SCHEMAS.get(body.type, TYPE_SCHEMAS['custom'])}."
    )
    try:
        response = await asyncio.to_thread(
            requests.post,
            f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_TEXT_MODEL}:generateContent",
            headers={
                "x-goog-api-key": require_gemini(),
                "Content-Type": "application/json",
            },
            json={
                "contents": [{"parts": [{
                    "text": (
                        "You are a D&D 5e content designer. Be accurate, imaginative, "
                        "and return JSON only.\n\n" + prompt
                    ),
                }]}],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "temperature": 0.7,
                },
            },
            timeout=(10, 120),
        )
        response.raise_for_status()
        response_data = response.json()
        data = parse_ai_json(
            response_data["candidates"][0]["content"]["parts"][0]["text"]
        )
        return {"name": data.get("name", ""), "description": data.get("description", ""), "story": data.get("story", ""), "attributes": data.get("attributes", {})}
    except HTTPException:
        raise
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="Gemini ha restituito un formato non valido") from exc
    except requests.HTTPError as exc:
        status_code = getattr(exc.response, "status_code", None)
        if status_code == 429:
            raise HTTPException(
                status_code=429,
                detail="Gemini ha raggiunto il limite gratuito temporaneo. Riprova più tardi.",
            ) from exc
        logger.exception("Gemini content generation failed")
        raise HTTPException(status_code=502, detail="Errore nella generazione testo Gemini") from exc
    except Exception as exc:
        logger.exception("Gemini content generation failed")
        raise HTTPException(status_code=502, detail="Errore nella generazione testo Gemini") from exc


async def save_file(path: str, data: bytes, content_type: str, user_id: str, original_filename: Optional[str] = None) -> str:
    stored_path = put_object(path, data, content_type)
    await db.files.insert_one({
        "id": str(uuid.uuid4()), "storage_path": stored_path, "user_id": user_id,
        "original_filename": original_filename, "content_type": content_type,
        "is_deleted": False, "created_at": utc_now(),
    })
    return stored_path


ARTWORK_CLEANUP_PROMPT = (
    "Clean this artwork before it is saved. Remove any visible decorative signature, "
    "watermark, logo, artist mark, text, letters, numbers, or readable glyphs that may "
    "have been added by the image model. Preserve the original subject, pose, composition, "
    "lighting, colors, and portrait aspect ratio. Do not add any new writing or change the "
    "artwork into a card, poster, cover, banner, or interface. Return only the cleaned artwork."
)


def _artwork_input_filename(content_type: str) -> str:
    extension = {
        "image/jpeg": "jpg",
        "image/webp": "webp",
        "image/gif": "gif",
    }.get(content_type, "png")
    return f"artwork.{extension}"


async def cleanup_artwork(data: bytes, content_type: str) -> tuple[bytes, str]:
    """Remove model-added marks before artwork reaches storage."""
    if not ARTWORK_CLEANUP_ENABLED:
        return data, content_type
    if not data or not content_type.startswith("image/"):
        raise ValueError("Cannot clean an empty or non-image artwork")

    client = require_openai()
    image_file = io.BytesIO(data)
    image_file.name = _artwork_input_filename(content_type)
    response = await client.images.edit(
        model=ARTWORK_CLEANUP_MODEL,
        image=image_file,
        prompt=ARTWORK_CLEANUP_PROMPT,
    )
    result = response.data[0] if response.data else None
    image_value = result.get("b64_json") if isinstance(result, dict) else getattr(result, "b64_json", None)
    if image_value:
        cleaned_data = base64.b64decode(image_value)
        return cleaned_data, "image/png"

    image_url = result.get("url") if isinstance(result, dict) else getattr(result, "url", None)
    if image_url:
        image_response = await asyncio.to_thread(requests.get, image_url, timeout=(10, 120))
        image_response.raise_for_status()
        cleaned_content_type = image_response.headers.get("content-type", "image/png").split(";", 1)[0].lower()
        if not cleaned_content_type.startswith("image/"):
            raise ValueError("OpenAI cleanup did not return an image")
        return image_response.content, cleaned_content_type

    raise ValueError("OpenAI cleanup did not return image data")


def require_artwork_cleanup() -> None:
    """Confirm that the optional cleanup pass can run for this request."""
    if not ARTWORK_CLEANUP_ENABLED:
        raise HTTPException(
            status_code=503,
            detail="La pulizia opzionale di firme e filigrane non è disponibile su questo server.",
        )
    if MOCK_DATA:
        raise HTTPException(
            status_code=503,
            detail="La pulizia opzionale di firme e filigrane non è disponibile nella modalità demo.",
        )
    if not (OPENAI_API_KEY or "").strip():
        raise HTTPException(
            status_code=503,
            detail="La pulizia opzionale di firme e filigrane non è configurata su questo server.",
        )


async def save_artwork(
    path: str,
    data: bytes,
    content_type: str,
    user_id: str,
    original_filename: Optional[str] = None,
    *,
    cleanup: bool = False,
) -> tuple[str, Optional[str]]:
    """Validate and persist generated artwork, optionally cleaning model-added marks."""
    cleanup_notice = None
    if cleanup:
        try:
            require_artwork_cleanup()
            data, content_type = await cleanup_artwork(data, content_type)
        except Exception as exc:
            logger.warning("Artwork cleanup skipped; preserving original artwork: %s", exc)
            cleanup_notice = "Artwork generato, ma la pulizia di firme e filigrane non è riuscita. L’immagine originale è stata salvata."
        else:
            if not data or not content_type.startswith("image/"):
                raise HTTPException(status_code=502, detail="La pulizia non ha restituito un'immagine valida")

    extension = {
        "image/jpeg": "jpg",
        "image/webp": "webp",
        "image/png": "png",
    }.get(content_type, "png")
    if cleanup and not cleanup_notice:
        path = f"{path.rsplit('.', 1)[0]}.{extension}" if "." in path.rsplit("/", 1)[-1] else f"{path}.{extension}"
    if cleanup and not cleanup_notice and original_filename:
        cleaned_filename = f"{Path(original_filename).stem}.{extension}"
    else:
        cleaned_filename = original_filename or f"generated.{extension}"
    return await save_file(path, data, content_type, user_id, cleaned_filename), cleanup_notice


@api_router.post("/ai/generate-image")
async def generate_image(body: GenerateImageInput, user: User = Depends(require_premium)):
    if MOCK_DATA:
        # 1x1 transparent PNG: enough for the editor/export flow without fake credentials.
        demo_png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")
        path = f"artwork/{user.user_id}/{uuid.uuid4()}.png"
        return {"artwork_path": await save_file(path, demo_png, "image/png", user.user_id, "mock-generated.png")}
    type_hint = TYPE_LABELS.get(body.type or "", "")
    prompt = (
        f"Create one art-only dark fantasy illustration depicting: {body.prompt}. "
        f"{'Subject category: ' + type_hint + '. ' if type_hint else ''}"
        "Detailed digital painting, dramatic lighting, obsidian, antique gold and crimson palette, portrait orientation. "
        "This is not a card design, cover, poster, sign, scroll, banner, or interface. "
        "Treat any names in the subject as internal character or place names only; never render them as writing. "
        "Absolutely no typography, words, letters, numbers, readable runes, glyphs, captions, signatures, watermarks, borders, frames, or labels."
    )
    try:
        response = await asyncio.to_thread(
            requests.post,
            f"https://api.segmind.com/v1/{SEGMIND_IMAGE_MODEL}",
            headers={"x-api-key": require_segmind(), "Content-Type": "application/json"},
            json={
                "prompt": prompt,
                "samples": 1,
                "guidance": 3.5,
                "steps": 25,
                "prompt_strength": 0.8,
                "aspect_ratio": "2:3",
                "output_format": "webp",
                "output_quality": 85,
            },
            timeout=(10, 120),
        )
        response.raise_for_status()
        content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
        if content_type.startswith("image/"):
            artwork_data = response.content
        else:
            payload = response.json()
            image_value = payload.get("image") or payload.get("output") or payload.get("url")
            if isinstance(image_value, list):
                image_value = image_value[0] if image_value else None
            if not isinstance(image_value, str) or not image_value:
                raise ValueError("Segmind did not return image data")
            if image_value.startswith(("https://", "http://")):
                image_response = await asyncio.to_thread(requests.get, image_value, timeout=(10, 120))
                image_response.raise_for_status()
                artwork_data = image_response.content
                content_type = image_response.headers.get("content-type", "image/jpeg").split(";", 1)[0].lower()
            else:
                artwork_data = base64.b64decode(image_value.split(",", 1)[-1])
                content_type = "image/png"
        if not artwork_data or not content_type.startswith("image/"):
            raise ValueError("Segmind did not return a usable image")
        extension = {"image/jpeg": "jpg", "image/webp": "webp", "image/png": "png"}.get(content_type, "png")
        path = f"artwork/{user.user_id}/{uuid.uuid4()}.{extension}"
        artwork_path, cleanup_notice = await save_artwork(
            path,
            artwork_data,
            content_type,
            user.user_id,
            f"segmind-generated.{extension}",
            cleanup=body.cleanup,
        )
        result = {"artwork_path": artwork_path}
        if cleanup_notice:
            result["cleanup_notice"] = cleanup_notice
        return result
    except HTTPException:
        raise
    except requests.RequestException as exc:
        logger.exception("Segmind image generation failed")
        raise HTTPException(status_code=502, detail="Segmind non ha potuto generare l'immagine") from exc
    except Exception as exc:
        logger.exception("Segmind image processing failed")
        raise HTTPException(status_code=502, detail="Segmind ha restituito un'immagine non valida") from exc


@api_router.post("/upload")
async def upload(file: UploadFile = File(...), user: User = Depends(get_current_user)):
    ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename and "." in file.filename else "png"
    content_type = MIME_TYPES.get(ext, file.content_type or "application/octet-stream")
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Carica un file immagine valido")
    data = await file.read()
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="L'immagine supera il limite di 10 MB")
    path = f"uploads/{user.user_id}/{uuid.uuid4()}.{ext}"
    return {"artwork_path": await save_file(path, data, content_type, user.user_id, file.filename)}


@api_router.get("/files/{path:path}")
async def download(path: str, user: User = Depends(get_current_user)):
    record = await db.files.find_one({"storage_path": path, "is_deleted": False})
    if not record or record["user_id"] != user.user_id:
        raise HTTPException(status_code=404, detail="File non trovato")
    return Response(content=get_object(path), media_type=record.get("content_type", "application/octet-stream"))


@api_router.post("/cards", response_model=Card)
async def create_card(body: CardCreate, user: User = Depends(get_current_user)):
    card = Card(user_id=user.user_id, **body.model_dump(exclude_none=True))
    await db.cards.insert_one(card.model_dump())
    return card


@api_router.get("/cards", response_model=List[Card])
async def list_cards(type: Optional[str] = None, search: Optional[str] = None, user: User = Depends(get_current_user)):
    cards = await db.cards.find({"user_id": user.user_id}).sort("created_at", -1).to_list(1000)
    if type and type != "all":
        cards = [card for card in cards if card.get("type") == type]
    if search:
        needle = search.casefold()
        cards = [card for card in cards if needle in card.get("name", "").casefold()]
    return [Card(**card) for card in cards]


@api_router.get("/cards/{card_id}", response_model=Card)
async def get_card(card_id: str, user: User = Depends(get_current_user)):
    card = await db.cards.find_one({"id": card_id, "user_id": user.user_id})
    if not card:
        raise HTTPException(status_code=404, detail="Carta non trovata")
    return Card(**card)


@api_router.put("/cards/{card_id}", response_model=Card)
async def update_card(card_id: str, body: CardUpdate, user: User = Depends(get_current_user)):
    card = await db.cards.find_one({"id": card_id, "user_id": user.user_id})
    if not card:
        raise HTTPException(status_code=404, detail="Carta non trovata")
    updates = body.model_dump(exclude_none=True)
    updates["updated_at"] = utc_now()
    await db.cards.update_one({"id": card_id, "user_id": user.user_id}, {"$set": updates})
    card.update(updates)
    return Card(**card)


@api_router.delete("/cards/{card_id}")
async def delete_card(card_id: str, user: User = Depends(get_current_user)):
    result = await db.cards.delete_one({"id": card_id, "user_id": user.user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Carta non trovata")
    return {"ok": True}


@api_router.get("/public/cards/{card_id}")
async def public_get_card(card_id: str):
    card = await db.cards.find_one({"id": card_id}, {"user_id": 0})
    if not card:
        raise HTTPException(status_code=404, detail="Carta non trovata")
    return card


@api_router.get("/public/files/{path:path}")
async def public_download(path: str):
    record = await db.files.find_one({"storage_path": path, "is_deleted": False})
    if not record:
        raise HTTPException(status_code=404, detail="File non trovato")
    return Response(content=get_object(path), media_type=record.get("content_type", "application/octet-stream"))


class PremiumToggle(BaseModel):
    enabled: bool


@api_router.get("/admin/users")
async def admin_list_users(admin: User = Depends(require_admin)):
    users = await db.users.find({}, {"password_hash": 0}).sort("created_at", -1).to_list(1000)
    return [{**item, "is_premium": compute_premium(User(**item))} for item in users]


@api_router.post("/admin/users/{uid}/premium")
async def admin_set_premium(uid: str, body: PremiumToggle, admin: User = Depends(require_admin)):
    result = await db.users.update_one({"user_id": uid}, {"$set": {"premium_manual": body.enabled}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Utente non trovato")
    return {"ok": True}


class CheckoutRequest(BaseModel):
    lookup_key: str = PREMIUM_LOOKUP_KEY
    origin_url: str


def require_stripe() -> None:
    if not stripe.api_key:
        raise HTTPException(status_code=503, detail="Stripe non configurato")


def stripe_field(resource: Any, field: str, default: Any = None) -> Any:
    if isinstance(resource, dict):
        return resource.get(field, default)
    return getattr(resource, field, default)


def premium_until_from_subscription(subscription: Any) -> Optional[str]:
    period_end = stripe_field(subscription, "current_period_end")
    if period_end is None:
        items = stripe_field(subscription, "items", {})
        data = stripe_field(items, "data", [])
        if data:
            period_end = stripe_field(data[0], "current_period_end")
    if not period_end:
        return None
    return datetime.fromtimestamp(int(period_end), tz=timezone.utc).isoformat()


async def sync_subscription_entitlement(subscription_id: str, fallback_user_id: Optional[str] = None) -> Optional[str]:
    """Synchronize Premium access from Stripe's actual subscription period."""
    subscription = stripe.Subscription.retrieve(subscription_id)
    metadata = stripe_field(subscription, "metadata", {}) or {}
    user_id = stripe_field(metadata, "user_id") or fallback_user_id
    premium_until = premium_until_from_subscription(subscription)
    if not user_id or not premium_until:
        logger.warning("Could not sync Stripe subscription %s: missing user or period end", subscription_id)
        return None
    await db.users.update_one(
        {"user_id": user_id},
        {"$set": {
            "premium_until": premium_until,
            "stripe_subscription_id": subscription_id,
            "stripe_customer_id": stripe_field(subscription, "customer"),
        }},
    )
    return user_id


async def revoke_subscription_entitlement(subscription: Any) -> Optional[str]:
    metadata = stripe_field(subscription, "metadata", {}) or {}
    user_id = stripe_field(metadata, "user_id")
    if not user_id:
        return None
    await db.users.update_one(
        {"user_id": user_id},
        {"$set": {
            "premium_until": datetime.now(timezone.utc).isoformat(),
            "stripe_subscription_id": None,
        }},
    )
    return user_id


@api_router.post("/payments/checkout")
async def create_checkout(req: CheckoutRequest, user: User = Depends(get_current_user)):
    require_stripe()
    prices = stripe.Price.list(lookup_keys=[req.lookup_key], active=True, limit=1).data
    if not prices:
        raise HTTPException(status_code=500, detail="Piano non trovato")
    price = prices[0]
    session = stripe.checkout.Session.create(
        line_items=[{"price": price.id, "quantity": 1}], mode="subscription",
        success_url=f"{req.origin_url}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{req.origin_url}/payment/cancel",
        metadata={"user_id": user.user_id, "lookup_key": req.lookup_key},
        subscription_data={"metadata": {"user_id": user.user_id}},
    )
    await db.payment_transactions.insert_one({
        "session_id": session.id, "user_id": user.user_id, "lookup_key": req.lookup_key,
        "amount": price.unit_amount or 0, "currency": price.currency, "status": "initiated",
        "payment_status": "pending", "stripe_subscription_id": None,
        "created_at": utc_now(), "updated_at": utc_now(),
    })
    return {"checkout_url": session.url, "session_id": session.id}


@api_router.get("/payments/status/{session_id}")
async def payment_status(session_id: str, user: User = Depends(get_current_user)):
    record = await db.payment_transactions.find_one({"session_id": session_id, "user_id": user.user_id})
    if not record:
        raise HTTPException(status_code=404, detail="Transazione non trovata")
    if stripe.api_key:
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            payment = stripe_field(session, "payment_status", record["payment_status"])
            status = stripe_field(session, "status", record["status"])
            subscription_id = stripe_field(session, "subscription")
            updates = {"status": status, "payment_status": payment, "updated_at": utc_now()}
            if subscription_id:
                updates["stripe_subscription_id"] = subscription_id
            await db.payment_transactions.update_one({"session_id": session_id, "user_id": user.user_id}, {"$set": updates})
            if payment == "paid" and subscription_id:
                await sync_subscription_entitlement(subscription_id, user.user_id)
            record.update(updates)
        except stripe.error.StripeError:
            logger.warning("Stripe status reconciliation failed for checkout session %s", session_id, exc_info=True)
    return {"session_id": record["session_id"], "status": record["status"], "payment_status": record["payment_status"]}


@api_router.post("/stripe/webhook")
async def stripe_webhook(request: Request):
    require_stripe()
    try:
        event = stripe.Webhook.construct_event(await request.body(), request.headers.get("stripe-signature", ""), STRIPE_WEBHOOK_SECRET)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Firma Stripe non valida") from exc
    event_type = event["type"]
    resource = event["data"]["object"]
    try:
        if event_type == "checkout.session.completed":
            session_id = stripe_field(resource, "id")
            subscription_id = stripe_field(resource, "subscription")
            updates = {
                "status": stripe_field(resource, "status", "completed"),
                "payment_status": stripe_field(resource, "payment_status", "paid"),
                "updated_at": utc_now(),
            }
            if subscription_id:
                updates["stripe_subscription_id"] = subscription_id
            await db.payment_transactions.update_one({"session_id": session_id}, {"$set": updates})
            if subscription_id:
                metadata = stripe_field(resource, "metadata", {}) or {}
                await sync_subscription_entitlement(subscription_id, stripe_field(metadata, "user_id"))
        elif event_type in {"invoice.paid", "invoice.payment_succeeded"}:
            subscription_id = stripe_field(resource, "subscription")
            if subscription_id:
                await sync_subscription_entitlement(subscription_id)
        elif event_type == "customer.subscription.deleted":
            await revoke_subscription_entitlement(resource)
    except stripe.error.StripeError:
        logger.exception("Stripe lifecycle sync failed for event %s", event_type)
        raise HTTPException(status_code=502, detail="Impossibile sincronizzare l'abbonamento Stripe")
    return {"status": "ok"}


@api_router.get("/")
async def root():
    return {"message": "TomeForge API", "health": "/api/health"}


app.include_router(api_router)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=[origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:5000,http://127.0.0.1:5000").split(",")],
    allow_origin_regex=r"https://.*\.replit\.dev",
    allow_methods=["*"],
    allow_headers=["*"],
)