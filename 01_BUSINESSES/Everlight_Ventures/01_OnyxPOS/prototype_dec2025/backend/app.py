"""
OnyxPOS - Main Flask Application
Multi-tenant POS SaaS Platform
"""
from flask import Flask, jsonify, g, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from datetime import datetime, timedelta
import os

# Import configuration
from config import config

# Import database
from database import Session, init_db

# Create Flask app
def create_app(config_name="development"):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Initialize extensions
    CORS(app, origins=app.config["CORS_ORIGINS"])
    jwt = JWTManager(app)

    # Initialize database
    with app.app_context():
        init_db()

    # Request lifecycle hooks
    @app.before_request
    def before_request():
        """Set up database session and tenant context before each request"""
        g.db = Session()

        # Extract tenant_id from JWT if authenticated
        try:
            from flask_jwt_extended import get_jwt, verify_jwt_in_request
            verify_jwt_in_request(optional=True)
            jwt_data = get_jwt()
            if jwt_data:
                g.tenant_id = jwt_data.get("tenant_id")
                g.user_id = jwt_data.get("sub")
        except:
            g.tenant_id = None
            g.user_id = None

        # Check subscription access (after setting tenant_id)
        from middleware import check_subscription_access
        access_check = check_subscription_access()
        if access_check:
            return access_check

    @app.after_request
    def after_request(response):
        """Clean up database session after each request"""
        Session.remove()
        return response

    @app.teardown_appcontext
    def shutdown_session(exception=None):
        """Remove database session"""
        Session.remove()

    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(500)
    def internal_error(error):
        Session.rollback()
        return jsonify({"error": "Internal server error"}), 500

    # Health check endpoint
    @app.route("/health")
    def health():
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0"
        })

    # Root endpoint
    @app.route("/")
    def index():
        return jsonify({
            "message": "Welcome to OnyxPOS API",
            "version": "1.0.0",
            "docs": "/api/docs"
        })

    # Register API blueprints
    from api.auth import auth_bp
    from api.inventory import inventory_bp
    from api.inventory_advanced import inventory_advanced_bp
    from api.inventory_lots import lots_bp
    from api.sales import sales_bp
    from api.analytics import analytics_bp
    from api.owner_dashboard import dashboard_bp
    from api.stripe_billing import billing_bp
    from api.crypto_payments import crypto_bp
    from api.stripe_connect import connect_bp
    from api.gusto_setup import gusto_bp
    from api.employees import employees_bp
    from api.timeclock import timeclock_bp
    from api.schedule import schedule_bp
    from api.payroll import payroll_bp
    from api.billing_gmv import billing_gmv_bp
    from api.diagnostics import diagnostics_bp
    from api.scheduled_tasks import scheduled_bp
    from api.tasks import tasks_bp
    from api.devices import devices_bp
    from api.channels import channels_bp
    from api.timeoff import timeoff_bp

    app.register_blueprint(auth_bp, url_prefix="/api/v1/auth")
    app.register_blueprint(inventory_bp, url_prefix="/api/v1/inventory")
    app.register_blueprint(inventory_advanced_bp, url_prefix="/api/v1/inventory")
    app.register_blueprint(lots_bp, url_prefix="/api/v1/inventory/lots")
    app.register_blueprint(sales_bp, url_prefix="/api/v1/sales")
    app.register_blueprint(analytics_bp, url_prefix="/api/v1/analytics")
    app.register_blueprint(dashboard_bp, url_prefix="/api/v1/dashboard")
    app.register_blueprint(billing_bp, url_prefix="/api/v1/billing")
    app.register_blueprint(billing_gmv_bp, url_prefix="/api/v1/billing")
    app.register_blueprint(diagnostics_bp, url_prefix="/api/v1/diagnostics")
    app.register_blueprint(crypto_bp, url_prefix="/api/v1/crypto")
    app.register_blueprint(connect_bp, url_prefix="/api/v1/connect")
    app.register_blueprint(gusto_bp, url_prefix="/api/v1/gusto")
    app.register_blueprint(employees_bp, url_prefix="/api/v1/employees")
    app.register_blueprint(timeclock_bp, url_prefix="/api/v1/timeclock")
    app.register_blueprint(schedule_bp, url_prefix="/api/v1/schedule")
    app.register_blueprint(payroll_bp, url_prefix="/api/v1/payroll")
    app.register_blueprint(scheduled_bp, url_prefix="/api/v1/scheduled")
    app.register_blueprint(tasks_bp, url_prefix="/api/v1/tasks")
    app.register_blueprint(devices_bp, url_prefix="/api/v1/devices")
    app.register_blueprint(channels_bp, url_prefix="/api/v1/channels")
    app.register_blueprint(timeoff_bp, url_prefix="/api/v1/timeoff")

    return app


if __name__ == "__main__":
    app = create_app()

    # Banner
    print("\n" + "=" * 60)
    print("  OnyxPOS API Server")
    print("  Next-Generation Point of Sale")
    print("  http://localhost:5000")
    print("=" * 60 + "\n")

    # Run development server
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
