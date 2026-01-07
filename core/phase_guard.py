from core.context import Context

def assert_phase(expected_phase: str):
    if Context.current_phase != expected_phase:
        raise RuntimeError(
            f"Phase violation: expected {expected_phase}, "
            f"got {Context.current_phase}"
        )
