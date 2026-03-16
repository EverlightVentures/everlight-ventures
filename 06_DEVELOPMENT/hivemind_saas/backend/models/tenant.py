"""
SQLAlchemy ORM models for multi-tenant data isolation.
Row-Level Security is enforced at the DB level via rls_policies.sql.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, Integer, Float, ForeignKey, Text, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from core.database import Base


def _now():
    return datetime.now(timezone.utc)


def _uuid():
    return str(uuid.uuid4())


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    plan_tier: Mapped[str] = mapped_column(String(50), default="spark")
    stripe_customer_id: Mapped[str] = mapped_column(String(255), nullable=True)
    stripe_subscription_id: Mapped[str] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    users: Mapped[list["User"]] = relationship("User", back_populates="tenant")
    integrations: Mapped[list["Integration"]] = relationship("Integration", back_populates="tenant")
    sessions: Mapped[list["HiveSession"]] = relationship("HiveSession", back_populates="tenant")


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(50), default="member")  # admin | member | viewer
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="users")


class Integration(Base):
    __tablename__ = "integrations"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id"), nullable=False)
    provider: Mapped[str] = mapped_column(String(100), nullable=False)  # anthropic, slack, etc.
    credential_type: Mapped[str] = mapped_column(String(50), nullable=False)  # api_key | oauth
    encrypted_credentials: Mapped[str] = mapped_column(Text, nullable=False)  # Fernet encrypted JSON
    scopes: Mapped[list] = mapped_column(JSON, default=list)
    label: Mapped[str] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="integrations")


class HiveSession(Base):
    __tablename__ = "hive_sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id"), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    agents: Mapped[list] = mapped_column(JSON, default=list)
    mode: Mapped[str] = mapped_column(String(50), default="full")
    status: Mapped[str] = mapped_column(String(50), default="queued")  # queued|running|completed|failed
    results: Mapped[dict] = mapped_column(JSON, nullable=True)
    mindmap_data: Mapped[dict] = mapped_column(JSON, nullable=True)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    duration_s: Mapped[float] = mapped_column(Float, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="sessions")
    messages: Mapped[list["Message"]] = relationship("Message", back_populates="session")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(String, ForeignKey("hive_sessions.id"), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String, nullable=False)  # denormalized for RLS
    role: Mapped[str] = mapped_column(String(50), nullable=False)  # user | claude | gemini | codex | perplexity
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    session: Mapped["HiveSession"] = relationship("HiveSession", back_populates="messages")


class SlackAuditLog(Base):
    __tablename__ = "slack_audit_log"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String, nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    channel: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=True)
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
