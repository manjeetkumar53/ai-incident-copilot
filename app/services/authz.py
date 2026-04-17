from __future__ import annotations

from fastapi import HTTPException, Request


def require_role(request: Request, allowed_roles: set[str]) -> str:
    role = request.headers.get("X-Role", "").strip().lower()
    if role not in allowed_roles:
        allowed = ", ".join(sorted(allowed_roles))
        raise HTTPException(status_code=403, detail=f"Role not allowed. Expected one of: {allowed}")
    return role
