from __future__ import annotations

import asyncio
import json
import os
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from langchain_core.messages import BaseMessage, HumanMessage, messages_from_dict, messages_to_dict

from agents.registry.loader import AgentConfig


@dataclass(slots=True)
class SessionRecord:
    message: BaseMessage
    timestamp_utc: str


class InMemoryContextStore:
    """Thread-safe in-memory context storage for local development."""

    def __init__(self) -> None:
        self._sessions: dict[str, list[SessionRecord]] = {}
        self._compression_counts: dict[str, int] = {}
        self._lock = threading.RLock()

    def add_message(self, session_id: str, message: BaseMessage) -> None:
        with self._lock:
            records = self._sessions.setdefault(session_id, [])
            records.append(
                SessionRecord(
                    message=message,
                    timestamp_utc=datetime.now(UTC).isoformat(),
                )
            )

    def get_records(self, session_id: str) -> list[SessionRecord]:
        with self._lock:
            return list(self._sessions.get(session_id, []))

    def replace_records(self, session_id: str, records: list[SessionRecord]) -> None:
        with self._lock:
            self._sessions[session_id] = list(records)

    def clear_session(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)
            self._compression_counts.pop(session_id, None)

    def increment_compression(self, session_id: str) -> None:
        with self._lock:
            self._compression_counts[session_id] = self._compression_counts.get(session_id, 0) + 1

    def get_compression_count(self, session_id: str) -> int:
        with self._lock:
            return self._compression_counts.get(session_id, 0)


class RedisContextStore:
    """Redis-backed context store mirroring the in-memory interface."""

    def __init__(self, redis_url: str):
        try:
            import redis  # type: ignore
        except ImportError as exc:
            raise RuntimeError("redis package is required for RedisContextStore") from exc

        self._client = redis.Redis.from_url(redis_url, decode_responses=True)

    def _messages_key(self, session_id: str) -> str:
        return f"context:messages:{session_id}"

    def _compression_key(self, session_id: str) -> str:
        return f"context:compression:{session_id}"

    def add_message(self, session_id: str, message: BaseMessage) -> None:
        payload = {
            "timestamp_utc": datetime.now(UTC).isoformat(),
            "message": messages_to_dict([message])[0],
        }
        self._client.rpush(self._messages_key(session_id), json.dumps(payload))

    def get_records(self, session_id: str) -> list[SessionRecord]:
        rows = self._client.lrange(self._messages_key(session_id), 0, -1)
        records: list[SessionRecord] = []
        for row in rows:
            payload = json.loads(row)
            msg = messages_from_dict([payload["message"]])[0]
            records.append(
                SessionRecord(
                    message=msg,
                    timestamp_utc=str(payload.get("timestamp_utc", datetime.now(UTC).isoformat())),
                )
            )
        return records

    def replace_records(self, session_id: str, records: list[SessionRecord]) -> None:
        key = self._messages_key(session_id)
        self._client.delete(key)
        if not records:
            return
        serialized = [
            json.dumps(
                {
                    "timestamp_utc": record.timestamp_utc,
                    "message": messages_to_dict([record.message])[0],
                }
            )
            for record in records
        ]
        self._client.rpush(key, *serialized)

    def clear_session(self, session_id: str) -> None:
        self._client.delete(self._messages_key(session_id))
        self._client.delete(self._compression_key(session_id))

    def increment_compression(self, session_id: str) -> None:
        self._client.incr(self._compression_key(session_id))

    def get_compression_count(self, session_id: str) -> int:
        value = self._client.get(self._compression_key(session_id))
        return int(value) if value is not None else 0


def _is_pinned(message: BaseMessage) -> bool:
    metadata = {}
    if isinstance(getattr(message, "additional_kwargs", None), dict):
        metadata = message.additional_kwargs.get("metadata", {})
    return bool(isinstance(metadata, dict) and metadata.get("pinned") is True)


def _is_system(message: BaseMessage) -> bool:
    return str(getattr(message, "type", "")).lower() == "system"


