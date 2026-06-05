import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.mark.parametrize(
    ("path", "method"),
    [
        ("/profile", "PATCH"),
        ("/advice/llm/generate", "POST"),
    ],
)
def test_cors_preflight_allows_frontend_dev_origin(path: str, method: str) -> None:
    with TestClient(app) as client:
        response = client.options(
            path,
            headers={
                "Origin": "http://127.0.0.1:5173",
                "Access-Control-Request-Method": method,
            },
        )

    assert response.status_code in {200, 204}
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
