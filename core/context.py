class Context:
    """
    Holds the current execution phase for phase-guard assertions.
    Update `current_phase` whenever the workflow transitions between phases.
    """
    current_phase: str = ""

    @classmethod
    def set_phase(cls, phase: str) -> None:
        cls.current_phase = phase
