import hashlib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BARDO_ASSET = REPO_ROOT / "attached_assets" / "Bardo__1787233073462.pdf"
EXPECTED_JOB_FINGERPRINT = "78d5dbfd2a524b445c4fd6ddcd61a686ffb9e98add882604fca26f2f24caa5a5"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_bardo_attached_asset_matches_failed_import_fingerprint():
    """Pin deterministic provenance evidence without authorizing any data mutation."""
    assert BARDO_ASSET.is_file()
    assert _sha256(BARDO_ASSET) == EXPECTED_JOB_FINGERPRINT
