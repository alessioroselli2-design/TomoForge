import asyncio

import pytest
from fastapi import HTTPException

from reference_library import reference_is_trusted, reference_rule_source
from routers.admin import admin_run_canonicalization
from routers.library import apply_private_reference, review_private_reference
from schemas.library import CanonicalizationRunInput, ReferenceReviewInput
from schemas.users import User
from services.canonical import (
    CanonicalizationBlockedError,
    canonical_group_key,
    canonicalize_group,
    canonicalization_status,
    is_character_sheet_source,
    record_ruleset,
    run_canonicalization,
    source_authority,
)
from translation_integrity import translation_verification_fingerprint


def record(identifier, **changes):
    value = {
        "id": identifier, "user_id": "owner", "reference_type": "class_feature",
        "name": "Azione", "normalized_name": "azione", "parent_class": "Guerriero",
        "parent_subclass": "", "level": "2", "description": "descrizione",
        "full_text": "testo della regola", "attributes": {}, "source_refs": [],
        "review_status": "pending",
    }
    value.update(changes)
    return value


def test_grouping_authority_and_character_sheet_exclusion():
    assert canonical_group_key(record("a")).startswith("dnd5e:2014:owner:class_feature:azione")
    ranks = [
        source_authority(record("a", source_refs=[{"authority_class": "official_errata"}]))[0],
        source_authority(record("b", source_refs=[{"authority_class": "official_revision"}]))[0],
        source_authority(record("c", source_refs=[{"authority_class": "reprint"}]))[0],
        source_authority(record("d", source_key="Manuale_del_giocatore.pdf"))[0],
        source_authority(record(
            "e",
            source_key="fan_translation.pdf",
            source_language="es",
            translation_status="translated",
        ))[0],
    ]
    assert ranks == sorted(ranks, reverse=True)
    assert len(set(ranks)) == len(ranks)
    assert is_character_sheet_source(record("a", source_key="Scheda_personaggio_template.pdf"))
    assert record_ruleset(record("a", source_refs=[{"filename": "Player_Handbook_2024.pdf"}])) == "2024"


def test_character_sheet_is_not_discovered_as_rule_manual(monkeypatch, tmp_path):
    from services import library

    (tmp_path / "Scheda_personaggio__template.pdf").write_bytes(b"template")
    (tmp_path / "Manuale_aggiuntivo.pdf").write_bytes(b"rules")
    monkeypatch.setattr(library, "SPELL_PDF_DIRECTORY", tmp_path)
    monkeypatch.setattr(library, "REFERENCE_MANUAL_FILENAMES", ())

    assert set(library.available_reference_manuals()) == {"Manuale_aggiuntivo.pdf"}


def test_unregistered_exact_copy_of_registered_manual_is_not_discovered(monkeypatch, tmp_path):
    from services import library

    registered_name = "Manuale_del_giocatore__1787259882002.pdf"
    (tmp_path / registered_name).write_bytes(b"registered manual bytes")
    (tmp_path / "same-manual-with-another-name.pdf").write_bytes(b"registered manual bytes")
    (tmp_path / "new-manual.pdf").write_bytes(b"different manual bytes")
    monkeypatch.setattr(library, "SPELL_PDF_DIRECTORY", tmp_path)
    monkeypatch.setattr(library, "REFERENCE_MANUAL_FILENAMES", (registered_name,))

    assert set(library.available_reference_manuals()) == {
        registered_name,
        "new-manual.pdf",
    }


def test_divergent_ai_selection_retains_whole_selected_record_and_provenance():
    first = record("one", full_text="vecchia regola")
    second = record("two", full_text="nuova regola", attributes={"danno": "2d6"})

    row = asyncio.run(canonicalize_group(
        [first, second],
        comparator=lambda candidates: {
            "selected_source_record_id": "two", "confidence": .91, "notes": "revision",
            "conflict_fields": [], "status": "verified",
        },
    ))

    assert row["verification_status"] == "verified"
    assert row["full_text"] == second["full_text"]
    assert row["attributes"] == second["attributes"]
    assert {entry["source_record_id"] for entry in row["source_refs"]} == {"one", "two"}


