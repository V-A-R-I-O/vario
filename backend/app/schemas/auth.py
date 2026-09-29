from pydantic import BaseModel

class LoginRequest(BaseModel):
    email: str
    password: str

class UserData(BaseModel):
    user_id: str
    email: str
    full_name: str
    role: str
    external_id: str
    token: str
