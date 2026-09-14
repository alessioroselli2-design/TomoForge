"""Conservative guided matcher for independently OCR-derived monster core fields.

This module is the first production matcher relaxation derived from repeated
privacy-safe diagnostics. It remains fail-closed: all three core fields must
agree semantically, and any textual disagreement must fit one of the explicitly
proven residual shapes before a guided merge is allowed.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Mapping

from services.monster_residual_diagnostics import residual_shape_core_field_matches
from services.monster_semantic_diagnostics import (
    deterministic_core_field_matches,
    semantic_core_field_matches,
)
from services.monster_speed_token_diagnostics import speed_multi_extra_token_profile

_CORE_FIELDS = ("classe_armatura", "punti_ferita", "velocita")
_ALPHA_RE = re.compile(r"[^\W\d_]+", re.UNICODE)


def _richness_score(value: object) -> tuple[int, int, int]:
    """Rank a transcription by retained information without semantic guessing."""
    text = unicodedata.normalize("NFKC", str(value or "")).strip()
    if not text:
        return (0, 0, 0)
    alpha_tokens = _ALPHA_RE.findall(text.casefold())
    alphanumeric = sum(char.isalnum() for char in text)
    return (len(alpha_tokens), alphanumeric, len(text))


def _richer_value(left: object, right: object) -> object:
    """Choose the more information-rich value; preserve primary on an exact tie."""
    return right if _richness_score(right) > _richness_score(left) else left


def guided_core_merge(
    left_attributes: Mapping[str, object],
    right_attributes: Mapping[str, object],
) -> dict[str, object] | None:
    """Return merged core values only when every conservative gate passes.

    Allowed residual shapes are intentionally narrow:
    - armor class: punctuation/symbol/spacing-only variation;
    - hit points: one extra alphabetic suffix token shorter than three letters;
    - speed: three or more extra alphabetic tokens, excluding duplicate ambiguity.

    A field that already matches after deterministic normalization is also safe,
    but at least one of the three proven residual shapes must be present for this
    guided path to be used. Unknown residual shapes fail closed.
    """
    semantic = semantic_core_field_matches(left_attributes, right_attributes)
    if not all(semantic.get(f"{field}_semantic_match", False) for field in _CORE_FIELDS):
        return None

    deterministic = deterministic_core_field_matches(left_attributes, right_attributes)
    residual = residual_shape_core_field_matches(left_attributes, right_attributes)
    speed_profile = speed_multi_extra_token_profile(left_attributes, right_attributes)

    ca_residual = residual.get(
        "classe_armatura_residual_non_alphanumeric_only_variation",
        False,
    )
    hp_residual = bool(
        residual.get("punti_ferita_residual_single_extra_alpha_token_short_lt3", False)
        and residual.get("punti_ferita_residual_single_extra_alpha_token_suffix", False)
    )
    speed_residual = bool(
        speed_profile.get("velocita_residual_extra_alpha_tokens_3_or_more", False)
        and not speed_profile.get("velocita_residual_duplicate_ambiguous", False)
    )

    field_gates = {
        "classe_armatura": bool(
            deterministic.get("classe_armatura_deterministic_match", False) or ca_residual
        ),
        "punti_ferita": bool(
            deterministic.get("punti_ferita_deterministic_match", False) or hp_residual
        ),
        "velocita": bool(
            deterministic.get("velocita_deterministic_match", False) or speed_residual
        ),
    }
    if not all(field_gates.values()):
        return None
    if not (ca_residual or hp_residual or speed_residual):
        return None

    return {
        field: _richer_value(left_attributes.get(field), right_attributes.get(field))
        for field in _CORE_FIELDS
    }
