import base64
import asyncio
import io
import json
import logging
import os
import re
import uuid
import copy
import time
from datetime import datetime, timezone, timedelta
from hashlib import sha256
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
    clean_text,
    compact_text,
    extract_reference_records,
    merge_reference_records,
    normalize_reference_name,
    reference_content_fingerprint,
    reference_is_trusted,
    reference_review_reason,
    reference_review_state,
    reference_rule_source,
    reference_snapshot,
    reference_snapshot_change_fields,
    reference_snapshot_changed,
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
GEMINI_TEXT_MODEL = os.getenv("GEMINI_TEXT_MODEL", "gemini-2.0-flash")
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
    "731764731-D-D-Manual-Del-Jugador-5e_1787286581630.pdf",
    "847921086-Manuale-Dei-Mostri-5e_ok_1787286581630.pdf",
    "Bardo__1787233073462.pdf",
    "Chierico_1787233073462.pdf",
    "Druido__1787233073462.pdf",
    "Mago__1787233073462.pdf",
    "Paladino__1787233073462.pdf",
    "Ranger__1787233073462.pdf",
    "Stregone__1787233073462.pdf",
    "Warlock__1787233073462.pdf",
)
REFERENCE_MANUAL_METADATA = {
    "731764731-D-D-Manual-Del-Jugador-5e_1787286581630.pdf": {
        "title": "Manual del Jugador",
        "language": "es",
        "native_text": True,
    },
}
# A parser revision is part of a source fingerprint only when a supplied
# manual needs a targeted re-index. This lets completed owner queues pick up
# improved recognition without needlessly rerunning unrelated manuals.
REFERENCE_MANUAL_PARSER_REVISIONS = {
    "731764731-D-D-Manual-Del-Jugador-5e_1787286581630.pdf": "character-options-v2",
}
OCR_ONLY_REFERENCE_MANUAL_FILENAMES = frozenset({
    "724962906-D-D-5e-Manuale-Del-Dungeon-Master_1787282954664.pdf",
})
OCR_REQUIRED_REFERENCE_PREFIXES = (
    "Manuale_del_giocatore",
    "Calderone-Omnicomprensivo",
)
MANUAL_COVERAGE_CATEGORIES = {
    "Manuale_del_giocatore__1787259882002.pdf": (
        "class", "subclass", "class_feature", "race", "subrace", "feat", "spell",
        "weapon", "armor", "shield", "equipment", "tool",
    ),
    "731764731-D-D-Manual-Del-Jugador-5e_1787286581630.pdf": (
        "class", "subclass", "class_feature", "race", "subrace", "feat", "spell",
        "weapon", "armor", "shield", "equipment", "tool",
    ),
    "Guida_onnicomprensiva_di_Xanathar__1787259928030.pdf": (
        "subclass", "class_feature", "feat", "spell",
    ),
    "Calderone-Omnicomprensivo-di-TASHA_1787259976040.pdf": (
        "subclass", "class_feature", "feat", "spell", "magic_item",
    ),
    "724962906-D-D-5e-Manuale-Del-Dungeon-Master_1787282954664.pdf": (
        "weapon", "armor", "shield", "equipment", "tool", "magic_item",
        "vehicle", "ammunition", "mount", "trade_good", "service",
    ),
    "847921086-Manuale-Dei-Mostri-5e_ok_1787286581630.pdf": ("monster",),
}
for _class_manual in (
    "Bardo__1787233073462.pdf",
    "Chierico_1787233073462.pdf",
    "Druido__1787233073462.pdf",
    "Mago__1787233073462.pdf",
    "Paladino__1787233073462.pdf",
    "Ranger__1787233073462.pdf",
    "Stregone__1787233073462.pdf",
    "Warlock__1787233073462.pdf",
):
    MANUAL_COVERAGE_CATEGORIES[_class_manual] = ("class", "subclass", "class_feature", "spell")

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
        self.order_fields: list[tuple[str, bool]] = []

    def sort(self, field: str, direction: int) -> "SupabaseCursor":
        self.order_fields.append((field, direction < 0))
        return self

    async def to_list(self, limit: int, offset: int = 0) -> list[dict]:
        client = self.collection.client
        statement = client.table(self.collection.name).select("*")
        statement = self.collection.apply_filters(statement, self.query)
        for field, descending in self.order_fields:
            statement = statement.order(field, desc=descending)
        result = statement.range(offset, offset + limit - 1).execute()
        return [self.collection.apply_projection(row, self.projection) for row in (result.data or [])]


class UpdateResult:
    def __init__(self, count: int):
        self.matched_count = count
        self.deleted_count = count


TRANSLATION_PROCESSING_STATUS = "processing"
TRANSLATION_LEASE_SECONDS = 180
TRANSLATION_WAIT_SECONDS = 135
TRANSLATION_POLL_INTERVAL_SECONDS = 0.05
MANUAL_PRELOAD_PAGE_BATCH_SIZE = 12
MANUAL_PRELOAD_LEASE_SECONDS = 300
MANUAL_PRELOAD_MAX_ATTEMPTS = 3
MANUAL_PRELOAD_ACTIVE_WORKERS: set[str] = set()
# Seconds to wait between successive retries after a provider rate-limit (429).
TRANSLATION_RATE_LIMIT_RETRY_DELAYS: tuple[int, ...] = (30, 60, 120)


class MemoryCursor:
    def __init__(self, rows: list[dict], projection: Optional[dict]):
        self.rows = rows
        self.projection = projection
        self.order_fields: list[tuple[str, int]] = []

    def sort(self, field: str, direction: int) -> "MemoryCursor":
        self.order_fields.append((field, direction))
        return self

    async def to_list(self, limit: int, offset: int = 0) -> list[dict]:
        for field, direction in reversed(self.order_fields):
            self.rows.sort(key=lambda row: row.get(field, ""), reverse=direction < 0)
        return [
            {key: value for key, value in row.items() if not self.projection or self.projection.get(key, 1) != 0}
            for row in self.rows[offset:offset + limit]
        ]


class MemoryCollection:
    def __init__(self):
        self.rows: list[dict] = []

    @staticmethod
    def matches(row: dict, query: dict) -> bool:
        for field, value in query.items():
            if field == "$or":
                if not isinstance(value, list) or not any(MemoryCollection.matches(row, option) for option in value):
                    return False
            elif isinstance(value, dict) and "$ne" in value:
                if row.get(field) == value["$ne"]:
                    return False
            elif isinstance(value, dict) and "$lt" in value:
                if row.get(field) is None or row.get(field) >= value["$lt"]:
                    return False
            elif isinstance(value, dict) and "$in" in value:
                if not isinstance(value["$in"], list) or row.get(field) not in value["$in"]:
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

    async def insert_many(self, documents: list[dict]) -> None:
        # Copy every document before changing the collection so the in-memory
        # implementation has the same all-or-nothing behavior as Supabase's
        # multi-row insert.
        copies = [copy.deepcopy(document) for document in documents]
        self.rows.extend(copies)

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
            if field == "$or":
                if not isinstance(value, list):
                    raise HTTPException(status_code=400, detail="Filtro OR non valido")
                clauses = []
                for option in value:
                    option_clauses = []
                    for option_field, option_value in option.items():
                        if isinstance(option_value, dict) and "$lt" in option_value:
                            option_clauses.append(f"{option_field}.lt.{option_value['$lt']}")
                        elif not isinstance(option_value, dict):
                            option_clauses.append(f"{option_field}.eq.{option_value}")
                        else:
                            raise HTTPException(status_code=400, detail=f"Filtro non supportato: {option_field}")
                    clauses.append(
                        option_clauses[0] if len(option_clauses) == 1
                        else f"and({','.join(option_clauses)})"
                    )
                statement = statement.or_(",".join(clauses))
            elif isinstance(value, dict):
                if "$ne" in value:
                    statement = statement.neq(field, value["$ne"])
                elif "$lt" in value:
                    statement = statement.lt(field, value["$lt"])
                elif "$in" in value:
                    if not isinstance(value["$in"], list):
                        raise HTTPException(status_code=400, detail=f"Filtro non valido: {field}")
                    statement = statement.in_(field, value["$in"])
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

    async def insert_many(self, documents: list[dict]) -> None:
        if documents:
            # PostgREST sends this as one PostgreSQL INSERT statement. A
            # constraint or persistence error therefore rolls back the whole
            # set instead of leaving earlier rows behind.
            self.client.table(self.name).insert(documents).execute()

    async def update_one(self, query: dict, update: dict) -> UpdateResult:
        changes = update.get("$set", update)
        statement = self.apply_filters(self.client.table(self.name).update(changes), query)
        # Ask PostgREST to return the changed rows so conditional updates can
        # be used as atomic claims by callers.
        result = statement.select("id").execute()
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
    reference_ids: list[str] = Field(default_factory=list)
    spell_ids: list[str] = Field(default_factory=list)
    rule_sources: list[dict] = Field(default_factory=list)
    source_refs: list[dict] = Field(default_factory=list)
    reference_snapshots: list[dict] = Field(default_factory=list)
    change_history: list[dict] = Field(default_factory=list)
    version: int = 0
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
    reference_ids: list[str] = Field(default_factory=list)
    spell_ids: list[str] = Field(default_factory=list)
    rule_sources: list[dict] = Field(default_factory=list)
    source_refs: list[dict] = Field(default_factory=list)


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
    reference_ids: Optional[list[str]] = None
    spell_ids: Optional[list[str]] = None
    rule_sources: Optional[list[dict]] = None
    source_refs: Optional[list[dict]] = None
    version: int = Field(..., ge=0)


class LinkedCardInput(BaseModel):
    reference_ids: list[str] = Field(default_factory=list)
    version: int = Field(..., ge=0)


class ReferenceUpdateInput(BaseModel):
    reference_ids: list[str] = Field(default_factory=list)
    version: int = Field(..., ge=0)


class ManualCompletionInput(BaseModel):
    """The server derives the eligible fields from the card's own identity."""
    version: int = Field(..., ge=0)


class CardVersionInput(BaseModel):
    version: int = Field(..., ge=0)


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
    translation_processing_confirmed: bool = False
    auto_accept: bool = False
    translation_batch_size: int = Field(default=2, ge=1, le=4)


class ReferenceImportResult(BaseModel):
    imported: int
    updated: int
    flagged_for_review: int
    skipped: int
    sources: list[dict]


