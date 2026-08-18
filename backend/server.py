import os
import uuid
import json
import base64
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Any, Annotated

import jwt
import bcrypt
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Response, UploadFile, File, Header, Query
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, EmailStr, BeforeValidator, ConfigDict

from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("tomeforge")

# --- Config ---
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY")
JWT_SECRET = os.environ.get("JWT_SECRET", "tomeforge_secret")
JWT_ALGO = "HS256"
TEXT_MODEL = "gemini-3-flash-preview"
IMAGE_MODEL = "gemini-3.1-flash-image-preview"

STORAGE_BASE = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip() or "https://integrations.emergentagent.com"
STORAGE_URL = STORAGE_BASE.rstrip("/") + "/objstore/api/v1/storage"
APP_NAME = "tomeforge"
_storage_key = None

MIME_TYPES = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
              "gif": "image/gif", "webp": "image/webp"}


def init_storage(force: bool = False):
    global _storage_key
    if _storage_key and not force:
        return _storage_key
    resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_LLM_KEY}, timeout=30)
    resp.raise_for_status()
    _storage_key = resp.json()["storage_key"]
    return _storage_key


def put_object(path: str, data: bytes, content_type: str) -> dict:
    key = init_storage()
    resp = requests.put(f"{STORAGE_URL}/objects/{path}",
                        headers={"X-Storage-Key": key, "Content-Type": content_type},
                        data=data, timeout=120)
    if resp.status_code == 404:
        key = init_storage(force=True)
        resp = requests.put(f"{STORAGE_URL}/objects/{path}",
                            headers={"X-Storage-Key": key, "Content-Type": content_type},
                            data=data, timeout=120)
    resp.raise_for_status()
    return resp.json()


def get_object(path: str):
    key = init_storage()
    resp = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=60)
    if resp.status_code == 404:
        key = init_storage(force=True)
        resp = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=60)
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")


# --- Mongo base model ---
def _validate_object_id(v: Any) -> str:
    return str(v)

PyObjectId = Annotated[str, BeforeValidator(_validate_object_id)]


# --- Models ---
class CardBack(BaseModel):
    style: str = "classic"
    color: str = "#7f1d1d"
    emblem: str = "flame"
    motto: str = ""


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
    back: CardBack = Field(default_factory=CardBack)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CardCreate(BaseModel):
    type: str
    custom_type: Optional[str] = None
    name: str = ""
    description: str = ""
    story: str = ""
    language: str = "it"
    attributes: dict = Field(default_factory=dict)
    artwork_path: Optional[str] = None
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
    back: Optional[CardBack] = None


class RegisterInput(BaseModel):
    email: EmailStr
    password: str
    name: str


class LoginInput(BaseModel):
    email: EmailStr
    password: str


class GenerateContentInput(BaseModel):
    type: str
    custom_type: Optional[str] = None
    prompt: str
    language: str = "it"


class GenerateImageInput(BaseModel):
    prompt: str
    type: Optional[str] = None


class User(BaseModel):
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    auth_provider: str = "email"


# --- App ---
app = FastAPI()
api_router = APIRouter(prefix="/api")


@app.on_event("startup")
async def startup():
    try:
        init_storage()
        logger.info("Storage initialized")
    except Exception as e:
        logger.error(f"Storage init failed: {e}")


# --- Auth helpers ---
def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def verify_password(pw: str, hashed: str) -> bool:
    return bcrypt.checkpw(pw.encode(), hashed.encode())


def create_jwt(user_id: str) -> str:
    payload = {"user_id": user_id, "exp": datetime.now(timezone.utc) + timedelta(days=7)}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


async def get_current_user(request: Request) -> User:
    token = request.cookies.get("session_token")
    if not token:
        auth = request.headers.get("Authorization")
        if auth and auth.startswith("Bearer "):
            token = auth.split(" ", 1)[1]
    if not token:
        raise HTTPException(status_code=401, detail="Non autenticato")

    # Try google session first
    session = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if session:
        expires_at = session["expires_at"]
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=401, detail="Sessione scaduta")
        user_doc = await db.users.find_one({"user_id": session["user_id"]}, {"_id": 0})
        if user_doc:
            return User(**user_doc)

    # Try JWT
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
        user_doc = await db.users.find_one({"user_id": payload["user_id"]}, {"_id": 0})
        if user_doc:
            return User(**user_doc)
    except jwt.PyJWTError:
        pass
    raise HTTPException(status_code=401, detail="Token non valido")


# --- Auth routes ---
@api_router.post("/auth/register")
async def register(body: RegisterInput):
    existing = await db.users.find_one({"email": body.email.lower()})
    if existing:
        raise HTTPException(status_code=400, detail="Email già registrata")
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    await db.users.insert_one({
        "user_id": user_id,
        "email": body.email.lower(),
        "name": body.name,
        "picture": None,
        "auth_provider": "email",
        "password_hash": hash_password(body.password),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    token = create_jwt(user_id)
    return {"token": token, "user": {"user_id": user_id, "email": body.email.lower(), "name": body.name, "picture": None, "auth_provider": "email"}}


@api_router.post("/auth/login")
async def login(body: LoginInput):
    user_doc = await db.users.find_one({"email": body.email.lower()})
    if not user_doc or not user_doc.get("password_hash"):
        raise HTTPException(status_code=401, detail="Credenziali non valide")
    if not verify_password(body.password, user_doc["password_hash"]):
        raise HTTPException(status_code=401, detail="Credenziali non valide")
    token = create_jwt(user_doc["user_id"])
    return {"token": token, "user": {"user_id": user_doc["user_id"], "email": user_doc["email"], "name": user_doc["name"], "picture": user_doc.get("picture"), "auth_provider": "email"}}


@api_router.post("/auth/google-session")
async def google_session(request: Request, response: Response):
    session_id = request.headers.get("X-Session-ID")
    if not session_id:
        raise HTTPException(status_code=400, detail="Session ID mancante")
    resp = requests.get("https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
                        headers={"X-Session-ID": session_id}, timeout=30)
    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Sessione Google non valida")
    data = resp.json()
    email = data["email"].lower()
    existing = await db.users.find_one({"email": email}, {"_id": 0})
    if existing:
        user_id = existing["user_id"]
        await db.users.update_one({"user_id": user_id}, {"$set": {"name": data.get("name"), "picture": data.get("picture")}})
    else:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        await db.users.insert_one({
            "user_id": user_id, "email": email, "name": data.get("name"),
            "picture": data.get("picture"), "auth_provider": "google",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    session_token = data["session_token"]
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    await db.user_sessions.insert_one({
        "user_id": user_id, "session_token": session_token,
        "expires_at": expires_at.isoformat(), "created_at": datetime.now(timezone.utc).isoformat(),
    })
    response.set_cookie("session_token", session_token, httponly=True, secure=True, samesite="none", path="/", max_age=7 * 24 * 60 * 60)
    return {"user": {"user_id": user_id, "email": email, "name": data.get("name"), "picture": data.get("picture"), "auth_provider": "google"}, "session_token": session_token}


@api_router.get("/auth/me")
async def auth_me(user: User = Depends(get_current_user)):
    return user


@api_router.post("/auth/logout")
async def logout(request: Request, response: Response):
    token = request.cookies.get("session_token")
    if token:
        await db.user_sessions.delete_one({"session_token": token})
    response.delete_cookie("session_token", path="/")
    return {"ok": True}


# --- AI routes ---
def _ai_error(e: Exception, fallback: str):
    msg = str(e).lower()
    if any(k in msg for k in ["budget", "quota", "insufficient", "exceeded", "402", "payment", "credit", "balance"]):
        return HTTPException(status_code=402, detail="Credito AI esaurito. Ricarica la Universal Key da Profilo → Manage plan → Universal Key → Add Balance.")
    return HTTPException(status_code=502, detail=fallback)


TYPE_LABELS = {
    "spell": "Magia/Incantesimo", "class": "Classe", "race": "Razza", "weapon": "Arma",
    "feat": "Talento", "monster": "Mostro/Nemico", "character": "Personaggio", "custom": "Tipo personalizzato",
}

TYPE_SCHEMAS = {
    "spell": '"attributes": {"livello": "", "scuola": "", "azione": "(Azione, Azione bonus o Reazione)", "tempo_lancio": "", "gittata": "", "area": "(es. Sfera 6 m, oppure - se a bersaglio singolo)", "componenti": "", "durata": "", "concentrazione": "(Sì o No)", "danno": "(es. 8d6 fuoco, oppure - se non infligge danni)", "effetto": ""}',
    "class": '"attributes": {"dado_vita": "", "abilita_primaria": "", "tiri_salvezza": "", "competenze": "", "caratteristiche": ["tratto1", "tratto2"]}',
    "race": '"attributes": {"bonus_caratteristiche": "", "velocita": "", "taglia": "", "linguaggi": "", "tratti": ["tratto1", "tratto2"]}',
    "weapon": '"attributes": {"danno": "", "tipo_danno": "", "proprieta": "", "peso": "", "costo": "", "categoria": ""}',
    "feat": '"attributes": {"prerequisito": "", "benefici": ["beneficio1", "beneficio2"]}',
    "monster": '"attributes": {"classe_armatura": "", "punti_ferita": "", "velocita": "", "for": "", "des": "", "cos": "", "int": "", "sag": "", "car": "", "tiri_salvezza": "", "resistenze": "", "vulnerabilita": "", "immunita": "", "sensi": "", "linguaggi": "", "grado_sfida": "", "azioni": [{"nome": "", "descrizione": ""}]}',
    "character": '"attributes": {"classe": "", "razza": "", "livello": "", "for": "", "des": "", "cos": "", "int": "", "sag": "", "car": "", "bonus_competenza": "", "classe_armatura": "", "punti_ferita": "", "cd_incantesimi": "", "competenze": "", "abilita_sottoclasse": ["abilita1"], "slot_incantesimi": [{"livello": 1, "totale": 2}]}',
    "custom": '"attributes": {"campo1": "", "campo2": ""}',
}


@api_router.post("/ai/generate-content")
async def generate_content(body: GenerateContentInput, user: User = Depends(get_current_user)):
    type_label = body.custom_type if body.type == "custom" and body.custom_type else TYPE_LABELS.get(body.type, body.type)
    lang = "italiano" if body.language == "it" else "inglese"
    schema = TYPE_SCHEMAS.get(body.type, TYPE_SCHEMAS["custom"])
    system = (
        f"Sei un maestro creatore di contenuti per Dungeons & Dragons 5e. "
        f"Genera contenuti coerenti, bilanciati e in lingua {lang}. "
        f"Rispondi SEMPRE ed ESCLUSIVAMENTE con un oggetto JSON valido, senza testo aggiuntivo, senza markdown, senza ```."
    )
    user_prompt = (
        f"Crea una carta di tipo '{type_label}' per D&D basata su questa richiesta: \"{body.prompt}\".\n"
        f"Restituisci un JSON con questa struttura esatta (in {lang}):\n"
        f'{{"name": "nome della carta", "description": "descrizione evocativa (max 3 frasi)", '
        f'"story": "breve storia/lore (max 4 frasi)", {schema}}}\n'
        f"Compila tutti i campi con valori realistici e coerenti con le regole D&D 5e. Le liste devono contenere elementi pertinenti."
    )
    try:
        chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"gen-{uuid.uuid4().hex[:8]}", system_message=system)
        chat.with_model("gemini", TEXT_MODEL)
        raw = await chat.send_message(UserMessage(text=user_prompt))
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("```")[1] if "```" in text else text
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1:
            text = text[start:end + 1]
        data = json.loads(text)
        return {
            "name": data.get("name", ""),
            "description": data.get("description", ""),
            "story": data.get("story", ""),
            "attributes": data.get("attributes", {}),
        }
    except json.JSONDecodeError:
        logger.error(f"JSON parse failed: {text[:200]}")
        raise HTTPException(status_code=502, detail="Generazione AI non valida, riprova")
    except Exception as e:
        logger.error(f"AI content error: {e}")
        raise _ai_error(e, "Errore nella generazione AI")


@api_router.post("/ai/generate-image")
async def generate_image(body: GenerateImageInput, user: User = Depends(get_current_user)):
    type_hint = TYPE_LABELS.get(body.type or "", "")
    art_prompt = (
        f"Epic dark fantasy trading card artwork, Dungeons and Dragons style, for: {body.prompt}. "
        f"{('Subject category: ' + type_hint + '. ') if type_hint else ''}"
        f"Highly detailed digital painting, dramatic lighting, obsidian and antique gold and crimson palette, "
        f"ornate, cinematic, no text, no borders, no watermark, portrait orientation."
    )
    try:
        chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"img-{uuid.uuid4().hex[:8]}", system_message="You are a master fantasy illustrator.")
        chat.with_model("gemini", IMAGE_MODEL).with_params(modalities=["image", "text"])
        _, images = await chat.send_message_multimodal_response(UserMessage(text=art_prompt))
        if not images:
            raise HTTPException(status_code=502, detail="Nessuna immagine generata")
        img = images[0]
        img_bytes = base64.b64decode(img["data"])
        ext = "png" if "png" in img["mime_type"] else "jpg"
        path = f"{APP_NAME}/artwork/{user.user_id}/{uuid.uuid4()}.{ext}"
        result = put_object(path, img_bytes, img["mime_type"])
        await db.files.insert_one({
            "id": str(uuid.uuid4()), "storage_path": result["path"], "user_id": user.user_id,
            "content_type": img["mime_type"], "is_deleted": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        return {"artwork_path": result["path"]}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AI image error: {e}")
        raise _ai_error(e, "Errore nella generazione immagine")


# --- File routes ---
@api_router.post("/upload")
async def upload(file: UploadFile = File(...), user: User = Depends(get_current_user)):
    ext = (file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "png")
    content_type = MIME_TYPES.get(ext, file.content_type or "application/octet-stream")
    path = f"{APP_NAME}/uploads/{user.user_id}/{uuid.uuid4()}.{ext}"
    data = await file.read()
    result = put_object(path, data, content_type)
    await db.files.insert_one({
        "id": str(uuid.uuid4()), "storage_path": result["path"], "user_id": user.user_id,
        "original_filename": file.filename, "content_type": content_type, "is_deleted": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"artwork_path": result["path"]}


@api_router.get("/files/{path:path}")
async def download(path: str, authorization: str = Header(None), auth: str = Query(None)):
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
    elif auth:
        token = auth
    if not token:
        raise HTTPException(status_code=401, detail="Non autorizzato")
    record = await db.files.find_one({"storage_path": path, "is_deleted": False}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="File non trovato")
    data, content_type = get_object(path)
    return Response(content=data, media_type=record.get("content_type", content_type))


# --- Card routes ---
@api_router.post("/cards", response_model=Card)
async def create_card(body: CardCreate, user: User = Depends(get_current_user)):
    card = Card(user_id=user.user_id, **body.model_dump(exclude_none=True))
    await db.cards.insert_one(card.model_dump())
    return card


@api_router.get("/cards", response_model=List[Card])
async def list_cards(type: Optional[str] = None, search: Optional[str] = None, user: User = Depends(get_current_user)):
    query = {"user_id": user.user_id}
    if type and type != "all":
        query["type"] = type
    if search:
        query["name"] = {"$regex": search, "$options": "i"}
    docs = await db.cards.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return [Card(**d) for d in docs]


@api_router.get("/cards/{card_id}", response_model=Card)
async def get_card(card_id: str, user: User = Depends(get_current_user)):
    doc = await db.cards.find_one({"id": card_id, "user_id": user.user_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Carta non trovata")
    return Card(**doc)


@api_router.put("/cards/{card_id}", response_model=Card)
async def update_card(card_id: str, body: CardUpdate, user: User = Depends(get_current_user)):
    doc = await db.cards.find_one({"id": card_id, "user_id": user.user_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Carta non trovata")
    updates = body.model_dump(exclude_none=True)
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.cards.update_one({"id": card_id, "user_id": user.user_id}, {"$set": updates})
    doc.update(updates)
    return Card(**doc)


@api_router.delete("/cards/{card_id}")
async def delete_card(card_id: str, user: User = Depends(get_current_user)):
    result = await db.cards.delete_one({"id": card_id, "user_id": user.user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Carta non trovata")
    return {"ok": True}


@api_router.get("/")
async def root():
    return {"message": "TomeForge API"}


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
