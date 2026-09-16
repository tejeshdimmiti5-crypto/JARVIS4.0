from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["vector_store"] == "chroma"


def test_chat_offline():
    response = client.post("/api/chat", json={"question": "What is a stack?"})
    assert response.status_code == 200
    assert "LIFO" in response.json()["answer"]
    assert response.json()["used_ai"] is False


def test_register_login_and_notes():
    email="test-student@example.com"
    password="StudentAI123!"
    register=client.post("/api/auth/register",json={"email":email,"password":password})
    assert register.status_code in (200,409)
    if register.status_code == 409:
        login=client.post("/api/auth/login",json={"email":email,"password":password})
        assert login.status_code==200
        token=login.json()["access_token"]
    else:
        token=register.json()["access_token"]
    headers={"Authorization":f"Bearer {token}"}
    note=client.post("/api/notes",headers=headers,json={"title":"DSA Revision","content":"Stacks use LIFO."})
    assert note.status_code==200
    notes=client.get("/api/notes",headers=headers)
    assert notes.status_code==200
    assert any(n["title"]=="DSA Revision" for n in notes.json())
