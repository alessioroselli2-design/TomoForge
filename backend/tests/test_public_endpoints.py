"""
Tests for the NEW public read-only endpoints used by /p/:id page and card front QR.
- GET /api/public/cards/{id}     (no auth, no user_id leaked, 404 if missing)
- GET /api/public/files/{path}   (no auth, returns image bytes)
"""
import os
import requests
import pytest

BASE_URL = os.environ['REACT_APP_BACKEND_URL'].rstrip('/') if 'REACT_APP_BACKEND_URL' in os.environ else None
if not BASE_URL:
    from pathlib import Path
    for line in Path('/app/frontend/.env').read_text().splitlines():
        if line.startswith('REACT_APP_BACKEND_URL='):
            BASE_URL = line.split('=', 1)[1].strip().rstrip('/')
            break
API = f"{BASE_URL}/api"

EMAIL = "mago@grimorio.it"
PASSWORD = "arcano123"


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{API}/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=20)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def some_card(token):
    r = requests.get(f"{API}/cards", headers={"Authorization": f"Bearer {token}"}, timeout=20)
    assert r.status_code == 200
    cards = r.json()
    assert cards, "No cards for pre-seeded account"
    # prefer Dardo Incantato (should have artwork now)
    for c in cards:
        if "Dardo" in c.get("name", ""):
            return c
    return cards[0]


class TestPublicCard:
    def test_public_card_no_auth_ok(self, some_card):
        r = requests.get(f"{API}/public/cards/{some_card['id']}", timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["id"] == some_card["id"]
        assert data["name"] == some_card["name"]
        # user_id must not leak
        assert "user_id" not in data, f"user_id leaked in public payload: {data.keys()}"
        assert "_id" not in data
        # basic fields present
        assert "type" in data
        assert "attributes" in data

    def test_public_card_returns_full_data(self, some_card, token):
        # Compare public vs authenticated
        r_pub = requests.get(f"{API}/public/cards/{some_card['id']}", timeout=20)
        r_auth = requests.get(f"{API}/cards/{some_card['id']}", headers={"Authorization": f"Bearer {token}"}, timeout=20)
        assert r_pub.status_code == 200 and r_auth.status_code == 200
        pub = r_pub.json()
        priv = r_auth.json()
        # description, story, attributes should match
        assert pub.get("name") == priv.get("name")
        assert pub.get("description") == priv.get("description")
        assert pub.get("story") == priv.get("story")
        assert pub.get("attributes") == priv.get("attributes")

    def test_public_card_not_found(self):
        r = requests.get(f"{API}/public/cards/does-not-exist", timeout=15)
        assert r.status_code == 404

    def test_public_card_no_authorization_header_required(self, some_card):
        # Explicitly pass a wrong bearer to ensure endpoint really is public
        r = requests.get(
            f"{API}/public/cards/{some_card['id']}",
            headers={"Authorization": "Bearer garbage"},
            timeout=15,
        )
        assert r.status_code == 200


class TestPublicFiles:
    def test_public_file_download_no_auth(self, some_card):
        artwork = some_card.get("artwork_path")
        if not artwork:
            pytest.skip("card has no artwork_path")
        r = requests.get(f"{API}/public/files/{artwork}", timeout=30)
        assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"
        assert len(r.content) > 500
        head = r.content[:8]
        assert head[:3] == b"\xff\xd8\xff" or head == b"\x89PNG\r\n\x1a\n"

    def test_public_file_not_found(self):
        r = requests.get(f"{API}/public/files/tomeforge/artwork/nope.png", timeout=15)
        assert r.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
