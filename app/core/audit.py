"""Audit-logging dependency for write operations."""

import hashlib
import json
import logging
from datetime import datetime, timezone

from fastapi import Depends, Request

from app.api.deps import get_current_user_id

logger = logging.getLogger("app.audit")


async def audit_log(request: Request, user_id: str = Depends(get_current_user_id)) -> None:
    """
    Log every mutating request (POST / PUT / PATCH / DELETE) with
    user id, action, timestamp, and a SHA-256 hash of the payload.

    Attach as a route dependency on write endpoints::

        @router.post("", dependencies=[Depends(audit_log)])
    """
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return

    body_bytes = await request.body()
    payload_hash = hashlib.sha256(body_bytes).hexdigest() if body_bytes else "empty"

    logger.info(
        "AUDIT | user=%s action=%s %s | ts=%s | payload_hash=%s",
        user_id,
        request.method,
        request.url.path,
        datetime.now(timezone.utc).isoformat(),
        payload_hash,
    )
