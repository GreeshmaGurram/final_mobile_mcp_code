class Phase:
    name: str
    agent_cls: type

    def __init__(self):
        if not self.name or not self.agent_cls:
            raise ValueError("Phase must define name and agent_cls")
