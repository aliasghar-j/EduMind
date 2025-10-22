import os
from typing import List, Dict, Any, Optional

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Required Sheets scope for read/write
SHEETS_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# EduMind sheet definitions: names and headers
SHEET_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "title": "Users",
        "headers": [
            "user_id","name","email","role","google_id","password",
            "profile_picture_url","date_joined","status"
        ],
    },
    {
        "title": "Students",
        "headers": [
            "student_id","interests","career_choices","syllabus_links",
            "uploaded_materials","mentor_match_ids","google_calendar_sync_id",
            "average_score","notes"
        ],
    },
    {
        "title": "Mentors",
        "headers": [
            "mentor_id","general_interests","career_background","available_slots",
            "scheduled_sessions","specialization_tags","ai_review_count","notes"
        ],
    },
    {
        "title": "Sessions",
        "headers": [
            "session_id","mentor_id","student_id","date","time","topic",
            "status","feedback","created_at","updated_at"
        ],
    },
    {
        "title": "Study_Materials",
        "headers": [
            "material_id","student_id","file_name","file_link","summary","upload_date",
            "related_quiz_ids"
        ],
    },
    {
        "title": "Quizzes",
        "headers": [
            "quiz_id","subject","difficulty_level","question_text","options",
            "correct_answer","related_material_id","created_by","created_at"
        ],
    },
    {
        "title": "Quiz_Scores",
        "headers": [
            "score_id","student_id","quiz_id","score","total_marks","date_taken",
            "performance_level","grader","notes"
        ],
    },
    {
        "title": "AI_Corrections",
        "headers": [
            "correction_id","mentor_id","student_id","file_link","ai_feedback",
            "ai_score","manual_feedback","final_score","date","related_material_id"
        ],
    },
    {
        "title": "Mentor_Recommendations",
        "headers": [
            "recommendation_id","student_id","mentor_id","match_percentage",
            "reason_for_match","date_generated","source"
        ],
    },
    {
        "title": "Config",
        "headers": ["key","value","description","updated_at"],
    },
]


def _column_letter(idx: int) -> str:
    """Convert 1-based column index to A1 letter(s)."""
    result = ""
    while idx:
        idx, rem = divmod(idx - 1, 26)
        result = chr(65 + rem) + result
    return result


def _build_service(credentials_path: str):
    creds = Credentials.from_service_account_file(credentials_path, scopes=SHEETS_SCOPES)
    return build("sheets", "v4", credentials=creds)


def init_sheets_client(app):
    """Initialize Google Sheets client and ensure datastore structure exists.

    Reads env/config: GOOGLE_APPLICATION_CREDENTIALS, GOOGLE_SHEETS_SPREADSHEET_ID.
    - Builds Sheets API service using a service account.
    - Creates a new spreadsheet if ID is missing, stores ID in app.config.
    - Ensures all tabs exist and writes headers for each sheet.
    - Seeds Config with initial keys if empty.
    """
    spreadsheet_id = app.config.get("GOOGLE_SHEETS_SPREADSHEET_ID") or os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID", "")
    credentials_path = app.config.get("GOOGLE_APPLICATION_CREDENTIALS") or os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")

    if not credentials_path:
        # Defer initialization if credentials are not provided
        app.logger.warning("GOOGLE_APPLICATION_CREDENTIALS not set; Sheets client not initialized.")
        return

    try:
        service = _build_service(credentials_path)
        if not spreadsheet_id:
            spreadsheet_id = _create_spreadsheet(service, title="EduMind Datastore")
            app.logger.info(f"Created new spreadsheet: {spreadsheet_id}")
            app.config["GOOGLE_SHEETS_SPREADSHEET_ID"] = spreadsheet_id

        _ensure_tabs(service, spreadsheet_id)
        _ensure_headers(service, spreadsheet_id)
        _seed_config(service, spreadsheet_id)

        # stash service instance for reuse (optional)
        app.extensions = getattr(app, "extensions", {})
        app.extensions["sheets_service"] = service
        app.extensions["spreadsheet_id"] = spreadsheet_id

    except HttpError as e:
        app.logger.error(f"Google Sheets API error: {e}")
    except Exception as e:
        app.logger.error(f"Sheets init failed: {e}")


