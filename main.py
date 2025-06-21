import os
import logging
from src.backend import create_app, logger

app = create_app()

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", app.config.PORT))
    debug = app.config.DEBUG
    logger.info(
        f"Starting FastAPI application on host=0.0.0.0, port={port}, debug={debug}")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        log_level="debug" if debug else "info",
        reload=debug  # Enable auto-reload in debug mode
    )
