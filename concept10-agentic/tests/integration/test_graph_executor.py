from __future__ import annotations

import pytest

from core.context.manager import ContextManager
from core.graph.executor import GraphExecutor
from core.schemas.base import AgentStatus


@pytest.mark.asyncio
async def test_graph_executor_full_run_with_mock_llm(mock_registry, sample_agent_request, mock_llm, monkeypatch):
    class FakeCompiledGraph:
        async def astream(self, state, config, stream_mode):
            llm_callable = state["context"]["llm_callable"]
            llm_result = await llm_callable(prompt="mock prompt", state=state)

            yield {
                "llm_call": {
                    "tool_results": {"llm_call": llm_result},
                    "current_node": "llm_call",
                    "trace_steps": [{"node": "llm_call"}],
                }
            }

            yield {
                "tool_call_0": {
                    "tool_results": {
                        "llm_call": llm_result,
                        "test-utility": {"status": "executed", "tool_id": "test-utility"},
                    },
                    "current_node": "tool:test-utility",
                    "trace_steps": [{"node": "tool:test-utility"}],
                }
            }

            yield {
                "final_output": {
                    "final_output": {
                        "agent_id": state["agent_id"],
                        "request_id": state["request_id"],
                        "llm_output": llm_result,
                        "tool_results": {
                            "llm_call": llm_result,
                            "test-utility": {"status": "executed", "tool_id": "test-utility"},
                        },
                    },
                    "error": None,
                    "current_node": "final_output",
                    "trace_steps": [{"node": "final_output"}],
                }
            }

    context_manager = ContextManager()
    executor = GraphExecutor(registry=mock_registry, context_manager=context_manager)
    monkeypatch.setattr(executor.graph_builder, "build_for_agent", lambda _cfg: FakeCompiledGraph())

    request = sample_agent_request.model_copy(
        update={
            "payload": {
                **sample_agent_request.payload,
                "tool_queue": ["test-utility"],
                "llm_callable": mock_llm,
            }
        }
    )

    response = await executor.execute(request)

    assert response.status == AgentStatus.success
    assert response.agent_id == "test-orchestrator"
    assert "llm_output" in response.output
    assert response.output["llm_output"]["response"] == "mocked llm response"
    assert "test-utility" in response.output["tool_results"]
    assert mock_llm.route.called
