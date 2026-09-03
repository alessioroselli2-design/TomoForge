from fastapi import APIRouter, Depends, HTTPException

from core.auth import compute_premium, require_admin
from core.db import get_db, SupabaseDatabase
from schemas.payments import PremiumToggle
from schemas.library import CanonicalizationRunInput, TranslationVerificationRunInput
from schemas.users import User
from services.canonical import (
    CanonicalizationBlockedError,
    canonicalization_status,
    run_canonicalization,
)
from services.translation_review import translation_review_status, run_translation_reviews

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


@router.get("/admin/translation-verification/status")
async def admin_translation_verification_status(
    user_id: str | None = None,
    admin: User = Depends(require_admin),
    db: SupabaseDatabase = Depends(get_db),
):
    return await translation_review_status(user_id or admin.user_id, db=db)


@router.post("/admin/translation-verification/run")
async def admin_run_translation_verification(
    body: TranslationVerificationRunInput,
    admin: User = Depends(require_admin),
    db: SupabaseDatabase = Depends(get_db),
):
    return await run_translation_reviews(
        body.user_id or admin.user_id, db=db, batch_size=body.batch_size
    )


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
    try:
        return await run_canonicalization(
            body.user_id or admin.user_id, db=db, batch_size=body.batch_size, ruleset=body.ruleset
        )
    except CanonicalizationBlockedError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "translation_verification_incomplete",
                "message": "Completa traduzioni e verifica AI prima della canonicalizzazione.",
                "translation_status": exc.translation_status,
            },
        ) from exc
