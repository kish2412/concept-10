from __future__ import annotations

import os
from typing import Any

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

_INSTRUMENTATION_APP: Any | None = None
_IS_CONFIGURED = False


def bind_fastapi_app(app: Any) -> None:
    global _INSTRUMENTATION_APP
    _INSTRUMENTATION_APP = app


def configure_otel(service_name: str) -> None:
    """Configure OTEL tracing and instrument the bound FastAPI app."""
    global _IS_CONFIGURED
    if _IS_CONFIGURED:
        return

    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": os.getenv("SERVICE_VERSION", "0.1.0"),
            "deployment.environment": os.getenv("APP_ENV", "local"),
            "agent.framework": "langgraph",
        }
    )

    provider = TracerProvider(resource=resource)
    if endpoint:
        exporter = OTLPSpanExporter(endpoint=endpoint)
        provider.add_span_processor(BatchSpanProcessor(exporter))

    trace.set_tracer_provider(provider)

    if _INSTRUMENTATION_APP is not None:
        FastAPIInstrumentor().instrument_app(_INSTRUMENTATION_APP)

    _IS_CONFIGURED = True
