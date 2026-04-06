from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


_STORE_PATH = Path("./capabilities") / "profiles.json"


def _ensure_store_file() -> None:
    _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not _STORE_PATH.exists():
        _STORE_PATH.write_text("{}", encoding="utf-8")


def _load_all() -> Dict[str, Dict[str, Any]]:
    _ensure_store_file()
    try:
        data = json.loads(_STORE_PATH.read_text(encoding="utf-8") or "{}")
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_all(data: Dict[str, Dict[str, Any]]) -> None:
    _ensure_store_file()
    _STORE_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def capability_store_registration(mcp):
    """
    Registers tools to save/list/delete capability profiles.
    Used by start_session(profile_name=...).
    """

    @mcp.tool()
    async def save_capability_profile(name: str, profile: Dict[str, Any]) -> Dict[str, Any]:
        if not name or not name.strip():
            return {"content": [{"type": "text", "text": "Error: name cannot be empty."}]}
        if not isinstance(profile, dict) or not profile:
            return {"content": [{"type": "text", "text": "Error: profile must be a non-empty JSON object."}]}

        all_profiles = _load_all()
        all_profiles[name.strip()] = profile
        _save_all(all_profiles)
        return {"content": [{"type": "text", "text": f"Saved capability profile '{name.strip()}'."}]}

    @mcp.tool()
    async def list_capability_profiles() -> Dict[str, Any]:
        all_profiles = _load_all()
        names = sorted(all_profiles.keys())
        return {"content": [{"type": "text", "text": f"Capability profiles: {names if names else '(none)'}"}]}

    @mcp.tool()
    async def delete_capability_profile(name: str) -> Dict[str, Any]:
        if not name or not name.strip():
            return {"content": [{"type": "text", "text": "Error: name cannot be empty."}]}
        all_profiles = _load_all()
        removed = all_profiles.pop(name.strip(), None)
        if removed is None:
            return {"content": [{"type": "text", "text": f"Profile '{name.strip()}' not found."}]}
        _save_all(all_profiles)
        return {"content": [{"type": "text", "text": f"Deleted capability profile '{name.strip()}'."}]}

