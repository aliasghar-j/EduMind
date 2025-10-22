from flask import Blueprint, jsonify, current_app, request, session

student_bp = Blueprint("student", __name__, url_prefix="/api/student")


@student_bp.route("/test", methods=["GET"])
def student_test():
    return jsonify(message="Hello from EduMind - Student"), 200


# Seed demo data: creates a demo student, mentor, profiles, and a session
@student_bp.route("/seed-demo", methods=["POST"]) 
def seed_demo():
    from app.models.repositories import (
        create_user, upsert_student_profile, upsert_mentor_profile, schedule_session,
    )
    app = current_app

    # Create demo student and mentor users
    student = create_user(app, name="Demo Student", email="student.demo@example.com", role="student")
    mentor = create_user(app, name="Demo Mentor", email="mentor.demo@example.com", role="mentor")

    # Upsert their profiles
    upsert_student_profile(
        app,
        student_id=student["user_id"],
        interests="data science; ai ethics",
        career_choices="ML engineer; research",
        syllabus_links="https://syllabus.edu/cs101|https://syllabus.edu/ml201",
        uploaded_materials="",
        mentor_match_ids=mentor["user_id"],
        google_calendar_sync_id="",
        notes="seed demo",
    )

    upsert_mentor_profile(
        app,
        mentor_id=mentor["user_id"],
        general_interests="machine learning; career coaching",
        career_background="industry",
        available_slots="2025-10-30T18:00Z",
        specialization_tags="ml,career",
        notes="seed demo",
    )

    # Schedule a session between them
    session_row = schedule_session(
        app,
        mentor_id=mentor["user_id"],
        student_id=student["user_id"],
        date="2025-10-30",
        time="18:00",
        topic="Career guidance",
    )

    return jsonify({
        "student_id": student["user_id"],
        "mentor_id": mentor["user_id"],
        "session_id": session_row["session_id"],
        "message": "Seed demo data created",
    }), 201


# List sessions for a given student_id
@student_bp.route("/sessions", methods=["GET"]) 
def list_student_sessions():
    from app.models.repositories import list_sessions_for_student
    app = current_app

    student_id = request.args.get("student_id")
    if not student_id:
        return jsonify(error="student_id query param is required"), 400

    sessions = list_sessions_for_student(app, student_id)
    return jsonify(sessions=sessions), 200


# Materials: create and list
@student_bp.route("/materials", methods=["POST"]) 
def create_material():
    from app.models.repositories import add_study_material
    app = current_app
    data = request.get_json(force=True) or {}
    required = ["student_id", "file_name", "file_link"]
    missing = [k for k in required if not data.get(k)]
    if missing:
        return jsonify(error=f"Missing fields: {', '.join(missing)}"), 400
    res = add_study_material(
        app,
        student_id=data["student_id"],
        file_name=data["file_name"],
        file_link=data["file_link"],
        summary=data.get("summary", ""),
        related_quiz_ids=data.get("related_quiz_ids", ""),
    )
    return jsonify(res), 201


@student_bp.route("/materials", methods=["GET"]) 
def list_materials():
    from app.models.repositories import list_study_materials_for_student
    app = current_app
    student_id = request.args.get("student_id")
    if not student_id:
        return jsonify(error="student_id query param is required"), 400
    items = list_study_materials_for_student(app, student_id)
    return jsonify(materials=items), 200


# Quizzes: create and list
# Quiz route removed: /quizzes (POST) 
def create_quiz_endpoint():
    from app.models.repositories import create_quiz
    app = current_app
    data = request.get_json(force=True) or {}
    required = ["subject", "difficulty_level", "question_text", "options", "correct_answer", "related_material_id", "created_by"]
    missing = [k for k in required if not data.get(k)]
    if missing:
        return jsonify(error=f"Missing fields: {', '.join(missing)}"), 400
    if not isinstance(data.get("options"), list):
        return jsonify(error="options must be a list of strings"), 400
    res = create_quiz(
        app,
        subject=data["subject"],
        difficulty_level=data["difficulty_level"],
        question_text=data["question_text"],
        options=data["options"],
        correct_answer=data["correct_answer"],
        related_material_id=data["related_material_id"],
        created_by=data["created_by"],
    )
    return jsonify(res), 201


