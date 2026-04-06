from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import decode_token
from models.tenant import Tenant, User

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class RequestContext:
    user: User
    tenant: Tenant


async def get_request_context(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> RequestContext:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    try:
        claims = decode_token(credentials.credentials)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    user = await db.scalar(
        select(User).where(
            User.id == str(claims.get("sub")),
            User.tenant_id == str(claims.get("tenant_id")),
            User.is_active.is_(True),
        )
    )
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    tenant = await db.scalar(
        select(Tenant).where(
            Tenant.id == user.tenant_id,
            Tenant.is_active.is_(True),
        )
    )
    if not tenant:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant not found")

    return RequestContext(user=user, tenant=tenant)


async def get_admin_context(context: RequestContext = Depends(get_request_context)) -> RequestContext:
    if context.user.role not in {"admin", "owner"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return context
