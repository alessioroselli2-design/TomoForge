from fastapi import APIRouter, Depends, HTTPException

from core.auth import compute_premium, require_admin
from core.db import get_db, SupabaseDatabase
from schemas.payments import PremiumToggle
from schemas.library import CanonicalizationRunInput
from schemas.users import User
from services.canonical import canonicalization_status, run_canonicalization

router = APIRouter()


@router.get("/admin/users")
async def admin_list_users(admin: User = Depends(require_admin), db: SupabaseDatabase = Depends(get_db)):
    users = await db.users.find({}, {"password_hash": 0}).sort("created_at", -1).to_list(1000)
    return [{**item, "is_premium": compute_premium(User(**item))} for item in users]


@router.post("/admin/users/{uid}/premium")
async def admin_set_premium(uid: str, body: PremiumToggle, admin: User = Depends(require_admin), db: SupabaseDatabase = Depends(get_db)):
    result = await db.users.update_one({"user_id": uid}, {"$set": {"premium_manual": body.enabled}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Utente non trovato")
    return {"ok": True}


@router.get("/admin/canonicalization/status")
async def admin_canonicalization_status(
    user_id: str | None = None,
    admin: User = Depends(require_admin),
    db: SupabaseDatabase = Depends(get_db),
):
    return await canonicalization_status(user_id or admin.user_id, db=db)


@router.post("/admin/canonicalization/run")
async def admin_run_canonicalization(
    body: CanonicalizationRunInput,
    admin: User = Depends(require_admin),
    db: SupabaseDatabase = Depends(get_db),
):
    return await run_canonicalization(
        body.user_id or admin.user_id, db=db, batch_size=body.batch_size, ruleset=body.ruleset
    )
