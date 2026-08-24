import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

import server
import services.payments as payments_mod


class FakeUsers:
    def __init__(self):
        self.updates = []

    async def update_one(self, query, update):
        self.updates.append((query, update))


class FakeDatabase:
    def __init__(self):
        self.users = FakeUsers()


def test_subscription_sync_uses_stripe_period_end(monkeypatch):
    fake_db = FakeDatabase()
    end = 1_800_000_000
    subscription = SimpleNamespace(
        metadata={"user_id": "user_123"},
        customer="cus_123",
        current_period_end=end,
        items=SimpleNamespace(data=[]),
    )
    monkeypatch.setattr(server.stripe.Subscription, "retrieve", lambda subscription_id: subscription)

    synced_user = asyncio.run(server.sync_subscription_entitlement("sub_123", db=fake_db))

    assert synced_user == "user_123"
    query, update = fake_db.users.updates[0]
    assert query == {"user_id": "user_123"}
    assert update["$set"]["stripe_subscription_id"] == "sub_123"
    assert update["$set"]["premium_until"] == datetime.fromtimestamp(end, tz=timezone.utc).isoformat()


def test_subscription_cancellation_revokes_automatic_entitlement(monkeypatch):
    fake_db = FakeDatabase()

    revoked_user = asyncio.run(server.revoke_subscription_entitlement({"metadata": {"user_id": "user_456"}}, db=fake_db))

    assert revoked_user == "user_456"
    query, update = fake_db.users.updates[0]
    assert query == {"user_id": "user_456"}
    assert update["$set"]["stripe_subscription_id"] is None
    assert datetime.fromisoformat(update["$set"]["premium_until"]).tzinfo is not None