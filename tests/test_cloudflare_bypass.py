import httpx
import pytest


@pytest.mark.asyncio
async def test_cloudflare_bypass():
    """Test Cloudflare bypass using nopecha.com demo."""
    async with httpx.AsyncClient() as client:
        # Test the Cloudflare demo page
        response = await client.post(
            "http://localhost:8191/v1",
            json={
                "cmd": "request.get",
                "url": "https://nopecha.com/demo/cloudflare",
                "maxTimeout": 60000
            },
            timeout=70.0
        )

        assert response.status_code == 200
        data = response.json()

        # Check the response structure
        assert data["status"] == "ok"
        assert data["message"] == "Success"
        assert "solution" in data

        solution = data["solution"]
        assert solution["status"] == 200
        assert solution["url"].startswith("https://nopecha.com/demo/cloudflare")
        assert len(solution["cookies"]) > 0
        assert solution["userAgent"] != ""

        # Check if we got past the Cloudflare challenge
        assert "Just a moment..." not in solution["response"]
        assert "Cloudflare" not in solution["response"] or "challenge" not in solution["response"].lower()

        # Look for evidence we reached the actual page
        # The nopecha demo page should have some specific content
        assert "nopecha" in solution["response"].lower() or "demo" in solution["response"].lower()


@pytest.mark.asyncio
async def test_regular_page_no_challenge():
    """Test that regular pages work without challenge."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8191/v1",
            json={
                "cmd": "request.get",
                "url": "https://example.com",
                "maxTimeout": 60000
            },
            timeout=70.0
        )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "ok"
        assert data["solution"]["status"] == 200
        assert "Example Domain" in data["solution"]["response"]
