"""Immutable source-only audit of seven existing Italian MPMM encounter creatures.

No write operations. Original registered identity, SHA256, page references,
OCR attributes, flags, and review status are strictly guarded.
"""
from __future__ import annotations
import hashlib
from typing import Any
from services.ocr_semantic_gates import monster_semantic_numeric_flags

OWNER = "user_fabf28726a20"
TITLE = "Mordenkainen Presenta: Mostri del Multiverso"
P1 = "Mostri del multi verso 1-100.pdf"
P2 = "Mostri del multiverso 101-200.pdf"
TARGETS = {
  "Adepto Di Arti Marziali": {
    "id": "ref_733ff0484b5e560d99847a4b87d66d6a",
    "source": "Mostri del multi verso 1-100.pdf",
    "pages": [
      48
    ],
    "checksum": "ddf5fd25d3d33859f938f351c15e27371bc057e3d54667f243b129597b30986a",
    "raw": "8fec978b1446679a1e2bf8684f39691c475d122451d632795902528de762c8d2",
    "attrs": {
      "classe_armatura": "16 (difesa senza armatura)",
      "punti_ferita": "60 (11d8 + 11)",
      "velocita": "12 m"
    },
    "dice": [
      60,
      11,
      8,
      11
    ]
  },
  "Armanite": {
    "id": "ref_b965d3b0881659b88a408dc1424069c5",
    "source": "Mostri del multi verso 1-100.pdf",
    "pages": [
      56
    ],
    "checksum": "b7fd77a070dd437a1639a14d86e9610238eeb0dde47ae2bac2b564118aa7c063",
    "raw": "8ed27e12fbaf98825af9a30b11e9307cc6b134861472527499f936b1b3b3e438",
    "attrs": {
      "classe_armatura": "16 (armatura naturale)",
      "punti_ferita": "94 (9d10 + 45)",
      "velocita": "18 m"
    },
    "dice": [
      94,
      9,
      10,
      45
    ]
  },
  "Boggle": {
    "id": "ref_7562f52e544c5b5582e3fa17ce29dc73",
    "source": "Mostri del multi verso 1-100.pdf",
    "pages": [
      74
    ],
    "checksum": "0a597c692a98b8a59caabd62ea59a974ae0cd3a1462c5caddbdf996e9bba637b",
    "raw": "9f064ed8fec9f1020d11cc2427590786fdc7d27a45c246b8bcf5fe7f2b197e5c",
    "attrs": {
      "classe_armatura": "14",
      "punti_ferita": "18 (4d6 + 4)",
      "velocita": "9 m, scalare 9 m"
    },
    "dice": [
      18,
      4,
      6,
      4
    ]
  },
  "Choldrith": {
    "id": "ref_1fdee4eaf3a650a182f67f3882b08154",
    "source": "Mostri del multi verso 1-100.pdf",
    "pages": [
      84
    ],
    "checksum": "c1c276942b27bddd0ef8cf2348f3e38f5fd6955456c1786e7139ea9d777b2620",
    "raw": "0def161268e7c95a2ac59130c88c5199da3f7b90d062558dc534822321e362d8",
    "attrs": {
      "classe_armatura": "15 (armatura naturale)",
      "punti_ferita": "66 (12d8 + 12)",
      "velocita": "9 m, scalare 9 m"
    },
    "dice": [
      66,
      12,
      8,
      12
    ]
  },
  "Coboldo Scudo Di Drago": {
    "id": "ref_7e05206e75b15c8f9463efcbf0c3b773",
    "source": "Mostri del multi verso 1-100.pdf",
    "pages": [
      86
    ],
    "checksum": "b1a6345f0900eb7ff49987774439d16055c95879bc99a170914b17e5c626b10b",
    "raw": "9c339dd9bb2e2dd4bd5b63832c0068afe8381c7624f499104f461ef8b849bdc5",
    "attrs": {
      "classe_armatura": "15 (cuoio, scudo)",
      "punti_ferita": "44 (8d6 + 16)",
      "velocita": "6 m"
    },
    "dice": [
      44,
      8,
      6,
      16
    ]
  },
  "Githyanki Gish": {
    "id": "ref_32f6a6bbcd635c229c51a6c7524c2810",
    "source": "Mostri del multiverso 101-200.pdf",
    "pages": [
      35,
      36
    ],
    "checksum": "7e315273d2756e94d12f5d4fcb5ad5323a9f7de10f0749f3bcddc1f1db1eff89",
    "raw": "11d5eeadac732ddc4ec69e6b204e60e7ef28861b6cf50b0010970dac6c4ce011",
    "attrs": {
      "classe_armatura": "17 (mezza armatura)",
      "punti_ferita": "130 (20d8 + 40)",
      "velocita": "9 m"
    },
    "dice": [
      130,
      20,
      8,
      40
    ]
  },
  "Guascone": {
    "id": "ref_2998ad476c965f98ad6cf75465b39a76",
    "source": "Mostri del multiverso 101-200.pdf",
    "pages": [
      47
    ],
    "checksum": "68fe532b668d7785b831d3a1823ca1fe76a0da1abfc5150233992fc751924bf1",
    "raw": "780314a5c110d735e40e1318ec845fb14d9bd05a5f53954372a108997fa27f93",
    "attrs": {
      "classe_armatura": "17 (armatura di cuoio, Difesa soave)",
      "punti_ferita": "66 (12d8 + 12)",
      "velocita": "9 m"
    },
    "dice": [
      66,
      12,
      8,
      12
    ]
  }
}


def original_refs(source: str, pages: list[int]) -> list[dict[str, Any]]:
    offset = 0 if source == P1 else 100
    return [
        {
            "page": p, "ruleset": "2014", "filename": source,
            "source_role": "authority", "logical_page": p + offset,
            "source_title": TITLE, "source_status": "active",
            "authority_class": "licensed_translation",
            "logical_source_id": "mpmm_2022_it",
        }
        for p in pages
    ]


def review_existing_statblock(name: str, row: dict[str, Any] | None) -> dict[str, Any]:
    if name not in TARGETS or not isinstance(row, dict):
        raise ValueError("unregistered_or_missing_entity")
    t = TARGETS[name]
    expected = {
        "id": t["id"], "user_id": OWNER, "name": name,
        "source_name": name, "normalized_name": name.casefold(),
        "reference_type": "other", "review_status": "needs_review",
        "review_flags": [], "canonical_id": None,
        "source_language": "it", "source_key": t["source"],
        "source_text_checksum": t["checksum"],
        "review_corrections": {"_source_changed": True},
        "attributes": {}, "source_attributes": {},
        "source_refs": original_refs(t["source"], t["pages"]),
    }
    if any(row.get(k) != v for k, v in expected.items()):
        raise ValueError("registered_source_record_drift")
    raw = row.get("source_full_text")
    if not isinstance(raw, str) or row.get("full_text") != raw:
        raise ValueError("historical_original_raw_changed")
    if hashlib.sha256(raw.encode("utf-8")).hexdigest() != t["raw"]:
        raise ValueError("original_raw_sha256_changed")
    hp, count, sides, bonus = t["dice"]
    if (count * (sides + 1)) // 2 + bonus != hp:
        raise ValueError("dice_average_incoherent")
    if monster_semantic_numeric_flags(t["attrs"]):
        raise ValueError("unmodified_global_numeric_gate_rejected")
    return {
        "name": name, "id": t["id"], "source_pages": t["pages"],
        "attributes": t["attrs"], "eligible": True,
        "original_source_unchanged": True, "writes": 0,
    }