def test_ai_cannot_override_a_higher_authority_source():
    errata = record("errata", source_refs=[{"authority_class": "official_errata"}], full_text="official")
    derived = record("derived", source_key="fan_notes.pdf", full_text="derived")
    row = asyncio.run(canonicalize_group(
        [errata, derived],
        comparator=lambda candidates: {
            "selected_source_record_id": "derived", "confidence": .99, "notes": "wrong priority",
            "conflict_fields": [], "status": "verified",
        },
    ))
    assert row["verification_status"] == "conflict"
    assert row["confidence"] == 0


def test_unreviewed_translation_cannot_be_certified_by_canonical_comparison_alone():
    translated = record(
        "translated",
        source_key="Manual_del_Jugador.pdf",
        source_language="es",
        source_full_text="texto original",
        full_text="testo tradotto",
        translation_status="translated",
    )
    calls = []
    row = asyncio.run(canonicalize_group(
        [translated],
        comparator=lambda candidates: calls.append(candidates) or {
            "selected_source_record_id": "translated", "confidence": .91, "notes": "translation checked",
            "conflict_fields": [], "status": "verified",
        },
    ))
    assert calls
    assert row["verification_status"] == "low_confidence"
    assert "visual_or_source_verification" in row["conflict_fields"]
    assert row["verification_model"] != "deterministic"


def test_current_translation_fidelity_verdict_allows_canonical_verification():
    translated = record(
        "translated",
        source_key="Manual_del_Jugador.pdf",
        source_language="es",
        source_name="Acción",
        source_description="Una regla.",
        source_full_text="La regla inflige 1d6 de daño.",
        source_attributes={"damage": "1d6"},
        full_text="La regola infligge 1d6 danni.",
        attributes={"damage": "1d6"},
        translation_status="translated",
        translation_review_status="ai_verified",
    )
    translated["translation_review_fingerprint"] = translation_verification_fingerprint(translated)

    row = asyncio.run(canonicalize_group(
        [translated],
        comparator=lambda candidates: {
            "selected_source_record_id": "translated",
            "confidence": .99,
            "notes": "selected",
            "conflict_fields": [],
            "status": "verified",
        },
    ))

    assert row["verification_status"] == "verified"


def test_translation_conflict_cannot_become_a_trusted_canonical_selection():
    translated = record(
        "translated",
        source_key="Manual_del_Jugador.pdf",
        source_language="es",
        source_name="Acción",
        source_description="Una regla.",
        source_full_text="La regla inflige 1d6 de daño.",
        source_attributes={"damage": "1d6"},
        full_text="La regola infligge 1d6 danni.",
        attributes={"damage": "1d6"},
        translation_status="translated",
        translation_review_status="conflict",
    )
    translated["translation_review_fingerprint"] = translation_verification_fingerprint(translated)

    row = asyncio.run(canonicalize_group(
        [translated],
        comparator=lambda candidates: {
            "selected_source_record_id": "translated",
            "confidence": .99,
            "notes": "selected",
            "conflict_fields": [],
            "status": "verified",
        },
    ))

    assert row["verification_status"] == "low_confidence"
    assert "visual_or_source_verification" in row["conflict_fields"]


def test_filename_alone_does_not_grant_errata_authority():
    assert source_authority(record("fake", source_key="my_errata_notes.pdf"))[0] == 10


def test_singleton_ocr_uncertainty_cannot_be_certified_by_text_only_ai():
    uncertain = record("ocr", review_flags=["ocr_da_verificare"])
    calls = []
    row = asyncio.run(canonicalize_group(
        [uncertain],
        comparator=lambda candidates: calls.append(candidates) or {
            "selected_source_record_id": "ocr",
            "confidence": .99,
            "notes": "text looks plausible",
            "conflict_fields": [],
            "status": "verified",
        },
    ))
    assert calls
    assert row["verification_status"] == "low_confidence"
    assert row["confidence"] <= .79
    assert "visual_or_source_verification" in row["conflict_fields"]


