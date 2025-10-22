from typing import Dict, List, Optional
from flask import current_app
from datetime import datetime

from app.utils.sheets import (
    sheets_append_row,
    sheets_get_rows,
    sheets_update_range,
)

# Utility helpers

def _col_letter(idx: int) -> str:
    # 1-indexed column index to letter (1->A)
    result = ""
    while idx > 0:
        idx, rem = divmod(idx - 1, 26)
        result = chr(65 + rem) + result
    return result


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


# Config sheet helpers

def get_config_value(app, key: str) -> Optional[str]:
    rows = sheets_get_rows(app, "Config")
    for row in rows:
        if row and row[0] == key:
            return row[1] if len(row) > 1 else None
    return None


def set_config_value(app, key: str, value: str) -> None:
    rows = sheets_get_rows(app, "Config")
    keys = [r[0] for r in rows if r]
    if key in keys:
        idx = keys.index(key)
        # Update the value in column B
        sheets_update_range(app, "Config", f"B{idx+2}", [[value]])
    else:
        sheets_append_row(app, "Config", [key, value])


# Sequence/ID generation using Config counters

def _next_seq(app, counter_key: str, prefix: str) -> str:
    current = get_config_value(app, counter_key)
    n = int(current or 0) + 1
    set_config_value(app, counter_key, str(n))
    return f"{prefix}{n}"


# Users

def create_user(app, name: str, email: str, role: str, google_id: Optional[str] = None, profile_picture_url: Optional[str] = None) -> Dict[str, str]:
    """Create a user row aligned with Users sheet headers.

    Headers: ["user_id","name","email","role","google_id","password","profile_picture_url","date_joined","status"]
    """
    user_id = _next_seq(app, "USER_COUNTER", "U_")
    date_joined = _now_iso()
    row = [
        user_id,
        name or "",
        email or "",
        role or "student",
        google_id or "",
        "",  # password
        profile_picture_url or "",
        date_joined,
        "active",
    ]
    sheets_append_row(app, "Users", row)
    return {"user_id": user_id, "name": name, "email": email, "role": role, "status": "active"}


def get_user_by_email(app, email: str) -> Optional[Dict[str, str]]:
    rows = sheets_get_rows(app, "Users")
    headers = rows[0] if rows else []
    email_idx = headers.index("email") if "email" in headers else 2
    id_idx = headers.index("user_id") if "user_id" in headers else 0
    role_idx = headers.index("role") if "role" in headers else 3
    for row in rows[1:]:
        if len(row) > email_idx and row[email_idx] == email:
            return {"user_id": row[id_idx], "email": email, "role": row[role_idx]}
    return None


def update_user_profile_by_email(
    app,
    email: str,
    name: Optional[str] = None,
    role: Optional[str] = None,
    google_id: Optional[str] = None,
    profile_picture_url: Optional[str] = None,
) -> Optional[Dict[str, str]]:
    """Update basic user fields by email if row exists.
    Returns dict with user_id and email when updated, else None.
    """
    rows = sheets_get_rows(app, "Users")
    if not rows:
        return None
    headers = rows[0]
    email_idx = headers.index("email") if "email" in headers else 2
    id_idx = headers.index("user_id") if "user_id" in headers else 0
    name_idx = headers.index("name") if "name" in headers else 1
    role_idx = headers.index("role") if "role" in headers else 3
    google_idx = headers.index("google_id") if "google_id" in headers else 4
    picture_idx = headers.index("profile_picture_url") if "profile_picture_url" in headers else 6

    target_row_index: Optional[int] = None
    for i, row in enumerate(rows[1:], start=2):
        if len(row) > email_idx and row[email_idx] == email:
            target_row_index = i
            break
    if not target_row_index:
        return None

    row = rows[target_row_index - 1] if (target_row_index - 1) < len(rows) else []

    def set_idx(r: List[str], idx: int, value: str):
        while len(r) <= idx:
            r.append("")
        r[idx] = value

    if name is not None:
        set_idx(row, name_idx, name)
    if role is not None:
        set_idx(row, role_idx, role)
    if google_id is not None:
        set_idx(row, google_idx, google_id)
    if profile_picture_url is not None:
        set_idx(row, picture_idx, profile_picture_url)

    end_col = _col_letter(max(len(row), len(headers)))
    sheets_update_range(app, "Users", f"A{target_row_index}:{end_col}{target_row_index}", [row])
    return {"user_id": row[id_idx], "email": email}


# Student profile upsert

