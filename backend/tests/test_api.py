"""Tests for the API routes — request validation and SSRF protection."""

import pytest
from httpx import AsyncClient, ASGITransport
from main import app


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_check(self, client):
        async with client as c:
            response = await c.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"


class TestAuditEndpointValidation:
    @pytest.mark.asyncio
    async def test_invalid_url_rejected(self, client):
        async with client as c:
            response = await c.post("/api/audit", json={"url": "not-a-url"})
            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_localhost_blocked(self, client):
        async with client as c:
            response = await c.post("/api/audit", json={"url": "http://localhost:8080"})
            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_127_0_0_1_blocked(self, client):
        async with client as c:
            response = await c.post("/api/audit", json={"url": "http://127.0.0.1:3000"})
            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_url_rejected(self, client):
        async with client as c:
            response = await c.post("/api/audit", json={})
            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_empty_body_rejected(self, client):
        async with client as c:
            response = await c.post(
                "/api/audit",
                content="",
                headers={"Content-Type": "application/json"},
            )
            assert response.status_code == 422
