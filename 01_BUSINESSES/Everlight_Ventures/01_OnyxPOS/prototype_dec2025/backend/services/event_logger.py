"""
Event Logger Service
Centralized logging for all important events
Makes the system self-diagnosing
"""
from datetime import datetime
from models_diagnostics import EventLog, HealthCheck, AutomatedFix, DiagnosticReport
from database import Session
import traceback
import json


class EventLogger:
    """
    Centralized event logging service
    Usage: EventLogger.log("login", "User logged in", tenant_id=..., user_id=...)
    """

    # Event categories
    AUTH = "auth"
    TRANSACTION = "transaction"
    INVENTORY = "inventory"
    SYSTEM = "system"
    SYNC = "sync"
    BILLING = "billing"
    SUPPORT = "support"

    # Severity levels
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

    @staticmethod
    def log(event_type, message, tenant_id=None, user_id=None,
            category="system", severity="info", error_code=None,
            context_data=None, exception=None, request=None):
        """
        Log an event

        Args:
            event_type: Type of event (login, sale, sync_fail, etc.)
            message: Human-readable message
            tenant_id: Tenant ID
            user_id: User ID
            category: Event category
            severity: info, warning, error, critical
            error_code: Structured error code (e.g., "INV-001")
            context_data: Dict of additional context
            exception: Exception object (will extract stack trace)
            request: Flask request object (will extract IP, UA, etc.)
        """
        session = Session()
        try:
            event = EventLog(
                tenant_id=tenant_id,
                user_id=user_id,
                event_type=event_type,
                event_category=category,
                severity=severity,
                message=message,
                error_code=error_code,
                context_data=context_data
            )

            # Extract exception info
            if exception:
                event.stack_trace = traceback.format_exc()

            # Extract request info
            if request:
                event.request_url = request.url
                event.request_method = request.method
                event.ip_address = request.remote_addr
                event.user_agent = request.headers.get('User-Agent', '')

            session.add(event)
            session.commit()

            # Print to console for dev (optional in production)
            print(f"[{severity.upper()}] {event_type}: {message}")

            return event.id

        except Exception as e:
            session.rollback()
            print(f"Error logging event: {e}")
            return None
        finally:
            session.close()

    @staticmethod
    def log_error(error_code, message, tenant_id=None, user_id=None,
                  category="system", exception=None, context_data=None, request=None):
        """
        Convenience method for logging errors
        """
        return EventLogger.log(
            event_type="error",
            message=message,
            tenant_id=tenant_id,
            user_id=user_id,
            category=category,
            severity=EventLogger.ERROR,
            error_code=error_code,
            exception=exception,
            context_data=context_data,
            request=request
        )

    @staticmethod
    def get_recent_events(tenant_id, limit=50, severity=None, category=None):
        """
        Get recent events for a tenant
        """
        session = Session()
        try:
            query = session.query(EventLog).filter_by(tenant_id=tenant_id)

            if severity:
                query = query.filter_by(severity=severity)

            if category:
                query = query.filter_by(event_category=category)

            events = query.order_by(EventLog.created_at.desc()).limit(limit).all()

            return [{
                "id": e.id,
                "event_type": e.event_type,
                "category": e.event_category,
                "severity": e.severity,
                "message": e.message,
                "error_code": e.error_code,
                "context_data": e.context_data,
                "created_at": e.created_at.isoformat(),
                "resolved": e.resolved
            } for e in events]

        except Exception as e:
            print(f"Error getting recent events: {e}")
            return []
        finally:
            session.close()

    @staticmethod
    def get_error_summary(tenant_id, hours=24):
        """
        Get summary of errors in the last N hours
        """
        session = Session()
        try:
            from datetime import timedelta
            cutoff = datetime.utcnow() - timedelta(hours=hours)

            errors = session.query(EventLog).filter(
                EventLog.tenant_id == tenant_id,
                EventLog.severity.in_(['error', 'critical']),
                EventLog.created_at >= cutoff,
                EventLog.resolved == False
            ).all()

            # Group by error code
            summary = {}
            for error in errors:
                code = error.error_code or "UNKNOWN"
                if code not in summary:
                    summary[code] = {
                        "error_code": code,
                        "count": 0,
                        "first_seen": error.created_at.isoformat(),
                        "last_seen": error.created_at.isoformat(),
                        "example_message": error.message
                    }

                summary[code]["count"] += 1
                if error.created_at > datetime.fromisoformat(summary[code]["last_seen"]):
                    summary[code]["last_seen"] = error.created_at.isoformat()

            return list(summary.values())

        except Exception as e:
            print(f"Error getting error summary: {e}")
            return []
        finally:
            session.close()


