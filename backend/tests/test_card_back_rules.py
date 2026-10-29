"""Official back selection is automatic, including for legacy stored cards."""
from schemas.cards import Card, CardBack, approved_back_payload


def test_legacy_styles_are_removed_from_all_read_cards():
    card = Card(
        user_id="user-1",
        type="monster",
        name="Drago",
        back={
            "variant": "silver",
            "style": "runic",
            "color": "#ff0000",
            "emblem": "skull",
            "motto": "Retro obsoleto",
        },
    )
    assert card.model_dump()["back"] == {"variant": "luminous"}


def test_character_is_only_category_with_two_back_variants():
    luminous = Card(user_id="user-1", type="character", back={"variant": "luminous"})
    silver = Card(user_id="user-1", type="character", back={"variant": "silver", "style": "damask"})
    assert luminous.model_dump()["back"] == {"variant": "luminous"}
    assert silver.model_dump()["back"] == {"variant": "silver"}
    assert Card(user_id="user-1", type="spell", back={"variant": "silver"}).model_dump()["back"] == {
        "variant": "luminous"
    }


def test_approved_back_payload_sanitizes_all_saved_categories():
    for kind in ("monster", "class", "subclass", "class_feature", "spell", "feat",
                 "race", "subrace", "weapon", "armor", "shield", "magic_item", "item", "custom"):
        assert approved_back_payload(kind, {"variant": "silver", "style": "runic"}) == {
            "variant": "luminous"
        }
    assert approved_back_payload("character", {"variant": "silver", "motto": "old"}) == {
        "variant": "silver"
    }
    assert approved_back_payload("character", CardBack()) == {"variant": "luminous"}
    assert approved_back_payload("monster") == {"variant": "luminous"}
