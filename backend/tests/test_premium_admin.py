"""
Backend tests for TomeForge Premium + Admin flow (iteration 8).

Covers the review_request items:
- Non-premium user AI endpoints gated by 402
- Admin login / /api/auth/me / /api/admin/users listing
- Non-admin cannot list /api/admin/users
- Admin can toggle premium ON/OFF for a user
- Stripe subscription checkout returns a real checkout.stripe.com URL
- /api/payments/status returns pending for unpaid session

IMPORTANT: leaves `mago@grimorio.it` as NON-premium at the end (premium_manual=false).
Does NOT actually call /api/ai/generate-content while user is premium (that would
consume real Emergent credits and is covered separately from the UI test).
"""
import os
import requests
import pytest
from pathlib import Path

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL')
if not BASE_URL:
    for line in Path('/app/frontend/.env').read_text().splitlines():
        if line.startswith('REACT_APP_BACKEND_URL='):
            BASE_URL = line.split('=', 1)[1].strip()
            break
BASE_URL = BASE_URL.rstrip('/')
API = f"{BASE_URL}/api"
ORIGIN = BASE_URL  # used for Stripe origin_url

MAGO_EMAIL = "mago@grimorio.it"
MAGO_PASSWORD = "arcano123"
ADMIN_EMAIL = "admin@tomeforge.it"
ADMIN_PASSWORD = "TomeAdmin2026!"


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=20)
    assert r.status_code == 200, f"login {email} failed: {r.status_code} {r.text}"
    return r.json()["token"], r.json()["user"]


@pytest.fixture(scope="module")
def mago_auth():
    tok, user = _login(MAGO_EMAIL, MAGO_PASSWORD)
    return {"token": tok, "user": user, "headers": {"Authorization": f"Bearer {tok}"}}


@pytest.fixture(scope="module")
def admin_auth():
    tok, user = _login(ADMIN_EMAIL, ADMIN_PASSWORD)
    return {"token": tok, "user": user, "headers": {"Authorization": f"Bearer {tok}"}}


@pytest.fixture(scope="module")
def mago_user_id(mago_auth):
    r = requests.get(f"{API}/auth/me", headers=mago_auth["headers"], timeout=20)
    assert r.status_code == 200
    return r.json()["user_id"]


