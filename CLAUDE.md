# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Byparr is a drop-in replacement for FlareSolverr that bypasses Cloudflare and other anti-bot challenges. It acts as a proxy service using nodriver (undetected Chrome) to solve challenges and return cookies/content.

## Known Issues

- **macOS**: nodriver has a known issue on macOS where it clicks wrong coordinates when solving Cloudflare captchas. Testing should be done on Linux/Windows or in Docker.

## Commands

### Development
```bash
# Install dependencies
uv sync

# Run locally
uv run main.py

# Install with dev dependencies
uv sync --group dev

# Install with test dependencies
uv sync --group test
```

### Testing
```bash
# Run tests with retries
uv run pytest --retries 3

# Run tests in parallel
uv run pytest --retries 3 -n auto

# Test in Docker
docker build --target test .
```

### Docker
```bash
# Run container
docker run --shm-size=2gb -p 8191:8191 ghcr.io/thephaseless/byparr:latest

# Use docker compose
docker compose up
```

## Architecture

The application is a FastAPI service with the following key components:

- **main.py**: Application entry point that configures FastAPI and runs Uvicorn
- **src/endpoints.py**: Defines API routes - main logic is in the `/v1` endpoint that handles bypass requests (now async)
- **src/models.py**: Pydantic models for request/response validation (FlareSolverr compatible)
- **src/utils.py**: nodriver browser automation logic and configuration
- **src/consts.py**: Configuration constants loaded from environment variables

The `/v1` endpoint accepts POST requests with URLs to bypass, uses nodriver to navigate and solve challenges using `tab.cf_verify()`, then returns cookies and page content.

## Key Technical Details

- Uses nodriver's undetected Chrome mode to avoid bot detection
- Built-in Cloudflare bypass with `tab.cf_verify()` method
- Supports HTTP/HTTPS/SOCKS5 proxies (Note: SOCKS5 with authentication not supported at browser args level, would need context-level proxy config)
- Saves screenshots on failure to `/tmp/screenshots/` for debugging
- Environment variables: USE_HEADLESS, PROXY, LOG_LEVEL, VERSION
- FlareSolverr API compatibility for easy migration
- Requires `--shm-size=2gb` in Docker to prevent Chrome crashes
- All endpoints are now async for better performance