# Hermes 
# Author: Indrajit Ghosh
# Created On: Sep 20, 2025

from flask import Flask
from app.extensions import db, migrate

def create_app(config_class="config.Config"):
    app = Flask(__name__)
    app.config.from_object(config_class)

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
