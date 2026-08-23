import uuid
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from core.config import utc_now


class CardBack(BaseModel):
    style: str = "classic"
    color: str = "#7f1d1d"
    emblem: str = "flame"
    motto: str = ""


class CardAppearance(BaseModel):
    title_effect: Literal[
        "gold", "silver", "rainbow", "crimson", "azure",
        "violet", "emerald", "copper", "rose", "arctic",
        "onyx", "amber", "ruby",
    ] = "gold"
    title_shadow: bool = True
    description_opacity: float = Field(default=0.64, ge=0.3, le=0.9)
    text_panel_color: str = "#05080a"
    text_color: str = "#f5f1df"
    front_background_start: str = "#151311"
    front_background_end: str = "#151311"
    front_background_gradient: bool = False
    title_custom_color_enabled: bool = False
    title_custom_color: str = "#f8d764"
    frame_custom_color_enabled: bool = False
    frame_custom_color: str = "#d4af37"


class Card(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    type: str
    custom_type: Optional[str] = None
    name: str = ""
    description: str = ""
    story: str = ""
    language: str = "it"
    attributes: dict = Field(default_factory=dict)
    artwork_path: Optional[str] = None
    frame: str = "gold"
    appearance: CardAppearance = Field(default_factory=CardAppearance)
    back: CardBack = Field(default_factory=CardBack)
    reference_ids: list[str] = Field(default_factory=list)
    spell_ids: list[str] = Field(default_factory=list)
    rule_sources: list[dict] = Field(default_factory=list)
    source_refs: list[dict] = Field(default_factory=list)
    reference_snapshots: list[dict] = Field(default_factory=list)
    change_history: list[dict] = Field(default_factory=list)
    version: int = 0
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)


class CardCreate(BaseModel):
    type: str
    custom_type: Optional[str] = None
    name: str = ""
    description: str = ""
    story: str = ""
    language: str = "it"
    attributes: dict = Field(default_factory=dict)
    artwork_path: Optional[str] = None
    frame: str = "gold"
    appearance: Optional[CardAppearance] = None
    back: Optional[CardBack] = None
    reference_ids: list[str] = Field(default_factory=list)
    spell_ids: list[str] = Field(default_factory=list)
    rule_sources: list[dict] = Field(default_factory=list)
    source_refs: list[dict] = Field(default_factory=list)


class CardUpdate(BaseModel):
    type: Optional[str] = None
    custom_type: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    story: Optional[str] = None
    language: Optional[str] = None
    attributes: Optional[dict] = None
    artwork_path: Optional[str] = None
    frame: Optional[str] = None
    appearance: Optional[CardAppearance] = None
    back: Optional[CardBack] = None
    reference_ids: Optional[list[str]] = None
    spell_ids: Optional[list[str]] = None
    rule_sources: Optional[list[dict]] = None
    source_refs: Optional[list[dict]] = None
    version: int = Field(..., ge=0)


class LinkedCardInput(BaseModel):
    reference_ids: list[str] = Field(default_factory=list)
    version: int = Field(..., ge=0)


class ReferenceUpdateInput(BaseModel):
    reference_ids: list[str] = Field(default_factory=list)
    version: int = Field(..., ge=0)


class ManualCompletionInput(BaseModel):
    """The server derives the eligible fields from the card's own identity."""
    version: int = Field(..., ge=0)


class CardVersionInput(BaseModel):
    version: int = Field(..., ge=0)
