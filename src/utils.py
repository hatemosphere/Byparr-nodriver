import logging
import os
from time import gmtime, strftime
import asyncio
from contextlib import asynccontextmanager

from fastapi import Header, HTTPException
from httpx import codes
import nodriver as nd

from src.consts import LOG_LEVEL, PROXY, USE_HEADLESS

logger = logging.getLogger("uvicorn.error")
logger.setLevel(LOG_LEVEL)
if len(logger.handlers) == 0:
    logger.addHandler(logging.StreamHandler())

# Enable debug logging for nodriver when in DEBUG mode
if LOG_LEVEL == logging.DEBUG:
    # Configure root logger to show debug messages
    logging.basicConfig(level=logging.DEBUG)

    # Enable nodriver logging
    nodriver_logger = logging.getLogger("nodriver")
    nodriver_logger.setLevel(logging.DEBUG)

    # Add handler if not already present
    if not nodriver_logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        nodriver_logger.addHandler(handler)

    # Also enable for submodules
    for submodule in ["nodriver.core", "nodriver.core.browser", "nodriver.cdp"]:
        sub_logger = logging.getLogger(submodule)
        sub_logger.setLevel(logging.DEBUG)


@asynccontextmanager
async def get_browser_instance(proxy: str | None = None):
    """Get nodriver browser instance - internal function."""
    logger.debug(
        f"Starting browser instance with proxy={proxy}, headless={USE_HEADLESS}"
    )

    if proxy and proxy.startswith("socks5://") and "@" in proxy:
        raise HTTPException(
            status_code=codes.BAD_REQUEST,
            detail="SOCKS5 proxy with authentication is not supported. Check README for more info.",
        )

    # Start browser with proper configuration
    browser_args = []
    if proxy:
        browser_args.append(f"--proxy-server={proxy}")

    logger.debug(f"Browser args: {browser_args}")
    logger.debug(f"Environment - DISPLAY={os.environ.get('DISPLAY')}")
    logger.debug(f"Running as user: {os.getuid() if hasattr(os, 'getuid') else 'N/A'}")

    try:
        browser = await nd.start(
            headless=USE_HEADLESS,
            lang="en-US",
            sandbox=False,  # Disable sandbox when running as root in Docker
            browser_args=browser_args if browser_args else None,
        )
        logger.debug("Browser started successfully")
    except Exception as e:
        logger.error(f"Failed to start browser: {e}", exc_info=True)
        raise

    try:
        yield browser
    finally:
        logger.debug("Stopping browser")
        browser.stop()


def get_browser(
    proxy: str | None = Header(
        default=PROXY,
        examples=["protocol://username:password@host:port"],
        description="Override default proxy address",
    ),
):
    """Get browser instance as FastAPI dependency."""
    return proxy


async def save_screenshot(tab):
    """Save screenshot on HTTPException."""
    await tab.save_screenshot(
        f"screenshots/{strftime('%Y-%m-%d %H:%M:%S', gmtime())}.png"
    )
