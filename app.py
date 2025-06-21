# my-repo/app.py (Updated Entry Point)

import os
from src.backend import create_app, logger # Import logger from the __init__ for consistency

app = create_app()

if __name__ == '__main__':
    # Development server configuration
    port = app.config['PORT']
    debug = app.config['DEBUG']
    
    logger.info(f"Starting Flask application on host=0.0.0.0, port={port}, debug={debug}")
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )