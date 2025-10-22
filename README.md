# EduMind Backend (Flask)

EduMind is a web platform that connects students with mentors for career guidance and learning support. This initialization sets up the backend using Flask with modular blueprints, environment-based configuration, CORS, and placeholders for Google OAuth and a Google Sheets-based datastore.

## Project Structure

```
EduMind/
├─ app/
│  ├─ __init__.py
│  ├─ routes/
│  │  ├─ __init__.py
│  │  ├─ student_routes.py
│  │  ├─ mentor_routes.py
│  │  └─ auth_routes.py
│  ├─ models/
│  │  └─ __init__.py
│  ├─ utils/
│  │  ├─ __init__.py
│  │  ├─ oauth.py
│  │  └─ sheets.py
│  ├─ static/
│  │  └─ .gitkeep
│  └─ templates/
│     └─ .gitkeep
├─ config.py
├─ requirements.txt
├─ run.py
├─ .env
└─ README.md
```

## Setup (Windows PowerShell)
- Create and activate a virtual environment:
  - `python -m venv .venv`
  - `./.venv/Scripts/Activate.ps1`
- Install dependencies:
  - `pip install -r requirements.txt`
- Configure environment variables:
  - Edit `.env` as needed:
    - `SECRET_KEY` — app secret
    - `GOOGLE_SHEETS_SPREADSHEET_ID` — target spreadsheet ID (the long ID in its URL)
    - `GOOGLE_APPLICATION_CREDENTIALS` — path to your Google service account JSON key
    - `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` — for future OAuth login (not required for Sheets service account)
- Run the server:
  - `python run.py`

## Configuration
- Environment-based config via `config.py`:
  - `DevelopmentConfig` and `ProductionConfig` based on `FLASK_ENV` or `APP_ENV`.
- Extensions:
  - CORS enabled globally.
  - Placeholder Google OAuth setup reading credentials from `.env`.
  - Placeholder Google Sheets setup reading spreadsheet and credentials settings.

## Test Routes
- `GET /api/student/test` → `{"message": "Hello from EduMind - Student"}`
- `GET /api/mentor/test` → `{"message": "Hello from EduMind - Mentor"}`
- `GET /api/auth/test` → `{"message": "Hello from EduMind - Auth"}`

## Notes
- No frontend/UI code is included in this initialization. Future work will integrate Google Stitch for UI.
- No ORM or database migrations are used; datastore will be Google Sheets.
- Next phase will implement helpers for Sheets read/write and the OAuth flow.