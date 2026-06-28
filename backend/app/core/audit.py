"""
ARGUS Platform — Audit Log Middleware
Records all mutating API calls to the audit_logs table.
"""

from __future__ import annotations

import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.database.models import AuditLog
from app.database.session import get_db


AUDIT_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
SKIP_PATHS = {"/health", "/docs", "/redoc", "/openapi.json", "/ws"}


class AuditLogMiddleware(BaseHTTPMiddleware):
    """Logs all state-changing requests to the audit_logs table."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip non-mutating requests and excluded paths
        if request.method not in AUDIT_METHODS:
            return await call_next(request)

        for skip in SKIP_PATHS:
            if request.url.path.startswith(skip):
                return await call_next(request)

        start_time = time.perf_counter()
        response = await call_next(request)
        duration_ms = int((time.perf_counter() - start_time) * 1000)

        # Extract user from token if present (best-effort, no exception on failure)
        user_id: str | None = None
        try:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                from app.core.security import decode_access_token

                payload = decode_access_token(auth_header[7:])
                if payload:
                    # Look up user_id by username
                    from app.database.models import User

                    with get_db() as db:
                        user = db.query(User).filter(User.username == payload["sub"]).first()
                        if user:
                            user_id = user.id
        except Exception:
            pass  # Audit never blocks the request

        # Write audit entry asynchronously in background
        try:
            path_parts = request.url.path.strip("/").split("/")
            resource_type = path_parts[1] if len(path_parts) > 1 else None
            resource_id = path_parts[2] if len(path_parts) > 2 else None

            with get_db() as db:
                log_entry = AuditLog(
                    user_id=user_id,
                    action=f"{request.method} {request.url.path}",
                    resource_type=resource_type,
                    resource_id=resource_id,
                    details={
                        "status_code": response.status_code,
                        "duration_ms": duration_ms,
                        "query_params": dict(request.query_params),
                    },
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent"),
                )
                db.add(log_entry)
        except Exception:
            pass  # Audit never blocks the request

        return response
