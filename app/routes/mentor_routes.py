from flask import Blueprint, jsonify, current_app, request, session

mentor_bp = Blueprint("mentor", __name__, url_prefix="/api/mentor")


@mentor_bp.route("/test", methods=["GET"]) 
def mentor_test():
    return jsonify(message="Hello from EduMind - Mentor"), 200


# List sessions for a given mentor_id
@mentor_bp.route("/sessions", methods=["GET"]) 
def list_mentor_sessions():
    from app.models.repositories import list_sessions_for_mentor
    app = current_app

    mentor_id = request.args.get("mentor_id")
    if not mentor_id:
        return jsonify(error="mentor_id query param is required"), 400

    sessions = list_sessions_for_mentor(app, mentor_id)
    return jsonify(sessions=sessions), 200


# ===== Mentor Profile & Interests/Teaching Areas (for dashboard) =====
@mentor_bp.route("/me/profile", methods=["GET"]) 
def get_my_mentor_profile():
    from app.models.repositories import get_mentor_profile
    app = current_app
    u = session.get("user") or {}
    mentor_id = u.get("user_id")
    if not mentor_id or u.get("role") != "mentor":
        return jsonify(error="Not authenticated as mentor"), 401
    prof = get_mentor_profile(app, mentor_id) or {}
    return jsonify(profile=prof, user={
        "user_id": mentor_id,
        "role": u.get("role"),
        "name": (u.get("profile") or {}).get("name"),
        "email": (u.get("profile") or {}).get("email"),
        "picture": (u.get("profile") or {}).get("picture"),
    }), 200


@mentor_bp.route("/me/interests", methods=["GET", "POST", "DELETE"]) 
def my_mentor_interests():
    from app.models.repositories import list_mentor_interests, update_mentor_interests
    app = current_app
    u = session.get("user") or {}
    mentor_id = u.get("user_id")
    if not mentor_id or u.get("role") != "mentor":
        return jsonify(error="Not authenticated as mentor"), 401

    if request.method == "GET":
        items = list_mentor_interests(app, mentor_id)
        return jsonify(interests=items), 200

    data = request.get_json(force=True) or {}
    if request.method == "POST":
        new_interest = (data.get("interest") or "").strip()
        if not new_interest:
            return jsonify(error="interest is required"), 400
        items = list_mentor_interests(app, mentor_id)
        if new_interest.lower() not in {i.lower() for i in items}:
            items.append(new_interest)
        res = update_mentor_interests(app, mentor_id, items)
        return jsonify(res), 200

    if request.method == "DELETE":
        target = (data.get("interest") or "").strip()
        if not target:
            return jsonify(error="interest is required"), 400
        items = list_mentor_interests(app, mentor_id)
        items = [i for i in items if i.lower() != target.lower()]
        res = update_mentor_interests(app, mentor_id, items)
        return jsonify(res), 200

    return jsonify(error="Unsupported method"), 405


@mentor_bp.route("/me/teaching-areas", methods=["GET", "POST", "DELETE"]) 
def my_mentor_teaching_areas():
    from app.models.repositories import list_mentor_teaching_areas, update_mentor_teaching_areas
    app = current_app
    u = session.get("user") or {}
    mentor_id = u.get("user_id")
    if not mentor_id or u.get("role") != "mentor":
        return jsonify(error="Not authenticated as mentor"), 401

    if request.method == "GET":
        items = list_mentor_teaching_areas(app, mentor_id)
        return jsonify(areas=items), 200

    data = request.get_json(force=True) or {}
    if request.method == "POST":
        new_area = (data.get("area") or "").strip()
        if not new_area:
            return jsonify(error="area is required"), 400
        items = list_mentor_teaching_areas(app, mentor_id)
        if new_area.lower() not in {i.lower() for i in items}:
            items.append(new_area)
        res = update_mentor_teaching_areas(app, mentor_id, items)
        return jsonify(res), 200

    if request.method == "DELETE":
        target = (data.get("area") or "").strip()
        if not target:
            return jsonify(error="area is required"), 400
        items = list_mentor_teaching_areas(app, mentor_id)
        items = [i for i in items if i.lower() != target.lower()]
        res = update_mentor_teaching_areas(app, mentor_id, items)
        return jsonify(res), 200

    return jsonify(error="Unsupported method"), 405


@mentor_bp.route("/me/career-background", methods=["GET", "POST", "DELETE"]) 
def my_mentor_career_background():
    from app.models.repositories import get_mentor_profile, update_mentor_career_background
    app = current_app
    u = session.get("user") or {}
    mentor_id = u.get("user_id")
    if not mentor_id or u.get("role") != "mentor":
        return jsonify(error="Not authenticated as mentor"), 401

    if request.method == "GET":
        prof = get_mentor_profile(app, mentor_id) or {}
        return jsonify(career_background=prof.get("career_background", "")), 200

    data = request.get_json(force=True) or {}
    if request.method == "POST":
        text = (data.get("career_background") or "").strip()
        res = update_mentor_career_background(app, mentor_id, text)
        return jsonify(res), 200

    if request.method == "DELETE":
        res = update_mentor_career_background(app, mentor_id, "")
        return jsonify(res), 200

    return jsonify(error="Unsupported method"), 405