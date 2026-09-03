from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class SpellImportResult(BaseModel):
    imported: int
    updated: int
    flagged_for_review: int
    skipped: int


class ReferenceImportInput(BaseModel):
    filenames: list[str] = Field(default_factory=list)
    start_page: int = Field(default=5, ge=1)
    end_page: Optional[int] = Field(default=None, ge=1)
    use_ai_ocr: bool = False
    external_processing_confirmed: bool = False
    translation_processing_confirmed: bool = False
    auto_accept: bool = False
    translation_batch_size: int = Field(default=2, ge=1, le=4)


class ReferenceImportResult(BaseModel):
    imported: int
    updated: int
    flagged_for_review: int
    skipped: int
    sources: list[dict]


class ManualPreloadInput(BaseModel):
    """Automatic preload intent; legacy consent fields remain API-compatible."""
    filename: Optional[str] = None
    enable_translation: bool = False
    enable_ocr: bool = False
    translation_processing_confirmed: bool = False
    external_processing_confirmed: bool = False
    retry: bool = False


class ReferenceReviewInput(BaseModel):
    review_status: Literal["pending", "verified", "needs_review"]
    review_notes: str = Field(default="", max_length=3000)
    # `corrected_*` is kept for the existing editor contract; the shorter
    # fields are used by the dedicated review queue.
    corrected_name: Optional[str] = Field(default=None, max_length=300)
    corrected_description: Optional[str] = Field(default=None, max_length=12000)
    corrected_full_text: Optional[str] = Field(default=None, max_length=120000)
    corrected_attributes: Optional[dict[str, Any]] = None
    name: Optional[str] = Field(default=None, max_length=240)
    description: Optional[str] = Field(default=None, max_length=12000)
    full_text: Optional[str] = Field(default=None, max_length=120000)
    attributes: Optional[dict[str, Any]] = None


class CanonicalizationRunInput(BaseModel):
    user_id: Optional[str] = None
    batch_size: int = Field(default=5, ge=1, le=25)
    ruleset: Literal["2014"] = "2014"


class TranslationRetryRunInput(BaseModel):
    user_id: Optional[str] = None
    batch_size: int = Field(default=5, ge=1, le=25)


class TranslationVerificationRunInput(BaseModel):
    user_id: Optional[str] = None
    batch_size: int = Field(default=5, ge=1, le=25)