def upsert_student_profile(
    app,
    student_id: str,
    interests: str = "",
    career_choices: str = "",
    syllabus_links: str = "",
    uploaded_materials: str = "",
    mentor_match_ids: str = "",
    google_calendar_sync_id: str = "",
    notes: str = "",
) -> Dict[str, str]:
    rows = sheets_get_rows(app, "Students")
    headers = rows[0] if rows else []
    id_idx = headers.index("student_id") if "student_id" in headers else 0
    # Try to find existing row and update in place
    found_idx = None
    for i, row in enumerate(rows[1:], start=2):
        if len(row) > id_idx and row[id_idx] == student_id:
            found_idx = i
            break
    data = [
        student_id,
        interests,
        career_choices,
        syllabus_links,
        uploaded_materials,
        mentor_match_ids,
        google_calendar_sync_id,
        notes,
        _now_iso(),
    ]
    if found_idx:
        # Update the entire row starting from A
        end_col = _col_letter(len(data))
        sheets_update_range(app, "Students", f"A{found_idx}:{end_col}{found_idx}", [data])
    else:
        sheets_append_row(app, "Students", data)
    return {"student_id": student_id}


# Mentor profile upsert

def upsert_mentor_profile(
    app,
    mentor_id: str,
    general_interests: str = "",
    career_background: str = "",
    available_slots: str = "",
    specialization_tags: str = "",
    notes: str = "",
) -> Dict[str, str]:
    rows = sheets_get_rows(app, "Mentors")
    headers = rows[0] if rows else []
    id_idx = headers.index("mentor_id") if "mentor_id" in headers else 0
    found_idx = None
    for i, row in enumerate(rows[1:], start=2):
        if len(row) > id_idx and row[id_idx] == mentor_id:
            found_idx = i
            break
    data = [
        mentor_id,
        general_interests,
        career_background,
        available_slots,
        "",  # scheduled_sessions placeholder
        specialization_tags,
        "",  # ai_review_count placeholder
        notes,
    ]
    if found_idx:
        end_col = _col_letter(len(data))
        sheets_update_range(app, "Mentors", f"A{found_idx}:{end_col}{found_idx}", [data])
    else:
        sheets_append_row(app, "Mentors", data)
    return {"mentor_id": mentor_id}


# Sessions scheduling

def schedule_session(
    app,
    mentor_id: str,
    student_id: str,
    date: str,
    time: str,
    topic: str,
    status: str = "scheduled",
) -> Dict[str, str]:
    session_id = _next_seq(app, "SESSION_COUNTER", "S_")
    data = [
        session_id,
        mentor_id,
        student_id,
        date,
        time,
        topic,
        status,
        "",
    ]
    sheets_append_row(app, "Sessions", data)
    return {"session_id": session_id, "mentor_id": mentor_id, "student_id": student_id}


# Listing helpers

def list_sessions_for_student(app, student_id: str) -> List[Dict[str, str]]:
    rows = sheets_get_rows(app, "Sessions")
    if not rows:
        return []
    headers = rows[0]
    id_idx = headers.index("session_id")
    student_idx = headers.index("student_id")
    mentor_idx = headers.index("mentor_id")
    date_idx = headers.index("date")
    time_idx = headers.index("time")
    topic_idx = headers.index("topic")
    out = []
    for row in rows[1:]:
        if len(row) > student_idx and row[student_idx] == student_id:
            out.append({
                "session_id": row[id_idx],
                "mentor_id": row[mentor_idx],
                "student_id": row[student_idx],
                "date": row[date_idx],
                "time": row[time_idx],
                "topic": row[topic_idx],
            })
    return out


def list_sessions_for_mentor(app, mentor_id: str) -> List[Dict[str, str]]:
    rows = sheets_get_rows(app, "Sessions")
    if not rows:
        return []
    headers = rows[0]
    id_idx = headers.index("session_id")
    student_idx = headers.index("student_id")
    mentor_idx = headers.index("mentor_id")
    date_idx = headers.index("date")
    time_idx = headers.index("time")
    topic_idx = headers.index("topic")
    out = []
    for row in rows[1:]:
        if len(row) > mentor_idx and row[mentor_idx] == mentor_id:
            out.append({
                "session_id": row[id_idx],
                "mentor_id": row[mentor_idx],
                "student_id": row[student_idx],
                "date": row[date_idx],
                "time": row[time_idx],
                "topic": row[topic_idx],
            })
    return out


# Study Materials

def add_study_material(
    app,
    student_id: str,
    file_name: str,
    file_link: str,
    summary: str = "",
    related_quiz_ids: str = "",
) -> Dict[str, str]:
    material_id = _next_seq(app, "MATERIAL_COUNTER", "M_")
    upload_date = _now_iso()
    row = [
        material_id,
        student_id,
        file_name,
        file_link,
        summary,
        upload_date,
        related_quiz_ids,
    ]
    sheets_append_row(app, "Study_Materials", row)
    return {"material_id": material_id, "student_id": student_id}


def list_study_materials_for_student(app, student_id: str) -> List[Dict[str, str]]:
    rows = sheets_get_rows(app, "Study_Materials")
    if not rows:
        return []
    headers = rows[0]
    id_idx = headers.index("material_id")
    student_idx = headers.index("student_id")
    file_name_idx = headers.index("file_name")
    file_link_idx = headers.index("file_link")
    summary_idx = headers.index("summary")
    upload_idx = headers.index("upload_date")
    related_idx = headers.index("related_quiz_ids")
    out = []
    for r in rows[1:]:
        if len(r) > student_idx and r[student_idx] == student_id:
            out.append({
                "material_id": r[id_idx],
                "student_id": r[student_idx],
                "file_name": r[file_name_idx],
                "file_link": r[file_link_idx],
                "summary": r[summary_idx] if len(r) > summary_idx else "",
                "upload_date": r[upload_idx] if len(r) > upload_idx else "",
                "related_quiz_ids": r[related_idx] if len(r) > related_idx else "",
            })
    return out


# Quizzes

def create_quiz(
    app,
    subject: str,
    difficulty_level: str,
    question_text: str,
    options: List[str],
    correct_answer: str,
    related_material_id: str,
    created_by: str,
) -> Dict[str, str]:
    quiz_id = _next_seq(app, "QUIZ_COUNTER", "Q_")
    created_at = _now_iso()
    options_str = "|".join(options)
    row = [
        quiz_id,
        subject,
        difficulty_level,
        question_text,
        options_str,
        correct_answer,
        related_material_id,
        created_by,
        created_at,
    ]
    sheets_append_row(app, "Quizzes", row)
    return {"quiz_id": quiz_id, "related_material_id": related_material_id}


def list_quizzes_for_material(app, material_id: str) -> List[Dict[str, str]]:
    rows = sheets_get_rows(app, "Quizzes")
    if not rows:
        return []
    headers = rows[0]
    id_idx = headers.index("quiz_id")
    subject_idx = headers.index("subject")
    difficulty_idx = headers.index("difficulty_level")
    question_idx = headers.index("question_text")
    options_idx = headers.index("options")
    correct_idx = headers.index("correct_answer")
    related_idx = headers.index("related_material_id")
    out = []
    for r in rows[1:]:
        if len(r) > related_idx and r[related_idx] == material_id:
            out.append({
                "quiz_id": r[id_idx],
                "subject": r[subject_idx],
                "difficulty_level": r[difficulty_idx],
                "question_text": r[question_idx],
                "options": r[options_idx],
                "correct_answer": r[correct_idx],
                "related_material_id": r[related_idx],
            })
    return out


def list_quizzes_for_student(app, student_id: str) -> List[Dict[str, str]]:
    # Map student's materials to quizzes
    mats = list_study_materials_for_student(app, student_id)
    mat_ids = {m["material_id"] for m in mats}
    rows = sheets_get_rows(app, "Quizzes")
    if not rows:
        return []
    headers = rows[0]
    id_idx = headers.index("quiz_id")
    subject_idx = headers.index("subject")
    difficulty_idx = headers.index("difficulty_level")
    question_idx = headers.index("question_text")
    options_idx = headers.index("options")
    correct_idx = headers.index("correct_answer")
    related_idx = headers.index("related_material_id")
    out = []
    for r in rows[1:]:
        if len(r) > related_idx and r[related_idx] in mat_ids:
            out.append({
                "quiz_id": r[id_idx],
                "subject": r[subject_idx],
                "difficulty_level": r[difficulty_idx],
                "question_text": r[question_idx],
                "options": r[options_idx],
                "correct_answer": r[correct_idx],
                "related_material_id": r[related_idx],
            })
    return out


# Quiz Scores

def _derive_performance_level(app, ratio: float) -> str:
    thresholds = get_config_value(app, "quiz_performance_thresholds") or "excellent>=0.85|good>=0.70"
    level_map = {"excellent": 0.85, "good": 0.70}
    try:
        parts = thresholds.split("|")
        tmp = {}
        for p in parts:
            name, val = p.split(">=")
            tmp[name.strip()] = float(val)
        level_map = tmp
    except Exception:
        pass
    if ratio >= level_map.get("excellent", 0.85):
        return "excellent"
    if ratio >= level_map.get("good", 0.70):
        return "good"
    return "needs_improvement"


def record_quiz_score(
    app,
    student_id: str,
    quiz_id: str,
    score: float,
    total_marks: float,
    grader: str = "",
    notes: str = "",
) -> Dict[str, str]:
    score_id = _next_seq(app, "SCORE_COUNTER", "SC_")
    date_taken = _now_iso()
    ratio = 0.0
    try:
        ratio = (float(score) / float(total_marks)) if float(total_marks) > 0 else 0.0
    except Exception:
        ratio = 0.0
    performance = _derive_performance_level(app, ratio)
    row = [
        score_id,
        student_id,
        quiz_id,
        str(score),
        str(total_marks),
        date_taken,
        performance,
        grader,
        notes,
    ]
    sheets_append_row(app, "Quiz_Scores", row)
    return {"score_id": score_id, "performance_level": performance}


def list_quiz_scores_for_student(app, student_id: str) -> List[Dict[str, str]]:
    rows = sheets_get_rows(app, "Quiz_Scores")
    if not rows:
        return []
    headers = rows[0]
    id_idx = headers.index("score_id")
    student_idx = headers.index("student_id")
    quiz_idx = headers.index("quiz_id")
    score_idx = headers.index("score")
    total_idx = headers.index("total_marks")
    date_idx = headers.index("date_taken")
    perf_idx = headers.index("performance_level")
    grader_idx = headers.index("grader")
    notes_idx = headers.index("notes")
    out = []
    for r in rows[1:]:
        if len(r) > student_idx and r[student_idx] == student_id:
            out.append({
                "score_id": r[id_idx],
                "student_id": r[student_idx],
                "quiz_id": r[quiz_idx],
                "score": r[score_idx],
                "total_marks": r[total_idx],
                "date_taken": r[date_idx],
                "performance_level": r[perf_idx],
                "grader": r[grader_idx] if len(r) > grader_idx else "",
                "notes": r[notes_idx] if len(r) > notes_idx else "",
            })
    return out


def get_student_profile(app, student_id: str) -> Optional[Dict[str, str]]:
    """Return student profile row from Students sheet."""
    rows = sheets_get_rows(app, "Students")
    if not rows:
        return None
    headers = rows[0]
    try:
        id_idx = headers.index("student_id")
    except ValueError:
        id_idx = 0
    for row in rows[1:]:
        if len(row) > id_idx and row[id_idx] == student_id:
            # Build dict by headers up to row length
            data = {}
            for i, h in enumerate(headers):
                if i < len(row):
                    data[h] = row[i]
            return data
    return None


def list_student_interests(app, student_id: str) -> List[str]:
    """Return interests as a list for given student_id."""
    prof = get_student_profile(app, student_id)
    if not prof:
        return []
    val = prof.get("interests", "")
    # Normalize split by ';' or '|' and commas
    parts = []
    for sep in [';', '|', ',']:
        if sep in val:
            parts = [p.strip() for p in val.split(sep) if p.strip()]
            break
    if not parts and val:
        parts = [val.strip()]
    return parts


def update_student_interests(app, student_id: str, interests: List[str]) -> Dict[str, str]:
    """Update interests cell for the given student without altering other columns."""
    rows = sheets_get_rows(app, "Students")
    if not rows:
        raise RuntimeError("Students sheet empty or missing")
    headers = rows[0]
    try:
        id_idx = headers.index("student_id")
    except ValueError:
        id_idx = 0
    try:
        interests_idx = headers.index("interests")
    except ValueError:
        interests_idx = 1
    target_row_idx = None
    for i, row in enumerate(rows[1:], start=2):
        if len(row) > id_idx and row[id_idx] == student_id:
            target_row_idx = i
            break
    if target_row_idx is None:
        # Create a minimal new row with student_id and interests, append
        normalized = '; '.join([s.strip() for s in interests if s.strip()])
        # Build row aligned to headers length
        data = [''] * len(headers)
        # Set student_id and interests
        data[id_idx] = student_id
        data[interests_idx] = normalized
        sheets_append_row(app, "Students", data)
        return {"student_id": student_id, "interests": normalized}
    else:
        normalized = '; '.join([s.strip() for s in interests if s.strip()])
        # Update only the interests cell
        col_letter = _col_letter(interests_idx + 1)  # headers are 0-based
        sheets_update_range(app, "Students", f"{col_letter}{target_row_idx}", [[normalized]])
        return {"student_id": student_id, "interests": normalized}


def get_mentor_profile(app, mentor_id: str) -> Optional[Dict[str, str]]:
    rows = sheets_get_rows(app, "Mentors")
    if not rows:
        return None
    headers = rows[0]
    try:
        id_idx = headers.index("mentor_id")
    except ValueError:
        id_idx = 0
    for row in rows[1:]:
        if len(row) > id_idx and row[id_idx] == mentor_id:
            data = {}
            for i, h in enumerate(headers):
                if i < len(row):
                    data[h] = row[i]
            return data
    return None


def list_mentor_interests(app, mentor_id: str) -> List[str]:
    prof = get_mentor_profile(app, mentor_id)
    if not prof:
        return []
    val = prof.get("general_interests", "")
    parts = []
    for sep in [';', '|', ',']:
        if sep in val:
            parts = [p.strip() for p in val.split(sep) if p.strip()]
            break
    if not parts and val:
        parts = [val.strip()]
    return parts


def update_mentor_interests(app, mentor_id: str, interests: List[str]) -> Dict[str, str]:
    rows = sheets_get_rows(app, "Mentors")
    if not rows:
        raise RuntimeError("Mentors sheet empty or missing")
    headers = rows[0]
    try:
        id_idx = headers.index("mentor_id")
    except ValueError:
        id_idx = 0
    try:
        interests_idx = headers.index("general_interests")
    except ValueError:
        interests_idx = 1
    target_row_idx = None
    for i, row in enumerate(rows[1:], start=2):
        if len(row) > id_idx and row[id_idx] == mentor_id:
            target_row_idx = i
            break
    normalized = '; '.join([s.strip() for s in interests if s.strip()])
    if target_row_idx is None:
        data = [''] * len(headers)
        data[id_idx] = mentor_id
        data[interests_idx] = normalized
        sheets_append_row(app, "Mentors", data)
    else:
        col_letter = _col_letter(interests_idx + 1)
        sheets_update_range(app, "Mentors", f"{col_letter}{target_row_idx}", [[normalized]])
    return {"mentor_id": mentor_id, "general_interests": normalized}


def list_mentor_teaching_areas(app, mentor_id: str) -> List[str]:
    prof = get_mentor_profile(app, mentor_id)
    if not prof:
        return []
    val = prof.get("specialization_tags", "")
    parts = []
    for sep in [';', '|', ',']:
        if sep in val:
            parts = [p.strip() for p in val.split(sep) if p.strip()]
            break
    if not parts and val:
        parts = [val.strip()]
    return parts


def update_mentor_teaching_areas(app, mentor_id: str, areas: List[str]) -> Dict[str, str]:
    rows = sheets_get_rows(app, "Mentors")
    if not rows:
        raise RuntimeError("Mentors sheet empty or missing")
    headers = rows[0]
    try:
        id_idx = headers.index("mentor_id")
    except ValueError:
        id_idx = 0
    try:
        areas_idx = headers.index("specialization_tags")
    except ValueError:
        areas_idx = 5
    target_row_idx = None
    for i, row in enumerate(rows[1:], start=2):
        if len(row) > id_idx and row[id_idx] == mentor_id:
            target_row_idx = i
            break
    normalized = '; '.join([s.strip() for s in areas if s.strip()])
    if target_row_idx is None:
        data = [''] * len(headers)
        data[id_idx] = mentor_id
        data[areas_idx] = normalized
        sheets_append_row(app, "Mentors", data)
    else:
        col_letter = _col_letter(areas_idx + 1)
        sheets_update_range(app, "Mentors", f"{col_letter}{target_row_idx}", [[normalized]])
    return {"mentor_id": mentor_id, "specialization_tags": normalized}


def update_mentor_career_background(app, mentor_id: str, career_background: str) -> Dict[str, str]:
    rows = sheets_get_rows(app, "Mentors")
    if not rows:
        raise RuntimeError("Mentors sheet empty or missing")
    headers = rows[0]
    try:
        id_idx = headers.index("mentor_id")
    except ValueError:
        id_idx = 0
    try:
        cb_idx = headers.index("career_background")
    except ValueError:
        cb_idx = 2
    target_row_idx = None
    for i, row in enumerate(rows[1:], start=2):
        if len(row) > id_idx and row[id_idx] == mentor_id:
            target_row_idx = i
            break
    normalized = (career_background or "").strip()
    if target_row_idx is None:
        data = [''] * len(headers)
        data[id_idx] = mentor_id
        data[cb_idx] = normalized
        sheets_append_row(app, "Mentors", data)
    else:
        col_letter = _col_letter(cb_idx + 1)
        sheets_update_range(app, "Mentors", f"{col_letter}{target_row_idx}", [[normalized]])
    return {"mentor_id": mentor_id, "career_background": normalized}