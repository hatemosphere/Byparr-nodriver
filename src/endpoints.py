import asyncio
import time
from http import HTTPStatus
from typing import Annotated

from bs4 import BeautifulSoup
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse

from src.consts import CHALLENGE_TITLES
from src.models import (
    HealthcheckResponse,
    LinkRequest,
    LinkResponse,
    Solution,
)
from src.utils import get_browser, get_browser_instance, logger, save_screenshot

router = APIRouter()

ProxyDep = Annotated[str | None, Depends(get_browser)]


@router.get("/", include_in_schema=False)
def read_root():
    """Redirect to /docs."""
    logger.debug("Redirecting to /docs")
    return RedirectResponse(url="/docs", status_code=301)


@router.get("/health")
async def health_check(proxy: ProxyDep):
    """Health check endpoint."""
    health_check_request = await read_item(
        LinkRequest.model_construct(url="https://google.com"),
        proxy,
    )

    if health_check_request.solution.status != HTTPStatus.OK:
        raise HTTPException(
            status_code=500,
            detail="Health check failed",
        )

    return HealthcheckResponse(user_agent=health_check_request.solution.user_agent)


@router.post("/v1")
async def read_item(request: LinkRequest, proxy: ProxyDep) -> LinkResponse:
    """Handle POST requests."""
    start_time = int(time.time() * 1000)
    request.url = request.url.replace('"', "").strip()
    logger.debug(f"Request started at {start_time}")

    async with get_browser_instance(proxy) as browser:
        tab = await browser.get(request.url)
        logger.debug(f"Got webpage: {request.url}")

        # Get page content
        try:
            content = await tab.get_content()
        except Exception as e:
            logger.error(f"Failed to get initial page content: {e}")
            return LinkResponse(
                status="error",
                message=f"Failed to get page content: {e!s}",
                solution=Solution(
                    url=request.url,
                    status=500,
                    cookies=[],
                    user_agent="",
                    response="",
                ),
                start_timestamp=start_time,
            )
        soup = BeautifulSoup(content, "html.parser")
        title_tag = soup.title

        logger.debug(f"Page title: '{title_tag.string if title_tag else 'No title'}'")
        logger.debug(f"Checking against challenge titles: {CHALLENGE_TITLES}")

        if (
            title_tag
            and title_tag.string
            and any(
                challenge_title in title_tag.string.strip()
                for challenge_title in CHALLENGE_TITLES
            )
        ):
            logger.debug(f"Challenge detected: '{title_tag.string}'")
            # Wait a bit before starting to solve the challenge
            logger.debug("Sleeping 3 seconds before attempting bypass...")
            await asyncio.sleep(3)

            try:
                # Try to use nodriver's verify_cf for Cloudflare bypass
                logger.debug("Attempting verify_cf...")
                await tab.verify_cf()
                logger.info("Cloudflare challenge bypassed using verify_cf")
            except Exception as e:
                logger.warning(f"verify_cf failed: {e}")

            # Smart wait for page to load after solving
            logger.debug("Waiting for page to load after challenge...")
            max_wait = 10  # Maximum 10 seconds
            check_interval = 1  # Check every second
            waited = 0

            # Store the challenge title to detect when it changes
            challenge_title = title_tag.string.strip()

            while waited < max_wait:
                await asyncio.sleep(check_interval)
                waited += check_interval

                try:
                    # Get current page state
                    current_content = await tab.get_content()
                    current_soup = BeautifulSoup(current_content, "html.parser")
                    current_title = (
                        current_soup.title.string if current_soup.title else ""
                    )
                    current_url = str(tab.url)
                except Exception as e:
                    logger.debug(f"Failed to get page content: {e}. Retrying...")
                    continue

                # Check if title changed from challenge page
                if current_title != challenge_title and not any(
                    challenge in current_title for challenge in CHALLENGE_TITLES
                ):
                    logger.debug(
                        f"Title changed from '{challenge_title}' to '{current_title}'"
                    )
                    logger.debug(f"URL: {current_url}")

                    # Wait for the page to stabilize
                    await tab.wait()
                    logger.info(f"Page loaded after {waited}s")
                    break

                logger.debug(f"Still waiting... ({waited}s) - Title: '{current_title}'")

        # Re-check title after bypass attempt
        try:
            content = await tab.get_content()
            soup = BeautifulSoup(content, "html.parser")
            current_title = soup.title.string if soup.title else ""
        except Exception as e:
            logger.warning(f"Failed to get final page content: {e}")
            # Use the last known good content if available
            current_title = ""

        logger.debug(f"Title after bypass attempt: '{current_title}'")

        if any(
            challenge_title in current_title for challenge_title in CHALLENGE_TITLES
        ):
            elapsed_time = int(time.time() * 1000) - start_time
            logger.error(f"Failed to bypass challenge after {elapsed_time}ms")
            await save_screenshot(tab)
            raise HTTPException(status_code=500, detail="Could not bypass challenge")

        # Get cookies
        cookies = await tab.browser.cookies.get_all()
        formatted_cookies = []

        for cookie in cookies:
            formatted_cookie = {
                "name": cookie.name,
                "value": cookie.value,
                "domain": cookie.domain,
                "path": cookie.path,
                "httpOnly": cookie.http_only,
                "secure": cookie.secure,
                "sameSite": cookie.same_site.value if cookie.same_site else "None",
                "size": cookie.size,
                "session": cookie.session,
            }

            if cookie.expires is not None:
                formatted_cookie["expires"] = cookie.expires

            formatted_cookies.append(formatted_cookie)

        # Get user agent
        user_agent_result = await tab.evaluate("navigator.userAgent")
        # Extract string from the result tuple
        user_agent = (
            str(user_agent_result[0])
            if isinstance(user_agent_result, tuple)
            else str(user_agent_result)
        )

        elapsed_time = int(time.time() * 1000) - start_time
        logger.debug(f"Request completed in {elapsed_time}ms")

        return LinkResponse(
            message="Success",
            solution=Solution(
                user_agent=user_agent,
                url=str(tab.url),
                status=200,
                cookies=formatted_cookies,
                headers={},
                response=str(soup),
            ),
            start_timestamp=start_time,
        )
