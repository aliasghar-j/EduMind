import os
from flask import Blueprint, current_app, send_from_directory, abort, Response

ui_bp = Blueprint("ui", __name__, url_prefix="/ui")


def _pages_base_dir() -> str:
    """Compute absolute path to the frontend pages directory.

    Uses the Flask application's root_path (points to the `app/` directory),
    then navigates up one level to the project root and into `frontend/pages`.
    """
    return os.path.abspath(os.path.join(current_app.root_path, "..", "frontend", "pages"))


def _serve_index_from(folder_name: str):
    base_dir = _pages_base_dir()
    target_dir = os.path.join(base_dir, folder_name)
    index_path = os.path.join(target_dir, "index.html")

    if not os.path.isfile(index_path):
        abort(404)

    return send_from_directory(directory=target_dir, path="index.html")


@ui_bp.route("/landing", methods=["GET"]) 
def landing_page():
    return _serve_index_from("edumind_landing_page")


@ui_bp.route("/mentor-login", methods=["GET"]) 
def mentor_login_page():
    return _serve_index_from("mentor_login_page")


@ui_bp.route("/mentor-dashboard", methods=["GET"]) 
def mentor_dashboard_page():
    return _serve_index_from("mentor_dashboard")


@ui_bp.route("/mentor-details", methods=["GET"]) 
def mentor_details_page():
    return _serve_index_from("mentor_details_page")


@ui_bp.route("/student-login", methods=["GET"]) 
def student_login_page():
    return _serve_index_from("student_login_page")


@ui_bp.route("/student-dashboard", methods=["GET"]) 
def student_dashboard_page():
    return _serve_index_from("student_dashboard")

# Serve additional files within the student dashboard folder (e.g., calendar.js, images)
@ui_bp.route("/student-dashboard/<path:filename>", methods=["GET"]) 
def student_dashboard_assets(filename: str):
    base_dir = _pages_base_dir()
    target_dir = os.path.join(base_dir, "student_dashboard")
    asset_path = os.path.join(target_dir, filename)
    if not os.path.isfile(asset_path):
        abort(404)
    return send_from_directory(directory=target_dir, path=filename)


# Dev-only script placeholder to avoid 404 when static pages reference Vite client
@ui_bp.route("/@vite/client", methods=["GET"]) 
def vite_client_placeholder():
    return Response("// Vite client placeholder for static serving", mimetype="application/javascript"), 200