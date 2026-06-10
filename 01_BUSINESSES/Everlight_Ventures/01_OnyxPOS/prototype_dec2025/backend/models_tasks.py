"""
Additional models for Task Management, Time Off, and Payroll Periods
"""
from sqlalchemy import Column, String, Text, DateTime, Numeric, Boolean, ForeignKey, Enum as SQLEnum, Index
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime
import uuid


def generate_uuid():
    return str(uuid.uuid4())


class PayrollPeriod(Base):
    """Track payroll periods and when they've been processed"""
    __tablename__ = "payroll_periods"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    # Period dates
    period_start = Column(DateTime, nullable=False, index=True)
    period_end = Column(DateTime, nullable=False, index=True)

    # Status and totals
    status = Column(String(20), default="pending")  # pending, processing, completed
    total_amount = Column(Numeric(12, 2), default=0)
    total_hours = Column(Numeric(10, 2), default=0)

    # Processing info
    run_date = Column(DateTime)
    run_by_user_id = Column(String(36), ForeignKey("users.id"))
    notes = Column(Text)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Constraints
    __table_args__ = (
        Index("idx_payroll_period_tenant", "tenant_id", "period_start", "period_end"),
    )

    def __repr__(self):
        return f"<PayrollPeriod {self.period_start} to {self.period_end}: ${self.total_amount}>"


class TimeOffRequest(Base):
    """Employee time-off requests"""
    __tablename__ = "time_off_requests"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Request details
    start_date = Column(DateTime, nullable=False, index=True)
    end_date = Column(DateTime, nullable=False)
    reason = Column(Text)
    request_type = Column(String(20), default="vacation")  # vacation, sick, personal, other

    # Status
    status = Column(String(20), default="pending")  # pending, approved, denied, cancelled
    approved_by_user_id = Column(String(36), ForeignKey("users.id"))
    approved_at = Column(DateTime)
    denial_reason = Column(Text)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="time_off_requests")
    approver = relationship("User", foreign_keys=[approved_by_user_id])

    # Constraints
    __table_args__ = (
        Index("idx_timeoff_user_tenant", "tenant_id", "user_id"),
        Index("idx_timeoff_dates", "start_date", "end_date"),
    )

    def __repr__(self):
        return f"<TimeOffRequest {self.user_id}: {self.start_date} to {self.end_date} ({self.status})>"


class Task(Base):
    """Task management system"""
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    # Task details
    title = Column(String(200), nullable=False)
    description = Column(Text)

    # Assignment
    assigned_to_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"))
    created_by_user_id = Column(String(36), ForeignKey("users.id"), nullable=False)

    # Status and priority
    status = Column(String(20), default="received")  # received, acknowledged, in_progress, complete, cancelled
    priority = Column(String(10), default="medium")  # low, medium, high

    # Dates
    due_date = Column(DateTime)
    acknowledged_at = Column(DateTime)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    assigned_to = relationship("User", foreign_keys=[assigned_to_user_id], backref="assigned_tasks")
    created_by = relationship("User", foreign_keys=[created_by_user_id], backref="created_tasks")

    # Constraints
    __table_args__ = (
        Index("idx_task_assigned_tenant", "tenant_id", "assigned_to_user_id"),
        Index("idx_task_status", "status", "due_date"),
    )

    def __repr__(self):
        return f"<Task {self.title}: {self.status}>"
