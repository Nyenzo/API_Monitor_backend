from pydantic import BaseModel, EmailStr, Field


# Request body for new user registration
class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(default="", max_length=255)


# Request body for email/password login
class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


# Returned after signup, login, or token refresh with both tokens
class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    user_id: str
    email: str


# Request body for exchanging a refresh token for a new access token
class RefreshRequest(BaseModel):
    refresh_token: str


# Minimal user identity returned by the /auth/me endpoint
class UserInfo(BaseModel):
    id: str
    email: str
