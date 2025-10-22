import os
from flask import current_app
from google_auth_oauthlib.flow import Flow

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/calendar.readonly",
]


def init_google_oauth(app):
    """
    Initialize Google OAuth config values from environment.
    Stores client credentials in app.config for use by the auth blueprint.
    """
    app.config["GOOGLE_CLIENT_ID"] = os.getenv("GOOGLE_CLIENT_ID", "")
    app.config["GOOGLE_CLIENT_SECRET"] = os.getenv("GOOGLE_CLIENT_SECRET", "")
    # Default redirect URI; can be overridden by environment.
    app.config.setdefault(
        "GOOGLE_OAUTH_REDIRECT_URI",
        os.getenv("GOOGLE_OAUTH_REDIRECT_URI", "http://127.0.0.1:5000/api/auth/google/callback"),
    )


def build_google_flow(redirect_uri: str | None = None) -> Flow:
    """
    Construct a Google OAuth Flow using client config from app.config.
    """
    client_id = current_app.config.get("GOOGLE_CLIENT_ID", "")
    client_secret = current_app.config.get("GOOGLE_CLIENT_SECRET", "")

    client_config = {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }

    redirect = redirect_uri or current_app.config.get("GOOGLE_OAUTH_REDIRECT_URI")

    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=redirect,
    )
    return flow