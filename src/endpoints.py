import time
from http import HTTPStatus
from typing import Optional

from bs4 import BeautifulSoup
from fastapi import APIRouter, HTTPException, Header
from fastapi.responses import RedirectResponse
import nodriver as uc

from src.consts import CHALLENGE_TITLES
from src.models import (
    HealthcheckResponse,
    LinkRequest,
    LinkResponse,
    Solution,
)
from src.consts import PROXY
from src.utils import get_browser, logger, save_screenshot

router = APIRouter()


@router.get("/", include_in_schema=False)
def read_root():
    """Redirect to /docs."""
    logger.debug("Redirecting to /docs")
    return RedirectResponse(url="/docs", status_code=301)


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    # Simple health check without browser initialization
    # Just verify the service is running
    return HealthcheckResponse(user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


@router.post("/v1")
async def read_item(
    request: LinkRequest,
    proxy: Optional[str] = Header(
        default=PROXY,
        examples=["protocol://username:password@host:port"],
        description="Override default proxy address",
    )
) -> LinkResponse:
    """Handle POST requests."""
    start_time = int(time.time() * 1000)
    request.url = request.url.replace('"', "").strip()

    async with get_browser(proxy) as browser:
        return await _process_request(browser, request, start_time)


async def _process_request(browser: uc.Browser, request: LinkRequest, start_time: int) -> LinkResponse:
    """Process the actual request with the browser."""
    tab = await browser.get(request.url)
    logger.debug(f"Got webpage: {request.url}")

    # Get page content
    content = await tab.get_content()
    soup = BeautifulSoup(content, 'html.parser')
    title_tag = soup.title

    if title_tag and title_tag.string in CHALLENGE_TITLES:
        logger.debug("Challenge detected")
        # Use nodriver's built-in Cloudflare bypass
        await tab.cf_verify()
        logger.info("Cloudflare bypass completed")

        # Refresh content after bypass
        content = await tab.get_content()
        soup = BeautifulSoup(content, 'html.parser')

    # Check if challenge still exists
    current_title = await tab.title
    if current_title in CHALLENGE_TITLES:
        await save_screenshot(tab)
        raise HTTPException(status_code=500, detail="Could not bypass challenge")

    # Get cookies
    cookies = await tab.browser.cookies.get_all()
    formatted_cookies = []
    for cookie in cookies:
        # Handle cookie as either an object with attributes or a dict
        if hasattr(cookie, '__dict__'):
            # Object with attributes
            name = getattr(cookie, 'name', '')
            value = getattr(cookie, 'value', '')
            domain = getattr(cookie, 'domain', '')
            path = getattr(cookie, 'path', '/')
            secure = getattr(cookie, 'secure', False)
            http_only = getattr(cookie, 'httpOnly', False)
            same_site = getattr(cookie, 'sameSite', 'None')
            expires = getattr(cookie, 'expires', -1)
        else:
            # Dictionary
            name = cookie.get('name', '')
            value = cookie.get('value', '')
            domain = cookie.get('domain', '')
            path = cookie.get('path', '/')
            secure = cookie.get('secure', False)
            http_only = cookie.get('httpOnly', False)
            same_site = cookie.get('sameSite', 'None')
            expires = cookie.get('expires', -1)

        formatted_cookie = {
            "name": name,
            "value": value,
            "domain": domain,
            "path": path,
            "secure": secure,
            "httpOnly": http_only,
            "sameSite": same_site,
            "size": len(f"{name}={value}".encode()),
            "session": expires == -1,
        }

        if expires != -1:
            formatted_cookie["expires"] = expires

        formatted_cookies.append(formatted_cookie)

    # Get user agent
    user_agent = await tab.evaluate("navigator.userAgent")
    if isinstance(user_agent, tuple):
        user_agent = str(user_agent[0])

    return LinkResponse(
        message="Success",
        solution=Solution(
            user_agent=str(user_agent),
            url=str(tab.url),
            status=200,
            cookies=formatted_cookies,
            headers={},
            response=str(soup),
        ),
        start_timestamp=start_time,
    )
