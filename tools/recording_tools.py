from typing import Any, Dict


def recording_tools_registration(mcp, shared_state):
    """
    Registers small helper tools to inspect/clear recorded actions.
    """

    @mcp.tool()
    async def get_recorded_actions() -> Dict[str, Any]:
        if not getattr(shared_state, "action_recorder", None):
            return {
                "content": [{
                    "type": "text",
                    "text": "Error: action recorder not available in shared_state."
                }]
            }
        actions = shared_state.action_recorder.list_actions()
        return {
            "content": [{
                "type": "text",
                "text": str(actions)
            }]
        }

    @mcp.tool()
    async def clear_recorded_actions() -> Dict[str, Any]:
        if not getattr(shared_state, "action_recorder", None):
            return {
                "content": [{
                    "type": "text",
                    "text": "Error: action recorder not available in shared_state."
                }]
            }
        shared_state.action_recorder.clear()
        return {
            "content": [{
                "type": "text",
                "text": "Cleared recorded actions and cached locators."
            }]
        }

