from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from typing import Dict, Any

from app.seed_data import SEED_USERS

app = FastAPI(title="Mock Auth Service")

class VerifyRequest(BaseModel):
    email: str
    password: str

@app.post("/verify")
def verify_credentials(req: VerifyRequest) -> Dict[str, Any]:
    user = SEED_USERS.get(req.email)
    if not user or user["password"] != req.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Return user record without password
    user_copy = user.copy()
    user_copy.pop("password")
    return user_copy