# ---------- 1. Auth / me flags ----------
class TestAuthMeFlags:
    def test_mago_me_flags(self, mago_auth):
        r = requests.get(f"{API}/auth/me", headers=mago_auth["headers"], timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert d["email"] == MAGO_EMAIL
        assert d.get("is_admin") in (False, None), f"mago should not be admin: {d}"
        assert d.get("is_premium") is False, f"mago should NOT be premium at test start: {d}"

    def test_admin_me_flags(self, admin_auth):
        r = requests.get(f"{API}/auth/me", headers=admin_auth["headers"], timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert d["email"] == ADMIN_EMAIL
        assert d.get("is_admin") is True
        assert d.get("is_premium") is True


# ---------- 2. Non-premium AI gating (402) ----------
class TestAIPremiumGate:
    def test_generate_content_402_for_non_premium(self, mago_auth):
        r = requests.post(f"{API}/ai/generate-content",
                          headers=mago_auth["headers"],
                          json={"type": "spell", "prompt": "test prompt", "language": "it"},
                          timeout=30)
        assert r.status_code == 402, f"expected 402, got {r.status_code}: {r.text}"
        assert "Premium" in r.json().get("detail", "")

    def test_generate_image_402_for_non_premium(self, mago_auth):
        r = requests.post(f"{API}/ai/generate-image",
                          headers=mago_auth["headers"],
                          json={"prompt": "test", "type": "spell"},
                          timeout=30)
        assert r.status_code == 402, f"expected 402, got {r.status_code}: {r.text}"
        assert "Premium" in r.json().get("detail", "")

    def test_ai_endpoints_require_auth(self):
        r = requests.post(f"{API}/ai/generate-content",
                          json={"type": "spell", "prompt": "x", "language": "it"},
                          timeout=15)
        assert r.status_code == 401


# ---------- 3. Admin endpoints ----------
class TestAdminEndpoints:
    def test_non_admin_cannot_list_users(self, mago_auth):
        r = requests.get(f"{API}/admin/users", headers=mago_auth["headers"], timeout=20)
        assert r.status_code == 403

    def test_admin_lists_users(self, admin_auth, mago_user_id):
        r = requests.get(f"{API}/admin/users", headers=admin_auth["headers"], timeout=20)
        assert r.status_code == 200
        users = r.json()
        assert isinstance(users, list) and len(users) >= 2
        # find mago
        mago = next((u for u in users if u.get("user_id") == mago_user_id), None)
        assert mago is not None, "mago not found in admin list"
        assert "is_premium" in mago
        assert "premium_manual" in mago
        assert mago["premium_manual"] is False
        assert mago["is_premium"] is False
        # find admin
        admin_row = next((u for u in users if u.get("email") == ADMIN_EMAIL), None)
        assert admin_row is not None
        assert admin_row.get("is_admin") is True
        assert admin_row.get("is_premium") is True

    def test_toggle_premium_on_off(self, admin_auth, mago_auth, mago_user_id):
        # ---- Turn ON ----
        r = requests.post(f"{API}/admin/users/{mago_user_id}/premium",
                          headers=admin_auth["headers"], json={"enabled": True}, timeout=20)
        assert r.status_code == 200, r.text
        # verify /auth/me flip
        me = requests.get(f"{API}/auth/me", headers=mago_auth["headers"], timeout=20).json()
        assert me.get("is_premium") is True, f"expected is_premium True after grant, got {me}"

        # Verify AI endpoint no longer 402 (we don't fully invoke to save credits — try a
        # minimal request and only assert that the response is NOT 402). To keep costs
        # low we assert the status code is NOT the premium-gate 402.
        # NOTE: since a real Gemini call would spend credits, we use a very short prompt
        # BUT we still make the call — that is what proves premium is truly lifted.
        # To fully avoid spend we assert only "not 402".
        # ---> we skip actually calling the AI to keep this backend test cheap; the
        # frontend playwright will drive one real generation.

        # ---- Turn OFF ----
        r = requests.post(f"{API}/admin/users/{mago_user_id}/premium",
                          headers=admin_auth["headers"], json={"enabled": False}, timeout=20)
        assert r.status_code == 200
        me = requests.get(f"{API}/auth/me", headers=mago_auth["headers"], timeout=20).json()
        assert me.get("is_premium") is False

        # AI endpoint should be 402 again
        r = requests.post(f"{API}/ai/generate-content",
                          headers=mago_auth["headers"],
                          json={"type": "spell", "prompt": "x", "language": "it"},
                          timeout=20)
        assert r.status_code == 402

    def test_toggle_premium_unknown_user_404(self, admin_auth):
        r = requests.post(f"{API}/admin/users/nonexistent/premium",
                          headers=admin_auth["headers"], json={"enabled": True}, timeout=20)
        assert r.status_code == 404


# ---------- 4. Stripe checkout ----------
class TestStripeCheckout:
    def test_checkout_returns_stripe_url(self, mago_auth):
        r = requests.post(f"{API}/payments/checkout",
                          headers=mago_auth["headers"],
                          json={"lookup_key": "premium_monthly", "origin_url": ORIGIN},
                          timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "checkout_url" in data
        assert "session_id" in data
        assert data["checkout_url"].startswith("https://checkout.stripe.com/"), \
            f"expected checkout.stripe.com URL, got {data['checkout_url']}"
        assert data["session_id"].startswith("cs_"), f"expected cs_* session_id, got {data['session_id']}"
        # persist for next test
        TestStripeCheckout._session_id = data["session_id"]

    def test_payment_status_pending_before_pay(self, mago_auth):
        sid = getattr(TestStripeCheckout, "_session_id", None)
        if not sid:
            pytest.skip("no session id from previous test")
        r = requests.get(f"{API}/payments/status/{sid}", timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["session_id"] == sid
        # unpaid
        assert d["payment_status"] in ("pending", "unpaid"), f"unexpected payment_status: {d}"

    def test_payment_status_unknown_404(self):
        r = requests.get(f"{API}/payments/status/cs_test_nonexistent_session", timeout=20)
        assert r.status_code == 404


# ---------- 5. Regression: public card still works ----------
class TestPublicCardRegression:
    def test_public_card_still_reachable(self, mago_auth):
        r = requests.get(f"{API}/cards", headers=mago_auth["headers"], timeout=20)
        assert r.status_code == 200
        cards = r.json()
        if not cards:
            pytest.skip("no cards to check")
        card_id = cards[0]["id"]
        # unauth
        r = requests.get(f"{API}/public/cards/{card_id}", timeout=20)
        assert r.status_code == 200
        data = r.json()
        assert "user_id" not in data


# ---------- 6. Cleanup: ensure mago left non-premium ----------
class TestCleanup:
    def test_final_state_mago_not_premium(self, admin_auth, mago_auth, mago_user_id):
        # force-off just in case
        requests.post(f"{API}/admin/users/{mago_user_id}/premium",
                      headers=admin_auth["headers"], json={"enabled": False}, timeout=20)
        me = requests.get(f"{API}/auth/me", headers=mago_auth["headers"], timeout=20).json()
        assert me.get("is_premium") is False, f"mago must be left non-premium: {me}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
