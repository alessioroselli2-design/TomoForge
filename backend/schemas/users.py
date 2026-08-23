from typing import Optional

from pydantic import BaseModel, EmailStr


class User(BaseModel):
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    auth_provider: str = "email"
    is_admin: bool = False
    premium_manual: bool = False
    premium_until: Optional[str] = None
    supabase_auth_id: Optional[str] = None


class RegisterInput(BaseModel):
    email: EmailStr
    password: str
    name: str


class LoginInput(BaseModel):
    email: EmailStr
    password: str


class SupabaseSessionInput(BaseModel):
    access_token: str
