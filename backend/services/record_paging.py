"""Bounded pagination helpers for Supabase-compatible collections."""
from __future__ import annotations

from typing import Any

DEFAULT_PAGE_SIZE = 1000
DEFAULT_MAXIMUM = 100_000


async def list_collection_rows(
    collection,
    query: dict[str, Any],
    *,
    page_size: int = DEFAULT_PAGE_SIZE,
    maximum: int = DEFAULT_MAXIMUM,
) -> list[dict]:
    """Return all matching rows without a silent single-request cutoff."""
    if page_size < 1:
        raise ValueError("page_size_must_be_positive")
    if maximum < 1:
        raise ValueError("maximum_must_be_positive")

    records: list[dict] = []
    cursor = collection.find(query)
    while True:
        page = await cursor.to_list(page_size, offset=len(records))
        if len(records) + len(page) > maximum:
            raise RuntimeError("collection_record_limit_exceeded")
        records.extend(page)
        if len(page) < page_size:
            return records
        if len(records) == maximum:
            extra = await cursor.to_list(1, offset=len(records))
            if extra:
                raise RuntimeError("collection_record_limit_exceeded")
            return records
