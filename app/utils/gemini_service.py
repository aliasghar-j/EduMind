import os
import json
from typing import List, Dict, Any

try:
    import requests
except Exception:
    requests = None

GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"


def _build_prompt(subject: str, questions: List[Dict[str, Any]], answers: List[int]) -> str:
    # Ask Gemini to evaluate MCQ answers and return a concise JSON
    return (
        "You are grading a 10-question multiple-choice quiz for subject '" + subject + "'. "
        "Each question has options[0..N]. Grade strictly by provided correct_index when present. "
        "If correct_index is missing, infer the correct option based on question_text and options. "
        "Return ONLY JSON with keys: score (int), incorrect (array of objects with index, your_answer_index, correct_index, feedback). "
        "Avoid any extra text. Use concise feedback (<120 chars).\n" 
        + json.dumps({"questions": questions, "answers": answers})
    )


def evaluate_mcq_answers(app, subject: str, questions: List[Dict[str, Any]], answers: List[int]) -> Dict[str, Any]:
    """
    Evaluate MCQ answers using Gemini when API key is available.
    Fallback: return None to signal caller to use local scoring.
    """
    api_key = os.getenv("GEMINI_API_KEY", "") or getattr(app.config, "GEMINI_API_KEY", "")
    if not api_key or requests is None:
        return None

    payload = {
        "contents": [
            {
                "parts": [{"text": _build_prompt(subject, questions, answers)}]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 512
        }
    }

    try:
        r = requests.post(
            GEMINI_ENDPOINT,
            params={"key": api_key},
            json=payload,
            timeout=20
        )
        if r.status_code != 200:
            app.logger.warning(f"Gemini API error {r.status_code}: {r.text[:200]}")
            return None
        data = r.json()
        # Extract text from candidates
        candidates = (data.get("candidates") or [])
        if not candidates:
            return None
        parts = ((candidates[0] or {}).get("content") or {}).get("parts") or []
        text = parts[0].get("text") if parts else ""
        if not text:
            return None
        # The model is instructed to return strict JSON
        try:
            res = json.loads(text)
            # Basic shape check
            if "score" in res and "incorrect" in res:
                return res
        except Exception:
            app.logger.warning("Gemini response parse failed; falling back to local.")
            return None
    except Exception as e:
        app.logger.warning(f"Gemini request failed: {e}")
        return None

    return None


# New: Generate 10 MCQs for a given subject strictly via Gemini

def _build_generation_prompt(subject: str) -> str:
    return (
        "Generate 10 multiple-choice questions for subject '" + subject + "'. "
        "Each question must include: id (string), question_text (string), options (array of 4 strings), correct_index (int). "
        "Return ONLY strict JSON: {\"questions\": [{id, question_text, options, correct_index}...]}. "
        "Do not include markdown or any extra commentary."
    )


def generate_mcqs(app, subject: str) -> Dict[str, Any]:
    api_key = os.getenv("GEMINI_API_KEY", "") or getattr(app.config, "GEMINI_API_KEY", "")
    if not api_key or requests is None:
        raise RuntimeError("Gemini API unavailable or requests missing")

    payload = {
        "contents": [
            {
                "parts": [{"text": _build_generation_prompt(subject)}]
            }
        ],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 1024
        }
    }

    r = requests.post(
        GEMINI_ENDPOINT,
        params={"key": api_key},
        json=payload,
        timeout=25
    )
    if r.status_code != 200:
        raise RuntimeError(f"Gemini error {r.status_code}: {r.text[:200]}")
    data = r.json()
    candidates = (data.get("candidates") or [])
    if not candidates:
        raise RuntimeError("No candidates from Gemini")
    parts = ((candidates[0] or {}).get("content") or {}).get("parts") or []
    text = parts[0].get("text") if parts else ""
    if not text:
        raise RuntimeError("Empty response text from Gemini")

    try:
        res = json.loads(text)
        questions = res.get("questions") or []
        if not isinstance(questions, list) or len(questions) != 10:
            raise RuntimeError("Gemini did not return 10 questions")
        # Minimal normalization
        normalized = []
        for i, q in enumerate(questions):
            qid = q.get("id") or f"{subject}-{i+1}"
            qt = q.get("question_text") or ""
            opts = q.get("options") or []
            ci = q.get("correct_index")
            if not isinstance(opts, list) or len(opts) < 4 or not isinstance(ci, int):
                raise RuntimeError("Invalid question format from Gemini")
            normalized.append({
                "id": qid,
                "question_text": qt,
                "options": opts,
                "correct_index": ci,
            })
        return {"questions": normalized}
    except Exception as e:
        raise RuntimeError(f"Failed to parse Gemini questions: {e}")