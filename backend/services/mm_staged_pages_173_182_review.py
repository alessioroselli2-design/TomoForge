"""Non-canonical staging audit of 11 original Italian MM monster candidates.

This module is built from the prior internal source-staging artifact for physical
PDF pages 173-182. The original PDF pages are NOT independently reread by this
module. It validates provenance, integrity, arithmetic and typed fields and
returns a status that explicitly prohibits canonical/DB promotion pending an
independent visual source recheck. No PDF content, OCR dump or secrets stored.
"""
from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from typing import Any

from services.ocr_semantic_gates import (
    monster_identity_sanity_flags,
    monster_semantic_numeric_flags,
)

SOURCE_ID = "mm_2014_it"
FILENAME = "847921086-Manuale-Dei-Mostri-5e.pdf"
SHA256 = "b33eb72e5eb78fe3e3dcbde5315f5b9afbe42e4a457a518cc93f7766979a381c"
PAGE_COUNT = 353
ALLOWED_PAGES = frozenset(range(173, 183))
HP_RE = re.compile(
    r"([0-9]+) [(]([0-9]+)d([0-9]+)(?: ([+-]) ([0-9]+))?[)]$"
)
EXPECTED: list[dict[str, Any]] = json.loads(
    "[{\"name\":\"Grell\",\"id\":\"ref_8eb6373625f1bcff4a7d6ea3fbb50df3\",\"page\":173,\"attributes\":{\"tipo_creatura\":\"Aberrazione\",\"taglia\":\"Media\",\"allineamento\":\"neutrale malvagio\",\"classe_armatura\":\"12\",\"punti_ferita\":\"55 (10d8 + 10)\",\"velocita\":\"3 m, volare 9 m (fluttuare)\",\"grado_sfida\":\"3\",\"caratteristiche\":{\"for\":\"15\",\"des\":\"14\",\"cos\":\"13\",\"int\":\"12\",\"sag\":\"11\",\"car\":\"9\"},\"azioni_nomi_da_completare\":[\"Multiattacco\",\"Tentacoli\",\"Becco\"],\"completezza_scheda\":\"statistiche_essenziali\"},\"source_excerpt\":\"Grell. Aberrazione Media, neutrale malvagio. Classe Armatura 12. Punti Ferita 55 (10d8 + 10). Velocità 3 m, volare 9 m (fluttuare). Sfida 3.\",\"source_text_checksum\":\"97550c8713aee03beb8215032d0ee38eb0f2657c0381184844b7e802f7ca4136\"},{\"name\":\"Grick\",\"id\":\"ref_0a49f679e41415ad0b4f9b41f25ae1fa\",\"page\":174,\"attributes\":{\"tipo_creatura\":\"Mostruosità\",\"taglia\":\"Media\",\"allineamento\":\"neutrale\",\"classe_armatura\":\"14 (armatura naturale)\",\"punti_ferita\":\"27 (6d8)\",\"velocita\":\"9 m, scalare 9 m\",\"grado_sfida\":\"2\",\"caratteristiche\":{\"for\":\"14\",\"des\":\"14\",\"cos\":\"11\",\"int\":\"3\",\"sag\":\"14\",\"car\":\"5\"},\"azioni_nomi_da_completare\":[\"Multiattacco\",\"Tentacoli\",\"Becco\"],\"completezza_scheda\":\"statistiche_essenziali\"},\"source_excerpt\":\"Grick. Mostruosità Media, neutrale. Classe Armatura 14 (armatura naturale). Punti Ferita 27 (6d8). Velocità 9 m, scalare 9 m. Sfida 2.\",\"source_text_checksum\":\"af739d6c6fb2fe4ff0d82637f240c192b02aa38a712c982c3791fe6d50aa069d\"},{\"name\":\"Grick Alfa\",\"id\":\"ref_5dda43563a5a19b8ff39fc58156b353c\",\"page\":174,\"attributes\":{\"tipo_creatura\":\"Mostruosità\",\"taglia\":\"Grande\",\"allineamento\":\"neutrale\",\"classe_armatura\":\"18 (armatura naturale)\",\"punti_ferita\":\"75 (10d10 + 20)\",\"velocita\":\"9 m, scalare 9 m\",\"grado_sfida\":\"7\",\"caratteristiche\":{\"for\":\"18\",\"des\":\"16\",\"cos\":\"15\",\"int\":\"4\",\"sag\":\"14\",\"car\":\"9\"},\"azioni_nomi_da_completare\":[\"Multiattacco\",\"Coda\",\"Tentacoli\",\"Becco\"],\"completezza_scheda\":\"statistiche_essenziali\"},\"source_excerpt\":\"Grick Alfa. Mostruosità Grande, neutrale. Classe Armatura 18 (armatura naturale). Punti Ferita 75 (10d10 + 20). Velocità 9 m, scalare 9 m. Sfida 7.\",\"source_text_checksum\":\"cb7bfd13f4d2d31136a1bbbba6739f6e5355a57f9d9b5ad4cee1285874bfa24a\"},{\"name\":\"Grifone\",\"id\":\"ref_25c6315c6ab873061b673b6183e54eff\",\"page\":175,\"attributes\":{\"tipo_creatura\":\"Mostruosità\",\"taglia\":\"Grande\",\"allineamento\":\"senza allineamento\",\"classe_armatura\":\"12\",\"punti_ferita\":\"59 (7d10 + 21)\",\"velocita\":\"9 m, volare 24 m\",\"grado_sfida\":\"2\",\"caratteristiche\":{\"for\":\"18\",\"des\":\"15\",\"cos\":\"16\",\"int\":\"2\",\"sag\":\"13\",\"car\":\"8\"},\"azioni_nomi_da_completare\":[\"Multiattacco\",\"Becco\",\"Artigli\"],\"completezza_scheda\":\"statistiche_essenziali\"},\"source_excerpt\":\"Grifone. Mostruosità Grande, senza allineamento. Classe Armatura 12. Punti Ferita 59 (7d10 + 21). Velocità 9 m, volare 24 m. Sfida 2.\",\"source_text_checksum\":\"ffa89bccb467744131f5181721a198c0cb03819324745364b45f35f28b808d86\"},{\"name\":\"Grimlock\",\"id\":\"ref_2e32feecca6fe404a1cb7d3f535df23c\",\"page\":176,\"attributes\":{\"tipo_creatura\":\"Umanoide\",\"taglia\":\"Medio\",\"allineamento\":\"neutrale malvagio\",\"classe_armatura\":\"11\",\"punti_ferita\":\"11 (2d8 + 2)\",\"velocita\":\"9 m\",\"grado_sfida\":\"1/4\",\"caratteristiche\":{\"for\":\"16\",\"des\":\"12\",\"cos\":\"12\",\"int\":\"9\",\"sag\":\"8\",\"car\":\"6\"},\"azioni_nomi_da_completare\":[\"Clava di Osso Chiodata\"],\"completezza_scheda\":\"statistiche_essenziali\",\"sottotipo_creatura\":\"grimlock\"},\"source_excerpt\":\"Grimlock. Umanoide Medio, neutrale malvagio. Classe Armatura 11. Punti Ferita 11 (2d8 + 2). Velocità 9 m. Sfida 1/4.\",\"source_text_checksum\":\"6ccc08338df915cffc5e52f435c3c26333a33731035f7b127a8a4245f09293c2\"},{\"name\":\"Guardiano Protettore\",\"id\":\"ref_eeb5be4c99218cf7763e1c3e5d0c77ba\",\"page\":177,\"attributes\":{\"tipo_creatura\":\"Costrutto\",\"taglia\":\"Grande\",\"allineamento\":\"senza allineamento\",\"classe_armatura\":\"17 (armatura naturale)\",\"punti_ferita\":\"142 (15d10 + 60)\",\"velocita\":\"9 m\",\"grado_sfida\":\"7\",\"caratteristiche\":{\"for\":\"18\",\"des\":\"8\",\"cos\":\"18\",\"int\":\"7\",\"sag\":\"10\",\"car\":\"3\"},\"azioni_nomi_da_completare\":[\"Multiattacco\",\"Pugno\"],\"completezza_scheda\":\"statistiche_essenziali\",\"reazioni_nomi_da_completare\":[\"Protettore\"]},\"source_excerpt\":\"Guardiano Protettore. Costrutto Grande, senza allineamento. Classe Armatura 17 (armatura naturale). Punti Ferita 142 (15d10 + 60). Velocità 9 m. Sfida 7.\",\"source_text_checksum\":\"eb27ddf83f47ddf9cdf7c574d65e7008d56dbb321ca4f266c4d71f25e4600d85\"},{\"name\":\"Hobgoblin\",\"id\":\"ref_9b9b9e693e9f2455f098188b57725d0e\",\"page\":179,\"attributes\":{\"tipo_creatura\":\"Umanoide\",\"taglia\":\"Medio\",\"allineamento\":\"legale malvagio\",\"classe_armatura\":\"18 (cotta di maglia, scudo)\",\"punti_ferita\":\"11 (2d8 + 2)\",\"velocita\":\"9 m\",\"grado_sfida\":\"1/2\",\"caratteristiche\":{\"for\":\"13\",\"des\":\"12\",\"cos\":\"12\",\"int\":\"10\",\"sag\":\"10\",\"car\":\"9\"},\"azioni_nomi_da_completare\":[\"Spada Lunga\",\"Arco Lungo\"],\"completezza_scheda\":\"statistiche_essenziali\",\"sottotipo_creatura\":\"goblinoide\"},\"source_excerpt\":\"Hobgoblin. Umanoide Medio, legale malvagio. Classe Armatura 18 (cotta di maglia, scudo). Punti Ferita 11 (2d8 + 2). Velocità 9 m. Sfida 1/2.\",\"source_text_checksum\":\"f4e89c5c6c71e8d2e171b9b1edb688ddcc38b4c2e181c0bf7123f61be3045b53\"},{\"name\":\"Hobgoblin Capitano\",\"id\":\"ref_60ba7dca3ea0c3b36b21aa63d958da73\",\"page\":179,\"attributes\":{\"tipo_creatura\":\"Umanoide\",\"taglia\":\"Medio\",\"allineamento\":\"legale malvagio\",\"classe_armatura\":\"17 (mezza armatura)\",\"punti_ferita\":\"39 (6d8 + 12)\",\"velocita\":\"9 m\",\"grado_sfida\":\"3\",\"caratteristiche\":{\"for\":\"15\",\"des\":\"14\",\"cos\":\"14\",\"int\":\"12\",\"sag\":\"10\",\"car\":\"13\"},\"azioni_nomi_da_completare\":[\"Multiattacco\",\"Spadone\",\"Giavellotto\",\"Autorità\"],\"completezza_scheda\":\"statistiche_essenziali\",\"sottotipo_creatura\":\"goblinoide\"},\"source_excerpt\":\"Hobgoblin Capitano. Umanoide Medio, legale malvagio. Classe Armatura 17 (mezza armatura). Punti Ferita 39 (6d8 + 12). Velocità 9 m. Sfida 3.\",\"source_text_checksum\":\"7f1cfa4fbf1d2394090653e837de7c13ddea3faf5ea7da64f254551351c0e40a\"},{\"name\":\"Hobgoblin Signore Della Guerra\",\"id\":\"ref_67b7fcec074f8bdc1cd5ae5ce1f8b271\",\"page\":180,\"attributes\":{\"tipo_creatura\":\"Umanoide\",\"taglia\":\"Medio\",\"allineamento\":\"legale malvagio\",\"classe_armatura\":\"20 (armatura completa, scudo)\",\"punti_ferita\":\"97 (13d8 + 39)\",\"velocita\":\"9 m\",\"grado_sfida\":\"6\",\"caratteristiche\":{\"for\":\"16\",\"des\":\"14\",\"cos\":\"16\",\"int\":\"14\",\"sag\":\"11\",\"car\":\"15\"},\"azioni_nomi_da_completare\":[\"Multiattacco\",\"Spada Lunga\",\"Scudo da Sfondamento\",\"Giavellotto\",\"Autorità\"],\"completezza_scheda\":\"statistiche_essenziali\",\"reazioni_nomi_da_completare\":[\"Parata\"],\"sottotipo_creatura\":\"goblinoide\"},\"source_excerpt\":\"Hobgoblin Signore Della Guerra. Umanoide Medio, legale malvagio. Classe Armatura 20 (armatura completa, scudo). Punti Ferita 97 (13d8 + 39). Velocità 9 m. Sfida 6.\",\"source_text_checksum\":\"44d6cf6d2b7bd04e798aab7b6a5811f2c64d699bfd2855dfb4e5eead8364f3f3\"},{\"name\":\"Idra\",\"id\":\"ref_5d0e92c5ad20ccfe243c00b7ec98e804\",\"page\":181,\"attributes\":{\"tipo_creatura\":\"Mostruosità\",\"taglia\":\"Enorme\",\"allineamento\":\"senza allineamento\",\"classe_armatura\":\"15 (armatura naturale)\",\"punti_ferita\":\"172 (15d12 + 75)\",\"velocita\":\"9 m, nuotare 9 m\",\"grado_sfida\":\"8\",\"caratteristiche\":{\"for\":\"20\",\"des\":\"12\",\"cos\":\"20\",\"int\":\"2\",\"sag\":\"10\",\"car\":\"7\"},\"azioni_nomi_da_completare\":[\"Multiattacco\",\"Morso\"],\"completezza_scheda\":\"statistiche_essenziali\",\"tratti_da_completare\":[\"Teste Multiple\",\"Teste Reattive\",\"Trattenere il Respiro\",\"Sempre Sveglia\"]},\"source_excerpt\":\"Idra. Mostruosità Enorme, senza allineamento. Classe Armatura 15 (armatura naturale). Punti Ferita 172 (15d12 + 75). Velocità 9 m, nuotare 9 m. Sfida 8.\",\"source_text_checksum\":\"36a2d62e7075c6c6b048842d0fb78e940d6b8b928b09bc189f2b854e825959e8\"},{\"name\":\"Ippogrifo\",\"id\":\"ref_b8f3f202d482d5f22f8bf9c77c71bed1\",\"page\":182,\"attributes\":{\"tipo_creatura\":\"Mostruosità\",\"taglia\":\"Grande\",\"allineamento\":\"senza allineamento\",\"classe_armatura\":\"11\",\"punti_ferita\":\"19 (3d10 + 3)\",\"velocita\":\"12 m, volare 18 m\",\"grado_sfida\":\"1\",\"caratteristiche\":{\"for\":\"17\",\"des\":\"13\",\"cos\":\"13\",\"int\":\"2\",\"sag\":\"12\",\"car\":\"8\"},\"azioni_nomi_da_completare\":[\"Multiattacco\",\"Becco\",\"Artigli\"],\"completezza_scheda\":\"statistiche_essenziali\"},\"source_excerpt\":\"Ippogrifo. Mostruosità Grande, senza allineamento. Classe Armatura 11. Punti Ferita 19 (3d10 + 3). Velocità 12 m, volare 18 m. Sfida 1.\",\"source_text_checksum\":\"35dde77d326305f833fcec97f0cf4c0b38dba2a9adad43b9e36c940bc680e292\"}]"
)
INDEX = {entry["name"]: entry for entry in EXPECTED}
if len(INDEX) != len(EXPECTED):
    raise ValueError("duplicate_staged_names")


