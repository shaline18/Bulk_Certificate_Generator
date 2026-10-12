
from fastapi.testclient import TestClient

from bulk_certificate_generator.main import app

client = TestClient(app)


def test_home():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "message": "Bulk Certificate Generator API"
    }


def test_invalid_certificate_request():
    response = client.post(
        "/jobs",
        json={
            "event_name": "",
            "event_date": "2026-10-08",
            "issuer": "ABC Organization",
            "recipients": [
                {
                    "name": "",
                    "email": "invalid-email"
                }
            ]
        }
    )

    assert response.status_code == 422

