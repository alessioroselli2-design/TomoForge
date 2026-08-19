"""One-time, idempotent Mongo/Object Storage -> Supabase migration for TomeForge.

Run with --dry-run first. This program never deletes legacy or Supabase data.
"""
import argparse
import os
from datetime import date, datetime
from urllib.parse import quote

import requests
from pymongo import MongoClient
from supabase import create_client


def env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def json_value(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, list):
        return [json_value(item) for item in value]
    if isinstance(value, dict):
        return {key: json_value(item) for key, item in value.items()}
    return value


def select(document, fields):
    return {field: json_value(document[field]) for field in fields if field in document and document[field] is not None}


def legacy_storage_key(base_url: str) -> str:
    direct_key = os.getenv("LEGACY_STORAGE_KEY")
    if direct_key:
        return direct_key
    response = requests.post(
        f"{base_url.rstrip('/')}/init",
        json={"emergent_key": env("LEGACY_EMERGENT_LLM_KEY")},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["storage_key"]


def main():
    parser = argparse.ArgumentParser(description="Migrate TomeForge data to Supabase without deleting source data.")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be copied without writing to Supabase.")
    parser.add_argument("--skip-assets", action="store_true", help="Migrate database records only; do not copy artwork bytes.")
    args = parser.parse_args()

    source = MongoClient(env("LEGACY_MONGO_URL"))[env("LEGACY_DB_NAME")]
    target = create_client(env("SUPABASE_URL"), env("SUPABASE_SERVICE_ROLE_KEY"))
    bucket = os.getenv("SUPABASE_STORAGE_BUCKET", "tomeforge-assets")

    user_fields = {
        "user_id", "email", "name", "picture", "auth_provider", "password_hash",
        "is_admin", "premium_manual", "premium_until", "stripe_subscription_id",
        "stripe_customer_id", "created_at",
    }
    card_fields = {
        "id", "user_id", "type", "custom_type", "name", "description", "story",
        "language", "attributes", "artwork_path", "frame", "appearance", "back", "created_at", "updated_at",
    }
    payment_fields = {
        "session_id", "user_id", "lookup_key", "amount", "currency", "status",
        "payment_status", "stripe_subscription_id", "created_at", "updated_at",
    }

    counts = {"users": 0, "cards": 0, "payments": 0, "files": 0, "assets": 0}
    for document in source.users.find({}):
        record = select(document, user_fields)
        if not record.get("user_id") or not record.get("email"):
            raise SystemExit(f"Cannot migrate user without user_id/email: {document.get('_id')}")
        counts["users"] += 1
        if not args.dry_run:
            target.table("users").upsert(record, on_conflict="user_id").execute()

    for document in source.cards.find({}):
        record = select(document, card_fields)
        record.setdefault("id", str(document["_id"]))
        record.setdefault("frame", "gold")
        record.setdefault("appearance", {
            "title_effect": "gold",
            "title_shadow": True,
            "description_opacity": 0.64,
            "text_panel_color": "#05080a",
            "text_color": "#f5f1df",
            "front_background_start": "#151311",
            "front_background_end": "#151311",
            "front_background_gradient": False,
            "title_custom_color_enabled": False,
            "title_custom_color": "#f8d764",
            "frame_custom_color_enabled": False,
            "frame_custom_color": "#d4af37",
        })
        record.setdefault("back", {"style": "classic", "color": "#7f1d1d", "emblem": "flame", "motto": ""})
        if not record.get("user_id") or not record.get("type"):
            raise SystemExit(f"Cannot migrate card without owner/type: {document.get('_id')}")
        counts["cards"] += 1
        if not args.dry_run:
            target.table("cards").upsert(record, on_conflict="id").execute()

    for document in source.payment_transactions.find({}):
        record = select(document, payment_fields)
        if not record.get("session_id") or not record.get("user_id"):
            raise SystemExit(f"Cannot migrate payment without session/owner: {document.get('_id')}")
        counts["payments"] += 1
        if not args.dry_run:
            target.table("payment_transactions").upsert(record, on_conflict="session_id").execute()

    storage_base = os.getenv("LEGACY_STORAGE_URL")
    storage_key = None
    for document in source.files.find({"is_deleted": {"$ne": True}}):
        path = document.get("storage_path")
        if not path or not document.get("user_id"):
            raise SystemExit(f"Cannot migrate file without path/owner: {document.get('_id')}")
        record = {
            "id": str(document.get("id") or document["_id"]), "storage_path": path,
            "user_id": document["user_id"], "original_filename": document.get("original_filename"),
            "content_type": document.get("content_type", "application/octet-stream"),
            "is_deleted": False, "created_at": json_value(document.get("created_at")),
        }
        counts["files"] += 1
        if not args.skip_assets:
            if not storage_base:
                raise SystemExit("LEGACY_STORAGE_URL is required unless --skip-assets is used")
            storage_key = storage_key or legacy_storage_key(storage_base)
            response = requests.get(
                f"{storage_base.rstrip('/')}/objects/{quote(path, safe='/')}",
                headers={"X-Storage-Key": storage_key},
                timeout=120,
            )
            response.raise_for_status()
            if not args.dry_run:
                target.storage.from_(bucket).upload(path, response.content, {
                    "content-type": record["content_type"], "upsert": "true",
                })
            counts["assets"] += 1
        if not args.dry_run:
            target.table("files").upsert(record, on_conflict="storage_path").execute()

    mode = "DRY RUN — no data written" if args.dry_run else "MIGRATION COMPLETE"
    print(f"{mode}: " + ", ".join(f"{key}={value}" for key, value in counts.items()))


if __name__ == "__main__":
    main()