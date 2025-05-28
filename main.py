from __future__ import annotations

import logging

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware

from src.consts import LOG_LEVEL, VERSION
from src.endpoints import router
from src.middlewares import LogRequest
from src.utils import logger

logger.info("Using version %s", VERSION)
logger.info("Log level set to: %s", logging.getLevelName(LOG_LEVEL))

app = FastAPI(debug=LOG_LEVEL == logging.DEBUG, log_level=LOG_LEVEL)
app.add_middleware(GZipMiddleware)
app.add_middleware(LogRequest)

app.include_router(router=router)


if __name__ == "__main__":
    log_level_str = logging.getLevelName(LOG_LEVEL).lower()
    
    # Configure uvicorn logging
    import sys
    logging.basicConfig(
        level=LOG_LEVEL,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout,
        force=True
    )
    
    uvicorn.run(app, host="0.0.0.0", port=8191, log_level=log_level_str)  # noqa: S104
