import json
from datetime import datetime
from pathlib import Path
from typing import Optional


TRACE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "output" / "traces"

_active_sessions: dict[str, dict] = {}


def start_session(session_id: str) -> str:
    TRACE_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder_name = f"{session_id}_{ts}"
    folder = TRACE_DIR / folder_name
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "pipeline.json"
    trace = {"session_id": session_id, "started_at": datetime.now().isoformat(), "steps": {}}
    _active_sessions[session_id] = {"folder": folder, "path": str(path), "trace": trace}
    _flush(session_id)
    return str(path)


def append_step(session_id: str, step_name: str, data: dict):
    if session_id not in _active_sessions:
        start_session(session_id)
    session = _active_sessions[session_id]
    session["trace"]["steps"][step_name] = data
    session["trace"][f"last_updated"] = datetime.now().isoformat()
    _flush(session_id)


def update_step(session_id: str, step_name: str, data: dict):
    if session_id not in _active_sessions:
        return
    session = _active_sessions[session_id]
    existing = session["trace"]["steps"].get(step_name, {})
    existing.update(data)
    session["trace"]["steps"][step_name] = existing
    session["trace"]["last_updated"] = datetime.now().isoformat()
    _flush(session_id)


def get_session_path(session_id: str) -> Optional[str]:
    if session_id in _active_sessions:
        return _active_sessions[session_id]["path"]
    return None


def get_step_data(session_id: str, step_name: str) -> Optional[dict]:
    if session_id not in _active_sessions:
        return None
    return _active_sessions[session_id]["trace"]["steps"].get(step_name)


def _flush(session_id: str):
    session = _active_sessions[session_id]
    with open(session["path"], "w", encoding="utf-8") as f:
        json.dump(session["trace"], f, indent=2, ensure_ascii=False, default=str)