class ManualPreloadInput(BaseModel):
    """Automatic preload intent; legacy consent fields remain API-compatible."""
    filename: Optional[str] = None
    enable_translation: bool = False
    enable_ocr: bool = False
    translation_processing_confirmed: bool = False
    external_processing_confirmed: bool = False
    retry: bool = False


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
    await resume_manual_preload_workers()


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
    "feat": "Talento", "feature": "Privilegio di classe", "subclass": "Sottoclasse",
    "monster": "Mostro/Nemico", "character": "Personaggio", "custom": "Tipo personalizzato",
}
TYPE_SCHEMAS = {
    "spell": '"attributes": {"livello": "", "scuola": "", "azione": "", "tempo_lancio": "", "gittata": "", "area": "", "componenti": "", "durata": "", "concentrazione": "", "danno": "", "effetto": ""}',
    "class": '"attributes": {"dado_vita": "", "abilita_primaria": "", "tiri_salvezza": "", "competenze": "", "caratteristiche": []}',
    "subclass": '"attributes": {"dado_vita": "", "abilita_primaria": "", "tiri_salvezza": "", "competenze": "", "caratteristiche": []}',
    "feature": '"attributes": {"livello": "", "benefici": []}',
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
    matches = search_spell_records(await private_spell_records(user_id), query, limit=20)
    return next((spell for spell in matches if reference_is_trusted(spell)), None)


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
        "source_refs": spell.get("source_refs", []),
        "review_status": spell.get("review_status", "pending"),
        "review_state": reference_review_state(spell),
        "is_trusted": reference_is_trusted(spell),
        "needs_review": not reference_is_trusted(spell),
        "review_reason": reference_review_reason(spell),
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
    return spell_summary(spell)


@api_router.post("/spells/{spell_id}/apply")
async def apply_private_spell(spell_id: str, user: User = Depends(get_current_user)):
    spell = await db.private_spells.find_one({"id": spell_id, "user_id": user.user_id})
    if not spell:
        raise HTTPException(status_code=404, detail="Incantesimo non trovato nel tuo Grimorio")
    if not reference_is_trusted(spell):
        raise HTTPException(
            status_code=409,
            detail=reference_review_reason(spell) or "Questo incantesimo è da verificare e non può essere usato come dato certo.",
        )
    return {**spell_to_card_payload(spell), "spell_id": spell["id"]}


def available_reference_manuals() -> dict[str, Path]:
    """Discover supplied PDFs from the fixed local assets directory.

    The client still selects only a filename returned here; it can never pass a
    path.  Keeping the discovery local means a newly supplied manual joins the
    automatic queue without requiring a new server release.
    """
    known = [
        filename for filename in REFERENCE_MANUAL_FILENAMES
        if (SPELL_PDF_DIRECTORY / filename).is_file()
    ]
    known_set = set(known)
    additional = sorted(
        path.name for path in SPELL_PDF_DIRECTORY.glob("*.pdf")
        if path.is_file() and path.name not in known_set
    )
    return {filename: SPELL_PDF_DIRECTORY / filename for filename in [*known, *additional]}


def manual_requires_ocr(filename: str) -> bool:
    """Keep the import path and picker metadata consistent for scanned manuals."""
    return (
        filename in OCR_ONLY_REFERENCE_MANUAL_FILENAMES
        or filename.startswith(OCR_REQUIRED_REFERENCE_PREFIXES)
    )


def manual_source_metadata(filename: str) -> dict:
    """Return only local source metadata; never the source PDF or its text."""
    return {
        "title": Path(filename).stem.replace("_", " "),
        "language": "it",
        "native_text": not manual_requires_ocr(filename),
        **REFERENCE_MANUAL_METADATA.get(filename, {}),
    }


def manual_source_language(filename: str) -> str:
    return manual_source_metadata(filename)["language"]


def manual_source_fingerprint(path: Path) -> str:
    """Detect replacement of a local source without retaining its PDF bytes."""
    stat = path.stat()
    value = f"{path.name}:{stat.st_size}:{stat.st_mtime_ns}"
    parser_revision = REFERENCE_MANUAL_PARSER_REVISIONS.get(path.name)
    if parser_revision:
        value = f"{value}:parser:{parser_revision}"
    return sha256(value.encode("utf-8")).hexdigest()


def manual_page_count(path: Path) -> Optional[int]:
    try:
        import fitz
        document = fitz.open(path)
        page_count = len(document)
        document.close()
        return page_count
    except Exception:
        return None


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


def _gemini_text_from_response(payload: object) -> str:
    """Extract a single text response from Gemini's public response shape."""
    if not isinstance(payload, dict):
        raise ValueError("risposta JSON non oggetto")
    candidates = payload.get("candidates")
    candidate = candidates[0] if isinstance(candidates, list) and candidates else {}
    if not isinstance(candidate, dict):
        raise ValueError("candidato non valido")
    content = candidate.get("content")
    parts = content.get("parts") if isinstance(content, dict) else []
    if not isinstance(parts, list):
        raise ValueError("parti non valide")
    text = "\n".join(
        part.get("text", "") for part in parts if isinstance(part, dict) and part.get("text")
    ).strip()
    if not text:
        raise ValueError("risposta senza testo")
    return text


def _openai_text_from_response(payload: object) -> str:
    """Extract one chat-completion message without accepting partial output."""
    if not isinstance(payload, dict):
        raise ValueError("risposta OpenAI non oggetto")
    choices = payload.get("choices")
    choice = choices[0] if isinstance(choices, list) and choices else {}
    message = choice.get("message") if isinstance(choice, dict) else {}
    content = message.get("content") if isinstance(message, dict) else ""
    if not isinstance(content, str) or not content.strip():
        raise ValueError("risposta OpenAI senza testo")
    return content.strip()


def _json_from_model_text(text: str) -> object:
    """Accept raw JSON or the fenced JSON often returned by text models."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def _openai_translation_response(prompt: str) -> object:
    """Use the user-approved fallback only when Gemini cannot serve a batch."""
    if not OPENAI_API_KEY:
        raise RuntimeError("fallback OpenAI non configurato")
    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": OPENAI_TEXT_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Restituisci esclusivamente il JSON richiesto. "
                        "Non aggiungere testo introduttivo o markdown."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0,
            "max_tokens": 8192,
        },
        timeout=(15, 120),
    )
    response.raise_for_status()
    return _json_from_model_text(_openai_text_from_response(response.json()))


def _is_provider_rate_limited(exc: Exception) -> bool:
    """Return True when *exc* signals an HTTP 429 rate-limit from a provider."""
    return (
        isinstance(exc, requests.HTTPError)
        and getattr(getattr(exc, "response", None), "status_code", None) == 429
    )


def translate_spanish_reference_batch(records: list[dict]) -> tuple[dict[str, dict], str]:
    """Translate a small structured Spanish batch without sending PDF pages.

    The caller preserves the source fields before this function runs. Any
    malformed or incomplete response is returned as a batch failure, allowing
    the import to store the untouched Spanish record for human review.

    When both providers respond with HTTP 429 the error code is
    ``"provider_rate_limited"`` so callers can distinguish a temporary limit
    from a permanent content failure and schedule a deferred retry.
    """
    if not records:
        return {}, ""
    source_records = [
        {
            "id": record["id"],
            "name": record["source_name"],
            "description": record["source_description"],
            "full_text": record["source_full_text"],
            "attributes": record.get("source_attributes", {}),
        }
        for record in records
    ]
    prompt = (
        "Traduci dallo spagnolo all'italiano questi record strutturati di un manuale "
        "di gioco. Traduci soltanto nome, descrizione e valori di attributes; non "
        "aggiungere regole, non riassumere, non omettere dettagli, non alterare ID, "
        "dadi, numeri, prezzi o nomi delle chiavi. full_text deve contenere la "
        "traduzione completa del testo sorgente, senza abbreviazioni. Restituisci esclusivamente JSON "
        "valido nel formato {\"records\":[{\"id\":\"...\",\"name\":\"...\","
        "\"description\":\"...\",\"full_text\":\"...\",\"attributes\":{...}}]}. Ogni ID ricevuto deve "
        "comparire esattamente una volta.\n\n"
        + json.dumps(source_records, ensure_ascii=False, separators=(",", ":"))
    )
    try:
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_TEXT_MODEL}:generateContent",
            headers={"x-goog-api-key": require_gemini(), "Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0,
                    "responseMimeType": "application/json",
                    "maxOutputTokens": 8192,
                },
            },
            timeout=(15, 120),
        )
        response.raise_for_status()
        decoded = _json_from_model_text(_gemini_text_from_response(response.json()))
    except (requests.RequestException, ValueError, TypeError, json.JSONDecodeError) as exc:
        primary_rate_limited = _is_provider_rate_limited(exc)
        logger.warning(
            "Traduzione Gemini non disponibile per un gruppo di %s record: %s; provo OpenAI autorizzato",
            len(records),
            exc,
        )
        try:
            decoded = _openai_translation_response(prompt)
        except (requests.RequestException, RuntimeError, ValueError, TypeError, json.JSONDecodeError) as fallback_exc:
            logger.warning(
                "Traduzione OpenAI non disponibile per un gruppo di %s record: %s",
                len(records),
                fallback_exc,
            )
            # Distinguish a temporary rate limit from a permanent content
            # failure so the caller can schedule a deferred retry instead of
            # immediately flagging the record for human review.
            if primary_rate_limited or _is_provider_rate_limited(fallback_exc):
                return {}, "provider_rate_limited"
            return {}, "provider_translation_failed"

    translated_rows = decoded.get("records") if isinstance(decoded, dict) else None
    if not isinstance(translated_rows, list):
        return {}, "provider_translation_invalid"
    expected_ids = {record["id"] for record in records}
    translated: dict[str, dict] = {}
    for item in translated_rows:
        if not isinstance(item, dict) or item.get("id") not in expected_ids:
            continue
        name = clean_text(str(item.get("name") or ""))
        description = clean_text(str(item.get("description") or ""))
        full_text = clean_text(str(item.get("full_text") or ""))
        attributes = item.get("attributes")
        if name and description and full_text and isinstance(attributes, dict):
            translated[item["id"]] = {
                "name": name,
                "description": compact_text(description),
                "full_text": full_text,
                "attributes": attributes,
            }
    if set(translated) != expected_ids:
        return {}, "provider_translation_incomplete"
    return translated, ""


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


async def private_manual_import_jobs(user_id: str) -> list[dict]:
    """Load only owner-scoped preload metadata, never manual source material."""
    collection = getattr(db, "private_manual_import_jobs", None)
    if collection is None:
        return []
    try:
        return await collection.find({"user_id": user_id}).to_list(200)
    except Exception as exc:
        if "private_manual_import_jobs" in str(exc):
            logger.warning("Automatic manual preload schema is not available yet")
            return []
        raise


async def resolve_reference_provenance(user_id: str, reference_ids: list[str]) -> tuple[list[str], list[dict]]:
    """Validate selected reference records and derive their immutable provenance."""
    requested_ids = list(dict.fromkeys(reference_id for reference_id in reference_ids if reference_id))
    if not requested_ids:
        return [], []
    records_by_id = {
        record["id"]: record
        for record in await private_reference_records(user_id)
        if record.get("id") in requested_ids
    }
    missing = [reference_id for reference_id in requested_ids if reference_id not in records_by_id]
    if missing:
        raise HTTPException(status_code=404, detail="Uno o più riferimenti normativi non sono più disponibili")
    unverified = [
        reference_id for reference_id in requested_ids
        if not reference_is_trusted(records_by_id[reference_id])
    ]
    if unverified:
        raise HTTPException(
            status_code=409,
            detail="Uno o più riferimenti sono da verificare e non possono essere collegati come dati certi.",
        )
    sources: list[dict] = []
    seen_sources: set[str] = set()
    for reference_id in requested_ids:
        for source in records_by_id[reference_id].get("source_refs", []):
            key = json.dumps(source, sort_keys=True, ensure_ascii=False)
            if key not in seen_sources:
                seen_sources.add(key)
                sources.append(source)
    return requested_ids, sources


async def resolve_spell_provenance(user_id: str, spell_ids: list[str]) -> tuple[list[str], list[dict]]:
    """Validate private Grimorio entries and derive their manual/page links."""
    requested_ids = list(dict.fromkeys(spell_id for spell_id in spell_ids if spell_id))
    if not requested_ids:
        return [], []
    records_by_id = {
        spell["id"]: spell
        for spell in await private_spell_records(user_id)
        if spell.get("id") in requested_ids
    }
    missing = [spell_id for spell_id in requested_ids if spell_id not in records_by_id]
    if missing:
        raise HTTPException(status_code=404, detail="Uno o più incantesimi del Grimorio non sono più disponibili")
    unverified = [spell_id for spell_id in requested_ids if not reference_is_trusted(records_by_id[spell_id])]
    if unverified:
        reason = reference_review_reason(records_by_id[unverified[0]])
        raise HTTPException(
            status_code=409,
            detail=reason or "Uno o più incantesimi sono da verificare e non possono essere collegati come dati certi.",
        )
    sources: list[dict] = []
    seen_sources: set[str] = set()
    for spell_id in requested_ids:
        for source in records_by_id[spell_id].get("source_refs", []):
            key = json.dumps(source, sort_keys=True, ensure_ascii=False)
            if key not in seen_sources:
                seen_sources.add(key)
                sources.append(source)
    return requested_ids, sources


def merge_source_refs(*source_groups: list[dict]) -> list[dict]:
    """Merge already-validated source metadata without trusting client input."""
    sources: list[dict] = []
    seen_sources: set[str] = set()
    for source_group in source_groups:
        for source in source_group:
            key = json.dumps(source, sort_keys=True, ensure_ascii=False)
            if key not in seen_sources:
                seen_sources.add(key)
                sources.append(source)
    return sources


async def rule_sources_for_card(user_id: str, reference_ids: list[str], spell_ids: list[str]) -> list[dict]:
    """Build one safe manual/page entry for every server-validated linked rule."""
    references = {
        record["id"]: record
        for record in await private_reference_records(user_id)
        if record.get("id") in reference_ids
    }
    spells = {
        spell["id"]: spell
        for spell in await private_spell_records(user_id)
        if spell.get("id") in spell_ids
    }
    return [
        reference_rule_source(references[reference_id])
        for reference_id in reference_ids
        if reference_id in references
    ] + [
        {
            "source_kind": "spell",
            "source_id": spell_id,
            "name": spells[spell_id].get("name", ""),
            "reference_type": "spell",
            "source_refs": spells[spell_id].get("source_refs", []),
        }
        for spell_id in spell_ids
        if spell_id in spells
    ]


def reference_snapshot_for_card(record: dict, card_type: str, saved_at: str = "") -> dict:
    """Record both source text and the values that were derived from it."""
    snapshot = reference_snapshot(record, saved_at)
    if card_type != "character":
        return snapshot

    payload = reference_to_card_payload(record)
    derived = copy.deepcopy(payload.get("attributes") or {})
    reference_type = record.get("reference_type")
    name = record.get("name", "")
    reference_id = record.get("id", "")
    if reference_type == "class":
        derived["classe"] = name
    elif reference_type in {"race", "subrace"}:
        derived["razza"] = name
    elif reference_type == "subclass":
        derived["sottoclasse"] = name
    else:
        list_field = (
            "privilegi" if reference_type in {"class_feature", "ability", "feat"}
            else "incantesimi" if reference_type == "spell"
            else "equipaggiamento" if reference_type in {
                "weapon", "armor", "shield", "equipment", "tool", "magic_item",
                "vehicle", "ammunition", "mount", "trade_good", "service",
            }
            else ""
        )
        if list_field:
            derived[list_field] = [{
                "reference_id": reference_id,
                "nome": name,
                "descrizione": payload.get("description", ""),
            }]
    snapshot["derived_attributes"] = derived
    snapshot["derived_card_fields"] = {}
    return snapshot


async def reference_records_by_id(user_id: str, reference_ids: list[str]) -> dict[str, dict]:
    requested = set(reference_ids)
    return {
        record["id"]: record
        for record in await private_reference_records(user_id)
        if record.get("id") in requested
    }


def reference_snapshots_for_card(
    existing_snapshots: list[dict],
    records_by_id: dict[str, dict],
    reference_ids: list[str],
    card_type: str,
    saved_at: str,
) -> list[dict]:
    """Keep acknowledged snapshots for existing links; baseline only new links."""
    existing_by_id = {
        snapshot.get("reference_id"): snapshot
        for snapshot in existing_snapshots or []
        if snapshot.get("reference_id")
    }
    snapshots = []
    for reference_id in reference_ids:
        if reference_id in existing_by_id:
            snapshots.append(existing_by_id[reference_id])
        elif reference_id in records_by_id:
            snapshots.append(reference_snapshot_for_card(records_by_id[reference_id], card_type, saved_at))
    return snapshots


def _is_empty_card_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, dict)):
        return not value
    return False


CARD_HISTORY_LIMIT = 20
CARD_HISTORY_FIELDS = (
    "type", "custom_type", "name", "description", "story", "language",
    "attributes", "artwork_path", "frame", "appearance", "back",
    "reference_ids", "spell_ids", "rule_sources", "source_refs", "reference_snapshots",
)


def card_change_patch(before: dict, after: dict) -> tuple[dict, dict, list[str]]:
    """Return small before/after patches rather than duplicating whole cards."""
    previous: dict = {}
    current: dict = {}
    changed: list[str] = []
    for field in CARD_HISTORY_FIELDS:
        before_value = before.get(field)
        after_value = after.get(field)
        if before_value != after_value:
            previous[field] = copy.deepcopy(before_value)
            current[field] = copy.deepcopy(after_value)
            changed.append(field)
    return previous, current, changed


def append_card_history(
    history: list[dict],
    before: dict,
    after: dict,
    source: Literal["user", "manual"],
    action: Literal["update", "reference_update", "manual_completion"],
    reference_ids: Optional[list[str]] = None,
) -> list[dict]:
    """Append an account-owned card change, dropping redo entries after a new edit."""
    previous, current, changed = card_change_patch(before, after)
    if not changed:
        return copy.deepcopy(history or [])
    entry = {
        "id": str(uuid.uuid4()),
        "source": source,
        "action": action,
        "created_at": utc_now(),
        "changed_fields": changed,
        "before": previous,
        "after": current,
        "undone": False,
    }
    if reference_ids:
        entry["reference_ids"] = list(dict.fromkeys(reference_ids))
    active_history = [item for item in (history or []) if not item.get("undone")]
    return (active_history + [entry])[-CARD_HISTORY_LIMIT:]


def card_history_view(history: list[dict]) -> list[dict]:
    """Keep history responses explicit while never exposing internal card ownership."""
    return public_card_payload({"change_history": history or []})["change_history"]


def apply_history_entry(card: dict, entry: dict, direction: Literal["before", "after"]) -> dict:
    restored = copy.deepcopy(card)
    for field, value in (entry.get(direction) or {}).items():
        restored[field] = copy.deepcopy(value)
    return restored


async def save_card_versioned(card: dict, user_id: str, updates: dict, expected_version: int) -> dict:
    """Save only if this is still the version the caller read, avoiding lost edits."""
    stored_version = int(card.get("version", 0) or 0)
    if expected_version != stored_version:
        raise HTTPException(
            status_code=409,
            detail="La scheda è stata modificata altrove. Ricaricala prima di salvare o aggiornare le regole.",
        )
    saved_updates = {**updates, "version": stored_version + 1}
    result = await db.cards.update_one(
        {"id": card["id"], "user_id": user_id, "version": stored_version},
        {"$set": saved_updates},
    )
    if result.matched_count == 0:
        raise HTTPException(
            status_code=409,
            detail="La scheda è stata modificata altrove. Ricaricala prima di salvare o aggiornare le regole.",
        )
    card.update(saved_updates)
    return card


async def insert_cards_atomically(cards: list[Card]) -> None:
    """Persist a linked-card set without exposing a partially written set.

    SupabaseCollection uses one bulk INSERT, which is atomic at the database
    level. The compensating deletes also protect callers backed by a simpler
    collection (and make failures injected by tests deterministic) if that
    collection wrote some rows before raising.
    """
    documents = [card.model_dump() for card in cards]
    if not documents:
        return

    try:
        await db.cards.insert_many(documents)
    except Exception:
        for document in documents:
            try:
                await db.cards.delete_one({"id": document["id"]})
            except Exception:
                logger.exception("Failed to clean up a partially persisted linked card")
        raise


def character_default_fields(record: dict) -> tuple[tuple[str, Any], ...]:
    source = record.get("attributes") or {}
    reference_type = record.get("reference_type")
    if reference_type == "class":
        return (
            ("dadi_vita", source.get("dado_vita")),
            ("competenze", source.get("competenze")),
            ("tiri_salvezza", source.get("tiri_salvezza")),
        )
    if reference_type in {"race", "subrace"}:
        return (
            ("velocita", source.get("velocita")),
            ("linguaggi", source.get("linguaggi")),
            ("tratti_razza", source.get("tratti")),
        )
    if reference_type == "subclass":
        return (("abilita_sottoclasse", source.get("caratteristiche") or source.get("privilegi")),)
    return ()


def character_manual_defaults(records: list[dict], attributes: dict) -> dict:
    """Mirror only deterministic, missing character fields from trusted records."""
    completed = copy.deepcopy(attributes or {})
    for record in records:
        for field, value in character_default_fields(record):
            if _is_empty_card_value(completed.get(field)) and not _is_empty_card_value(value):
                completed[field] = copy.deepcopy(value)
    return completed


async def manual_completion_preview_for_card(card: dict, user_id: str) -> tuple[dict, list[dict], list[str]]:
    """Resolve exact, trusted manual records from the saved character identity."""
    attributes = card.get("attributes") or {}
    lookups = (
        (attributes.get("classe"), {"class"}),
        (attributes.get("sottoclasse"), {"subclass"}),
        (attributes.get("razza"), {"race", "subrace"}),
        (attributes.get("sottorazza"), {"subrace"}),
    )
    records: list[dict] = []
    seen_ids: set[str] = set()
    available = await private_reference_records(user_id)
    linked_ids = set(card.get("reference_ids") or [])
    if linked_ids:
        records = [
            record for record in available
            if record.get("id") in linked_ids and reference_is_trusted(record)
        ]
        seen_ids = {record["id"] for record in records}
    for query, allowed_types in (() if linked_ids else lookups):
        normalized_query = normalize_reference_name(str(query or ""))
        if not normalized_query:
            continue
        for record in available:
            if (
                record.get("reference_type") in allowed_types
                and record.get("normalized_name") == normalized_query
                and reference_is_trusted(record)
                and record.get("id") not in seen_ids
            ):
                records.append(record)
                seen_ids.add(record["id"])
    completed = copy.deepcopy(attributes)
    field_sources: dict[str, dict] = {}
    for record in records:
        for field, value in character_default_fields(record):
            if _is_empty_card_value(completed.get(field)) and not _is_empty_card_value(value):
                completed[field] = copy.deepcopy(value)
                field_sources[field] = reference_rule_source(record)
    changes = [
        {
            "field": field,
            "before": copy.deepcopy(attributes.get(field)),
            "after": copy.deepcopy(completed[field]),
            "rule_source": field_sources.get(field),
        }
        for field in completed
        if completed[field] != attributes.get(field)
    ]
    return completed, changes, [record["id"] for record in records]


def refresh_derived_attributes(attributes: dict, old_snapshot: dict, new_snapshot: dict) -> tuple[dict, list[str]]:
    """Refresh only values that still equal the prior derived version."""
    refreshed = copy.deepcopy(attributes or {})
    protected: list[str] = []
    old_values = old_snapshot.get("derived_attributes") or {}
    new_values = new_snapshot.get("derived_attributes") or {}
    reference_id = old_snapshot.get("reference_id")
    for field, new_value in new_values.items():
        old_value = old_values.get(field)
        current_value = refreshed.get(field)
        if (
            isinstance(new_value, list)
            and all(isinstance(entry, dict) and entry.get("reference_id") == reference_id for entry in new_value)
        ):
            current_entries = current_value if isinstance(current_value, list) else []
            old_entries = old_value if isinstance(old_value, list) else []
            matching_entries = [
                entry for entry in current_entries
                if isinstance(entry, dict) and entry.get("reference_id") == reference_id
            ]
            untouched_entries = [
                entry for entry in current_entries
                if not (isinstance(entry, dict) and entry.get("reference_id") == reference_id)
            ]
            unchanged_entries = [entry for entry in matching_entries if entry in old_entries]
            manual_entries = [entry for entry in matching_entries if entry not in old_entries]
            # A removed entry is also an intentional user choice: do not bring
            # it back merely because the reference source was corrected.
            if manual_entries or (old_entries and not matching_entries):
                refreshed[field] = untouched_entries + copy.deepcopy(manual_entries)
                protected.append(field)
            else:
                refreshed[field] = untouched_entries + copy.deepcopy(new_value)
        elif _is_empty_card_value(current_value) or current_value == old_value:
            refreshed[field] = copy.deepcopy(new_value)
        elif current_value != new_value:
            protected.append(field)
    return refreshed, protected


def reference_update_report(card: dict, records_by_id: dict[str, dict]) -> list[dict]:
    """Describe current reference changes without modifying the saved card."""
    snapshots_by_id = {
        snapshot.get("reference_id"): snapshot
        for snapshot in card.get("reference_snapshots") or []
        if snapshot.get("reference_id")
    }
    updates = []
    for reference_id in card.get("reference_ids") or []:
        snapshot = snapshots_by_id.get(reference_id)
        record = records_by_id.get(reference_id)
        if not record:
            updates.append({
                "reference_id": reference_id,
                "status": "missing",
                "before": snapshot,
                "after": None,
                "changed_fields": ["fonte non disponibile"],
            })
        elif not snapshot:
            updates.append({
                "reference_id": reference_id,
                "status": "untracked",
                "before": None,
                "after": reference_snapshot_for_card(record, card.get("type", "custom")),
                "changed_fields": [],
            })
        elif reference_snapshot_changed(snapshot, record):
            updates.append({
                "reference_id": reference_id,
                "status": "updated",
                "before": snapshot,
                "after": reference_snapshot_for_card(record, card.get("type", "custom")),
                "changed_fields": reference_snapshot_change_fields(snapshot, record),
            })
    return updates


def remove_unlinked_reference_attributes(attributes: dict, reference_ids: list[str]) -> dict:
    """Keep manual entries while dropping list entries derived from removed records."""
    allowed_ids = set(reference_ids)
    reconciled = copy.deepcopy(attributes or {})
    for field in ("privilegi", "incantesimi", "equipaggiamento"):
        entries = reconciled.get(field)
        if isinstance(entries, list):
            reconciled[field] = [
                entry for entry in entries
                if not isinstance(entry, dict)
                or not entry.get("reference_id")
                or entry["reference_id"] in allowed_ids
            ]
    return reconciled


async def find_private_reference(user_id: str, query: str, card_type: Optional[str] = None) -> Optional[dict]:
    records = await private_reference_records(user_id)
    matches = search_reference_records(records, query, limit=20)
    if card_type:
        matches = [record for record in matches if CARD_TYPE_BY_REFERENCE_TYPE.get(record.get("reference_type")) == card_type]
    return next((record for record in matches if reference_is_trusted(record)), None)


async def import_private_reference_manuals(user_id: str, body: ReferenceImportInput) -> ReferenceImportResult:
    """Import source records locally, translating Spanish facts in small batches."""
    manuals = available_reference_manuals()
    requested = body.filenames or list(manuals)
    unknown = sorted(set(requested) - set(manuals))
    if unknown:
        raise HTTPException(status_code=400, detail="Uno o più manuali richiesti non sono disponibili localmente")
    if body.end_page and body.end_page < body.start_page:
        raise HTTPException(status_code=400, detail="L'intervallo di pagine non è valido")
    spanish_manuals = [
        filename for filename in requested
        if manual_source_language(filename) == "es"
    ]
    if spanish_manuals and not body.translation_processing_confirmed:
        raise HTTPException(
            status_code=400,
            detail="Conferma esplicitamente l'invio del testo estratto a Gemini per la traduzione italiana",
        )
    if spanish_manuals:
        if body.end_page is None:
            raise HTTPException(
                status_code=400,
                detail="Per tradurre il manuale spagnolo seleziona un intervallo di massimo 12 pagine",
            )
        if body.end_page - body.start_page + 1 > 12:
            raise HTTPException(
                status_code=400,
                detail="La traduzione del manuale spagnolo è limitata a 12 pagine per importazione",
            )
    if body.use_ai_ocr:
        spanish_native_manuals = [
            filename for filename in requested
            if manual_source_language(filename) == "es"
        ]
        if spanish_native_manuals:
            raise HTTPException(
                status_code=400,
                detail="Questo manuale ha testo nativo: l'OCR non è consentito e non verranno inviate pagine a Gemini",
            )
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
        source_metadata = manual_source_metadata(filename)
        report = await asyncio.to_thread(
            extract_reference_records,
            manuals[filename],
            ocr_callback,
            body.start_page,
            body.end_page,
            manual_requires_ocr(filename),
            source_metadata["language"],
        )
        for record in report.records:
            source_name = record["name"]
            source_description = record["description"]
            source_full_text = record["full_text"]
            source_normalized_name = record["normalized_name"]
            source_checksum = sha256(
                f"{source_name}\n{source_full_text}".encode("utf-8")
            ).hexdigest()
            all_records.append({
                **record,
                "source_key": filename,
                "source_language": source_metadata["language"],
                "source_normalized_name": source_normalized_name,
                "source_name": source_name,
                "source_description": source_description,
                "source_full_text": source_full_text,
                "source_attributes": dict(record.get("attributes") or {}),
                "source_text_checksum": source_checksum,
            })
        source_reports.append({
            "filename": filename,
            "title": source_metadata["title"],
            "source_language": source_metadata["language"],
            "native_text": source_metadata["native_text"],
            "pages_read": report.pages_read,
            "pages_needing_ocr": report.pages_needing_ocr,
            "records_detected": len(report.records),
            "translated": 0,
            "translation_failed": 0,
            "translation_rate_limited": 0,
            "translation_reused": 0,
        })

    # A page range can repeat a source-local heading (notably equipment table
    # labels). Collapse those copies before looking up or inserting so the
    # source-aware database uniqueness rule is never used as control flow.
    all_records = merge_reference_records(all_records)
    collection = getattr(db, "private_reference_records", None)
    if collection is None:
        raise HTTPException(status_code=503, detail="Biblioteca privata non disponibile: applica prima la migrazione SQL")

    existing_records = await private_reference_records(user_id)
    existing_by_source = {
        (
            record.get("reference_type"),
            record.get("source_key"),
            record.get("source_normalized_name") or record.get("normalized_name"),
        ): record
        for record in existing_records
    }
    existing_by_source_name = {
        (
            record.get("source_key"),
            record.get("source_normalized_name") or record.get("normalized_name"),
        ): record
        for record in existing_records
        if record.get("source_key") and (
            record.get("source_normalized_name") or record.get("normalized_name")
        )
    }
    # Older imports may predate source_normalized_name or contain a parser
    # label that differs from the canonical stored name. Keep a direct view
    # of the database uniqueness key so a re-import updates that row instead
    # of letting a duplicate-key error interrupt the whole preload chunk.
    existing_by_storage_key = {
        (
            record.get("reference_type"),
            record.get("source_key"),
            record.get("normalized_name") or normalize_reference_name(record.get("name", "")),
        ): record
        for record in existing_records
        if record.get("reference_type") and record.get("source_key")
    }
    existing_by_content = {
        (
            record.get("reference_type"),
            record.get("normalized_name") or normalize_reference_name(record.get("name", "")),
            record.get("source_language", "it"),
            reference_content_fingerprint(record),
        ): record
        for record in existing_records
        if record.get("reference_type") and (record.get("name") or record.get("normalized_name"))
    }

    def existing_for_import(record: dict) -> Optional[dict]:
        source_match = existing_by_source.get((
            record["reference_type"],
            record["source_key"],
            record["source_normalized_name"],
        ))
        if source_match:
            return source_match
        # Parsing improvements can correctly reclassify a record (for
        # example, from a generic heading to a feat) while its source section
        # is otherwise unchanged. Reuse that owner record so its provenance,
        # translation, review history, and any existing links remain intact.
        source_name_match = existing_by_source_name.get((
            record["source_key"],
            record["source_normalized_name"],
        ))
        if source_name_match:
            return source_name_match
        stored_name_match = existing_by_storage_key.get((
            record["reference_type"],
            record["source_key"],
            record["normalized_name"],
        ))
        if stored_name_match:
            return stored_name_match
        if record.get("source_language") == "es" or record.get("review_flags"):
            return None
        return existing_by_content.get((
            record["reference_type"],
            record["normalized_name"],
            record.get("source_language", "it"),
            reference_content_fingerprint(record),
        ))

    localized_records: list[dict] = []
    translation_queue: list[dict] = []
    report_by_filename = {report["filename"]: report for report in source_reports}
    for record in merge_reference_records(all_records):
        existing = existing_for_import(record)
        if record["source_language"] != "es":
            localized_records.append({
                **record,
                "translation_status": "not_required",
                "translation_error": "",
            })
            continue
        if (
            existing
            and existing.get("translation_status") == "translated"
            and existing.get("source_text_checksum") == record["source_text_checksum"]
        ):
            # Keep a completed translation on repeat imports. This makes a
            # page-range retry cheap and prevents provider limits from making
            # an already imported source unusable.
            localized_records.append({
                **record,
                "name": existing["name"],
                "normalized_name": existing["normalized_name"],
                "description": existing["description"],
                "full_text": existing["full_text"],
                "attributes": dict(existing.get("attributes") or {}),
                "translation_status": "translated",
                "translation_error": "",
            })
            report_by_filename[record["source_key"]]["translation_reused"] += 1
            continue
        translation_queue.append(record)

    translation_batches: list[list[dict]] = []
    current_batch: list[dict] = []
    current_size = 0
    for record in translation_queue:
        record_size = len(record["source_name"]) + len(record["source_description"]) + len(record["source_full_text"])
        if current_batch and (
            len(current_batch) >= body.translation_batch_size
            or current_size + record_size > 12000
        ):
            translation_batches.append(current_batch)
            current_batch = []
            current_size = 0
        current_batch.append(record)
        current_size += record_size
    if current_batch:
        translation_batches.append(current_batch)

    for batch in translation_batches:
        translated, error = await asyncio.to_thread(translate_spanish_reference_batch, batch)
        for record in batch:
            translated_record = translated.get(record["id"])
            report = report_by_filename[record["source_key"]]
            if translated_record:
                name = translated_record["name"]
                description = translated_record["description"]
                localized_records.append({
                    **record,
                    "name": name,
                    "normalized_name": normalize_reference_name(name),
                    "description": description,
                    "full_text": translated_record["full_text"],
                    "attributes": translated_record["attributes"],
                    "translation_status": "translated",
                    "translation_error": "",
                })
                report["translated"] += 1
            elif error == "provider_rate_limited":
                # A temporary rate-limit leaves the source fields intact and
                # does NOT add the human-review flag because the record will be
                # retried automatically by the preload worker with backoff.
                localized_records.append({
                    **record,
                    "translation_status": "failed",
                    "translation_error": "provider_rate_limited",
                })
                report["translation_rate_limited"] += 1
            else:
                localized_records.append({
                    **record,
                    "review_flags": sorted(set(record.get("review_flags") or []) | {"traduzione_da_verificare"}),
                    "translation_status": "failed",
                    "translation_error": error or "provider_translation_failed",
                })
                report["translation_failed"] += 1

    imported = updated = flagged = skipped = 0
    for record in localized_records:
        if not record.get("name") or not record.get("full_text"):
            skipped += 1
            continue
        existing = existing_for_import(record)
        owned_record_id = uuid.uuid5(uuid.NAMESPACE_URL, f"{user_id}:{record['id']}").hex
        payload = {
            **record,
            # Source-derived IDs are stable inside a source page but must not
            # collide when two separate owners import the same manual.
            "id": f"ref_{owned_record_id}",
            "user_id": user_id,
            "review_status": (
                # Auto-preload (auto_accept=True) marks successfully-translated
                # records as verified so they become immediately usable as
                # library probes. Manual imports and failed translations always
                # go to needs_review for human confirmation.
                "verified" if body.auto_accept and record.get("translation_status") != "failed"
                else "needs_review" if reference_review_state(record) == "review" else "pending"
            ),
            "review_notes": "",
            "updated_at": utc_now(),
        }
        def _merge_into_existing(base: dict, incoming: dict, rec: dict) -> None:
            """Apply incoming payload onto a known-existing record in all caches."""
            incoming["id"] = base["id"]
            incoming["source_refs"] = list(base.get("source_refs") or [])
            incoming["source_refs"].extend(
                ref for ref in rec.get("source_refs", [])
                if ref not in incoming["source_refs"]
            )
            incoming["source_key"] = base.get("source_key") or incoming["source_key"]
            incoming["source_normalized_name"] = (
                base.get("source_normalized_name") or incoming["source_normalized_name"]
            )
            unchanged_source = base.get("source_text_checksum") == rec.get("source_text_checksum")
            if unchanged_source and rec.get("translation_status") != "failed" and not body.auto_accept:
                incoming["review_status"] = base.get("review_status", incoming["review_status"])
                incoming["review_notes"] = base.get("review_notes", "")

        def _refresh_lookup_caches(stored: dict, merged: dict) -> None:
            """Keep all in-memory lookup caches current after each write."""
            combined = {**stored, **merged}
            existing_by_storage_key[(
                merged["reference_type"],
                merged.get("source_key", ""),
                merged["normalized_name"],
            )] = combined
            existing_by_source[(
                merged["reference_type"],
                merged.get("source_key", ""),
                merged.get("source_normalized_name") or merged["normalized_name"],
            )] = combined
            existing_by_source_name[(
                merged.get("source_key", ""),
                merged.get("source_normalized_name") or merged["normalized_name"],
            )] = combined
            existing_by_content[(
                merged["reference_type"],
                merged["normalized_name"],
                merged.get("source_language", "it"),
                reference_content_fingerprint(merged),
            )] = combined

        if existing:
            _merge_into_existing(existing, payload, record)
            # Human verification survives an unchanged repeat import. A new
            # source checksum or a failed translation must return to review.
            # Auto-accept (preload) overrides the stored status so a previously
            # failed translation can be promoted to verified on a successful retry.
            try:
                await collection.update_one({"id": existing["id"], "user_id": user_id}, {"$set": payload})
                _refresh_lookup_caches(existing, payload)
                updated += 1
            except Exception as upd_exc:
                if "23505" not in str(upd_exc) and "duplicate key" not in str(upd_exc).lower():
                    raise
                # Updating normalized_name to the Italian form collides with a
                # record already stored from a previous batch. Find the target
                # record, merge source_refs into it, then remove the stale
                # Spanish-named row so the DB stays consistent.
                target_rows = (
                    collection.client
                    .table("private_reference_records")
                    .select("*")
                    .eq("user_id", user_id)
                    .eq("reference_type", payload["reference_type"])
                    .eq("normalized_name", payload["normalized_name"])
                    .eq("source_key", payload.get("source_key", ""))
                    .limit(1)
                    .execute()
                )
                if target_rows.data:
                    target = target_rows.data[0]
                    merged_refs = list(target.get("source_refs") or [])
                    for ref in (existing.get("source_refs") or []) + (record.get("source_refs") or []):
                        if ref not in merged_refs:
                            merged_refs.append(ref)
                    await collection.update_one(
                        {"id": target["id"], "user_id": user_id},
                        {"$set": {"source_refs": merged_refs, "updated_at": utc_now()}},
                    )
                    # Remove the stale Spanish-named record so the unique key
                    # is held only by the correctly-named Italian record.
                    if existing["id"] != target["id"]:
                        await collection.delete_one({"id": existing["id"], "user_id": user_id})
                    _refresh_lookup_caches(target, {**target, "source_refs": merged_refs})
                    updated += 1
                else:
                    # Cannot locate the conflicting row; skip to avoid crash.
                    skipped += 1
        else:
            payload["imported_at"] = utc_now()
            try:
                await collection.insert_one(payload)
                _refresh_lookup_caches({}, payload)
                imported += 1
            except Exception as insert_exc:
                # A duplicate-key error (23505) means a previous batch already
                # stored a record that the in-memory cache missed (e.g. because
                # source_normalized_name differs between occurrences, or the
                # same source section ID was emitted by two parser pages).
                # Recover by fetching the true existing row and updating it.
                if "23505" not in str(insert_exc) and "duplicate key" not in str(insert_exc).lower():
                    raise
                dup: Optional[dict] = None
                # 1. Primary-key match: same generated id
                pk_rows = (
                    collection.client
                    .table("private_reference_records")
                    .select("*")
                    .eq("id", payload["id"])
                    .eq("user_id", user_id)
                    .limit(1)
                    .execute()
                )
                if pk_rows.data:
                    dup = pk_rows.data[0]
                # 2. Unique-name constraint: same (type, name, source_key)
                if dup is None:
                    name_rows = (
                        collection.client
                        .table("private_reference_records")
                        .select("*")
                        .eq("user_id", user_id)
                        .eq("reference_type", payload["reference_type"])
                        .eq("normalized_name", payload["normalized_name"])
                        .eq("source_key", payload.get("source_key", ""))
                        .limit(1)
                        .execute()
                    )
                    if name_rows.data:
                        dup = name_rows.data[0]
                if dup is None:
                    raise  # Cannot locate the conflicting row — re-raise
                _merge_into_existing(dup, payload, record)
                try:
                    await collection.update_one(
                        {"id": dup["id"], "user_id": user_id}, {"$set": payload}
                    )
                    _refresh_lookup_caches(dup, payload)
                    updated += 1
                except Exception as upd2_exc:
                    if "23505" not in str(upd2_exc) and "duplicate key" not in str(upd2_exc).lower():
                        raise
                    # Chain conflict: the Italian name being written to this row
                    # already belongs to a third record. Merge source_refs into
                    # that target and drop the stale intermediate row.
                    target2_rows = (
                        collection.client
                        .table("private_reference_records")
                        .select("*")
                        .eq("user_id", user_id)
                        .eq("reference_type", payload["reference_type"])
                        .eq("normalized_name", payload["normalized_name"])
                        .eq("source_key", payload.get("source_key", ""))
                        .limit(1)
                        .execute()
                    )
                    if target2_rows.data:
                        t2 = target2_rows.data[0]
                        merged_refs = list(t2.get("source_refs") or [])
                        for ref in (dup.get("source_refs") or []) + (record.get("source_refs") or []):
                            if ref not in merged_refs:
                                merged_refs.append(ref)
                        await collection.update_one(
                            {"id": t2["id"], "user_id": user_id},
                            {"$set": {"source_refs": merged_refs, "updated_at": utc_now()}},
                        )
                        if dup["id"] != t2["id"]:
                            await collection.delete_one({"id": dup["id"], "user_id": user_id})
                        _refresh_lookup_caches(t2, {**t2, "source_refs": merged_refs})
                        updated += 1
                    else:
                        skipped += 1
        flagged += reference_review_state(payload) == "review"
    return ReferenceImportResult(
        imported=imported,
        updated=updated,
        flagged_for_review=flagged,
        skipped=skipped,
        sources=source_reports,
    )


def _preload_waiting_status(filename: str, translation_confirmed: bool, ocr_confirmed: bool) -> str:
    return "queued"


def manual_preload_summary(job: Optional[dict], page_count: Optional[int]) -> dict:
    """Return progress metadata that is safe to show in the browser."""
    if not job:
        return {
            "status": "not_started",
            "current_page": 1,
            "page_count": page_count,
            "percent": 0,
            "records_imported": 0,
            "records_updated": 0,
            "records_flagged": 0,
            "records_skipped": 0,
            "pages_needing_ocr": [],
            "last_error": "",
            "translation_processing_confirmed": False,
            "external_processing_confirmed": False,
        }
    total = page_count or job.get("page_count") or 0
    current_page = max(1, int(job.get("current_page") or 1))
    completed_pages = min(total, max(0, current_page - 1)) if total else 0
    return {
        "status": job.get("status", "queued"),
        "current_page": current_page,
        "page_count": total or None,
        "percent": round((completed_pages / total) * 100) if total else 0,
        "records_imported": int(job.get("records_imported") or 0),
        "records_updated": int(job.get("records_updated") or 0),
        "records_flagged": int(job.get("records_flagged") or 0),
        "records_skipped": int(job.get("records_skipped") or 0),
        "pages_needing_ocr": list(job.get("pages_needing_ocr") or []),
        "last_error": job.get("last_error") or "",
        "translation_processing_confirmed": bool(job.get("translation_processing_confirmed")),
        "external_processing_confirmed": bool(job.get("external_processing_confirmed")),
    }


async def ensure_manual_preload_jobs(user_id: str, body: ManualPreloadInput) -> list[dict]:
    """Reconcile all supplied manuals with one durable, owner-scoped queue."""
    manuals = available_reference_manuals()
    if body.filename and body.filename not in manuals:
        raise HTTPException(status_code=400, detail="Il manuale richiesto non è disponibile localmente")
    selected_manuals = (
        {body.filename: manuals[body.filename]}
        if body.filename
        else manuals
    )

    collection = getattr(db, "private_manual_import_jobs", None)
    if collection is None:
        raise HTTPException(status_code=503, detail="Coda di indicizzazione non disponibile: applica prima la migrazione SQL")
    existing_by_filename = {
        job.get("filename"): job
        for job in await private_manual_import_jobs(user_id)
        if job.get("filename")
    }
    for filename, path in selected_manuals.items():
        existing = existing_by_filename.get(filename)
        source_language = manual_source_language(filename)
        needs_ocr = manual_requires_ocr(filename)
        # Supplied manuals are always processed automatically. Persist these
        # flags so a restart continues translation/OCR without another UI step.
        translation_confirmed = True
        ocr_confirmed = True

        fingerprint = manual_source_fingerprint(path)
        changed_source = bool(existing and existing.get("source_fingerprint") != fingerprint)
        status = existing.get("status") if existing else _preload_waiting_status(filename, translation_confirmed, ocr_confirmed)
        if status in {"waiting_translation_consent", "waiting_ocr_consent"}:
            status = "queued"
        if changed_source or (body.filename == filename and (body.enable_translation or body.enable_ocr or body.retry)):
            status = _preload_waiting_status(filename, translation_confirmed, ocr_confirmed)
        page_count = manual_page_count(path)
        payload = {
            "user_id": user_id,
            "filename": filename,
            "source_language": source_language,
            "source_fingerprint": fingerprint,
            "page_count": page_count or 0,
            "translation_processing_confirmed": translation_confirmed,
            "external_processing_confirmed": ocr_confirmed,
            "status": status,
            "updated_at": utc_now(),
        }
        if existing:
            if changed_source:
                payload.update({
                    "current_page": 1,
                    "attempt_count": 0,
                    "last_error": "",
                    "pages_needing_ocr": [],
                    "records_imported": 0,
                    "records_updated": 0,
                    "records_flagged": 0,
                    "records_skipped": 0,
                })
            elif status == "queued":
                payload.update({"lease_id": "", "lease_expires_at": 0, "last_error": ""})
            await collection.update_one({"id": existing["id"], "user_id": user_id}, {"$set": payload})
        else:
            await collection.insert_one({
                "id": f"manual_job_{uuid.uuid4().hex}",
                **payload,
                "current_page": 1,
                "attempt_count": 0,
                "last_error": "",
                "pages_needing_ocr": [],
                "records_imported": 0,
                "records_updated": 0,
                "records_flagged": 0,
                "records_skipped": 0,
                "lease_id": "",
                "lease_expires_at": 0,
                "created_at": utc_now(),
                "completed_at": None,
            })
    return await private_manual_import_jobs(user_id)


async def claim_next_manual_preload_job(user_id: str) -> Optional[dict]:
    """Lease exactly one queued chunk so concurrent requests cannot duplicate it."""
    collection = getattr(db, "private_manual_import_jobs", None)
    if collection is None:
        return None
    now = int(time.time())
    candidates = sorted(
        (
            job for job in await private_manual_import_jobs(user_id)
            if job.get("status") == "queued"
            or (job.get("status") == "processing" and int(job.get("lease_expires_at") or 0) < now)
        ),
        key=lambda job: (job.get("updated_at") or "", job.get("filename") or ""),
    )
    for candidate in candidates:
        lease_id = uuid.uuid4().hex
        claimed = await collection.update_one(
            {
                "id": candidate["id"],
                "user_id": user_id,
                "$or": [
                    {"status": "queued"},
                    {"status": "processing", "lease_expires_at": {"$lt": now}},
                ],
            },
            {"$set": {
                "status": "processing",
                "lease_id": lease_id,
                "lease_expires_at": now + MANUAL_PRELOAD_LEASE_SECONDS,
                "updated_at": utc_now(),
            }},
        )
        if claimed.matched_count:
            return await collection.find_one({"id": candidate["id"], "user_id": user_id})
    return None


async def renew_manual_preload_lease(user_id: str, job_id: str, lease_id: str) -> None:
    """Keep a long-running extraction owned until its current chunk checkpoints."""
    collection = getattr(db, "private_manual_import_jobs", None)
    if collection is None:
        return
    try:
        while True:
            await asyncio.sleep(max(1, MANUAL_PRELOAD_LEASE_SECONDS // 3))
            renewed = await collection.update_one(
                {"id": job_id, "user_id": user_id, "status": "processing", "lease_id": lease_id},
                {"$set": {
                    "lease_expires_at": int(time.time()) + MANUAL_PRELOAD_LEASE_SECONDS,
                    "updated_at": utc_now(),
                }},
            )
            if not renewed.matched_count:
                return
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("Could not renew the automatic manual preload lease")


_RATE_LIMIT_DRAIN_PAGE_SIZE = 200  # records per page when draining the retry queue


async def _drain_rate_limited_ids(
    records_collection: Any,
    query: dict,
) -> list[str]:
    """Return IDs of all records matching *query*, paginating to avoid fixed caps.

    A stable ``ORDER BY id ASC`` sort is applied before offset pagination so
    that each page is deterministic regardless of the underlying storage order.
    Without a stable sort, SQL/PostgREST pages may overlap or skip rows as
    concurrent updates change row positions.
    """
    ids: list[str] = []
    offset = 0
    while True:
        page = await records_collection.find(query).sort("id", 1).to_list(
            _RATE_LIMIT_DRAIN_PAGE_SIZE, offset
        )
        ids.extend(r["id"] for r in page)
        if len(page) < _RATE_LIMIT_DRAIN_PAGE_SIZE:
            break
        offset += _RATE_LIMIT_DRAIN_PAGE_SIZE
    return ids


async def _retry_rate_limited_translations(
    user_id: str,
    source_filename: str,
    records_collection: Any,
    delays: tuple[int, ...] = TRANSLATION_RATE_LIMIT_RETRY_DELAYS,
) -> int:
    """Retry rate-limited records from *source_filename* with exponential back-off.

    Each delay slot collects *all* still-pending IDs via offset pagination,
    then retries every one.  Records that still carry
    ``translation_error="provider_rate_limited"`` after all attempts are
    promoted to human review by adding ``traduzione_da_verificare`` so the
    queue always terminates with a definitive outcome instead of silently
    parking.

    Returns the count of records that could not be translated in any attempt.
    """
    rate_limit_query = {
        "user_id": user_id,
        "source_key": source_filename,
        "translation_error": "provider_rate_limited",
    }
    for attempt, delay in enumerate(delays):
        logger.info(
            "Traduzione con rate-limit: attesa %ss prima del tentativo %s/%s per %s",
            delay, attempt + 1, len(delays), source_filename,
        )
        await asyncio.sleep(delay)

        # Collect every pending ID before starting retries so that records
        # which succeed and disappear from the query do not shift the page
        # window for records that have not yet been attempted.
        pending_ids = await _drain_rate_limited_ids(records_collection, rate_limit_query)
        if not pending_ids:
            return 0

        for record_id in pending_ids:
            try:
                await retry_private_reference_translation(user_id, record_id)
            except Exception as exc:
                logger.warning(
                    "Retry rate-limit per %s fallito: %s", record_id, exc
                )

        # Re-check after this slot to exit early if all records resolved,
        # avoiding unnecessary waits.
        remaining_ids = await _drain_rate_limited_ids(records_collection, rate_limit_query)
        if not remaining_ids:
            return 0

    # After exhausting all delay slots, collect whatever is still stuck via
    # full pagination and elevate each one to human review — this is the
    # definitive terminal outcome so the queue does not park indefinitely.
    still_limited_ids = await _drain_rate_limited_ids(records_collection, rate_limit_query)
    for record_id in still_limited_ids:
        record = await records_collection.find_one({"id": record_id, "user_id": user_id})
        if not record:
            continue
        new_flags = sorted(
            set(record.get("review_flags") or []) | {"traduzione_da_verificare"}
        )
        await records_collection.update_one(
            {
                "id": record_id,
                "user_id": user_id,
                "translation_error": "provider_rate_limited",
            },
            {
                "$set": {
                    "review_flags": new_flags,
                    "review_status": "needs_review",
                    "translation_error": "provider_rate_limited_exhausted",
                    "updated_at": utc_now(),
                }
            },
        )
    return len(still_limited_ids)


async def process_manual_preload_job(user_id: str, job: dict) -> None:
    """Process one bounded page chunk and checkpoint the durable queue."""
    collection = getattr(db, "private_manual_import_jobs", None)
    if collection is None:
        return
    lease_id = job.get("lease_id")
    if not lease_id:
        return
    owned_query = {
        "id": job["id"],
        "user_id": user_id,
        "status": "processing",
        "lease_id": lease_id,
    }
    filename = job["filename"]
    manuals = available_reference_manuals()
    path = manuals.get(filename)
    if not path:
        await collection.update_one(
            owned_query,
            {"$set": {"status": "failed", "last_error": "manual_source_missing", "lease_id": "", "lease_expires_at": 0, "updated_at": utc_now()}},
        )
        return
    page_count = manual_page_count(path)
    if not page_count:
        await collection.update_one(
            owned_query,
            {"$set": {"status": "failed", "last_error": "manual_page_count_unavailable", "lease_id": "", "lease_expires_at": 0, "updated_at": utc_now()}},
        )
        return
    current_page = max(1, int(job.get("current_page") or 1))
    if current_page > page_count:
        await collection.update_one(
            owned_query,
            {"$set": {"status": "completed", "page_count": page_count, "completed_at": utc_now(), "lease_id": "", "lease_expires_at": 0, "updated_at": utc_now()}},
        )
        return

    end_page = min(page_count, current_page + MANUAL_PRELOAD_PAGE_BATCH_SIZE - 1)
    renewal_task = asyncio.create_task(renew_manual_preload_lease(user_id, job["id"], lease_id))
    try:
        report = await import_private_reference_manuals(
            user_id,
            ReferenceImportInput(
                filenames=[filename],
                start_page=current_page,
                end_page=end_page,
                use_ai_ocr=manual_requires_ocr(filename),
                external_processing_confirmed=bool(job.get("external_processing_confirmed")),
                translation_processing_confirmed=bool(job.get("translation_processing_confirmed")),
                auto_accept=True,
            ),
        )
    except Exception as exc:
        renewal_task.cancel()
        await asyncio.gather(renewal_task, return_exceptions=True)
        attempts = int(job.get("attempt_count") or 0) + 1
        retry_status = "queued" if attempts < MANUAL_PRELOAD_MAX_ATTEMPTS else "failed"
        await collection.update_one(
            owned_query,
            {"$set": {
                "status": retry_status,
                "attempt_count": attempts,
                "last_error": str(exc)[:500],
                "lease_id": "",
                "lease_expires_at": 0,
                "updated_at": utc_now(),
            }},
        )
        logger.warning("Manual preload failed for %s page %s: %s", filename, current_page, exc)
        return
    renewal_task.cancel()
    await asyncio.gather(renewal_task, return_exceptions=True)

    source_report = next((source for source in report.sources if source.get("filename") == filename), {})

    # If the provider returned 429 for any record, retry them with back-off
    # while still holding the job lease.  The job's last_error advertises the
    # recovery state so callers can see it is in progress.
    translation_rate_limited = int(source_report.get("translation_rate_limited") or 0)
    records_collection = getattr(db, "private_reference_records", None)
    if translation_rate_limited and records_collection is not None:
        await collection.update_one(
            owned_query,
            {"$set": {"last_error": "translation_rate_limited", "updated_at": utc_now()}},
        )
        rate_limit_renewal = asyncio.create_task(
            renew_manual_preload_lease(user_id, job["id"], lease_id)
        )
        try:
            await _retry_rate_limited_translations(
                user_id, filename, records_collection
            )
        finally:
            rate_limit_renewal.cancel()
            await asyncio.gather(rate_limit_renewal, return_exceptions=True)

    current_pages = set(range(current_page, end_page + 1))
    unreadable_pages = sorted(
        (set(job.get("pages_needing_ocr") or []) - current_pages)
        | set(source_report.get("pages_needing_ocr") or [])
    )
    attempts = int(job.get("attempt_count") or 0)
    if source_report.get("pages_needing_ocr") and manual_requires_ocr(filename):
        next_page = current_page
        attempts += 1
        next_status = "queued" if attempts < MANUAL_PRELOAD_MAX_ATTEMPTS else "failed"
        error = "ocr_pages_unavailable"
    else:
        next_page = end_page + 1
        next_status = "completed" if next_page > page_count else "queued"
        error = ""
        attempts = 0
    await collection.update_one(
        owned_query,
        {"$set": {
            "status": next_status,
            "current_page": next_page,
            "page_count": page_count,
            "attempt_count": attempts,
            "last_error": error,
            "pages_needing_ocr": unreadable_pages,
            "records_imported": int(job.get("records_imported") or 0) + report.imported,
            "records_updated": int(job.get("records_updated") or 0) + report.updated,
            "records_flagged": int(job.get("records_flagged") or 0) + report.flagged_for_review,
            "records_skipped": int(job.get("records_skipped") or 0) + report.skipped,
            "lease_id": "",
            "lease_expires_at": 0,
            "completed_at": utc_now() if next_status == "completed" else None,
            "updated_at": utc_now(),
        }},
    )


async def run_manual_preload_worker(user_id: str) -> None:
    """Drain an owner's queue outside the HTTP request, one checkpoint at a time."""
    try:
        while True:
            job = await claim_next_manual_preload_job(user_id)
            if not job:
                return
            await process_manual_preload_job(user_id, job)
    finally:
        MANUAL_PRELOAD_ACTIVE_WORKERS.discard(user_id)


def start_manual_preload_worker(user_id: str) -> None:
    if user_id in MANUAL_PRELOAD_ACTIVE_WORKERS:
        return
    MANUAL_PRELOAD_ACTIVE_WORKERS.add(user_id)
    asyncio.create_task(run_manual_preload_worker(user_id))


async def resume_manual_preload_workers() -> None:
    """Recover queued work and completed parser revisions after a restart."""
    collection = getattr(db, "private_manual_import_jobs", None)
    if collection is None:
        return
    try:
        jobs = await collection.find({}).to_list(2000)
    except Exception as exc:
        if "private_manual_import_jobs" in str(exc):
            logger.warning("Automatic manual preload schema is not available yet")
            return
        raise
    owners: set[str] = set()
    manuals = available_reference_manuals()
    for job in jobs:
        filename = job.get("filename")
        path = manuals.get(filename)
        if (
            job.get("status") == "completed"
            and path
            and job.get("source_fingerprint") != manual_source_fingerprint(path)
        ):
            reset = await collection.update_one(
                {"id": job["id"], "user_id": job.get("user_id"), "status": "completed"},
                {"$set": {
                    "status": "queued",
                    "source_fingerprint": manual_source_fingerprint(path),
                    "page_count": manual_page_count(path) or 0,
                    "current_page": 1,
                    "attempt_count": 0,
                    "last_error": "",
                    "pages_needing_ocr": [],
                    "records_imported": 0,
                    "records_updated": 0,
                    "records_flagged": 0,
                    "records_skipped": 0,
                    "lease_id": "",
                    "lease_expires_at": 0,
                    "completed_at": None,
                    "updated_at": utc_now(),
                }},
            )
            if reset.matched_count:
                owners.add(job.get("user_id", ""))
            continue
        if (
            job.get("status") == "processing"
            and int(job.get("lease_expires_at") or 0) < int(time.time())
        ):
            await collection.update_one(
                {
                    "id": job["id"],
                    "status": "processing",
                    "lease_expires_at": {"$lt": int(time.time())},
                },
                {"$set": {"status": "queued", "lease_id": "", "lease_expires_at": 0, "updated_at": utc_now()}},
            )
            owners.add(job.get("user_id", ""))
        elif job.get("status") == "queued":
            owners.add(job.get("user_id", ""))
    for owner_id in owners - {""}:
        start_manual_preload_worker(owner_id)


def _translation_lease_is_active(record: dict) -> bool:
    return (
        record.get("translation_status") == TRANSLATION_PROCESSING_STATUS
        and int(record.get("translation_lease_expires_at") or 0) > int(time.time())
    )


async def _wait_for_translation(collection: Any, user_id: str, reference_id: str, fallback: dict) -> dict:
    """Return the result of a retry owned by another concurrent request."""
    lease_remaining = max(
        0,
        int(fallback.get("translation_lease_expires_at") or 0) - int(time.time()),
    )
    deadline = asyncio.get_running_loop().time() + min(TRANSLATION_WAIT_SECONDS, lease_remaining)
    current = fallback
    while asyncio.get_running_loop().time() < deadline:
        await asyncio.sleep(TRANSLATION_POLL_INTERVAL_SECONDS)
        current = await collection.find_one({"id": reference_id, "user_id": user_id})
        if not current or current.get("translation_status") != TRANSLATION_PROCESSING_STATUS:
            return current or fallback
    # Never issue a second provider request while its lease is still valid.
    return current or fallback


async def retry_private_reference_translation(user_id: str, reference_id: str) -> dict:
    """Retry one failed Spanish translation without re-reading the manual."""
    collection = getattr(db, "private_reference_records", None)
    if collection is None:
        raise HTTPException(status_code=503, detail="Biblioteca privata non disponibile: applica prima la migrazione SQL")

    record = await collection.find_one({"id": reference_id, "user_id": user_id})
    if not record:
        raise HTTPException(status_code=404, detail="Contenuto non trovato nella tua biblioteca privata")
    if record.get("source_language") != "es":
        raise HTTPException(status_code=400, detail="Questo record non richiede una traduzione dallo spagnolo")
    # Retrying is intentionally idempotent for completed records. In
    # particular, do not call the provider or replace a successful translation.
    if record.get("translation_status") != "failed" and _translation_lease_is_active(record):
        return await _wait_for_translation(
            collection,
            user_id,
            reference_id,
            record,
        )
    if record.get("translation_status") != "failed":
        if record.get("translation_status") != TRANSLATION_PROCESSING_STATUS:
            return record
        # An abandoned request can be reclaimed only after its persisted lease
        # expires. The conditional update below makes that recovery atomic.

    # Claim the failed row atomically. Only the request that changes the
    # status can contact Gemini; expired claims can be safely recovered.
    now = int(time.time())
    lease_id = uuid.uuid4().hex
    claim = await collection.update_one(
        {
            "id": reference_id,
            "user_id": user_id,
            "$or": [
                {"translation_status": "failed"},
                {
                    "translation_status": TRANSLATION_PROCESSING_STATUS,
                    "translation_lease_expires_at": {"$lt": now + 1},
                },
            ],
        },
        {
            "$set": {
                "translation_status": TRANSLATION_PROCESSING_STATUS,
                "translation_error": "",
                "translation_lease_id": lease_id,
                "translation_lease_expires_at": now + TRANSLATION_LEASE_SECONDS,
                "updated_at": utc_now(),
            }
        },
    )
    if not claim or not getattr(claim, "matched_count", 0):
        current = await collection.find_one({"id": reference_id, "user_id": user_id})
        if current and current.get("translation_status") == TRANSLATION_PROCESSING_STATUS:
            return await _wait_for_translation(
                collection,
                user_id,
                reference_id,
                current,
            )
        return current or record

    # Reload after claiming so the response and source fields always come
    # from the record that owns this retry, not from a stale pre-claim read.
    record = await collection.find_one({"id": reference_id, "user_id": user_id}) or record

    source_record = {
        "id": reference_id,
        "source_name": record.get("source_name", ""),
        "source_description": record.get("source_description", ""),
        "source_full_text": record.get("source_full_text", ""),
        "source_attributes": dict(record.get("source_attributes") or {}),
    }
    try:
        translated, error = await asyncio.to_thread(
            translate_spanish_reference_batch,
            [source_record],
        )
    except Exception as exc:
        logger.warning("Retry della traduzione Gemini fallito per %s: %s", reference_id, exc)
        translated, error = {}, "provider_translation_failed"

    translated_record = translated.get(reference_id)
    processing_query = {
        "id": reference_id,
        "user_id": user_id,
        "translation_status": TRANSLATION_PROCESSING_STATUS,
        "translation_lease_id": lease_id,
    }
    if not translated_record:
        final_error = error or "provider_translation_failed"
        # A rate-limit is a temporary provider signal, not a content problem.
        # Preserve the error code WITHOUT adding the review flag so the
        # automatic backoff loop (_retry_rate_limited_translations) can detect
        # it on subsequent passes and escalate only after all attempts are gone.
        if final_error == "provider_rate_limited":
            await collection.update_one(
                processing_query,
                {
                    "$set": {
                        "translation_status": "failed",
                        "translation_error": "provider_rate_limited",
                        "translation_lease_id": "",
                        "translation_lease_expires_at": 0,
                        "updated_at": utc_now(),
                    }
                },
            )
        else:
            # Keep all source-derived fields untouched and retain the review
            # flag.  The conditional filter also avoids overwriting a concurrent
            # success.
            await collection.update_one(
                processing_query,
                {
                    "$set": {
                        "review_flags": sorted(set(record.get("review_flags") or []) | {"traduzione_da_verificare"}),
                        "review_status": "needs_review",
                        "translation_status": "failed",
                        "translation_error": final_error,
                        "translation_lease_id": "",
                        "translation_lease_expires_at": 0,
                        "updated_at": utc_now(),
                    }
                },
            )
        return await collection.find_one({"id": reference_id, "user_id": user_id}) or record

    remaining_review_flags = sorted(
        set(record.get("review_flags") or []) - {"traduzione_da_verificare"}
    )
    await collection.update_one(
        processing_query,
        {
            "$set": {
                "name": translated_record["name"],
                "normalized_name": normalize_reference_name(translated_record["name"]),
                "description": translated_record["description"],
                "full_text": translated_record["full_text"],
                "attributes": translated_record["attributes"],
                "translation_status": "translated",
                "translation_error": "",
                "translation_lease_id": "",
                "translation_lease_expires_at": 0,
                "review_flags": remaining_review_flags,
                "review_status": "needs_review" if remaining_review_flags else "pending",
                "updated_at": utc_now(),
            }
        },
    )
    return await collection.find_one({"id": reference_id, "user_id": user_id}) or record


def reference_summary(record: dict) -> dict:
    review_state = reference_review_state(record)
    return {
        "id": record["id"],
        "name": record["name"],
        "reference_type": record.get("reference_type", "other"),
        "attributes": record.get("attributes", {}),
        "source_refs": record.get("source_refs", []),
        "source_language": record.get("source_language", "it"),
        "source_name": record.get("source_name", ""),
        "translation_status": record.get("translation_status", "not_required"),
        "review_status": record.get("review_status", "pending"),
        "review_notes": record.get("review_notes", ""),
        "review_reason": reference_review_reason(record),
        "review_state": review_state,
        "is_trusted": review_state == "valid",
        "needs_review": review_state == "review",
    }


async def private_reference_review_history(user_id: str, reference_id: str) -> list[dict]:
    """Load the append-only audit trail for one owner-controlled record."""
    collection = getattr(db, "private_reference_review_history", None)
    if collection is None:
        raise HTTPException(status_code=503, detail="Cronologia revisioni non disponibile: applica prima la migrazione SQL")
    try:
        return await collection.find(
            {"user_id": user_id, "reference_id": reference_id}
        ).sort("reviewed_at", -1).sort("id", -1).to_list(500)
    except Exception as exc:
        if "private_reference_review_history" in str(exc):
            raise HTTPException(
                status_code=503,
                detail="Cronologia revisioni non disponibile: applica prima la migrazione SQL",
            ) from exc
        raise


async def reference_review_details(record: dict) -> dict:
    """Return the private side-by-side material needed to review one record.

    This projection is only used by the authenticated owner review flow. The
    regular library search and card APIs continue to expose summaries without
    extracted manual text.
    """
    summary = reference_summary(record)
    source_language = record.get("source_language", "it")
    original = {
        "name": record.get("source_name") or (record.get("name") if source_language != "es" else ""),
        "description": record.get("source_description") or (
            record.get("description") if source_language != "es" else ""
        ),
        "full_text": record.get("source_full_text") or (
            record.get("full_text") if source_language != "es" else ""
        ),
        "attributes": copy.deepcopy(
            record.get("source_attributes")
            or (record.get("attributes") if source_language != "es" else {})
            or {}
        ),
    }
    translation = {
        "name": record.get("name", ""),
        "description": record.get("description", ""),
        "full_text": record.get("full_text", ""),
        "attributes": copy.deepcopy(record.get("attributes") or {}),
    }
    return {
        **summary,
        "source_name": original["name"],
        "source_description": original["description"],
        "source_full_text": original["full_text"],
        "source_attributes": original["attributes"],
        "original": original,
        "translation": translation,
        "manual": copy.deepcopy(record.get("source_refs") or []),
        "review_history": await private_reference_review_history(record["user_id"], record["id"]),
    }


def public_reference_snapshot(snapshot: dict) -> dict:
    """Project a private comparison snapshot to rule identity and provenance."""
    allowed = {
        "reference_id",
        "name",
        "reference_type",
        "source_refs",
        "source_text_checksum",
        "content_revision",
        "saved_at",
        "derived_attributes",
    }
    return {
        key: copy.deepcopy(value)
        for key, value in (snapshot or {}).items()
        if key in allowed
    }


def public_card_payload(card: dict) -> dict:
    """Strip raw manual extracts from every card-shaped response.

    Snapshots and history retain their private comparison data server-side, but
    browser clients only need the linked manual/page metadata and derived card
    fields. This recursively handles old history entries as well as current
    snapshots created before this guard existed.
    """
    def redact(value):
        if isinstance(value, list):
            return [redact(item) for item in value]
        if not isinstance(value, dict):
            return value
        if value.get("reference_id") and any(
            key in value for key in ("source_text_checksum", "content_revision", "saved_at")
        ):
            return public_reference_snapshot(value)
        return {
            key: redact(item)
            for key, item in value.items()
            if key not in {"full_text", "source_full_text", "source_description", "source_attributes"}
        }

    return redact(copy.deepcopy(card))


def public_reference_update(update: dict) -> dict:
    """Use the same redaction policy for the source-update comparison route."""
    result = public_card_payload(update)
    for key in ("before", "after"):
        if result.get(key):
            result[key] = public_reference_snapshot(result[key])
    return result


def card_response(card: dict) -> Card:
    return Card(**public_card_payload(card))


def manual_coverage_report(records: list[dict]) -> list[dict]:
    """Summarise every supplied manual without exposing any source page text."""
    report: list[dict] = []
    for filename in available_reference_manuals():
        categories = MANUAL_COVERAGE_CATEGORIES.get(filename, tuple(REFERENCE_TYPES))
        source_records = [
            record for record in records
            if any(ref.get("filename") == filename for ref in record.get("source_refs", []))
        ]
        coverage = []
        for reference_type in categories:
            category_records = [
                record for record in source_records
                if record.get("reference_type") == reference_type
            ]
            valid = sum(reference_is_trusted(record) for record in category_records)
            to_review = sum(reference_review_state(record) == "review" for record in category_records)
            coverage.append({
                "reference_type": reference_type,
                "valid": valid,
                "to_review": to_review,
                "missing": int(not category_records),
                "records_total": len(category_records),
            })
        report.append({
            "filename": filename,
            "title": manual_source_metadata(filename)["title"],
            "source_language": manual_source_language(filename),
            "categories": coverage,
        })
    return report


def manual_import_progress(filename: str, records: list[dict], page_count: Optional[int]) -> dict:
    """Summarise import state without exposing extracted manual text."""
    source_records = [
        record for record in records
        if any(ref.get("filename") == filename for ref in record.get("source_refs", []))
    ]
    imported_pages = sorted({
        ref.get("page")
        for record in source_records
        for ref in record.get("source_refs", [])
        if ref.get("filename") == filename and isinstance(ref.get("page"), int)
    })
    translated = sum(record.get("translation_status") == "translated" for record in source_records)
    failed = sum(record.get("translation_status") == "failed" for record in source_records)
    processing = sum(record.get("translation_status") == TRANSLATION_PROCESSING_STATUS for record in source_records)
    to_review = sum(reference_review_state(record) == "review" for record in source_records)
    ready = sum(reference_is_trusted(record) for record in source_records)
    translation_pending = failed + processing + sum(
        record.get("source_language") == "es"
        and record.get("translation_status", "not_required") not in {"translated", "failed", TRANSLATION_PROCESSING_STATUS}
        for record in source_records
    )
    translation_total = translated + translation_pending
    return {
        "records_total": len(source_records),
        "records_ready": ready,
        "records_translated": translated,
        "records_to_review": to_review,
        "records_failed": failed,
        "records_processing": processing,
        "translation_total": translation_total,
        "translation_progress": round((translated / translation_total) * 100) if translation_total else 0,
        "imported_pages": imported_pages,
        "pages_with_records": len(imported_pages),
        "page_progress": round((len(imported_pages) / page_count) * 100) if page_count else 0,
    }


@api_router.get("/library/manuals")
async def private_library_manuals(user: User = Depends(require_premium)):
    """Return local import metadata only, never the manual files or page text."""
    records = await private_reference_records(user.user_id)
    jobs_by_filename = {
        job.get("filename"): job
        for job in await private_manual_import_jobs(user.user_id)
        if job.get("filename")
    }
    manuals = []
    for filename, path in available_reference_manuals().items():
        source_records = [
            record for record in records
            if any(ref.get("filename") == filename for ref in record.get("source_refs", []))
        ]
        page_count = manual_page_count(path)
        progress = manual_import_progress(filename, records, page_count)
        manuals.append({
            "filename": filename,
            "title": manual_source_metadata(filename)["title"],
            "source_language": manual_source_language(filename),
            "native_text": manual_source_metadata(filename)["native_text"],
            "page_count": page_count,
            "imported_records": len(source_records),
            "requires_ocr": manual_requires_ocr(filename),
            "job": manual_preload_summary(jobs_by_filename.get(filename), page_count),
            **progress,
        })
    return {"manuals": manuals}


@api_router.post("/library/preload")
async def start_private_library_preload(
    body: ManualPreloadInput = ManualPreloadInput(),
    user: User = Depends(require_premium),
):
    """Start or resume automatic indexing without exposing or uploading PDFs."""
    try:
        await ensure_manual_preload_jobs(user.user_id, body)
        start_manual_preload_worker(user.user_id)
        return await private_library_manuals(user)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Automatic manual preload could not be started")
        raise HTTPException(status_code=502, detail="Impossibile avviare l'indicizzazione automatica") from exc


@api_router.get("/library/coverage")
async def private_library_coverage(user: User = Depends(require_premium)):
    """Report record readiness by supplied manual and applicable category."""
    records = await private_reference_records(user.user_id)
    manuals = manual_coverage_report(records)
    totals = {
        "valid": sum(category["valid"] for manual in manuals for category in manual["categories"]),
        "to_review": sum(category["to_review"] for manual in manuals for category in manual["categories"]),
        "missing": sum(category["missing"] for manual in manuals for category in manual["categories"]),
    }
    return {"manuals": manuals, "totals": totals}


@api_router.get("/library")
async def search_private_library(
    q: str = Query("", max_length=120),
    types: str = Query("", max_length=200),
    review_only: bool = False,
    include_unverified: bool = False,
    source_filename: str = Query("", max_length=300),
    user: User = Depends(get_current_user),
):
    # Direct service tests invoke this route without FastAPI dependency
    # resolution, which leaves a Query object in optional parameters.
    source_filename = source_filename if isinstance(source_filename, str) else ""
    requested_types = {value.strip() for value in types.split(",") if value.strip()}
    if requested_types - set(REFERENCE_TYPES):
        raise HTTPException(status_code=400, detail="Tipo di contenuto non valido")
    if source_filename and source_filename not in available_reference_manuals():
        raise HTTPException(status_code=400, detail="Manuale non disponibile nella biblioteca privata")
    records = await private_reference_records(user.user_id)
    if requested_types:
        records = [record for record in records if record.get("reference_type") in requested_types]
    if source_filename:
        records = [
            record for record in records
            if any(ref.get("filename") == source_filename for ref in record.get("source_refs", []))
        ]
    if review_only:
        records = [record for record in records if reference_review_state(record) == "review"]
    records = search_reference_records(records, q, limit=40)
    excluded_unverified = sum(not reference_is_trusted(record) for record in records)
    if not include_unverified:
        records = [record for record in records if reference_is_trusted(record)]
    summaries = [reference_summary(record) for record in records]
    if summaries:
        return {
            "status": "sourced",
            "records": summaries,
            "excluded_unverified": excluded_unverified,
        }
    return {
        "status": "unavailable",
        "records": [],
        "excluded_unverified": excluded_unverified,
        "message": "Il contenuto richiesto non è disponibile come fonte verificata nella tua biblioteca.",
    }


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
    # Manual/page provenance is enough to assess a rule. Never send source
    # pages or their full extracted text to the browser.
    return reference_summary(record)


@api_router.get("/library/{reference_id}/review")
async def get_private_reference_review(
    reference_id: str,
    user: User = Depends(require_premium),
):
    record = await db.private_reference_records.find_one({"id": reference_id, "user_id": user.user_id})
    if not record:
        raise HTTPException(status_code=404, detail="Contenuto non trovato nella tua biblioteca privata")
    return await reference_review_details(record)


@api_router.post("/library/{reference_id}/apply")
async def apply_private_reference(reference_id: str, user: User = Depends(get_current_user)):
    record = await db.private_reference_records.find_one({"id": reference_id, "user_id": user.user_id})
    if not record:
        raise HTTPException(status_code=404, detail="Contenuto non trovato nella tua biblioteca privata")
    if not reference_is_trusted(record):
        raise HTTPException(
            status_code=409,
            detail="Questo contenuto è da verificare e non può essere usato come dato certo.",
        )
    return {**reference_to_card_payload(record), "reference_id": record["id"]}


@api_router.post("/library/{reference_id}/translation-retry")
async def retry_private_reference_translation_endpoint(
    reference_id: str,
    user: User = Depends(require_premium),
):
    return reference_summary(await retry_private_reference_translation(user.user_id, reference_id))


@api_router.patch("/library/{reference_id}/review")
async def review_private_reference(
    reference_id: str,
    body: ReferenceReviewInput,
    user: User = Depends(require_premium),
):
    record = await db.private_reference_records.find_one({"id": reference_id, "user_id": user.user_id})
    if not record:
        raise HTTPException(status_code=404, detail="Contenuto non trovato nella tua biblioteca privata")
    review_notes = body.review_notes.strip()
    review_entry = {
        "id": f"review_{uuid.uuid4().hex}",
        "reference_id": record["id"],
        "user_id": user.user_id,
        "reviewer_id": user.user_id,
        "reviewer_name": user.name,
        "reviewer_email": user.email,
        "reviewed_at": utc_now(),
        "review_status": body.review_status,
        "review_notes": review_notes,
    }
    history_collection = getattr(db, "private_reference_review_history", None)
    if history_collection is None:
        raise HTTPException(status_code=503, detail="Cronologia revisioni non disponibile: applica prima la migrazione SQL")
    try:
        # A single INSERT is append-only at the database level: concurrent
        # reviewers cannot erase an already persisted decision.
        await history_collection.insert_one(review_entry)
    except Exception as exc:
        if "private_reference_review_history" in str(exc):
            raise HTTPException(
                status_code=503,
                detail="Cronologia revisioni non disponibile: applica prima la migrazione SQL",
            ) from exc
        raise
    await db.private_reference_records.update_one(
        {"id": reference_id, "user_id": user.user_id},
        {"$set": {
            "review_status": body.review_status,
            "review_notes": review_notes,
            "updated_at": utc_now(),
        }},
    )
    updated = await db.private_reference_records.find_one({"id": reference_id, "user_id": user.user_id})
    fallback = {
        **record,
        "review_status": body.review_status,
        "review_notes": review_notes,
    }
    return {"ok": True, **await reference_review_details(updated or fallback)}


@api_router.post("/ai/generate-content")
async def generate_content(body: GenerateContentInput, user: User = Depends(require_premium)):
    if MOCK_DATA:
        return {
            "name": "Eco della Luna (Demo)",
            "description": f"Una creazione simulata per: {body.prompt}.",
            "story": "Il testo dimostrativo appare senza chiamare OpenAI.",
            "attributes": {"livello": "2", "scuola": "Illusione", "azione": "1 azione", "danno": "2d6 psichico"},
            "source": "ai_generated",
            "source_status": "unavailable",
            "source_message": "Nessuna fonte verificata è disponibile nella biblioteca: questo è contenuto dimostrativo.",
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
        return {
            "name": data.get("name", ""),
            "description": data.get("description", ""),
            "story": data.get("story", ""),
            "attributes": data.get("attributes", {}),
            "source": "ai_generated",
            "source_status": "unavailable",
            "source_message": "Il contenuto richiesto non è disponibile come fonte verificata nella tua biblioteca; il testo generato non è una regola certa.",
        }
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
    data = body.model_dump(exclude_none=True)
    reference_ids, reference_sources = await resolve_reference_provenance(user.user_id, data.get("reference_ids", []))
    spell_ids, spell_sources = await resolve_spell_provenance(user.user_id, data.get("spell_ids", []))
    data["reference_ids"] = reference_ids
    data["spell_ids"] = spell_ids
    data["source_refs"] = merge_source_refs(reference_sources, spell_sources)
    data["rule_sources"] = await rule_sources_for_card(user.user_id, reference_ids, spell_ids)
    data["attributes"] = remove_unlinked_reference_attributes(data.get("attributes", {}), reference_ids)
    records_by_id = await reference_records_by_id(user.user_id, reference_ids)
    data["reference_snapshots"] = reference_snapshots_for_card(
        [], records_by_id, reference_ids, data.get("type", "custom"), utc_now()
    )
    card = Card(user_id=user.user_id, **data)
    await db.cards.insert_one(card.model_dump())
    return card_response(card.model_dump())


@api_router.get("/cards", response_model=List[Card])
async def list_cards(type: Optional[str] = None, search: Optional[str] = None, user: User = Depends(get_current_user)):
    cards = await db.cards.find({"user_id": user.user_id}).sort("created_at", -1).to_list(1000)
    if type and type != "all":
        cards = [card for card in cards if card.get("type") == type]
    if search:
        needle = search.casefold()
        cards = [card for card in cards if needle in card.get("name", "").casefold()]
    return [card_response(card) for card in cards]


@api_router.get("/cards/{card_id}", response_model=Card)
async def get_card(card_id: str, user: User = Depends(get_current_user)):
    card = await db.cards.find_one({"id": card_id, "user_id": user.user_id})
    if not card:
        raise HTTPException(status_code=404, detail="Carta non trovata")
    return card_response(card)


@api_router.put("/cards/{card_id}", response_model=Card)
async def update_card(card_id: str, body: CardUpdate, user: User = Depends(get_current_user)):
    card = await db.cards.find_one({"id": card_id, "user_id": user.user_id})
    if not card:
        raise HTTPException(status_code=404, detail="Carta non trovata")
    before_card = copy.deepcopy(card)
    updates = body.model_dump(exclude_none=True)
    expected_version = updates.pop("version")
    if "reference_ids" in updates or "spell_ids" in updates:
        reference_ids, reference_sources = await resolve_reference_provenance(
            user.user_id, updates.get("reference_ids", card.get("reference_ids", []))
        )
        spell_ids, spell_sources = await resolve_spell_provenance(
            user.user_id, updates.get("spell_ids", card.get("spell_ids", []))
        )
        updates["reference_ids"] = reference_ids
        updates["spell_ids"] = spell_ids
        updates["source_refs"] = merge_source_refs(reference_sources, spell_sources)
        updates["rule_sources"] = await rule_sources_for_card(user.user_id, reference_ids, spell_ids)
        updates["attributes"] = remove_unlinked_reference_attributes(
            updates.get("attributes", card.get("attributes", {})),
            reference_ids,
        )
        records_by_id = await reference_records_by_id(user.user_id, reference_ids)
        updates["reference_snapshots"] = reference_snapshots_for_card(
            card.get("reference_snapshots", []),
            records_by_id,
            reference_ids,
            updates.get("type", card.get("type", "custom")),
            utc_now(),
        )
    else:
        # Provenance is always derived server-side. Ignore stale or forged
        # snapshots sent by older clients when the references did not change.
        updates.pop("source_refs", None)
        updates.pop("rule_sources", None)
    updates["updated_at"] = utc_now()
    after_card = copy.deepcopy(card)
    after_card.update(updates)
    updates["change_history"] = append_card_history(
        card.get("change_history", []),
        before_card,
        after_card,
        "user",
        "update",
    )
    await save_card_versioned(card, user.user_id, updates, expected_version)
    return card_response(card)


@api_router.get("/cards/{card_id}/reference-updates")
async def card_reference_updates(card_id: str, user: User = Depends(get_current_user)):
    """Return changed linked references and their saved/current private snapshots."""
    card = await db.cards.find_one({"id": card_id, "user_id": user.user_id})
    if not card:
        raise HTTPException(status_code=404, detail="Carta non trovata")
    records_by_id = await reference_records_by_id(user.user_id, card.get("reference_ids") or [])
    updates = reference_update_report(card, records_by_id)
    return {
        "updates": [public_reference_update(update) for update in updates],
        "updated_count": sum(update["status"] == "updated" for update in updates),
        "untracked_count": sum(update["status"] == "untracked" for update in updates),
    }


@api_router.post("/cards/{card_id}/manual-completion", response_model=Card)
async def complete_card_from_manuals(
    card_id: str,
    body: ManualCompletionInput,
    user: User = Depends(get_current_user),
):
    """Save a server-derived manual completion as a distinct, undoable event."""
    card = await db.cards.find_one({"id": card_id, "user_id": user.user_id})
    if not card:
        raise HTTPException(status_code=404, detail="Carta non trovata")
    if card.get("type") != "character":
        raise HTTPException(status_code=400, detail="Il completamento dai manuali è disponibile solo per i personaggi")

    before_card = copy.deepcopy(card)
    after_card = copy.deepcopy(card)
    completed_attributes, _changes, source_ids = await manual_completion_preview_for_card(card, user.user_id)
    after_card["attributes"] = completed_attributes
    history = append_card_history(
        card.get("change_history", []),
        before_card,
        after_card,
        "manual",
        "manual_completion",
        source_ids,
    )
    updates = {
        "attributes": after_card["attributes"],
        "change_history": history,
        "updated_at": utc_now(),
    }
    await save_card_versioned(card, user.user_id, updates, body.version)
    return card_response(card)


@api_router.get("/cards/{card_id}/manual-completion-preview")
async def card_manual_completion_preview(card_id: str, user: User = Depends(get_current_user)):
    """Calculate the exact trusted fields that a manual completion would add."""
    card = await db.cards.find_one({"id": card_id, "user_id": user.user_id})
    if not card:
        raise HTTPException(status_code=404, detail="Carta non trovata")
    if card.get("type") != "character":
        raise HTTPException(status_code=400, detail="Il completamento dai manuali è disponibile solo per i personaggi")
    attributes, changes, reference_ids = await manual_completion_preview_for_card(card, user.user_id)
    return {"attributes": attributes, "changes": changes, "reference_ids": reference_ids, "version": card.get("version", 0)}


@api_router.post("/cards/{card_id}/reference-updates")
async def refresh_card_reference_updates(
    card_id: str,
    body: ReferenceUpdateInput,
    user: User = Depends(get_current_user),
):
    """Apply selected current reference values without overwriting manual choices."""
    card = await db.cards.find_one({"id": card_id, "user_id": user.user_id})
    if not card:
        raise HTTPException(status_code=404, detail="Carta non trovata")
    before_card = copy.deepcopy(card)
    linked_ids = list(dict.fromkeys(card.get("reference_ids") or []))
    requested_ids = list(dict.fromkeys(body.reference_ids or linked_ids))
    if not set(requested_ids).issubset(linked_ids):
        raise HTTPException(status_code=400, detail="Puoi aggiornare solo riferimenti già collegati alla carta")
    records_by_id = await reference_records_by_id(user.user_id, requested_ids)
    missing = [reference_id for reference_id in requested_ids if reference_id not in records_by_id]
    if missing:
        raise HTTPException(status_code=404, detail="Uno o più riferimenti normativi non sono più disponibili")
    unverified = [reference_id for reference_id in requested_ids if not reference_is_trusted(records_by_id[reference_id])]
    if unverified:
        raise HTTPException(
            status_code=409,
            detail="Un riferimento aggiornato è da verificare e non può sostituire dati regolamentari.",
        )

    snapshots_by_id = {
        snapshot.get("reference_id"): snapshot
        for snapshot in card.get("reference_snapshots") or []
        if snapshot.get("reference_id")
    }
    attributes = copy.deepcopy(card.get("attributes") or {})
    protected_fields: dict[str, list[str]] = {}
    refreshed_ids = []
    for reference_id in requested_ids:
        previous = snapshots_by_id.get(reference_id)
        current = reference_snapshot_for_card(records_by_id[reference_id], card.get("type", "custom"), utc_now())
        if previous and reference_snapshot_changed(previous, records_by_id[reference_id]):
            attributes, protected = refresh_derived_attributes(attributes, previous, current)
            if protected:
                protected_fields[reference_id] = protected
            if card.get("type") != "character":
                for field, prior_value in (previous.get("derived_card_fields") or {}).items():
                    next_value = (current.get("derived_card_fields") or {}).get(field)
                    if card.get(field) == prior_value:
                        card[field] = next_value
                    elif card.get(field) != next_value:
                        protected_fields.setdefault(reference_id, []).append(field)
            refreshed_ids.append(reference_id)
            snapshots_by_id[reference_id] = current
        elif not previous:
            snapshots_by_id[reference_id] = current

    snapshots = [
        snapshots_by_id[reference_id]
        for reference_id in linked_ids
        if reference_id in snapshots_by_id
    ]
    updates = {
        "attributes": attributes,
        "reference_snapshots": snapshots,
        "updated_at": utc_now(),
    }
    for field in ("name", "description", "story", "language"):
        if field in card:
            updates[field] = card[field]
    after_card = copy.deepcopy(card)
    after_card.update(updates)
    updates["change_history"] = append_card_history(
        card.get("change_history", []),
        before_card,
        after_card,
        "manual",
        "reference_update",
        requested_ids,
    )
    await save_card_versioned(card, user.user_id, updates, body.version)
    return {
        "card": card_response(card),
        "updated_reference_ids": refreshed_ids,
        "protected_fields": protected_fields,
    }


@api_router.get("/cards/{card_id}/history")
async def card_history(card_id: str, user: User = Depends(get_current_user)):
    """Return the short, account-scoped audit trail for a card."""
    card = await db.cards.find_one({"id": card_id, "user_id": user.user_id})
    if not card:
        raise HTTPException(status_code=404, detail="Carta non trovata")
    history = card_history_view(card.get("change_history", []))
    return {
        "history": history,
        "can_undo": any(not entry.get("undone") for entry in history),
        "can_redo": any(entry.get("undone") for entry in history),
    }


@api_router.post("/cards/{card_id}/history/undo")
async def undo_card_change(
    card_id: str,
    body: CardVersionInput,
    user: User = Depends(get_current_user),
):
    """Undo the latest saved user or manual change without crossing accounts."""
    card = await db.cards.find_one({"id": card_id, "user_id": user.user_id})
    if not card:
        raise HTTPException(status_code=404, detail="Carta non trovata")
    history = copy.deepcopy(card.get("change_history") or [])
    target = next((entry for entry in reversed(history) if not entry.get("undone")), None)
    if not target:
        raise HTTPException(status_code=409, detail="Non ci sono modifiche da annullare")

    restored = apply_history_entry(card, target, "before")
    target["undone"] = True
    updates = {
        field: restored[field]
        for field in target.get("before", {})
        if field in restored
    }
    updates["change_history"] = history
    updates["updated_at"] = utc_now()
    await save_card_versioned(card, user.user_id, updates, body.version)
    return {
        "card": card_response(card),
        "history": card_history_view(history),
        "entry": card_history_view([target])[0],
    }


@api_router.post("/cards/{card_id}/history/redo")
async def redo_card_change(
    card_id: str,
    body: CardVersionInput,
    user: User = Depends(get_current_user),
):
    """Restore the most recently undone change while the redo branch is intact."""
    card = await db.cards.find_one({"id": card_id, "user_id": user.user_id})
    if not card:
        raise HTTPException(status_code=404, detail="Carta non trovata")
    history = copy.deepcopy(card.get("change_history") or [])
    target = next((entry for entry in history if entry.get("undone")), None)
    if not target:
        raise HTTPException(status_code=409, detail="Non ci sono modifiche da ripristinare")

    restored = apply_history_entry(card, target, "after")
    target["undone"] = False
    updates = {
        field: restored[field]
        for field in target.get("after", {})
        if field in restored
    }
    updates["change_history"] = history
    updates["updated_at"] = utc_now()
    await save_card_versioned(card, user.user_id, updates, body.version)
    return {
        "card": card_response(card),
        "history": card_history_view(history),
        "entry": card_history_view([target])[0],
    }


@api_router.delete("/cards/{card_id}")
async def delete_card(
    card_id: str,
    body: CardVersionInput,
    user: User = Depends(get_current_user),
):
    result = await db.cards.delete_one({
        "id": card_id,
        "user_id": user.user_id,
        "version": body.version,
    })
    if result.deleted_count == 0:
        current = await db.cards.find_one({"id": card_id, "user_id": user.user_id})
        if current:
            raise HTTPException(
                status_code=409,
                detail="La scheda è stata modificata altrove. Ricaricala prima di eliminarla.",
            )
        raise HTTPException(status_code=404, detail="Carta non trovata")
    return {"ok": True}


@api_router.post("/cards/{card_id}/linked", response_model=List[Card])
async def create_linked_cards(
    card_id: str,
    body: LinkedCardInput,
    user: User = Depends(get_current_user),
):
    """Create printable rule cards from a character's selected references.

    The reference record remains the source of truth: cards only copy its
    current structured payload and keep both its id and provenance snapshot.
    """
    character = await db.cards.find_one({"id": card_id, "user_id": user.user_id})
    if not character:
        raise HTTPException(status_code=404, detail="Personaggio non trovato")
    if character.get("type") != "character":
        raise HTTPException(status_code=400, detail="Le carte collegate partono da un personaggio")

    persisted_ids = list(dict.fromkeys(character.get("reference_ids") or []))
    requested_ids = body.reference_ids or persisted_ids
    requested_ids = list(dict.fromkeys(requested_ids))
    if not requested_ids:
        raise HTTPException(status_code=400, detail="Il personaggio non ha riferimenti normativi selezionati")
    if not set(requested_ids).issubset(persisted_ids):
        raise HTTPException(status_code=400, detail="Puoi creare carte solo dai riferimenti già collegati al personaggio")

    records_by_id = {
        record["id"]: record
        for record in await private_reference_records(user.user_id)
        if record.get("id") in requested_ids
    }
    if len(records_by_id) != len(requested_ids):
        raise HTTPException(status_code=404, detail="Uno o più riferimenti normativi non sono più disponibili")
    if any(not reference_is_trusted(record) for record in records_by_id.values()):
        raise HTTPException(
            status_code=409,
            detail="I riferimenti da verificare non possono generare carte regolamentari.",
        )

    # Creating linked cards is based on the character's selected references.
    # Reserve the version before inserting any child cards so two screens
    # cannot both materialize different views of a stale character.
    original_version = int(character.get("version", 0) or 0)
    original_updated_at = character.get("updated_at")
    await save_card_versioned(
        character,
        user.user_id,
        {"updated_at": utc_now()},
        body.version,
    )

    created = []
    for reference_id in requested_ids:
        record = records_by_id[reference_id]
        payload = reference_to_card_payload(record)
        card = Card(
            user_id=user.user_id,
            type=payload["card_type"],
            name=payload["name"],
            description=payload["description"],
            story=payload["story"],
            language=payload["content_language"],
            attributes=payload["attributes"],
            reference_ids=[reference_id],
            rule_sources=[reference_rule_source(record)],
            source_refs=payload["source_refs"],
            reference_snapshots=[reference_snapshot_for_card(record, payload["card_type"], utc_now())],
        )
        created.append(card)

    try:
        await insert_cards_atomically(created)
    except Exception:
        # The reservation prevents a concurrent mutation while the child
        # cards are being written. If persistence fails, release it only if
        # the reservation is still ours; never overwrite a later concurrent
        # change.
        rollback_updates = {"version": original_version}
        if original_updated_at is not None:
            rollback_updates["updated_at"] = original_updated_at
        try:
            await db.cards.update_one(
                {
                    "id": character["id"],
                    "user_id": user.user_id,
                    "version": original_version + 1,
                },
                {"$set": rollback_updates},
            )
            character.update(rollback_updates)
        except Exception:
            logger.exception("Failed to roll back character version after linked-card failure")
        raise

    return [card_response(card.model_dump()) for card in created]


@api_router.get("/public/cards/{card_id}")
async def public_get_card(card_id: str):
    card = await db.cards.find_one({"id": card_id})
    if not card:
        raise HTTPException(status_code=404, detail="Carta non trovata")
    # Public cards are deliberately a rendered-card projection, not a copy of
    # the stored document. In particular, reference snapshots contain private
    # source text used only by authenticated owners for change comparison.
    public_fields = (
        "id", "type", "custom_type", "name", "description", "story", "language",
        "attributes", "artwork_path", "frame", "appearance", "back",
    )
    return {field: card[field] for field in public_fields if field in card}


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