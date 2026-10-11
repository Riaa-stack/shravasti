from pydantic import BaseModel

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: str | None = None
    name: str | None = None
    email: str | None = None
    role: str | None = None

class TokenPayload(BaseModel):
    sub: str | None = None
    role: str | None = None