def test_invalid_or_low_confidence_ai_never_certifies_and_protects_use():
    first, second = record("one", full_text="a"), record("two", full_text="b")
    low = asyncio.run(canonicalize_group(
        [first, second],
        comparator=lambda candidates: {
            "selected_source_record_id": "one", "confidence": .4, "notes": "",
            "conflict_fields": [], "status": "verified",
        },
    ))
    assert low["verification_status"] == "low_confidence"
    assert not reference_is_trusted({"review_status": "verified", "ai_review_status": "conflict"})
    assert not reference_is_trusted({
        "review_status": "verified", "ai_review_status": "verified",
        "ai_review_corrections": {"selected": False},
    })
    invalid = asyncio.run(canonicalize_group(
        [first, second],
        comparator=lambda candidates: {
            "selected_source_record_id": "one", "confidence": 4.0, "notes": "",
            "conflict_fields": [], "status": "verified",
        },
    ))
    assert invalid["verification_status"] == "conflict"
    explicit_conflict = asyncio.run(canonicalize_group(
        [first, second],
        comparator=lambda candidates: {
            "selected_source_record_id": "two", "confidence": .86, "notes": "different rules",
            "conflict_fields": ["full_text"], "status": "conflict",
        },
    ))
    assert explicit_conflict["verification_status"] == "conflict"
    assert explicit_conflict["conflict_fields"] == ["full_text"]


def test_apply_endpoint_rejects_uncertain_canonical_record():
    class Database:
        def __init__(self):
            from core.db import MemoryCollection
            self.private_reference_records = MemoryCollection()

    db = Database()
    db.private_reference_records.rows = [
        record("uncertain", review_status="verified", ai_review_status="low_confidence"),
    ]
    user = type("User", (), {"user_id": "owner"})()

    with pytest.raises(HTTPException) as error:
        asyncio.run(apply_private_reference("uncertain", user=user, db=db))
    assert error.value.status_code == 409


def test_rule_source_keeps_canonical_decision_and_all_provenance():
    canonical_refs = [
        {"source_record_id": "old", "filename": "Manuale.pdf", "selected": False},
        {"source_record_id": "new", "filename": "Errata.pdf", "selected": True},
    ]
    source = reference_rule_source(record(
        "new",
        canonical_id="canon-1",
        ai_review_status="verified",
        ai_confidence=.94,
        ai_review_corrections={
            "selected": True,
            "canonical_source_refs": canonical_refs,
        },
    ))
    assert source["canonical_id"] == "canon-1"
    assert source["canonical_selected"] is True
    assert source["canonical_source_refs"] == canonical_refs


def test_unconfirmed_content_change_invalidates_old_canonical_decision_until_next_batch():
    class Database:
        def __init__(self):
            from core.db import MemoryCollection
            self.private_reference_records = MemoryCollection()
            self.private_reference_canonical = MemoryCollection()
            self.private_reference_review_history = MemoryCollection()

    db = Database()
    db.private_reference_records.rows = [record("selected", review_status="verified")]
    asyncio.run(run_canonicalization("owner", db=db))
    owner = User(
        user_id="owner",
        email="owner@example.test",
        name="Owner",
        is_admin=True,
        premium_manual=True,
    )

    asyncio.run(review_private_reference(
        "selected",
        ReferenceReviewInput(
            review_status="needs_review",
            review_notes="correzione",
            full_text="testo della regola corretto",
        ),
        user=owner,
        db=db,
    ))
    changed = db.private_reference_records.rows[0]
    assert changed["canonical_id"] is None
    assert changed["ai_review_status"] == "pending"
    assert changed["ai_review_corrections"]["canonical_invalidated"] is True
    assert not reference_is_trusted(changed)
    with pytest.raises(HTTPException) as error:
        asyncio.run(apply_private_reference("selected", user=owner, db=db))
    assert error.value.status_code == 409


