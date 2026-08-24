import logging
from datetime import datetime, timezone
from typing import Any, Optional

import stripe

from core.config import utc_now
from core.db import db as _singleton_db

logger = logging.getLogger("tomeforge")


def require_stripe() -> None:
    from fastapi import HTTPException
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


async def sync_subscription_entitlement(subscription_id: str, fallback_user_id: Optional[str] = None, *, db=None) -> Optional[str]:
    """Synchronize Premium access from Stripe's actual subscription period."""
    _db = db if db is not None else _singleton_db
    subscription = stripe.Subscription.retrieve(subscription_id)
    metadata = stripe_field(subscription, "metadata", {}) or {}
    user_id = stripe_field(metadata, "user_id") or fallback_user_id
    premium_until = premium_until_from_subscription(subscription)
    if not user_id or not premium_until:
        logger.warning("Could not sync Stripe subscription %s: missing user or period end", subscription_id)
        return None
    await _db.users.update_one(
        {"user_id": user_id},
        {"$set": {
            "premium_until": premium_until,
            "stripe_subscription_id": subscription_id,
            "stripe_customer_id": stripe_field(subscription, "customer"),
        }},
    )
    return user_id


async def revoke_subscription_entitlement(subscription: Any, *, db=None) -> Optional[str]:
    _db = db if db is not None else _singleton_db
    metadata = stripe_field(subscription, "metadata", {}) or {}
    user_id = stripe_field(metadata, "user_id")
    if not user_id:
        return None
    await _db.users.update_one(
        {"user_id": user_id},
        {"$set": {
            "premium_until": datetime.now(timezone.utc).isoformat(),
            "stripe_subscription_id": None,
        }},
    )
    return user_id
