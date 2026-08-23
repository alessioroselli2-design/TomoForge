import logging
import os
import stripe
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent
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
OPENAI_OCR_MODEL = os.getenv("OPENAI_OCR_MODEL", "gpt-4o")
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
# manual needs a targeted re-index.
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

TRANSLATION_PROCESSING_STATUS = "processing"
TRANSLATION_LEASE_SECONDS = 180
TRANSLATION_WAIT_SECONDS = 135
TRANSLATION_POLL_INTERVAL_SECONDS = 0.05
MANUAL_PRELOAD_PAGE_BATCH_SIZE = 12
MANUAL_PRELOAD_LEASE_SECONDS = 300
MANUAL_PRELOAD_MAX_ATTEMPTS = 3
# Seconds to wait between successive retries after a provider rate-limit (429).
TRANSLATION_RATE_LIMIT_RETRY_DELAYS: tuple[int, ...] = (30, 60, 120)


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
    from fastapi import HTTPException
    if not JWT_SECRET:
        raise HTTPException(status_code=503, detail="JWT_SECRET o SESSION_SECRET non configurato")
