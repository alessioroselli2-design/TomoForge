import logging

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request

from core.auth import get_current_user
from core.config import STRIPE_WEBHOOK_SECRET, utc_now
from core.db import db
from schemas.payments import CheckoutRequest
from schemas.users import User
from services.payments import (
    require_stripe,
    revoke_subscription_entitlement,
    stripe_field,
    sync_subscription_entitlement,
)

router = APIRouter()
logger = logging.getLogger("tomeforge")


@router.post("/payments/checkout")
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


@router.get("/payments/status/{session_id}")
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


@router.post("/stripe/webhook")
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


@router.get("/")
async def root():
    return {"message": "TomeForge API", "health": "/api/health"}