def audit(
    name: str,
    catalog: dict[str, Any] | None,
    existing_id: bool = False,
    same_name_monster: bool = False,
) -> dict[str, Any]:
    """Check the staging artifact, without asserting independent PDF acceptance."""
    required = {
        "logical_source_id": SOURCE_ID,
        "physical_filename": FILENAME,
        "physical_sha256": SHA256,
        "physical_pages": PAGE_COUNT,
        "source_status": "active",
        "source_role": "authority",
        "authority_class": "licensed_translation",
        "text_mode": "vision_required",
    }
    if not isinstance(catalog, dict) or any(
        catalog.get(key) != value for key, value in required.items()
    ):
        raise ValueError("registered_original_source_mismatch")
    if existing_id or same_name_monster:
        raise ValueError("monster_collision")
    if name not in INDEX:
        raise ValueError("unknown_staged_monster")
    candidate = INDEX[name]
    page = candidate["page"]
    if page not in ALLOWED_PAGES:
        raise ValueError("page_outside_12_page_limit")

    token = f"{SOURCE_ID}|{FILENAME}|{page}|{name.casefold()}"
    identity = "ref_" + hashlib.sha256(token.encode()).hexdigest()[:32]
    if identity != candidate["id"]:
        raise ValueError("staged_identity_drift")
    if hashlib.sha256(
        candidate["source_excerpt"].encode()
    ).hexdigest() != candidate["source_text_checksum"]:
        raise ValueError("staged_excerpt_checksum_drift")

    attrs = deepcopy(candidate["attributes"])
    if attrs.get("completezza_scheda") != "statistiche_essenziali":
        raise ValueError("invalid_completion_claim")
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(attrs):
        raise ValueError("identity_or_numeric_semantic_gate")
    hp = HP_RE.fullmatch(attrs["punti_ferita"])
    if hp is None:
        raise ValueError("malformed_staged_hit_dice")
    avg, count, faces, sign, modifier = hp.groups()
    delta = int(modifier or 0) * (-1 if sign == "-" else 1)
    expected_hp = int(count) * (int(faces) + 1) // 2 + delta
    if int(avg) != expected_hp:
        raise ValueError("hit_dice_arithmetic_mismatch")
    abilities = attrs.get("caratteristiche")
    if not isinstance(abilities, dict) or set(abilities) != {
        "for", "des", "cos", "int", "sag", "car"
    }:
        raise ValueError("six_characteristics_missing")
    if any(
        not str(score).isdigit() or not 1 <= int(score) <= 30
        for score in abilities.values()
    ):
        raise ValueError("ability_score_out_of_range")

    return {
        "id": identity,
        "name": name,
        "physical_page": page,
        "source_excerpt": candidate["source_excerpt"],
        "source_text_checksum": candidate["source_text_checksum"],
        "attributes": attrs,
        "status": "staged_pending_independent_visual_source_confirmation",
        "canonical_eligible": False,
        "writes": 0,
    }
