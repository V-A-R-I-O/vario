from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_verify_success():
    res = client.post("/verify", json={
        "email": "emp1@org.example.com",
        "password": "password123"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["email"] == "emp1@org.example.com"
    assert "password" not in data
    assert data["role"] == "end_user"

def test_verify_invalid_password():
    res = client.post("/verify", json={
        "email": "emp1@org.example.com",
        "password": "wrong"
    })
    assert res.status_code == 401

def test_verify_nonexistent_user():
    res = client.post("/verify", json={
        "email": "nobody@org.example.com",
        "password": "password123"
    })
    assert res.status_code == 401

def test_all_seeded_roles_exist():
    # AC 6: ≥1 end_user + 3 admins
    roles_checked = set()
    emails_to_check = [
        "emp1@org.example.com",
        "hr@org.example.com",
        "it@org.example.com",
        "admissions@org.example.com"
    ]
    
    for email in emails_to_check:
        res = client.post("/verify", json={
            "email": email,
            "password": "password123"
        })
        assert res.status_code == 200
        roles_checked.add(res.json()["role"])
        
    assert "end_user" in roles_checked
    assert "hr_admin" in roles_checked
    assert "it_admin" in roles_checked
    assert "admissions_admin" in roles_checked
