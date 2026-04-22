# api/tests/test_aib_api.py
import pytest
from ninja.testing import TestClient
from unittest.mock import patch, MagicMock


@pytest.fixture
def client():
    from aib.api import router
    return TestClient(router)


@pytest.mark.django_db
def test_create_session(client):
    response = client.post("/sessions/")
    assert response.status_code == 201
    data = response.json()
    assert "session_id" in data
    assert "session_token" in data


@pytest.mark.django_db
def test_get_session(client):
    from aib.models import AibSession
    session = AibSession.objects.create()
    response = client.get(
        f"/sessions/{session.id}/",
        headers={"X-AIB-Token": session.session_token},
    )
    assert response.status_code == 200
    data = response.json()
    assert str(data["session_id"]) == str(session.id)
    assert data["messages"] == []


@pytest.mark.django_db
def test_get_session_wrong_token_returns_403(client):
    from aib.models import AibSession
    session = AibSession.objects.create()
    response = client.get(
        f"/sessions/{session.id}/",
        headers={"X-AIB-Token": "bad-token"},
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_send_message(client):
    from aib.models import AibSession
    session = AibSession.objects.create()
    mock_reply = ("Hello! I'm Trudy.", {"company_name": None})

    with patch("aib.api.AibService") as MockService:
        MockService.return_value.chat.return_value = mock_reply
        response = client.post(
            f"/sessions/{session.id}/messages/",
            json={"content": "Hi", "step": "get-started"},
            headers={"X-AIB-Token": session.session_token},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Hello! I'm Trudy."
    assert "extracted_fields" in data


@pytest.mark.django_db
def test_claim_session_requires_auth(client):
    from aib.models import AibSession
    session = AibSession.objects.create()
    response = client.post(
        f"/sessions/{session.id}/claim/",
        json={"session_token": session.session_token},
    )
    assert response.status_code == 401