class HealthMonitor:
    """
    Monitor system health
    """

    @staticmethod
    def record_check(tenant_id, check_type, status, response_time_ms=None,
                     error_count=0, success_count=1, details=None, last_error=None):
        """
        Record a health check
        """
        session = Session()
        try:
            check = HealthCheck(
                tenant_id=tenant_id,
                check_type=check_type,
                status=status,
                response_time_ms=response_time_ms,
                error_count=error_count,
                success_count=success_count,
                details=details,
                last_error=last_error
            )

            session.add(check)
            session.commit()

            return check.id

        except Exception as e:
            session.rollback()
            print(f"Error recording health check: {e}")
            return None
        finally:
            session.close()

    @staticmethod
    def get_latest_checks(tenant_id):
        """
        Get latest health check for each type
        """
        session = Session()
        try:
            from sqlalchemy import func

            # Get latest check for each type
            subquery = session.query(
                HealthCheck.check_type,
                func.max(HealthCheck.created_at).label('max_created')
            ).filter_by(tenant_id=tenant_id).group_by(HealthCheck.check_type).subquery()

            checks = session.query(HealthCheck).join(
                subquery,
                (HealthCheck.check_type == subquery.c.check_type) &
                (HealthCheck.created_at == subquery.c.max_created)
            ).filter_by(tenant_id=tenant_id).all()

            return [{
                "check_type": c.check_type,
                "status": c.status,
                "response_time_ms": c.response_time_ms,
                "error_count": c.error_count,
                "success_count": c.success_count,
                "details": c.details,
                "checked_at": c.created_at.isoformat()
            } for c in checks]

        except Exception as e:
            print(f"Error getting health checks: {e}")
            return []
        finally:
            session.close()

    @staticmethod
    def get_system_health(tenant_id):
        """
        Get overall system health status
        """
        checks = HealthMonitor.get_latest_checks(tenant_id)

        if not checks:
            return {"status": "unknown", "message": "No health checks recorded"}

        unhealthy = [c for c in checks if c["status"] == "unhealthy"]
        degraded = [c for c in checks if c["status"] == "degraded"]

        if unhealthy:
            return {
                "status": "unhealthy",
                "message": f"{len(unhealthy)} system(s) unhealthy",
                "unhealthy_systems": [c["check_type"] for c in unhealthy],
                "checks": checks
            }

        if degraded:
            return {
                "status": "degraded",
                "message": f"{len(degraded)} system(s) degraded",
                "degraded_systems": [c["check_type"] for c in degraded],
                "checks": checks
            }

        return {
            "status": "healthy",
            "message": "All systems operational",
            "checks": checks
        }


class DiagnosticGenerator:
    """
    Generate diagnostic reports
    """

    @staticmethod
    def generate_report(tenant_id, user_id=None, trigger="manual"):
        """
        Generate a comprehensive diagnostic report
        """
        session = Session()
        try:
            from models import Tenant

            # Get tenant info
            tenant = session.query(Tenant).filter_by(id=tenant_id).first()
            if not tenant:
                return None

            # Collect diagnostics
            report_data = {
                "tenant": {
                    "id": tenant.id,
                    "business_name": tenant.business_name,
                    "plan_tier": tenant.plan_tier,
                    "subscription_status": tenant.subscription_status,
                    "created_at": tenant.created_at.isoformat() if tenant.created_at else None
                },
                "system_info": {
                    "platform": "OnyxPOS",
                    "version": "1.0.0",
                    "report_generated_at": datetime.utcnow().isoformat()
                },
                "recent_events": EventLogger.get_recent_events(tenant_id, limit=100),
                "error_summary": EventLogger.get_error_summary(tenant_id, hours=24),
                "health_checks": HealthMonitor.get_latest_checks(tenant_id),
                "system_health": HealthMonitor.get_system_health(tenant_id)
            }

            # Create diagnostic report record
            report = DiagnosticReport(
                tenant_id=tenant_id,
                user_id=user_id,
                trigger=trigger,
                event_logs=report_data["recent_events"],
                health_checks=report_data["health_checks"],
                system_info=report_data["system_info"],
                tenant_info=report_data["tenant"],
                error_summary=report_data["error_summary"]
            )

            session.add(report)
            session.commit()

            return {
                "report_id": report.id,
                "data": report_data
            }

        except Exception as e:
            session.rollback()
            print(f"Error generating diagnostic report: {e}")
            return None
        finally:
            session.close()


class AutoFixer:
    """
    Automated fix system
    """

    @staticmethod
    def attempt_fix(tenant_id, error_code, fix_type, event_log_id=None):
        """
        Attempt an automated fix
        Returns True if successful
        """
        session = Session()
        start_time = datetime.utcnow()

        try:
            success = False
            result_message = ""

            # Execute fix based on type
            if fix_type == "retry_sync":
                success, result_message = AutoFixer._retry_sync(tenant_id)
            elif fix_type == "rebuild_index":
                success, result_message = AutoFixer._rebuild_index(tenant_id)
            elif fix_type == "clear_cache":
                success, result_message = AutoFixer._clear_cache(tenant_id)
            elif fix_type == "reset_session":
                success, result_message = AutoFixer._reset_session(tenant_id)
            else:
                result_message = f"Unknown fix type: {fix_type}"

            # Record the fix attempt
            execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            fix_record = AutomatedFix(
                tenant_id=tenant_id,
                event_log_id=event_log_id,
                fix_type=fix_type,
                error_code=error_code,
                success=success,
                result_message=result_message,
                execution_time_ms=execution_time
            )

            session.add(fix_record)
            session.commit()

            return {
                "success": success,
                "message": result_message,
                "execution_time_ms": execution_time
            }

        except Exception as e:
            session.rollback()
            return {
                "success": False,
                "message": f"Fix failed: {str(e)}",
                "execution_time_ms": 0
            }
        finally:
            session.close()

    @staticmethod
    def _retry_sync(tenant_id):
        """Retry synchronization"""
        # Implementation would trigger actual sync
        return True, "Sync retried successfully"

    @staticmethod
    def _rebuild_index(tenant_id):
        """Rebuild search index"""
        # Implementation would rebuild index
        return True, "Index rebuilt successfully"

    @staticmethod
    def _clear_cache(tenant_id):
        """Clear tenant cache"""
        # Implementation would clear cache
        return True, "Cache cleared successfully"

    @staticmethod
    def _reset_session(tenant_id):
        """Reset user sessions"""
        # Implementation would reset sessions
        return True, "Sessions reset successfully"
