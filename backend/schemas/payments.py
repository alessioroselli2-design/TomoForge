from pydantic import BaseModel

from core.config import PREMIUM_LOOKUP_KEY


class PremiumToggle(BaseModel):
    enabled: bool


class CheckoutRequest(BaseModel):
    lookup_key: str = PREMIUM_LOOKUP_KEY
    origin_url: str
