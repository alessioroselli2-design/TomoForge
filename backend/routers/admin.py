from fastapi import APIRouter, Depends, HTTPException

from core.auth import compute_premium, require_admin
from core.db import db
from schemas.payments import PremiumToggle
from schemas.users import User

router = APIRouter()


@router.get("/admin/users")
async def admin_list_users(admin: User = Depends(require_admin)):
    users = await db.users.find({}, {"password_hash": 0}).sort("created_at", -1).to_list(1000)
    return [{**item, "is_premium": compute_premium(User(**item))} for item in users]


@router.post("/admin/users/{uid}/premium")
async def admin_set_premium(uid: str, body: PremiumToggle, admin: User = Depends(require_admin)):
    result = await db.users.update_one({"user_id": uid}, {"$set": {"premium_manual": body.enabled}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Utente non trovato")
    return {"ok": True}
