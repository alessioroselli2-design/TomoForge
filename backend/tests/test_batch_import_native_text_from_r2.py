from scripts.batch_import_native_text_from_r2 import _eligibility_reason


def test_accepts_active_italian_native_text_authority():
    assert _eligibility_reason(
        "Manuale del giocatore .pdf",
        {
            "language": "it",
            "text_mode": "text",
            "source_status": "active",
            "source_role": "authority",
        },
    ) == ""


def test_rejects_vision_sources():
    reason = _eligibility_reason(
        "847921086-Manuale-Dei-Mostri-5e.pdf",
        {
            "language": "it",
            "text_mode": "vision_required",
            "source_status": "active",
            "source_role": "authority",
        },
    )
    assert reason == "text mode vision_required"


def test_rejects_non_italian_sources():
    reason = _eligibility_reason(
        "616924846-Volo-s-Guide-to-Monsters.pdf",
        {
            "language": "en",
            "text_mode": "text",
            "source_status": "active",
            "source_role": "authority",
        },
    )
    assert reason == "language en"


def test_rejects_spell_card_aids_even_when_text_native():
    reason = _eligibility_reason(
        "Ranger .pdf",
        {
            "language": "it",
            "text_mode": "text",
            "source_status": "active",
            "source_role": "extraction_aid",
        },
    )
    assert reason == "spell-card extraction aid"
