from phases.base import Phase
from agents.implementations.generation_agent import GenerationAgent

class GenerationPhase(Phase):
    name = "generation"
    agent_cls = GenerationAgent
