import logging
from contextlib import asynccontextmanager
from time import gmtime, strftime
from typing import Optional

import nodriver as uc
from fastapi import HTTPException
from httpx import codes

from src.consts import LOG_LEVEL, PROXY, USE_HEADLESS, USE_XVFB

logger = logging.getLogger("uvicorn.error")
logger.setLevel(LOG_LEVEL)
if len(logger.handlers) == 0:
    logger.addHandler(logging.StreamHandler())

# Configure nodriver logging
nodriver_logger = logging.getLogger("nodriver")
nodriver_logger.setLevel(LOG_LEVEL)
if len(nodriver_logger.handlers) == 0:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    nodriver_logger.addHandler(handler)

# Root logger is now configured in main.py


@asynccontextmanager
async def get_browser(proxy: Optional[str] = None):
    """Get nodriver browser instance."""
    # Use default proxy if not provided
    if proxy is None:
        proxy = PROXY

    if proxy and proxy.startswith("socks5://") and "@" in proxy:
        raise HTTPException(
            status_code=codes.BAD_REQUEST,
            detail="SOCKS5 proxy with authentication is not supported. Check README for more info.",
        )

    # Build browser args only if needed
    browser_args = None

    # Add proxy if provided
    if proxy:
        browser_args = [f"--proxy-server={proxy}"]

    logger.debug(f"Starting browser with headless={USE_HEADLESS} (GUI {'disabled' if USE_HEADLESS else 'enabled'}), xvfb={USE_XVFB}, proxy={proxy}")
    browser = await uc.start(
        headless=USE_HEADLESS,
        lang="en-US",
        sandbox=False,  # Required when running as root (Docker)
        browser_args=browser_args,
    )
    logger.debug("Browser started successfully")

    try:
        yield browser
    finally:
        logger.debug("Stopping browser")
        browser.stop()


async def save_screenshot(tab):
    """Save screenshot on HTTPException."""
    try:
        screenshot_path = f"/tmp/screenshots/{strftime('%Y-%m-%d %H:%M:%S', gmtime())}.png"
        await tab.save_screenshot(screenshot_path)
        logger.info(f"Screenshot saved to {screenshot_path}")
    except Exception as e:
        logger.error(f"Failed to save screenshot: {e}")
