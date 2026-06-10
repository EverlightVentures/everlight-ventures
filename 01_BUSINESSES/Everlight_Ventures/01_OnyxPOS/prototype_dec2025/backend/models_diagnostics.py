"""
Diagnostics & Event Logging Models
For self-diagnosing, supportless POS system
"""
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Text, DateTime, JSON,
    ForeignKey, Index, Boolean
)
from sqlalchemy.ext.declarative import declarative_base
from models import Base
import uuid


def generate_uuid():
    """Generate UUID as string"""
    return str(uuid.uuid4())


class EventLog(Base):
    """
    Comprehensive event logging for diagnostics
    Every important action gets logged here
    """
    __tablename__ = "event_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), index=True)

    # Event details
    event_type = Column(String(50), nullable=False, index=True)  # login, sale, sync, error, etc.
    event_category = Column(String(50), nullable=False, index=True)  # auth, transaction, inventory, system
    severity = Column(String(20), default="info")  # info, warning, error, critical

    # What happened
    message = Column(Text, nullable=False)
    error_code = Column(String(50), index=True)  # Structured error codes like "INV-001", "SYNC-402"

    # Context
    context_data = Column(JSON)  # Store any relevant data (transaction_id, item_id, etc.)
    stack_trace = Column(Text)  # For errors
    request_url = Column(String(500))
    request_method = Column(String(10))
    ip_address = Column(String(50))
    user_agent = Column(String(500))

    # Resolution tracking
    resolved = Column(Boolean, default=False)
    resolution_note = Column(Text)
    resolved_at = Column(DateTime)
    resolved_by = Column(String(36))  # user_id or "AI" or "auto"

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Constraints
    __table_args__ = (
        Index("idx_event_tenant_type", "tenant_id", "event_type"),
        Index("idx_event_tenant_severity", "tenant_id", "severity"),
        Index("idx_event_tenant_created", "tenant_id", "created_at"),
        Index("idx_event_error_code", "error_code"),
    )

    def __repr__(self):
        return f"<EventLog {self.event_type} {self.severity} {self.created_at}>"


class HealthCheck(Base):
    """
    System health monitoring
    Tracks various system metrics for diagnostics
    """
    __tablename__ = "health_checks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    # Check details
    check_type = Column(String(50), nullable=False)  # database, queue, payment_gateway, sync, printer
    status = Column(String(20), nullable=False)  # healthy, degraded, unhealthy

    # Metrics
    response_time_ms = Column(Integer)
    error_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)

    # Details
    details = Column(JSON)  # Store check-specific data
    last_error = Column(Text)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    __table_args__ = (
        Index("idx_health_tenant_type", "tenant_id", "check_type"),
        Index("idx_health_tenant_status", "tenant_id", "status"),
    )

    def __repr__(self):
        return f"<HealthCheck {self.check_type} {self.status}>"


class SupportTicket(Base):
    """
    Support tickets (created when AI can't solve the issue)
    """
    __tablename__ = "support_tickets"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), index=True)

    # Ticket details
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    priority = Column(String(20), default="normal")  # low, normal, high, urgent
    status = Column(String(50), default="open")  # open, in_progress, waiting_customer, resolved, closed
    category = Column(String(50))  # billing, technical, feature_request, bug

    # AI attempted resolution
    ai_attempted = Column(Boolean, default=False)
    ai_suggested_fixes = Column(JSON)  # List of fixes AI tried
    ai_confidence_score = Column(Integer)  # 0-100, how confident AI was

    # Diagnostics attached
    diagnostic_bundle_url = Column(Text)  # S3/storage URL for diagnostic bundle
    error_codes = Column(JSON)  # List of error codes related to this ticket
    event_log_snapshot = Column(JSON)  # Last 50 events

    # Assignment
    assigned_to = Column(String(50))  # "AI", "L2_contractor", "founder", email
    assigned_at = Column(DateTime)

    # Resolution
    resolution = Column(Text)
    resolved_at = Column(DateTime)
    customer_satisfied = Column(Boolean)

    # SLA tracking
    plan_tier = Column(String(50))  # Copy of tenant's tier at time of ticket
    target_response_hours = Column(Integer)
    first_response_at = Column(DateTime)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_ticket_tenant_status", "tenant_id", "status"),
        Index("idx_ticket_priority", "priority"),
        Index("idx_ticket_assigned", "assigned_to"),
    )

    def __repr__(self):
        return f"<SupportTicket #{self.id[:8]} {self.status}>"

    def is_sla_breached(self):
        """Check if SLA response time was breached"""
        if not self.target_response_hours or not self.first_response_at:
            return False

        time_to_response = (self.first_response_at - self.created_at).total_seconds() / 3600
        return time_to_response > self.target_response_hours


class DiagnosticReport(Base):
    """
    Diagnostic bundles created on-demand
    Contains snapshot of system state for troubleshooting
    """
    __tablename__ = "diagnostic_reports"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"))

    # Report details
    trigger = Column(String(100))  # manual, auto_error, support_request

    # Captured data
    event_logs = Column(JSON)  # Last 100 events
    health_checks = Column(JSON)  # Current health status
    system_info = Column(JSON)  # Version, environment, etc.
    tenant_info = Column(JSON)  # Plan, limits, usage
    error_summary = Column(JSON)  # Summary of recent errors

    # Storage
    full_report_url = Column(Text)  # S3/storage URL for complete report

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    def __repr__(self):
        return f"<DiagnosticReport {self.id[:8]} {self.trigger}>"


class AutomatedFix(Base):
    """
    Track automated fixes attempted by the system
    """
    __tablename__ = "automated_fixes"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    event_log_id = Column(String(36), ForeignKey("event_logs.id", ondelete="SET NULL"))

    # Fix details
    fix_type = Column(String(100), nullable=False)  # retry_sync, rebuild_index, clear_cache, etc.
    error_code = Column(String(50))  # What error this was fixing

    # Result
    success = Column(Boolean, default=False)
    result_message = Column(Text)
    execution_time_ms = Column(Integer)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    __table_args__ = (
        Index("idx_fix_tenant_type", "tenant_id", "fix_type"),
        Index("idx_fix_success", "success"),
    )

    def __repr__(self):
        return f"<AutomatedFix {self.fix_type} {'✓' if self.success else '✗'}>"
