"""
Local preferences: API keys, email, last ticker. Saved to .app_prefs.json.
"""
import json
from pathlib import Path

_PREFS_PATH = Path(__file__).resolve().parent.parent / ".app_prefs.json"
_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _load_prefs() -> dict:
    """Load saved API keys and email from local file. Keys: google_api_key, sec_email."""
    try:
        if _PREFS_PATH.exists():
            with open(_PREFS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_prefs(google_api_key: str, sec_email: str, last_ticker: str = None, last_company_options: list = None, last_company_symbols: list = None) -> None:
    """Save API keys, email, and last selected company to local file."""
    try:
        data = {}
        if _PREFS_PATH.exists():
            try:
                with open(_PREFS_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                pass
        data["google_api_key"] = (google_api_key or "").strip()
        data["sec_email"] = (sec_email or "").strip()
        if last_ticker is not None:
            data["last_ticker"] = (last_ticker or "").strip()
        if last_company_options is not None:
            data["last_company_options"] = list(last_company_options) if last_company_options else []
        if last_company_symbols is not None:
            data["last_company_symbols"] = list(last_company_symbols) if last_company_symbols else []
        with open(_PREFS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass
