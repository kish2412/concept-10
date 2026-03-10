from __future__ import annotations

import importlib
from typing import Any

from pydantic import BaseModel

from core.schemas.base import AgentRequest, AgentResponse


class SchemaValidator:
    """Loads and validates pydantic schemas from dotted module paths."""

    def __init__(self) -> None:
        self._cache: dict[str, type[BaseModel]] = {}

    def load_model(self, dotted_path: str) -> type[BaseModel]:
        if dotted_path in self._cache:
            return self._cache[dotted_path]

        module_path, _, attr_name = dotted_path.rpartition(".")
        if not module_path or not attr_name:
            raise ValueError(f"Invalid dotted path: '{dotted_path}'")

        module = importlib.import_module(module_path)
        model = getattr(module, attr_name, None)
        if model is None:
            raise ValueError(f"Model not found at dotted path: '{dotted_path}'")
        if not isinstance(model, type) or not issubclass(model, BaseModel):
            raise TypeError(f"Path does not resolve to a Pydantic model: '{dotted_path}'")

        self._cache[dotted_path] = model
        return model

    def validate_input(self, agent_config: Any, raw: dict[str, Any]) -> AgentRequest:
        model = self.load_model(agent_config.input_schema)
        validated = model.model_validate(raw)
        if not isinstance(validated, AgentRequest):
            raise TypeError(
                f"Input schema '{agent_config.input_schema}' must inherit AgentRequest"
            )
        return validated

    def validate_output(self, agent_config: Any, raw: dict[str, Any]) -> AgentResponse:
        model = self.load_model(agent_config.output_schema)
        validated = model.model_validate(raw)
        if not isinstance(validated, AgentResponse):
            raise TypeError(
                f"Output schema '{agent_config.output_schema}' must inherit AgentResponse"
            )
        return validated
