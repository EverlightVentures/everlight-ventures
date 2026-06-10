"""
Diagnostics & Support API
Self-diagnosing system for supportless scaling
"""
from flask import Blueprint, request, jsonify, g
from flask_jwt_extended import jwt_required
from services.event_logger import EventLogger, HealthMonitor, DiagnosticGenerator, AutoFixer
from models_diagnostics import SupportTicket
from database import Session
from datetime import datetime

diagnostics_bp = Blueprint("diagnostics", __name__)


# Error code documentation (shared by multiple endpoints)
ERROR_DOCS = {
    # Auth errors
    "AUTH-001": {
        "title": "Invalid credentials",
        "description": "The email or password provided is incorrect",
        "severity": "info",
        "user_action": "Please check your email and password and try again",
        "possible_fixes": ["reset_password"],
        "common_causes": ["Typo in password", "Wrong email address", "Caps lock enabled"]
    },
    "AUTH-002": {
        "title": "Session expired",
        "description": "Your session has expired and you need to log in again",
        "severity": "info",
        "user_action": "Please log in again",
        "possible_fixes": ["reset_session"],
        "common_causes": ["Inactivity timeout", "Browser cleared cookies"]
    },
    # Inventory errors
    "INV-001": {
        "title": "Insufficient stock",
        "description": "Cannot complete sale because item is out of stock",
        "severity": "warning",
        "user_action": "Receive more stock or remove item from sale",
        "possible_fixes": ["adjust_inventory"],
        "common_causes": ["Stock not received", "Inventory count incorrect"]
    },
    "INV-002": {
        "title": "Item not found",
        "description": "The requested item does not exist",
        "severity": "error",
        "user_action": "Check the item SKU and try again",
        "possible_fixes": ["rebuild_index"],
        "common_causes": ["Item deleted", "Wrong SKU", "Database sync issue"]
    },
    # Sync errors
    "SYNC-401": {
        "title": "Network connection lost",
        "description": "Unable to reach server",
        "severity": "critical",
        "user_action": "Check your internet connection",
        "possible_fixes": ["retry_sync"],
        "common_causes": ["WiFi disconnected", "Server maintenance", "Firewall blocking"]
    },
    "SYNC-402": {
        "title": "Sync conflict",
        "description": "Data conflict detected during sync",
        "severity": "warning",
        "user_action": "Automatic resolution attempted",
        "possible_fixes": ["retry_sync", "rebuild_index"],
        "common_causes": ["Concurrent edits", "Offline changes", "Clock skew"]
    },
    # Payment errors
    "PAY-001": {
        "title": "Payment declined",
        "description": "Card payment was declined",
        "severity": "warning",
        "user_action": "Try a different payment method",
        "possible_fixes": [],
        "common_causes": ["Insufficient funds", "Expired card", "Incorrect card details"]
    },
    "PAY-002": {
        "title": "Payment gateway timeout",
        "description": "Payment gateway did not respond in time",
        "severity": "error",
        "user_action": "Please try again",
        "possible_fixes": ["retry_payment"],
        "common_causes": ["Gateway maintenance", "Network issue", "High traffic"]
    },
    # System errors
    "SYS-001": {
        "title": "Database connection error",
        "description": "Cannot connect to database",
        "severity": "critical",
        "user_action": "Please wait while we resolve this",
        "possible_fixes": ["retry_sync"],
        "common_causes": ["Database maintenance", "Connection pool exhausted"]
    },
    "SYS-002": {
        "title": "Service unavailable",
        "description": "A required service is temporarily unavailable",
        "severity": "critical",
        "user_action": "Please try again in a few moments",
        "possible_fixes": ["retry_sync"],
        "common_causes": ["Service restart", "Deployment in progress"]
    }
}


@diagnostics_bp.route("/health", methods=["GET"])
@jwt_required()
def get_system_health():
    """
    Get overall system health for tenant
    Shows status of all subsystems
    """
    try:
        tenant_id = g.tenant_id
        health = HealthMonitor.get_system_health(tenant_id)

        return jsonify(health), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@diagnostics_bp.route("/recent-events", methods=["GET"])
