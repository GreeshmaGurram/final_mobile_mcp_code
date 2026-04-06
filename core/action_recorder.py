from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class RecordedAction:
    name: str
    params: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None


class ActionRecorder:
    """
    Small in-memory recorder used by MCP tools to:
    - remember element locators for later (tap/text/etc.)
    - record actions for debugging / test generation
    """

    def __init__(self) -> None:
        self._actions: List[RecordedAction] = []
        self._element_locators: Dict[str, Tuple[str, str]] = {}
        self._session: Dict[str, Any] = {"platform": None, "device": None, "app": None}

    def set_session(self, platform: str, device: Dict[str, Any], app: str) -> None:
        self._session = {"platform": platform, "device": device, "app": app}

    def register_element(self, element_id: str, strategy: str, selector: str) -> None:
        if element_id:
            self._element_locators[element_id] = (strategy, selector)

    def get_element_locator(self, element_id: str) -> Optional[Dict[str, str]]:
        loc = self._element_locators.get(element_id)
        if not loc:
            return None
        strategy, selector = loc
        return {"strategy": strategy, "selector": selector}

    def record(self, name: str, params: Dict[str, Any], result: Optional[Dict[str, Any]] = None) -> None:
        self._actions.append(RecordedAction(name=name, params=params or {}, result=result))

    def list_actions(self) -> List[Dict[str, Any]]:
        return [
            {"name": a.name, "params": a.params, "result": a.result}
            for a in self._actions
        ]

    def clear(self) -> None:
        self._actions.clear()
        self._element_locators.clear()
        self._session = {"platform": None, "device": None, "app": None}

    def get_session_info(self) -> Dict[str, Any]:
        return dict(self._session)

