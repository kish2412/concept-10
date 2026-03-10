from __future__ import annotations

from collections import deque

from agents.registry.loader import AgentConfig, AgentRegistry


class AgentCategorizer:
    """Category-oriented query and dependency helpers for registered agents."""

    def __init__(self, registry: AgentRegistry):
        self.registry = registry

    def get_orchestrators(self) -> list[AgentConfig]:
        return self.registry.list_by_category("orchestrator")

    def get_utilities(self) -> list[AgentConfig]:
        return self.registry.list_by_category("utility")

    def get_specialists(self, domain: str) -> list[AgentConfig]:
        specialists = self.registry.list_by_category("specialist")
        normalized = domain.strip().lower()
        if not normalized:
            return specialists

        return [
            agent
            for agent in specialists
            if any(normalized in tag.lower() for tag in agent.tags)
        ]

    def build_execution_graph(self, orchestrator_id: str) -> dict[str, list[str]]:
        orchestrator = self.registry.get(orchestrator_id)
        if orchestrator.category != "orchestrator":
            raise ValueError(f"Agent '{orchestrator_id}' is not an orchestrator")

        graph: dict[str, list[str]] = {}
        queue = deque([orchestrator.id])
        visited: set[str] = set()

        while queue:
            current_id = queue.popleft()
            if current_id in visited:
                continue
            visited.add(current_id)

            current_agent = self.registry.get(current_id)
            graph[current_agent.id] = list(current_agent.tools)

            for dependency_id in current_agent.tools:
                if dependency_id not in visited:
                    # If an unknown tool id appears, AgentRegistry.get will raise and surface early.
                    self.registry.get(dependency_id)
                    queue.append(dependency_id)

        return graph
