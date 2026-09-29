import pytest
from app.services.jwt_service import issue_token, verify_token
from app.config import settings

def test_jwt_issue_and_verify():
    # AC 5: decoded JWT contains user_id, role, email
    token = issue_token(user_id="user-123", role="hr_admin", email="hr@org.com")
    
    payload = verify_token(token)
    assert payload["sub"] == "user-123"
    assert payload["role"] == "hr_admin"
    assert payload["email"] == "hr@org.com"
    assert "exp" in payload

def test_jwt_invalid_token():
    with pytest.raises(ValueError, match="Invalid or expired token"):
        verify_token("invalid.token.string")
