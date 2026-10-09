import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.services.jwt_service import issue_token

@pytest.fixture
def auth_headers():
    token = issue_token("u1", "end_user", "test@test.com")
    return {"Authorization": f"Bearer {token}"}

@pytest.mark.asyncio
async def test_create_and_list_conversations(auth_headers):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create
        res = await client.post("/api/conversations", json={"role_pack": "hr"}, headers=auth_headers)
        assert res.status_code == 201
        data = res.json()["data"]
        assert data["role_pack"] == "hr"
        assert "New HR conversation" in data["title"]
        conv_id = data["id"]
        
        # List
        res2 = await client.get("/api/conversations", headers=auth_headers)
        assert res2.status_code == 200
        list_data = res2.json()["data"]["conversations"]
        assert len(list_data) >= 1
        assert list_data[0]["id"] == conv_id
        
        # List messages
        res3 = await client.get(f"/api/conversations/{conv_id}/messages", headers=auth_headers)
        assert res3.status_code == 200
        msg_data = res3.json()["data"]
        assert msg_data["conversation_id"] == conv_id
        assert len(msg_data["messages"]) == 0
