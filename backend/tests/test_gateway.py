import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_envelope_wrapper_success():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["status"] == "ok"
        assert data["error"] is None

@pytest.mark.asyncio
async def test_protected_route_missing_auth():
    # Trying to access a dummy protected route or non-existent api route
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/chat")
        assert response.status_code == 401
        data = response.json()
        assert data["status"] == "error"
        assert data["error"] == "Missing or invalid token"

@pytest.mark.asyncio
async def test_invalid_body_422():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Auth login expects email and password
        response = await client.post("/api/auth/login", json={"email": "wrong"})
        assert response.status_code == 422
        data = response.json()
        assert data["status"] == "error"
        assert "Validation error" in data["error"]

@pytest.mark.asyncio
async def test_rate_limiting():
    from app.utils.rate_limit import limiter
    limiter.requests.clear()
    
    transport = ASGITransport(app=app, client=("192.168.1.100", 12345))
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Hit /api/auth/login 11 times from same IP
        for _ in range(10):
            res = await client.post("/api/auth/login", json={"email": "a", "password": "b"})
        
        res = await client.post("/api/auth/login", json={"email": "a", "password": "b"})
        assert res.status_code == 429
        data = res.json()
        assert data["status"] == "error"
        assert "Rate limit exceeded" in data["error"]
        assert "x-ratelimit-limit" in res.headers
        
    limiter.requests.clear()


async def _login(client, email):
    return await client.post("/api/auth/login", json={"email": email, "password": "wrong"})


@pytest.mark.asyncio
async def test_login_limit_is_per_account_not_per_address():
    # N3: four presenters behind the demo proxy arrive from one address.
    from app.utils.rate_limit import limiter
    limiter.requests.clear()

    transport = ASGITransport(app=app, client=("172.18.0.9", 40000))  # the proxy
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for _ in range(10):
            assert (await _login(client, "pavan@org.example.com")).status_code != 429
        assert (await _login(client, "Pavan@org.example.com ")).status_code == 429
        # Another presenter on another laptop, same proxy address, still gets in.
        assert (await _login(client, "rohith@org.example.com")).status_code != 429
    limiter.requests.clear()


@pytest.mark.asyncio
async def test_one_address_is_still_capped_across_accounts():
    from app.utils.rate_limit import limiter
    limiter.requests.clear()

    transport = ASGITransport(app=app, client=("192.168.1.100", 12345))
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for i in range(60):
            assert (await _login(client, f"user{i}@org.example.com")).status_code != 429
        assert (await _login(client, "user60@org.example.com")).status_code == 429
    limiter.requests.clear()


@pytest.mark.asyncio
async def test_auth_route_injects_user_state():
    # To test this we need a dummy route. 
    # Instead of creating one in production code, we can inject one for test only.
    @app.get("/api/test-protected")
    def test_protected(request: pytest.importorskip("fastapi").Request):
        return {
            "user_id": request.state.user_id,
            "role": request.state.role,
            "email": request.state.email
        }
    
    from app.services.jwt_service import issue_token
    token = issue_token("u1", "end_user", "test@test.com")
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/test-protected", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert data["data"]["user_id"] == "u1"
        assert data["data"]["role"] == "end_user"
        assert data["data"]["email"] == "test@test.com"

