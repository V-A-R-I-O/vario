from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.schemas.auth import LoginRequest, UserData
from app.services.auth_adapter import AuthAdapter
from app.services.jwt_service import issue_token
from app.models.user import User
from app.utils.envelope import success_response, error_response

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/login")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    # 1. Authenticate via Mock Auth Adapter
    try:
        auth_data = await AuthAdapter.authenticate(req.email, req.password)
        if not auth_data:
            return JSONResponse(
                status_code=401,
                content=error_response("Invalid email or password")
            )
    except ConnectionError as e:
        return JSONResponse(
            status_code=503,
            content=error_response("Authentication service is currently unavailable")
        )
    
    # 2. Upsert user in database
    result = await db.execute(select(User).where(User.external_id == auth_data["external_id"]))
    user = result.scalars().first()
    
    if not user:
        # First login -> create
        user = User(
            email=auth_data["email"],
            full_name=auth_data["full_name"],
            role=auth_data["role"],
            external_id=auth_data["external_id"]
        )
        db.add(user)
    else:
        # Subsequent login -> update
        user.email = auth_data["email"]
        user.full_name = auth_data["full_name"]
        user.role = auth_data["role"]
    
    await db.commit()
    await db.refresh(user)
    
    # 3. Issue VARIO JWT
    token = issue_token(user_id=user.user_id, role=user.role, email=user.email)
    
    # 4. Return standard envelope
    user_data = UserData(
        user_id=user.user_id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        external_id=user.external_id,
        token=token
    )
    
    return JSONResponse(
        status_code=200,
        content=success_response(user_data.model_dump())
    )
