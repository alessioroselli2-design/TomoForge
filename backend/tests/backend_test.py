"""
TomeForge backend tests.
Covers: auth (register/login/me), cards CRUD, AI text (OpenAI),
AI image (OpenAI Images) + Supabase Storage, file upload/download.
"""
import io
import os
import uuid
import hashlib
import pytest
import requests

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION_TESTS") != "1",
    reason="Integration tests need a configured Supabase/OpenAI environment. Set RUN_INTEGRATION_TESTS=1 to run them.",
)

BASE_URL = os.environ['REACT_APP_BACKEND_URL'].rstrip('/') if 'REACT_APP_BACKEND_URL' in os.environ else None
if not BASE_URL:
    # Fallback: read frontend/.env
    from pathlib import Path
    for line in Path('/app/frontend/.env').read_text().splitlines():
        if line.startswith('REACT_APP_BACKEND_URL='):
            BASE_URL = line.split('=', 1)[1].strip().rstrip('/')
            break

API = f"{BASE_URL}/api"

EXISTING_EMAIL = "mago@grimorio.it"
EXISTING_PASSWORD = "arcano123"


# ---------- Fixtures ----------
@pytest.fixture(scope="session")
def s():
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    return sess


@pytest.fixture(scope="session")
def token(s):
    """Log into the pre-seeded account. If not present, register it."""
    r = s.post(f"{API}/auth/login", json={"email": EXISTING_EMAIL, "password": EXISTING_PASSWORD}, timeout=20)
    if r.status_code == 401:
        r = s.post(f"{API}/auth/register", json={"email": EXISTING_EMAIL, "password": EXISTING_PASSWORD, "name": "Mago Test"}, timeout=20)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    data = r.json()
    assert "token" in data and len(data["token"]) > 20
    return data["token"]


@pytest.fixture(scope="session")
def auth_headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ---------- Health / Root ----------
def test_root(s):
    r = s.get(f"{API}/", timeout=15)
    assert r.status_code == 200
    assert r.json().get("message") == "TomeForge API"


# ---------- Auth ----------
class TestAuth:
    def test_register_duplicate_fails(self, s):
        r = s.post(f"{API}/auth/register", json={"email": EXISTING_EMAIL, "password": EXISTING_PASSWORD, "name": "Dup"}, timeout=20)
        # First test run may create it (200), otherwise duplicate 400. Both acceptable.
        assert r.status_code in (200, 400), r.text

    def test_login_bad_password(self, s):
        r = s.post(f"{API}/auth/login", json={"email": EXISTING_EMAIL, "password": "wrong"}, timeout=20)
        assert r.status_code == 401

    def test_login_good(self, s):
        r = s.post(f"{API}/auth/login", json={"email": EXISTING_EMAIL, "password": EXISTING_PASSWORD}, timeout=20)
        assert r.status_code == 200
        data = r.json()
        assert data["user"]["email"] == EXISTING_EMAIL
        assert data["user"]["auth_provider"] == "email"
        assert isinstance(data["token"], str)

    def test_me_with_bearer(self, s, auth_headers):
        r = s.get(f"{API}/auth/me", headers=auth_headers, timeout=15)
        assert r.status_code == 200
        assert r.json()["email"] == EXISTING_EMAIL

    def test_me_no_token(self, s):
        r = requests.get(f"{API}/auth/me", timeout=15)
        assert r.status_code == 401

    def test_register_new_and_login(self, s):
        email = f"test_{uuid.uuid4().hex[:8]}@grimorio.it"
        r = s.post(f"{API}/auth/register", json={"email": email, "password": "pw123456", "name": "Ephemeral"}, timeout=20)
        assert r.status_code == 200
        tok = r.json()["token"]
        # login again
        r2 = s.post(f"{API}/auth/login", json={"email": email, "password": "pw123456"}, timeout=20)
        assert r2.status_code == 200
        # me with token
        r3 = requests.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {tok}"}, timeout=15)
        assert r3.status_code == 200
        assert r3.json()["email"] == email


# ---------- Cards CRUD ----------
class TestCards:
    def test_create_get_update_delete(self, s, auth_headers):
        # CREATE
        payload = {
            "type": "spell",
            "name": "TEST_Palla di Fuoco",
            "description": "Un test spell",
            "story": "Storia test",
            "language": "it",
            "attributes": {"livello": "3", "scuola": "Evocazione"},
        }
        r = s.post(f"{API}/cards", headers=auth_headers, json=payload, timeout=20)
        assert r.status_code == 200, r.text
        card = r.json()
        assert card["name"] == payload["name"]
        assert card["type"] == "spell"
        assert card["attributes"]["livello"] == "3"
        assert "id" in card and card["id"]
        cid = card["id"]

        # GET (list)
        r = s.get(f"{API}/cards", headers=auth_headers, timeout=15)
        assert r.status_code == 200
        assert any(c["id"] == cid for c in r.json())

        # GET filter by type
        r = s.get(f"{API}/cards?type=spell", headers=auth_headers, timeout=15)
        assert r.status_code == 200
        assert all(c["type"] == "spell" for c in r.json())

        # GET filter by search
        r = s.get(f"{API}/cards?search=TEST_Palla", headers=auth_headers, timeout=15)
        assert r.status_code == 200
        assert any(c["id"] == cid for c in r.json())

        # GET single
        r = s.get(f"{API}/cards/{cid}", headers=auth_headers, timeout=15)
        assert r.status_code == 200
        assert r.json()["name"] == payload["name"]

        # UPDATE
        r = s.put(f"{API}/cards/{cid}", headers=auth_headers,
                  json={"name": "TEST_Palla di Fuoco Aggiornata", "version": card["version"]}, timeout=15)
        assert r.status_code == 200
        assert r.json()["name"] == "TEST_Palla di Fuoco Aggiornata"

        # verify persistence
        r = s.get(f"{API}/cards/{cid}", headers=auth_headers, timeout=15)
        assert r.json()["name"] == "TEST_Palla di Fuoco Aggiornata"

        # DELETE
        r = s.delete(f"{API}/cards/{cid}", headers=auth_headers, json={"version": r.json()["version"]}, timeout=15)
        assert r.status_code == 200

        # verify gone
        r = s.get(f"{API}/cards/{cid}", headers=auth_headers, timeout=15)
        assert r.status_code == 404

    def test_cards_require_auth(self, s):
        r = requests.get(f"{API}/cards", timeout=15)
        assert r.status_code == 401


