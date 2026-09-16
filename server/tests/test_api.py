from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_chat_offline():
    response = client.post("/api/chat", json={"question": "What is a stack?"})
    assert response.status_code == 200
    assert "LIFO" in response.json()["answer"]
    assert response.json()["used_ai"] is False
