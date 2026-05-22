"""Backend client for the Streamlit UI.

Two implementations behind one interface so the same UI runs either way:

  HttpClient   — calls the FastAPI backend over HTTP (local two-process setup).
  LocalClient  — runs the pipeline in-process by calling the backend endpoint
                 functions directly (single-process hosting, e.g. Streamlit
                 Community Cloud, where there is no separate backend).

Selection: set NLSQL_INPROCESS=1 to use the in-process client; otherwise HTTP.
Backend modules are imported lazily so HTTP-only runs never import them.
"""
from __future__ import annotations

import os
from typing import Dict, Optional

import requests


class HttpClient:
    in_process = False

    def __init__(self, base: str):
        self.base = base

    def get(self, path: str, **params) -> Optional[Dict]:
        try:
            return requests.get(f"{self.base}{path}", params=params, timeout=15).json()
        except requests.RequestException:
            return None

    def post(self, path: str, payload: Dict, timeout: int = 120) -> Dict:
        try:
            resp = requests.post(f"{self.base}{path}", json=payload, timeout=timeout)
            try:
                return resp.json()
            except ValueError:
                # Backend returned non-JSON (e.g. a 500 plain-text error)
                snippet = resp.text[:300] if resp.text else "empty response"
                return {"ok": False, "error": f"Backend error (HTTP {resp.status_code}): {snippet}"}
        except requests.RequestException as e:
            return {"ok": False, "error": f"Cannot reach backend at {self.base}: {e}"}


class LocalClient:
    in_process = True

    def get(self, path: str, **params) -> Optional[Dict]:
        from app.backend import main
        if path == "/health":
            return main.health()
        if path == "/schema":
            return main.schema()
        if path == "/audit":
            return main.audit_endpoint(limit=int(params.get("limit", 20)),
                                       user_id=params.get("user_id"))
        return None

    def post(self, path: str, payload: Dict, timeout: int = 120) -> Dict:
        from app.backend import main
        try:
            if path == "/plan":
                return main.plan_endpoint(main.PlanRequest(**payload)).model_dump()
            if path == "/generate":
                return main.generate_endpoint(main.GenerateRequest(**payload)).model_dump()
            if path == "/run":
                return main.run_endpoint(main.RunRequest(**payload)).model_dump()
        except Exception as e:
            return {"ok": False, "error": str(e)}
        return {"ok": False, "error": f"unknown path {path}"}


def get_client():
    if os.getenv("NLSQL_INPROCESS", "").lower() in ("1", "true", "yes"):
        return LocalClient()
    return HttpClient(os.getenv("BACKEND_URL", "http://127.0.0.1:8000"))


def ensure_seeded() -> None:
    """No-op: data now comes live from the OpenMetadata API. No seeding needed."""
    pass
