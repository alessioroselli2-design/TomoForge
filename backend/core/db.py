import copy
import logging
from typing import Any, Optional

from fastapi import HTTPException
from supabase import Client, create_client

from core.config import (
    MOCK_DATA, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY,
    SUPABASE_ANON_KEY, SUPABASE_STORAGE_BUCKET,
)

logger = logging.getLogger("tomeforge")


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
            self.client.table(self.name).insert(documents).execute()

    async def update_one(self, query: dict, update: dict) -> UpdateResult:
        changes = update.get("$set", update)
        statement = self.apply_filters(self.client.table(self.name).update(changes), query)
        # `users` is keyed by `user_id`; every other collection currently
        # exposes the conventional `id` primary key.
        result = statement.select("user_id" if self.name == "users" else "id").execute()
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


def get_db() -> SupabaseDatabase:
    """FastAPI dependency: return the shared database singleton."""
    return db


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
