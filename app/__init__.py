# Hermes 
# Author: Indrajit Ghosh
# Created On: Sep 20, 2025

import logging
from flask import Flask

from app.extensions import db, migrate
from config import LOG_FILE

def configure_logging(app:Flask):
    # --- Main application logger ---
    logging.basicConfig(
        format='[%(asctime)s] %(levelname)s %(name)s: %(message)s',
        filename=str(LOG_FILE),
        datefmt='%d-%b-%Y %I:%M:%S %p'
    )

    if app.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        
        # Fix werkzeug handler in debug mode
        logging.getLogger('werkzeug').handlers = []

def create_app(config_class="config.Config"):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Configure logging
    configure_logging(app)

    db.init_app(app)
    migrate.init_app(app, db)

    # register blueprints
    from app.home.home import home_bp
    app.register_blueprint(home_bp)
    
    from app.api.admin_api import admin_bp
    app.register_blueprint(admin_bp)

    from app.api.email_api import email_bp
    app.register_blueprint(email_bp)

    from app.api.user_api import user_bp
    app.register_blueprint(user_bp)

    return app