def _create_spreadsheet(service, title: str) -> str:
    body = {
        "properties": {"title": title},
        "sheets": [],
    }
    resp = service.spreadsheets().create(body=body).execute()
    return resp["spreadsheetId"]


def _get_existing_sheet_titles(service, spreadsheet_id: str) -> List[str]:
    meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    titles = [s["properties"]["title"] for s in meta.get("sheets", [])]
    return titles


def _ensure_tabs(service, spreadsheet_id: str):
    existing = set(_get_existing_sheet_titles(service, spreadsheet_id))
    requests = []
    for sd in SHEET_DEFINITIONS:
        title = sd["title"]
        if title not in existing:
            requests.append({
                "addSheet": {
                    "properties": {
                        "title": title,
                        "gridProperties": {"rowCount": 1000, "columnCount": max(10, len(sd["headers"]))}
                    }
                }
            })
    if requests:
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": requests}
        ).execute()


def _ensure_headers(service, spreadsheet_id: str):
    for sd in SHEET_DEFINITIONS:
        title = sd["title"]
        headers = sd["headers"]
        range_a1 = f"{title}!A1:{_column_letter(len(headers))}1"
        # Read first row
        read = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=f"{title}!1:1").execute()
        values = read.get("values", [])
        if not values:
            service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_a1,
                valueInputOption="RAW",
                body={"values": [headers]},
            ).execute()


def _seed_config(service, spreadsheet_id: str):
    # Only seed if Config sheet is effectively empty (no data beyond header)
    read = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range="Config!A2:D2").execute()
    if read.get("values"):
        return
    rows = [
        ["google_oauth_scopes", "openid email profile", "OAuth scopes for Google Sign-In", _now_iso()],
        ["last_sync_timestamp", "", "Last successful sync with Sheets datastore", _now_iso()],
        ["calendar_default_timezone", "UTC", "Default timezone for sessions and calendar sync", _now_iso()],
        ["default_session_duration_minutes", "60", "Default session length if not specified", _now_iso()],
        ["quiz_performance_thresholds", "excellent>=0.85|good>=0.70", "Thresholds for performance level derivation", _now_iso()],
        ["app_version", "v0.1", "EduMind backend datastore version", _now_iso()],
    ]
    service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range="Config!A2",
        valueInputOption="RAW",
        body={"values": rows},
    ).execute()


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


# Basic CRUD helpers

def sheets_append_row(app, sheet_name: str, row: List[Any]):
    service = app.extensions.get("sheets_service")
    spreadsheet_id = app.extensions.get("spreadsheet_id")
    if not service or not spreadsheet_id:
        raise RuntimeError("Sheets service not initialized")
    service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=f"{sheet_name}!A:A",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": [row]},
    ).execute()


def sheets_get_rows(app, sheet_name: str, range_a1: Optional[str] = None) -> List[List[Any]]:
    service = app.extensions.get("sheets_service")
    spreadsheet_id = app.extensions.get("spreadsheet_id")
    if not service or not spreadsheet_id:
        raise RuntimeError("Sheets service not initialized")
    rng = range_a1 or f"{sheet_name}!A1:Z"
    resp = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=rng).execute()
    return resp.get("values", [])


def sheets_update_range(app, sheet_name: str, range_a1: str, values: List[List[Any]]):
    service = app.extensions.get("sheets_service")
    spreadsheet_id = app.extensions.get("spreadsheet_id")
    if not service or not spreadsheet_id:
        raise RuntimeError("Sheets service not initialized")
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"{sheet_name}!{range_a1}" if "!" not in range_a1 else range_a1,
        valueInputOption="RAW",
        body={"values": values},
    ).execute()