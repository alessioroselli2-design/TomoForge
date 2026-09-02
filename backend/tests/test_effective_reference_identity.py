from reference_library import (
    parse_reference_page,
    reference_effective_level,
    reference_effective_type,
    reference_to_card_payload,
)
from services.canonical import canonical_group_key
from services.canonical_identity import (
    identity_candidate_score,
    identity_candidates,
)


def legacy(identifier, **changes):
    record = {
        "id": identifier,
        "user_id": "owner",
        "reference_type": "ability",
        "name": "Palla di Fuoco",
        "normalized_name": "palla di fuoco",
        "source_key": f"{identifier}.pdf",
        "source_language": "it",
        "translation_status": "not_required",
        "full_text": (
            "Invocazione di 3° livello Tempo di Lancio: 1 azione "
            "Gittata: 45 metri Componenti: V, S, M (zolfo) "
            "Durata: Istantanea Una sfera di fuoco esplode sul bersaglio "
            "e il testo conserva una descrizione regolamentare completa."
        ),
        "source_full_text": "",
        "attributes": {},
        "source_attributes": {},
        "parent_class": "",
        "parent_subclass": "",
        "level": "",
        "ai_review_corrections": {},
    }
    record.update(changes)
    return record


def test_spanish_parenthetical_cantrip_is_parsed_as_spell():
    page = """ILUSIÓN MENOR
Ilusionismo (truco)
Tiempo de lanzamiento: 1 acción
Alance: 30 pies
Componentes: S, M (un poco de vellón)
Duración: 1 minuto
Creas una imagen o un sonido que dura durante el tiempo indicado y conserva
suficiente texto reglamentario para que el parser pueda validar el bloque.
"""
    records = parse_reference_page(
        page,
        "Manual del Jugador.pdf",
        684,
        "es",
    )

    assert len(records) == 1
    spell = records[0]
    assert spell["reference_type"] == "spell"
    assert spell["level"] == "0"
    assert spell["attributes"]["livello"] == "0"
    assert spell["attributes"]["scuola"] == "Ilusión"


def test_legacy_italian_spell_type_is_derived_without_mutation():
    record = legacy("legacy")

    assert record["reference_type"] == "ability"
    assert reference_effective_type(record) == "spell"
    assert reference_effective_level(record) == "3"
    assert record["reference_type"] == "ability"


def test_legacy_spanish_parenthetical_cantrip_becomes_effective_spell():
    record = legacy(
        "spanish",
        reference_type="other",
        name="Shillelagh",
        normalized_name="shillelagh",
        source_language="es",
        translation_status="translated",
        source_full_text=(
            "Transmutación (truco) Tiempo de lanzamiento: 1 acción adicional "
            "Alance: Toque Componentes: V, S, M (muérdago) Duración: 1 minuto "
            "La madera queda imbuida con el poder de la naturaleza."
        ),
        full_text=(
            "Trasmutazione (trucco) Tempo di lancio: 1 azione aggiuntiva "
            "Raggio: Contatto Componenti: V, S, M Durata: 1 minuto "
            "Il legno viene infuso con il potere della natura."
        ),
    )

    assert reference_effective_type(record) == "spell"
    assert reference_effective_level(record) == "0"

    card = reference_to_card_payload(record)
    assert card["card_type"] == "spell"
    assert card["reference_type"] == "spell"
    assert card["level"] == "0"


def test_prose_does_not_get_promoted_to_spell_without_spell_structure():
    record = legacy(
        "feature",
        reference_type="class_feature",
        full_text=(
            "Invocazione potente che permette al personaggio di usare "
            "una capacità speciale durante il combattimento."
        ),
    )

    assert reference_effective_type(record) == "class_feature"


def test_canonical_key_groups_legacy_spell_with_true_spell():
    old = legacy("old")
    parsed = legacy(
        "parsed",
        reference_type="spell",
        level="3",
    )

    assert canonical_group_key(old) == canonical_group_key(parsed)


def test_identity_prefilter_accepts_cross_legacy_spell_type():
    old = legacy("old")
    parsed = legacy(
        "parsed",
        reference_type="spell",
        level="3",
        source_language="es",
        translation_status="translated",
    )

    assert identity_candidate_score(old, parsed) >= 0
    assert parsed in identity_candidates(old, [old, parsed])