@jwt_required()
def get_recent_events():
    """
    Get recent events for diagnostics
    Query params: ?limit=50&severity=error&category=transaction
    """
    try:
        tenant_id = g.tenant_id
        limit = request.args.get("limit", 50, type=int)
        severity = request.args.get("severity")
        category = request.args.get("category")

        events = EventLogger.get_recent_events(
            tenant_id,
            limit=min(limit, 200),  # Cap at 200
            severity=severity,
            category=category
        )

        return jsonify({
            "events": events,
            "count": len(events)
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@diagnostics_bp.route("/error-summary", methods=["GET"])
@jwt_required()
def get_error_summary():
    """
    Get summary of recent errors
    Query params: ?hours=24
    """
    try:
        tenant_id = g.tenant_id
        hours = request.args.get("hours", 24, type=int)

        summary = EventLogger.get_error_summary(tenant_id, hours=hours)

        return jsonify({
            "errors": summary,
            "period_hours": hours,
            "total_unique_errors": len(summary),
            "total_error_count": sum(e["count"] for e in summary)
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@diagnostics_bp.route("/generate-report", methods=["POST"])
@jwt_required()
def generate_diagnostic_report():
    """
    Generate comprehensive diagnostic report
    This is the "one-click diagnostic bundle" button
    """
    try:
        tenant_id = g.tenant_id
        user_id = g.user_id

        report = DiagnosticGenerator.generate_report(
            tenant_id=tenant_id,
            user_id=user_id,
            trigger="manual"
        )

        if not report:
            return jsonify({"error": "Failed to generate report"}), 500

        return jsonify({
            "message": "Diagnostic report generated",
            "report_id": report["report_id"],
            "data": report["data"]
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@diagnostics_bp.route("/auto-fix", methods=["POST"])
@jwt_required()
def attempt_auto_fix():
    """
    Attempt automated fix
    Request body: {
        "error_code": "SYNC-402",
        "fix_type": "retry_sync"
    }
    """
    try:
        tenant_id = g.tenant_id
        data = request.json

        error_code = data.get("error_code")
        fix_type = data.get("fix_type")

        if not error_code or not fix_type:
            return jsonify({"error": "error_code and fix_type required"}), 400

        result = AutoFixer.attempt_fix(
            tenant_id=tenant_id,
            error_code=error_code,
            fix_type=fix_type
        )

        if result["success"]:
            # Log the successful fix
            EventLogger.log(
                event_type="auto_fix_success",
                message=f"Automated fix applied: {fix_type}",
                tenant_id=tenant_id,
                category=EventLogger.SYSTEM,
                severity=EventLogger.INFO,
                context_data={
                    "fix_type": fix_type,
                    "error_code": error_code
                }
            )

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@diagnostics_bp.route("/support-ticket", methods=["POST"])
@jwt_required()
def create_support_ticket():
    """
    Create support ticket (when AI can't solve)
    Request body: {
        "title": "Cannot sync inventory",
        "description": "Detailed description...",
        "priority": "high",
        "category": "technical",
        "ai_attempted": true,
        "ai_suggested_fixes": ["retry_sync", "rebuild_index"],
        "attach_diagnostics": true
    }
    """
    try:
        tenant_id = g.tenant_id
        user_id = g.user_id
        data = request.json

        # Validate required fields
        if not data.get("title") or not data.get("description"):
            return jsonify({"error": "title and description required"}), 400

        # Get tenant info for SLA
        from models import Tenant
        tenant = g.db.query(Tenant).filter_by(id=tenant_id).first()

        # Set target response time based on tier
        sla_hours = {
            "starter": 72,   # 72 hours
            "growth": 48,    # 48 hours
            "scale": 12      # 12 hours (premium)
        }
        target_response = sla_hours.get(tenant.plan_tier, 72)

        # Generate diagnostic report if requested
        diagnostic_report = None
        if data.get("attach_diagnostics", True):
            diagnostic_report = DiagnosticGenerator.generate_report(
                tenant_id=tenant_id,
                user_id=user_id,
                trigger="support_request"
            )

        # Get recent error codes
        error_summary = EventLogger.get_error_summary(tenant_id, hours=24)
        error_codes = [e["error_code"] for e in error_summary]

        # Get event snapshot
        recent_events = EventLogger.get_recent_events(tenant_id, limit=50)

        # Create ticket
        ticket = SupportTicket(
            tenant_id=tenant_id,
            user_id=user_id,
            title=data["title"],
            description=data["description"],
            priority=data.get("priority", "normal"),
            category=data.get("category", "technical"),
            ai_attempted=data.get("ai_attempted", False),
            ai_suggested_fixes=data.get("ai_suggested_fixes"),
            ai_confidence_score=data.get("ai_confidence_score"),
            error_codes=error_codes,
            event_log_snapshot=recent_events,
            diagnostic_bundle_url=diagnostic_report["report_id"] if diagnostic_report else None,
            plan_tier=tenant.plan_tier,
            target_response_hours=target_response,
            assigned_to="L2_contractor" if tenant.plan_tier in ["growth", "scale"] else "AI"
        )

        g.db.add(ticket)
        g.db.commit()

        # Log ticket creation
        EventLogger.log(
            event_type="support_ticket_created",
            message=f"Support ticket created: {ticket.title}",
            tenant_id=tenant_id,
            user_id=user_id,
            category=EventLogger.SUPPORT,
            severity=EventLogger.INFO if ticket.priority == "normal" else EventLogger.WARNING,
            context_data={
                "ticket_id": ticket.id,
                "priority": ticket.priority,
                "category": ticket.category
            }
        )

        return jsonify({
            "message": "Support ticket created",
            "ticket": {
                "id": ticket.id,
                "title": ticket.title,
                "priority": ticket.priority,
                "status": ticket.status,
                "target_response_hours": target_response,
                "assigned_to": ticket.assigned_to,
                "diagnostic_report_id": diagnostic_report["report_id"] if diagnostic_report else None
            }
        }), 201

    except Exception as e:
        g.db.rollback()
        return jsonify({"error": str(e)}), 500


@diagnostics_bp.route("/support-tickets", methods=["GET"])
@jwt_required()
def list_support_tickets():
    """
    List support tickets for tenant
    Query params: ?status=open&priority=high
    """
    try:
        tenant_id = g.tenant_id
        status = request.args.get("status")
        priority = request.args.get("priority")

        query = g.db.query(SupportTicket).filter_by(tenant_id=tenant_id)

        if status:
            query = query.filter_by(status=status)

        if priority:
            query = query.filter_by(priority=priority)

        tickets = query.order_by(SupportTicket.created_at.desc()).all()

        return jsonify({
            "tickets": [{
                "id": t.id,
                "title": t.title,
                "status": t.status,
                "priority": t.priority,
                "category": t.category,
                "created_at": t.created_at.isoformat(),
                "assigned_to": t.assigned_to,
                "ai_attempted": t.ai_attempted
            } for t in tickets],
            "count": len(tickets)
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@diagnostics_bp.route("/error-code-info/<error_code>", methods=["GET"])
def get_error_code_info(error_code):
    """
    Get information about a specific error code (public endpoint)
    This is what AI uses to understand errors
    """
    try:
        error_info = ERROR_DOCS.get(error_code)

        if not error_info:
            return jsonify({
                "error_code": error_code,
                "title": "Unknown error",
                "description": f"Error code {error_code} is not documented",
                "severity": "error",
                "user_action": "Please contact support with this error code"
            }), 200

        return jsonify({
            "error_code": error_code,
            **error_info
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@diagnostics_bp.route("/suggested-fixes/<error_code>", methods=["GET"])
def get_suggested_fixes(error_code):
    """
    Get AI-powered suggested fixes for an error code (public endpoint)
    """
    try:
        # Get error info from ERROR_DOCS
        error_info = ERROR_DOCS.get(error_code)

        if not error_info:
            return jsonify({
                "error_code": error_code,
                "error_title": "Unknown error",
                "error_description": f"Error code {error_code} is not documented",
                "suggested_fixes": [],
                "common_causes": [],
                "user_action": "Please contact support with this error code"
            }), 200

        # Build suggested fixes response
        fixes = []

        if "possible_fixes" in error_info:
            fix_descriptions = {
                "retry_sync": {
                    "name": "Retry Sync",
                    "description": "Retry synchronizing with the server",
                    "button_text": "Retry Now",
                    "estimated_time": "10 seconds"
                },
                "rebuild_index": {
                    "name": "Rebuild Index",
                    "description": "Rebuild search index for faster lookups",
                    "button_text": "Rebuild Index",
                    "estimated_time": "30 seconds"
                },
                "clear_cache": {
                    "name": "Clear Cache",
                    "description": "Clear cached data and reload fresh",
                    "button_text": "Clear Cache",
                    "estimated_time": "5 seconds"
                },
                "reset_session": {
                    "name": "Reset Session",
                    "description": "Log out and log back in",
                    "button_text": "Reset Session",
                    "estimated_time": "Immediate"
                },
                "adjust_inventory": {
                    "name": "Adjust Inventory",
                    "description": "Manually adjust inventory count",
                    "button_text": "Adjust Stock",
                    "estimated_time": "Manual"
                },
                "reset_password": {
                    "name": "Reset Password",
                    "description": "Send password reset email",
                    "button_text": "Reset Password",
                    "estimated_time": "Manual"
                }
            }

            for fix_type in error_info["possible_fixes"]:
                if fix_type in fix_descriptions:
                    fixes.append({
                        "type": fix_type,
                        **fix_descriptions[fix_type]
                    })

        return jsonify({
            "error_code": error_code,
            "error_title": error_info.get("title"),
            "error_description": error_info.get("description"),
            "suggested_fixes": fixes,
            "common_causes": error_info.get("common_causes", []),
            "user_action": error_info.get("user_action")
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
