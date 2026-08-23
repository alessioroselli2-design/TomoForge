from typing import Optional

from pydantic import BaseModel


class GenerateContentInput(BaseModel):
    type: str
    custom_type: Optional[str] = None
    prompt: str
    language: str = "it"


class GenerateImageInput(BaseModel):
    prompt: str
    type: Optional[str] = None
    cleanup: bool = False
