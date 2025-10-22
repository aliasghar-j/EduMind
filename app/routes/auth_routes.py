from flask import Blueprint, jsonify, request, redirect, session, current_app
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from app.utils.oauth import build_google_flow

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.route("/test", methods=["GET"]) 
def auth_test():
    return jsonify(message="Hello from EduMind - Auth"), 200


@auth_bp.route("/google/start", methods=["GET"]) 
def google_start():
    role = request.args.get("role", default="student")

    flow = build_google_flow()
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="false",
        prompt="consent",
    )

    session["oauth_state"] = state
    session["login_role"] = role

    return redirect(authorization_url)


@auth_bp.route("/google/callback", methods=["GET"]) 
def google_callback():
    state = session.get("oauth_state")
    flow = build_google_flow()
    # Reconstruct flow state is handled internally by google-auth-oauthlib
    flow.fetch_token(authorization_response=request.url)

    creds = flow.credentials

    # Verify ID token and extract user info
    request_adapter = google_requests.Request()
    userinfo = None
    try:
        if creds.id_token:
            info = id_token.verify_oauth2_token(creds.id_token, request_adapter, current_app.config.get("GOOGLE_CLIENT_ID"))
            userinfo = {
                "google_id": info.get("sub"),
                "email": info.get("email"),
                "name": info.get("name"),
                "picture": info.get("picture"),
            }
    except Exception:
        pass

    # Resolve role from stored user record if present; otherwise create new user with selected role
    app = current_app
    email = userinfo.get("email") if userinfo else None
    resolved_role = session.get("login_role", "student")
    user_id = None
    if email:
        from app.models.repositories import get_user_by_email, create_user, update_user_profile_by_email
        existing = get_user_by_email(app, email)
        if existing:
            resolved_role = existing.get("role", resolved_role)
            user_id = existing.get("user_id")
            # Update dynamic fields from Google profile for ongoing sync
            try:
                update_user_profile_by_email(
                    app,
                    email=email,
                    name=userinfo.get("name", None),
                    role=resolved_role,
                    google_id=(userinfo or {}).get("google_id", None),
                    profile_picture_url=(userinfo or {}).get("picture", None),
                )
            except Exception:
                pass
        else:
            created = create_user(
                app,
                name=userinfo.get("name", ""),
                email=email,
                role=resolved_role,
                google_id=(userinfo or {}).get("google_id", None),
                profile_picture_url=(userinfo or {}).get("picture", None),
            )
            user_id = created.get("user_id")

    session["user"] = {
        "role": resolved_role,
        "user_id": user_id,
        "tokens": {
            "access_token": creds.token,
            "refresh_token": getattr(creds, "refresh_token", None),
            "id_token": getattr(creds, "id_token", None),
            "expires_at": getattr(creds, "expiry", None).isoformat() if getattr(creds, "expiry", None) else None,
        },
        "profile": userinfo,
    }

    # Ensure corresponding profile rows exist in Sheets for dynamic sync
    try:
        from app.models.repositories import upsert_mentor_profile, upsert_student_profile, set_config_value
        from app.utils.sheets import init_sheets_client
        from datetime import datetime, timezone
        # If Sheets is not initialized, init now
        app.extensions = getattr(app, "extensions", {})
        if not app.extensions.get("sheets_service"):
            try:
                init_sheets_client(app)
            except Exception:
                pass
        if user_id and resolved_role == "mentor":
            upsert_mentor_profile(app, mentor_id=user_id)
        if user_id and resolved_role == "student":
            upsert_student_profile(app, student_id=user_id)
        # Update last sync timestamp
        ts = datetime.now(timezone.utc).isoformat()
        set_config_value(app, "last_sync_timestamp", ts)
    except Exception:
        pass

    # Redirect based on selected login page (student vs mentor)
    selected_role = session.get("login_role", "student")
    if selected_role == "mentor":
        return redirect("/ui/mentor-dashboard")
    return redirect("/ui/student-dashboard")


@auth_bp.route("/me", methods=["GET"]) 
def auth_me():
    """Return current session user info for frontend consumption."""
    u = session.get("user") or {}
    profile = u.get("profile") or {}
    return jsonify({
        "role": u.get("role"),
        "user_id": u.get("user_id"),
        "name": profile.get("name"),
        "email": profile.get("email"),
        "picture": profile.get("picture"),
    }), 200

@auth_bp.route("/sync", methods=["POST"]) 
def auth_sync():
    """Upsert current session user profile rows in Sheets.
    Creates Mentors/Students entries keyed by user_id. Returns sync result.
    """
    u = session.get("user") or {}
    role = u.get("role")
    user_id = u.get("user_id")
    app = current_app
    if not user_id or not role:
        return jsonify({"ok": False, "error": "no_session"}), 400
    # Ensure Sheets client is initialized
    try:
        from app.utils.sheets import init_sheets_client
        app.extensions = getattr(app, "extensions", {})
        if not app.extensions.get("sheets_service"):
            init_sheets_client(app)
    except Exception as e:
        return jsonify({"ok": False, "error": f"sheets_init_failed: {e}"}), 500
    # Upsert
    try:
        from app.models.repositories import upsert_mentor_profile, upsert_student_profile, set_config_value
        if role == "mentor":
            upsert_mentor_profile(app, mentor_id=user_id)
        elif role == "student":
            upsert_student_profile(app, student_id=user_id)
        from datetime import datetime, timezone
        set_config_value(app, "last_sync_timestamp", datetime.now(timezone.utc).isoformat())
        return jsonify({"ok": True, "role": role, "user_id": user_id}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": f"sync_failed: {e}"}), 500

@auth_bp.route("/logout", methods=["POST"]) 
def auth_logout():
    """Clear the current session and log the user out."""
    session.clear()
    return jsonify({"message": "logged out"}), 200