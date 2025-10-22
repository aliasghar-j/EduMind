import os
from dotenv import load_dotenv
from app import create_app


if __name__ == "__main__":
    load_dotenv()

    env = os.getenv("FLASK_ENV") or os.getenv("APP_ENV") or "development"
    app = create_app(env)

    port = int(os.getenv("PORT", 5000))
    host = os.getenv("HOST", "0.0.0.0")

    app.run(host=host, port=port, debug=app.config.get("DEBUG", False))