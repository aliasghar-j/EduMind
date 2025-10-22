import os
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv


def create_app(config_name: str | None = None) -> Flask:
    """Application factory for EduMind.

    - Loads environment variables from .env
    - Applies environment-based configuration
    - Initializes CORS
    - Registers Blueprints for modular routing
    - Sets up placeholders for Google OAuth and Google Sheets client
    """
    load_dotenv()

    from config import get_config

    env = (config_name or os.getenv("FLASK_ENV") or os.getenv("APP_ENV") or "development").lower()
    config_class = get_config(env)

    app = Flask(__name__)
    app.config.from_object(config_class)

    # Enable CORS for API communication (adjust origins later as needed)
    CORS(app)

    # Register blueprints
    from app.routes.student_routes import student_bp
    from app.routes.mentor_routes import mentor_bp
    from app.routes.auth_routes import auth_bp
    from app.routes.ui_routes import ui_bp

    app.register_blueprint(student_bp)
    app.register_blueprint(mentor_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(ui_bp)

    # Placeholder: Initialize Google OAuth (no logic yet)
    try:
        from app.utils.oauth import init_google_oauth
        init_google_oauth(app)
    except Exception:
        pass

    # Placeholder: Initialize Google Sheets client (no logic yet)
    try:
        from app.utils.sheets import init_sheets_client
        init_sheets_client(app)
    except Exception:
        pass

    return app