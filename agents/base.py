class BaseAgent:
    phase: str

    def run(self, prompt: str) -> str:
        raise NotImplementedError
