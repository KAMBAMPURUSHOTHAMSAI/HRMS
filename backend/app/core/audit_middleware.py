
import logging
import re

import jwt
from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.models.user import User
from app.models.user_role import UserRole
from app.services.audit_service import record_audit_event


logger = logging.getLogger("hrms.audit")

MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

ENTITY_NAMES = {
    "employees": "EMPLOYEE",
    "users": "USER",
    "departments": "DEPARTMENT",
    "designations": "DESIGNATION",
    "attendance": "ATTENDANCE",
    "leaves": "LEAVE_REQUEST",
    "leave-types": "LEAVE_TYPE",
    "payroll": "PAYROLL",
    "salary-slips": "SALARY_SLIP",
    "documents": "EMPLOYEE_DOCUMENT",
    "notifications": "NOTIFICATION",
    "roles": "ROLE",
    "audit-logs": "AUDIT_LOG",
}

SPECIAL_ROUTES = {
    "check-in": "CHECK_IN",
    "check-out": "CHECK_OUT",
    "approve": "APPROVE",
    "reject": "REJECT",
    "correction": "CORRECT",
    "lock": "LOCK",
    "simulate-credit": "SIMULATE_CREDIT",
    "retry": "RETRY",
    "read-all": "MARK_ALL_READ",
}


def _entity_type(route_path: str) -> str:
    path = route_path.lower()

    if "/roles/{role_id}/users/" in path:
        return "USER_ROLE"

    if "/roles/{role_id}/permissions/" in path:
        return "ROLE_PERMISSION"

    if "/roles/permissions" in path:
        return "PERMISSION"

    if "/notifications/admin/email-logs" in path:
        return "EMAIL_DELIVERY_LOG"

    parts = [
        part for part in path.strip("/").split("/")
        if part and part not in {"api", "v1"}
    ]

    if not parts:
        return "API_REQUEST"

    return ENTITY_NAMES.get(parts[0], parts[0].upper())


def _action(method: str, route_path: str) -> str:
    path = route_path.lower()
    last_segment = path.rstrip("/").split("/")[-1]

    for segment, name in SPECIAL_ROUTES.items():
        if last_segment == segment:
            return name

    if "/roles/{role_id}/users/" in path:
        return "ASSIGN" if method == "POST" else "REMOVE"

    if "/roles/{role_id}/permissions/" in path:
        return "ASSIGN" if method == "POST" else "REMOVE"

    if method == "POST":
        if last_segment == "generate":
            return "GENERATE"
        return "CREATE"

    if method == "PATCH":
        return "UPDATE"

    if method == "PUT":
        return "REPLACE"

    if method == "DELETE":
        return "DELETE"

    return method


def _entity_id(request: Request) -> str | None:
    # Record an ID available in the URL without reading request bodies.
    candidates = re.findall(r"/(\d+)(?=/|$)", request.url.path)

    if candidates:
        return candidates[-1]

    return None


class AuditMutationMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next,
    ) -> Response:
        response = await call_next(request)

        path = request.url.path

        if request.method not in MUTATING_METHODS:
            return response

        if not path.startswith("/api/v1/"):
            return response

        # Roles endpoints record their own more-specific audit events.
        if path.startswith("/api/v1/roles"):
            return response

        # Log only successful responses.
        if not 200 <= response.status_code < 300:
            return response

        # Do not log login attempts or authentication payloads.
        if path.rstrip("/") == "/api/v1/auth/login":
            return response

        authorization = request.headers.get("authorization", "")
        scheme, _, token = authorization.partition(" ")

        if scheme.lower() != "bearer" or not token:
            return response

        try:
            payload = decode_access_token(token)
            user_id = int(payload["sub"])
        except (
            jwt.PyJWTError,
            KeyError,
            TypeError,
            ValueError,
        ):
            return response

        db = SessionLocal()

        try:
            actor = db.scalar(
                select(User)
                .options(
                    selectinload(User.user_roles)
                    .selectinload(UserRole.role)
                )
                .where(
                    User.id == user_id,
                    User.is_active.is_(True),
                )
            )

            if actor is None:
                return response

            route = request.scope.get("route")
            route_path = getattr(
                route,
                "path",
                request.url.path,
            )

            entity_type = _entity_type(route_path)
            action = _action(request.method, route_path)

            record_audit_event(
                db,
                action=action,
                entity_type=entity_type,
                entity_id=_entity_id(request),
                description=(
                    f"{action} request completed successfully: "
                    f"{route_path}"
                ),
                actor=actor,
                details={
                    "method": request.method,
                    "route": route_path,
                    "status_code": response.status_code,
                },
                request=request,
            )

            db.commit()

        except Exception:
            db.rollback()
            # Audit failure should not convert a completed business
            # response into a failed API response.
            logger.exception(
                "Could not record an audit event for %s %s",
                request.method,
                path,
            )

        finally:
            db.close()

        return response