# Quiz route removed: /quizzes (GET) 
def list_quizzes_endpoint():
    from app.models.repositories import list_quizzes_for_material, list_quizzes_for_student
    app = current_app
    material_id = request.args.get("material_id")
    student_id = request.args.get("student_id")
    if material_id:
        items = list_quizzes_for_material(app, material_id)
    elif student_id:
        items = list_quizzes_for_student(app, student_id)
    else:
        return jsonify(error="material_id or student_id query param is required"), 400
    return jsonify(quizzes=items), 200


# Quiz route removed: /quiz/generate
def generate_quiz_endpoint():
    from app.utils.gemini_service import generate_quiz_questions

    data = request.get_json(force=True) or {}
    subject = data.get("subject")
    if not subject:
        return jsonify(error="Subject is required"), 400

    try:
        questions = generate_quiz_questions(subject)
        return jsonify(questions=questions), 200
    except Exception as e:
        current_app.logger.error(f"Quiz generation failed: {e}")
        return jsonify(error="Quiz generation failed"), 500


# Quiz Scores: record and list
# Quiz route removed: /quiz-scores (POST) 
def record_quiz_score_endpoint():
    from app.models.repositories import record_quiz_score
    app = current_app
    data = request.get_json(force=True) or {}
    required = ["student_id", "quiz_id", "score", "total_marks"]
    missing = [k for k in required if data.get(k) is None]
    if missing:
        return jsonify(error=f"Missing fields: {', '.join(missing)}"), 400
    try:
        score = float(data["score"])
        total = float(data["total_marks"])
    except Exception:
        return jsonify(error="score and total_marks must be numeric"), 400
    res = record_quiz_score(
        app,
        student_id=data["student_id"],
        quiz_id=data["quiz_id"],
        score=score,
        total_marks=total,
        grader=data.get("grader", ""),
        notes=data.get("notes", ""),
    )
    return jsonify(res), 201


# Quiz route removed: /quiz-scores (GET) 
def list_quiz_scores_endpoint():
    from app.models.repositories import list_quiz_scores_for_student
    app = current_app
    student_id = request.args.get("student_id")
    if not student_id:
        return jsonify(error="student_id query param is required"), 400
    items = list_quiz_scores_for_student(app, student_id)
    return jsonify(scores=items), 200


# ===== Student Profile & Interests (for dashboard) =====
@student_bp.route("/me/profile", methods=["GET"]) 
def get_my_profile():
    from app.models.repositories import get_student_profile
    app = current_app
    u = session.get("user") or {}
    student_id = u.get("user_id")
    if not student_id:
        return jsonify(error="Not authenticated"), 401
    prof = get_student_profile(app, student_id) or {}
    # Augment with basic identity fields
    return jsonify(profile=prof, user={
        "user_id": student_id,
        "role": u.get("role"),
        "name": (u.get("profile") or {}).get("name"),
        "email": (u.get("profile") or {}).get("email"),
        "picture": (u.get("profile") or {}).get("picture"),
    }), 200


@student_bp.route("/me/interests", methods=["GET", "POST", "DELETE"]) 
def my_interests():
    from app.models.repositories import list_student_interests, update_student_interests
    app = current_app
    u = session.get("user") or {}
    student_id = u.get("user_id")
    if not student_id:
        return jsonify(error="Not authenticated"), 401

    if request.method == "GET":
        items = list_student_interests(app, student_id)
        return jsonify(interests=items), 200

    data = request.get_json(force=True) or {}
    if request.method == "POST":
        new_interest = (data.get("interest") or "").strip()
        if not new_interest:
            return jsonify(error="interest is required"), 400
        items = list_student_interests(app, student_id)
        if new_interest.lower() not in {i.lower() for i in items}:
            items.append(new_interest)
        res = update_student_interests(app, student_id, items)
        return jsonify(res), 200

    if request.method == "DELETE":
        target = (data.get("interest") or "").strip()
        if not target:
            return jsonify(error="interest is required"), 400
        items = list_student_interests(app, student_id)
        items = [i for i in items if i.lower() != target.lower()]
        res = update_student_interests(app, student_id, items)
        return jsonify(res), 200

    return jsonify(error="Unsupported method"), 405