def _approx_tokens(text: str) -> int:
    return max(1, (len(text) + 3) // 4)


class ContextManager:
    """Session context manager with token-budgeted retrieval and compression."""

    def __init__(self, llm_summarizer: Any | None = None) -> None:
        backend = os.getenv("CONTEXT_BACKEND", "memory").strip().lower()
        if backend == "redis":
            redis_url = os.getenv("CONTEXT_REDIS_URL", "redis://localhost:6379/0")
            self._store = RedisContextStore(redis_url)
        else:
            self._store = InMemoryContextStore()
        self._llm_summarizer = llm_summarizer

    def add_message(self, session_id: str, message: BaseMessage) -> None:
        self._store.add_message(session_id, message)

    def get_context(self, session_id: str, agent_config: AgentConfig) -> list[BaseMessage]:
        records = self._store.get_records(session_id)
        if not records:
            return []

        model_name = self._resolve_model_name(agent_config)
        budget = int(agent_config.max_context_tokens)

        system_records = [record for record in records if _is_system(record.message)]
        pinned_records = [
            record for record in records if _is_pinned(record.message) and not _is_system(record.message)
        ]

        selected: list[SessionRecord] = []
        selected.extend(system_records)
        for record in pinned_records:
            if record not in selected:
                selected.append(record)

        used_tokens = sum(self._count_message_tokens(record.message, model_name) for record in selected)
        if used_tokens > budget:
            return [record.message for record in selected]

        for record in reversed(records):
            if record in selected:
                continue
            message_tokens = self._count_message_tokens(record.message, model_name)
            if used_tokens + message_tokens > budget:
                continue
            selected.append(record)
            used_tokens += message_tokens

        ordered = sorted(selected, key=lambda item: item.timestamp_utc)
        return [record.message for record in ordered]

    async def summarise_and_compress(self, session_id: str) -> None:
        records = self._store.get_records(session_id)
        if len(records) < 4:
            return

        model_name = os.getenv("DEFAULT_AGENT_MODEL", "")
        token_count = sum(self._count_message_tokens(record.message, model_name) for record in records)
        threshold = int(float(os.getenv("CONTEXT_DEFAULT_MAX_TOKENS", "8192")) * 0.8)
        if token_count <= threshold:
            return

        system_records = [record for record in records if _is_system(record.message)]
        pinned_records = [record for record in records if _is_pinned(record.message)]
        compressible = [
            record
            for record in records
            if not _is_system(record.message) and not _is_pinned(record.message)
        ]
        if len(compressible) < 2:
            return

        split_index = max(1, len(compressible) // 2)
        to_compress = compressible[:split_index]
        to_keep = compressible[split_index:]

        summary_text = await self._summarize_messages([record.message for record in to_compress])
        summary_message = HumanMessage(
            content=f"[COMPRESSED_CONTEXT] {summary_text}",
            additional_kwargs={"metadata": {"compressed": True, "pinned": True}},
        )
        summary_record = SessionRecord(
            message=summary_message,
            timestamp_utc=datetime.now(UTC).isoformat(),
        )

        new_records = list(system_records)
        for record in pinned_records:
            if record not in new_records:
                new_records.append(record)
        new_records.append(summary_record)
        for record in to_keep:
            if record not in new_records:
                new_records.append(record)

        new_records_sorted = sorted(new_records, key=lambda item: item.timestamp_utc)
        self._store.replace_records(session_id, new_records_sorted)
        self._store.increment_compression(session_id)

    def clear_session(self, session_id: str) -> None:
        self._store.clear_session(session_id)

    def get_session_stats(self, session_id: str) -> dict[str, Any]:
        records = self._store.get_records(session_id)
        model_name = os.getenv("DEFAULT_AGENT_MODEL", "")
        token_count = sum(self._count_message_tokens(record.message, model_name) for record in records)
        oldest = min((record.timestamp_utc for record in records), default=None)
        return {
            "token_count": token_count,
            "message_count": len(records),
            "compression_count": self._store.get_compression_count(session_id),
            "oldest_message_ts": oldest,
        }

    def build_runtime_context(self, request_id: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "request_id": request_id,
            "metadata": metadata or {},
        }

    def build_trace_url(self, request_id: str) -> str | None:
        return None

    def _count_message_tokens(self, message: BaseMessage, model_name: str) -> int:
        content = str(getattr(message, "content", ""))
        try:
            import tiktoken  # type: ignore

            if model_name:
                encoding = tiktoken.encoding_for_model(model_name)
            else:
                encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(content))
        except Exception:
            return _approx_tokens(content)

    @staticmethod
    def _resolve_model_name(agent_config: AgentConfig) -> str:
        candidate = getattr(agent_config, "model_name", None)
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
        return os.getenv("DEFAULT_AGENT_MODEL", "").strip()

    async def _summarize_messages(self, messages: list[BaseMessage]) -> str:
        if callable(self._llm_summarizer):
            result = self._llm_summarizer(messages)
            if asyncio.iscoroutine(result):
                result = await result
            return str(result)

        flattened = "\n".join(str(getattr(message, "content", "")) for message in messages)
        if len(flattened) <= 1200:
            return flattened
        return f"{flattened[:1200]}..."
