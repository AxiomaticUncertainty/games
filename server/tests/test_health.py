from fastapi.testclient import TestClient

from tests.conftest import log_in


def test_healthz_reports_ok_without_logging_in(client: TestClient) -> None:
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_docs_are_not_exposed(client: TestClient) -> None:
    log_in(client)

    for path in ("/docs", "/redoc", "/openapi.json"):
        assert client.get(path).status_code == 404, path
