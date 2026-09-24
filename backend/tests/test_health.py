from httpx import AsyncClient


async def test_health(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_versioned_health_and_request_id(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health", headers={"x-request-id": "test-id"})
    assert response.status_code == 200
    assert response.headers["x-request-id"] == "test-id"
