from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import jwt

UNAUTHORIZED_MESSAGE = "Unauthorized"


@dataclass(frozen=True)
class AuthContext:
    user_id: str
    tenant_id: Optional[str] = None


class AuthService:
    """JWT validation stub — Zitadel integration in Phase 3."""

    def __init__(self, secret: str, algorithm: str = "HS256") -> None:
        self.secret = secret
        self.algorithm = algorithm

    def issue_token(self, user_id: str, tenant_id: Optional[str] = None) -> str:
        payload: dict[str, str] = {"sub": user_id}
        if tenant_id:
            payload["tenant_id"] = tenant_id
        return jwt.encode(payload, self.secret, algorithm=self.algorithm)

    def validate(self, token: Optional[str]) -> Optional[AuthContext]:
        if not token:
            return None
        try:
            payload = jwt.decode(token, self.secret, algorithms=[self.algorithm])
        except jwt.PyJWTError:
            return None
        user_id = payload.get("sub")
        if not user_id:
            return None
        return AuthContext(user_id=user_id, tenant_id=payload.get("tenant_id"))

    def require_auth(self, token: Optional[str]) -> AuthContext:
        ctx = self.validate(token)
        if ctx is None:
            raise PermissionError(UNAUTHORIZED_MESSAGE)
        return ctx

    def validate_tenant_access(self, ctx: AuthContext, requested_tenant_id: str) -> bool:
        if ctx.tenant_id is None:
            return True
        return ctx.tenant_id == requested_tenant_id
