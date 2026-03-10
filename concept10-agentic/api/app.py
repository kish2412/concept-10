from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from agents.registry.api import router as agents_router
from agents.registry.loader import AgentRegistry
from api.routers.orchestrate import router as orchestrate_router
from api.routers.specialist import router as specialist_router
from api.routers.utility import router as utility_router
from core.context.manager import ContextManager
from core.graph.executor import GraphExecutor
from observability.logging import configure_logging
from observability.middleware import LangSmithMiddleware, RequestTrackerMiddleware
from observability.otel import bind_fastapi_app, configure_otel

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    registry = AgentRegistry()
    await registry.load()
    context_manager = ContextManager()
    executor = GraphExecutor(registry=registry, context_manager=context_manager)

    app.state.registry = registry
    app.state.context_manager = context_manager
    app.state.executor = executor

    configure_otel(service_name="agent-orchestration-framework")
    yield


app = FastAPI(title="agent-orchestration-framework", lifespan=lifespan)
bind_fastapi_app(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(LangSmithMiddleware)
app.add_middleware(RequestTrackerMiddleware)

app.include_router(agents_router)
app.include_router(orchestrate_router)
app.include_router(utility_router)
app.include_router(specialist_router, prefix="/specialist", tags=["specialist"])


@app.exception_handler(ValueError)
async def value_error_handler(_request: Request, exc: ValueError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(KeyError)
async def key_error_handler(_request: Request, exc: KeyError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