def test_in_memory_batch_persists_only_live_canonical_columns_and_resumes():
    class Database:
        def __init__(self):
            from core.db import MemoryCollection
            self.private_reference_records = MemoryCollection()
            self.private_reference_canonical = MemoryCollection()

    db = Database()
    db.private_reference_records.rows = [
        record("old", full_text="old", source_refs=[{"filename": "Manuale_del_giocatore.pdf", "page": 1}]),
        record("new", full_text="new", source_key="Errata.pdf", source_refs=[{"filename": "Errata.pdf", "page": 2, "authority_class": "official_errata"}]),
    ]
    result = asyncio.run(run_canonicalization(
        "owner", db=db, comparator=lambda _: {
            "selected_source_record_id": "new", "confidence": .9, "notes": "errata",
            "conflict_fields": [], "status": "verified",
        },
    ))
    row = db.private_reference_canonical.rows[0]
    assert result["processed_groups"] == 1
    assert set(row) == {
        "id", "user_id", "canonical_key", "reference_type", "normalized_name", "name",
        "description", "full_text", "attributes", "parent_class", "parent_subclass", "level",
        "source_record_ids", "source_refs", "source_count", "confidence", "verification_status",
        "conflict_fields", "verification_model", "verification_notes", "created_at", "updated_at",
    }
    assert row["source_record_ids"] == ["new", "old"]
    assert row["source_count"] == 2
    assert {ref["source_record_id"] for ref in row["source_refs"]} == {"old", "new"}
    assert next(item for item in db.private_reference_records.rows if item["id"] == "new")[
        "ai_review_corrections"
    ]["selected"]
    assert asyncio.run(run_canonicalization("owner", db=db))["processed_groups"] == 0
    db.private_reference_canonical.rows.clear()
    assert asyncio.run(run_canonicalization(
        "owner", db=db, comparator=lambda _: {
            "selected_source_record_id": "new", "confidence": .9, "notes": "errata",
            "conflict_fields": [], "status": "verified",
        },
    ))["processed_groups"] == 1
    db.private_reference_records.rows.append(record("next", name="Difesa", normalized_name="difesa"))
    status = asyncio.run(canonicalization_status("owner", db=db))
    assert status == {
        "owner_user_id": "owner", "ruleset": "2014", "total_groups": 2, "pending_groups": 1,
        "verified_groups": 1, "conflict_groups": 0, "low_confidence_groups": 0,
        "excluded_records": 0, "records_total": 3, "canonical_total": 1,
    }


def test_batch_refuses_all_writes_until_translations_are_ready():
    class Database:
        def __init__(self):
            from core.db import MemoryCollection
            self.private_reference_records = MemoryCollection()
            self.private_reference_canonical = MemoryCollection()

    db = Database()
    db.private_reference_records.rows = [record(
        "failed-translation",
        source_language="es",
        source_name="Acción",
        source_full_text="Texto original.",
        translation_status="failed",
    )]

    with pytest.raises(CanonicalizationBlockedError) as error:
        asyncio.run(run_canonicalization("owner", db=db))

    assert error.value.translation_status["translation_failed"] == 1
    assert db.private_reference_canonical.rows == []
    assert db.private_reference_records.rows[0].get("ai_review_status") is None


def test_admin_endpoint_reports_translation_gate_as_conflict():
    class Database:
        def __init__(self):
            from core.db import MemoryCollection
            self.private_reference_records = MemoryCollection()
            self.private_reference_canonical = MemoryCollection()

    db = Database()
    db.private_reference_records.rows = [record(
        "failed-translation",
        source_language="es",
        source_name="Acción",
        source_full_text="Texto original.",
        translation_status="failed",
    )]
    admin = User(
        user_id="owner",
        email="owner@example.test",
        name="Owner",
        is_admin=True,
    )

    with pytest.raises(HTTPException) as error:
        asyncio.run(admin_run_canonicalization(
            CanonicalizationRunInput(user_id="owner"),
            admin=admin,
            db=db,
        ))

    assert error.value.status_code == 409
    assert error.value.detail["code"] == "translation_verification_incomplete"
    assert error.value.detail["translation_status"]["translation_failed"] == 1
