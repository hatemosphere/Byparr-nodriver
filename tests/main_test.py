from http import HTTPStatus

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from main import app
from src.models import LinkRequest

test_websites = [
    "https://ext.to/",
    "https://www.ygg.re/",
    "https://extratorrent.st/",
    "https://idope.se/",
    "https://speed.cd/login",
    'https://www.yggtorrent.top/engine/search?do=search&order=desc&sort=publish_date&name="UNESCAPED"+"DOUBLEQUOTES"&category=2145'
]


@pytest.mark.asyncio
@pytest.mark.parametrize("website", test_websites)
async def test_bypass(website: str):
    """
    Tests if the service can bypass cloudflare/DDOS-GUARD on given websites.

    This test is skipped if the website is not reachable or does not have cloudflare/DDOS-GUARD.
    """
    async with httpx.AsyncClient() as test_client:
        test_request = await test_client.get(website)
        if (
            test_request.status_code != HTTPStatus.OK
            and "Just a moment..." not in test_request.text
        ):
            pytest.skip(f"Skipping {website} due to {test_request.status_code}")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/v1",
            json={
                **LinkRequest.model_construct(
                    url=website, max_timeout=30, cmd="request.get"
                ).model_dump(),
            },
            timeout=40.0,
        )

        assert response.status_code == HTTPStatus.OK


@pytest.mark.asyncio
async def test_health_check():
    """
    Tests the health check endpoint.

    This test ensures that the health check
    endpoint returns HTTPStatus.OK.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health", timeout=30.0)
        assert response.status_code == HTTPStatus.OK
