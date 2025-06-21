# my-repo/app.py (Updated Entry Point)

import uvicorn
import os
from src.backend import create_app, logger # Import logger from the __init__ for consistency

app = create_app()

if __name__ == '__main__':
    config = app.state.config
    host = config.HOST
    port = config.PORT
    debug = config.DEBUG
    
    logger.info(f"Starting FastAPI application on host={host}, port={port}, debug={debug}")
    uvicorn.run(
        "app:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info"
    )