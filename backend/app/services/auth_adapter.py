import httpx
from typing import Optional, Dict, Any
from app.config import settings

class AuthAdapter:
    @staticmethod
    async def authenticate(email: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Validates credentials against the org's identity provider (Mock Auth Service).
        Returns the user record on success, None on failure.
        """
        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(
                    f"{settings.MOCK_AUTH_URL}/verify",
                    json={"email": email, "password": password},
                    timeout=5.0
                )
                if res.status_code == 200:
                    return res.json()
        except httpx.RequestError as e:
            raise ConnectionError(f"Auth service unavailable: {str(e)}")
        return None