# ---------- AI: text generation (OpenAI) ----------
class TestAIText:
    def test_generate_content_spell_italian(self, s, auth_headers):
        r = s.post(f"{API}/ai/generate-content", headers=auth_headers, json={
            "type": "spell",
            "prompt": "Un incantesimo di livello 1 che evoca una piccola fiamma di luce dorata",
            "language": "it",
        }, timeout=120)
        assert r.status_code == 200, f"AI text failed: {r.status_code} {r.text[:300]}"
        data = r.json()
        assert data["name"], "empty name"
        assert data["description"], "empty description"
        assert data["story"], "empty story"
        assert isinstance(data["attributes"], dict) and data["attributes"], "empty attributes"
        # log for evidence
        print(f"[AI TEXT IT] name={data['name']!r} attrs_keys={list(data['attributes'].keys())}")

    def test_generate_content_monster_stat_block(self, s, auth_headers):
        r = s.post(f"{API}/ai/generate-content", headers=auth_headers, json={
            "type": "monster",
            "prompt": "Un lupo delle ombre, predatore di livello basso",
            "language": "it",
        }, timeout=120)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        attrs = data["attributes"]
        # Verify D&D-like monster fields present
        must = ["classe_armatura", "punti_ferita", "for", "des", "cos"]
        present = [k for k in must if k in attrs and attrs[k] not in ("", None)]
        assert len(present) >= 3, f"monster attrs missing: {attrs}"
        print(f"[AI MONSTER] name={data['name']!r} CA={attrs.get('classe_armatura')} PF={attrs.get('punti_ferita')}")


# ---------- AI: image generation (OpenAI Images) + storage ----------
class TestAIImage:
    """Only ONE paid image generation, per budget rules."""

    def test_generate_image_and_serve(self, s, auth_headers, token):
        r = s.post(f"{API}/ai/generate-image", headers=auth_headers, json={
            "prompt": "A red dragon coiled on a mountain of gold, dark fantasy oil painting",
            "type": "monster",
        }, timeout=180)
        assert r.status_code == 200, f"AI image failed: {r.status_code} {r.text[:300]}"
        data = r.json()
        assert "artwork_path" in data and data["artwork_path"], "no artwork_path"
        path = data["artwork_path"]
        assert path.startswith("tomeforge/artwork/"), f"unexpected path {path}"
        print(f"[AI IMAGE] artwork_path={path}")

        # Fetch via /api/files with Bearer
        r2 = requests.get(f"{API}/files/{path}", headers={"Authorization": f"Bearer {token}"}, timeout=60)
        assert r2.status_code == 200, f"file fetch failed: {r2.status_code} {r2.text[:200]}"
        img_bytes = r2.content
        assert len(img_bytes) > 5000, f"image too small: {len(img_bytes)} bytes"
        is_png = img_bytes[:8] == b"\x89PNG\r\n\x1a\n"
        is_jpeg = img_bytes[:3] == b"\xff\xd8\xff"
        assert is_png or is_jpeg, f"not PNG/JPEG: {img_bytes[:8]!r}"
        h = hashlib.sha256(img_bytes).hexdigest()
        print(f"[AI IMAGE] bytes={len(img_bytes)} sha256={h[:16]}...")

        # Fetch via query param (used by <img src>)
        r3 = requests.get(f"{API}/files/{path}?auth={token}", timeout=60)
        assert r3.status_code == 200
        assert len(r3.content) == len(img_bytes)

        # Fetch without auth -> 401
        r4 = requests.get(f"{API}/files/{path}", timeout=15)
        assert r4.status_code == 401


# ---------- File upload ----------
class TestUpload:
    def test_upload_and_serve(self, s, token, auth_headers):
        # tiny PNG (1x1 red pixel)
        png = bytes.fromhex(
            "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
            "0000000d49444154789c626001000000050001a5f645400000000049454e44ae426082"
        )
        files = {"file": ("pixel.png", io.BytesIO(png), "image/png")}
        # Do NOT include Content-Type header for multipart
        r = requests.post(f"{API}/upload", files=files, headers={"Authorization": f"Bearer {token}"}, timeout=60)
        assert r.status_code == 200, f"upload failed: {r.status_code} {r.text[:200]}"
        path = r.json()["artwork_path"]
        assert path.startswith("tomeforge/uploads/"), path

        # Serve back
        r2 = requests.get(f"{API}/files/{path}?auth={token}", timeout=30)
        assert r2.status_code == 200
        assert r2.content[:8] == b"\x89PNG\r\n\x1a\n"
        print(f"[UPLOAD] path={path} bytes={len(r2.content)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