# ===== Google Calendar Integration =====
@student_bp.route("/me/calendar/events", methods=["GET"])
def get_my_calendar_events():
    """Fetch upcoming events from user's Google Calendar."""
    from app.utils.calendar_service import GoogleCalendarService, create_credentials_from_session
    
    u = session.get("user") or {}
    student_id = u.get("user_id")
    if not student_id:
        return jsonify(error="Not authenticated"), 401
    
    # Check if user has Google OAuth tokens
    tokens = u.get("tokens")
    if not tokens or not tokens.get("access_token"):
        return jsonify(error="Google Calendar access not available. Please sign in with Google."), 403
    
    # Create credentials from session tokens
    credentials = create_credentials_from_session(tokens)
    if not credentials:
        return jsonify(error="Invalid Google credentials. Please re-authenticate."), 403
    
    # Initialize calendar service
    calendar_service = GoogleCalendarService()
    if not calendar_service.build_service(credentials):
        return jsonify(error="Failed to connect to Google Calendar."), 500
    
    # Get query parameters
    max_results = request.args.get("max_results", 10, type=int)
    days_ahead = request.args.get("days_ahead", 30, type=int)
    
    # Fetch events
    events = calendar_service.get_upcoming_events(max_results=max_results, days_ahead=days_ahead)
    
    return jsonify(events=events), 200


@student_bp.route("/me/calendar/status", methods=["GET"])
def get_calendar_status():
    """Check if user has Google Calendar access."""
    u = session.get("user") or {}
    student_id = u.get("user_id")
    if not student_id:
        return jsonify(error="Not authenticated"), 401
    
    # Check if user has Google OAuth tokens
    tokens = u.get("tokens")
    has_google_access = bool(tokens and tokens.get("access_token"))
    
    profile = u.get("profile") or {}
    
    return jsonify({
        "has_google_access": has_google_access,
        "user_email": profile.get("email"),
        "auth_method": "google" if has_google_access else "traditional"
    }), 200


@student_bp.route("/me/calendar/calendars", methods=["GET"])
def get_my_calendars():
    """Get list of user's Google Calendars."""
    from app.utils.calendar_service import GoogleCalendarService, create_credentials_from_session
    
    u = session.get("user") or {}
    student_id = u.get("user_id")
    if not student_id:
        return jsonify(error="Not authenticated"), 401
    
    # Check if user has Google OAuth tokens
    tokens = u.get("tokens")
    if not tokens or not tokens.get("access_token"):
        return jsonify(error="Google Calendar access not available. Please sign in with Google."), 403
    
    # Create credentials from session tokens
    credentials = create_credentials_from_session(tokens)
    if not credentials:
        return jsonify(error="Invalid Google credentials. Please re-authenticate."), 403
    
    # Initialize calendar service
    calendar_service = GoogleCalendarService()
    if not calendar_service.build_service(credentials):
        return jsonify(error="Failed to connect to Google Calendar."), 500
    
    # Fetch calendars
    calendars = calendar_service.get_calendar_list()
    
    return jsonify(calendars=calendars), 200


# Quiz route removed: /quiz/evaluate
def evaluate_quiz_answers():
    from app.utils.gemini_service import evaluate_mcq_answers
    app = current_app
    u = session.get("user") or {}
    student_id = u.get("user_id")
    if not student_id:
        return jsonify(error="Not authenticated"), 401

    data = request.get_json(force=True) or {}
    subject = (data.get("subject") or "").strip()
    questions = data.get("questions") or []
    answers = data.get("answers") or []

    if not subject:
        return jsonify(error="subject is required"), 400
    if not isinstance(questions, list) or not isinstance(answers, list):
        return jsonify(error="questions and answers must be lists"), 400
    if len(questions) != len(answers) or len(questions) == 0:
        return jsonify(error="questions and answers length mismatch or empty"), 400

    # Local scoring fallback
    total = len(questions)
    incorrect_details = []
    local_score = 0
    for i, q in enumerate(questions):
        correct_index = q.get("correct_index")
        ans = answers[i]
        if correct_index is None or ans is None:
            # Will be handled by Gemini if available
            continue
        if ans == correct_index:
            local_score += 1
        else:
            incorrect_details.append({
                "index": i,
                "your_answer_index": ans,
                "correct_index": correct_index,
                "feedback": ""
            })

    # Attempt Gemini evaluation for richer feedback
    try:
        gemini_res = evaluate_mcq_answers(app, subject, questions, answers)
        # Merge scores and feedback if Gemini returns a valid structure
        if gemini_res and isinstance(gemini_res, dict):
            score = gemini_res.get("score", local_score)
            incorrect = gemini_res.get("incorrect", incorrect_details)
            return jsonify(score=score, total=total, incorrect=incorrect), 200
    except Exception as e:
        # Fall back silently to local scoring
        app.logger.warning(f"Gemini evaluation failed: {e}")

    return jsonify(score=local_score, total=total, incorrect=incorrect_details), 200