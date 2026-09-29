import pytest
from unittest.mock import patch
from sqlalchemy.future import select
from app.models.user import User

@pytest.mark.asyncio
@patch("app.services.auth_adapter.AuthAdapter.authenticate")
async def test_login_success_first_time(mock_authenticate, async_client, db_session):
    # AC 1: Correct creds -> 200 with standard envelope
    # AC 3: First login -> row created
    
    mock_authenticate.return_value = {
        "user_id": "00000000-0000-0000-0000-000000000001",
        "email": "test@org.example.com",
        "full_name": "Test User",
        "role": "end_user",
        "external_id": "EMP-999"
    }
    
    res = await async_client.post("/api/auth/login", json={
        "email": "test@org.example.com",
        "password": "password123"
    })
    
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["error"] is None
    
    user_data = data["data"]
    assert user_data["email"] == "test@org.example.com"
    assert user_data["role"] == "end_user"
    assert "token" in user_data
    
    # Check database to ensure it was created
    result = await db_session.execute(select(User).where(User.external_id == "EMP-999"))
    db_user = result.scalars().first()
    assert db_user is not None
    assert db_user.full_name == "Test User"
    
@pytest.mark.asyncio
@patch("app.services.auth_adapter.AuthAdapter.authenticate")
async def test_login_success_second_time(mock_authenticate, async_client, db_session):
    # AC 4: Subsequent login -> no duplicate, row updated
    
    # Pre-insert user
    initial_user = User(
        email="test@org.example.com",
        full_name="Old Name",
        role="end_user",
        external_id="EMP-999"
    )
    db_session.add(initial_user)
    await db_session.commit()
    
    mock_authenticate.return_value = {
        "user_id": "00000000-0000-0000-0000-000000000001",
        "email": "newemail@org.example.com",
        "full_name": "New Name",
        "role": "hr_admin",
        "external_id": "EMP-999"
    }
    
    res = await async_client.post("/api/auth/login", json={
        "email": "test@org.example.com",
        "password": "password123"
    })
    
    assert res.status_code == 200
    
    # Check DB again
    # We must clear the session to avoid reading from identity map
    db_session.expunge_all()
    result = await db_session.execute(select(User).where(User.external_id == "EMP-999"))
    users = result.scalars().all()
    assert len(users) == 1
    db_user = users[0]
    
    assert db_user.full_name == "New Name"
    assert db_user.email == "newemail@org.example.com"
    assert db_user.role == "hr_admin"

@pytest.mark.asyncio
@patch("app.services.auth_adapter.AuthAdapter.authenticate")
async def test_login_invalid_credentials(mock_authenticate, async_client):
    # AC 2: Wrong credentials -> 401 with standard envelope
    mock_authenticate.return_value = None
    
    res = await async_client.post("/api/auth/login", json={
        "email": "wrong@org.example.com",
        "password": "badpassword"
    })
    
    assert res.status_code == 401
    data = res.json()
    assert data["status"] == "error"
    assert data["data"] is None
    assert data["error"] == "Invalid email or password"
