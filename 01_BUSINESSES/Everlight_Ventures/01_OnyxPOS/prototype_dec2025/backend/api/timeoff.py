"""
Time Off Request API
Allows employees to request time off and managers to approve/deny
"""
from flask import Blueprint, request, jsonify, g
from flask_jwt_extended import jwt_required, get_jwt
from sqlalchemy import and_, or_, text
from datetime import datetime, timedelta
import uuid

timeoff_bp = Blueprint('timeoff', __name__)


def generate_uuid():
    return str(uuid.uuid4())


@timeoff_bp.route('', methods=['GET'])
@jwt_required()
def get_time_off_requests():
    """Get time off requests - employees see their own, managers see all"""
    try:
        jwt_data = get_jwt()
        role = jwt_data.get('role')

        # Build query based on role
        query = "SELECT * FROM time_off_requests WHERE tenant_id = :tenant_id"
        params = {'tenant_id': g.tenant_id}

        # Employees only see their own requests
        if role not in ['owner', 'manager']:
            query += " AND user_id = :user_id"
            params['user_id'] = g.user_id

        # Filter by status if provided
        status = request.args.get('status')
        if status:
            query += " AND status = :status"
            params['status'] = status

        query += " ORDER BY created_at DESC"

        result = g.db.execute(text(query), params)
        requests_data = []

        for row in result:
            # Get user info
            user_query = text("SELECT first_name, last_name, email FROM users WHERE id = :user_id")
            user_result = g.db.execute(user_query, {'user_id': row.user_id}).fetchone()

            requests_data.append({
                'id': row.id,
                'user_id': row.user_id,
                'user_name': f"{user_result.first_name} {user_result.last_name}" if user_result else "Unknown",
                'start_date': row.start_date.isoformat(),
                'end_date': row.end_date.isoformat(),
                'reason': row.reason,
                'request_type': row.request_type,
                'status': row.status,
                'approved_by_user_id': row.approved_by_user_id,
                'approved_at': row.approved_at.isoformat() if row.approved_at else None,
                'denial_reason': row.denial_reason,
                'created_at': row.created_at.isoformat()
            })

        return jsonify({'requests': requests_data}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@timeoff_bp.route('', methods=['POST'])
@jwt_required()
def create_time_off_request():
    """Create a new time off request"""
    try:
        data = request.json

        # Validate required fields
        required = ['start_date', 'end_date', 'request_type']
        for field in required:
            if field not in data:
                return jsonify({'error': f'{field} is required'}), 400

        # Parse dates
        start_date = datetime.fromisoformat(data['start_date'].replace('Z', '+00:00'))
        end_date = datetime.fromisoformat(data['end_date'].replace('Z', '+00:00'))

        # Validate dates
        if end_date < start_date:
            return jsonify({'error': 'End date must be after start date'}), 400

        # Create request
        request_id = generate_uuid()
        query = text("""
            INSERT INTO time_off_requests
            (id, tenant_id, user_id, start_date, end_date, reason, request_type, status, created_at, updated_at)
            VALUES
            (:id, :tenant_id, :user_id, :start_date, :end_date, :reason, :request_type, 'pending', :created_at, :updated_at)
        """)

        g.db.execute(query, {
            'id': request_id,
            'tenant_id': g.tenant_id,
            'user_id': g.user_id,
            'start_date': start_date,
            'end_date': end_date,
            'reason': data.get('reason', ''),
            'request_type': data['request_type'],
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        })
        g.db.commit()

        return jsonify({
            'message': 'Time off request submitted',
            'request_id': request_id
        }), 201

    except Exception as e:
        g.db.rollback()
        return jsonify({'error': str(e)}), 500


@timeoff_bp.route('/<request_id>/approve', methods=['PUT'])
@jwt_required()
def approve_time_off(request_id):
    """Approve a time off request (managers/owners only)"""
    try:
        jwt_data = get_jwt()
        role = jwt_data.get('role')

        if role not in ['owner', 'manager']:
            return jsonify({'error': 'Insufficient permissions'}), 403

        query = text("""
            UPDATE time_off_requests
            SET status = 'approved',
                approved_by_user_id = :approver_id,
                approved_at = :approved_at,
                updated_at = :updated_at
            WHERE id = :request_id AND tenant_id = :tenant_id
        """)

        g.db.execute(query, {
            'approver_id': g.user_id,
            'approved_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'request_id': request_id,
            'tenant_id': g.tenant_id
        })
        g.db.commit()

        return jsonify({'message': 'Time off request approved'}), 200

    except Exception as e:
        g.db.rollback()
        return jsonify({'error': str(e)}), 500


@timeoff_bp.route('/<request_id>/deny', methods=['PUT'])
@jwt_required()
def deny_time_off(request_id):
    """Deny a time off request (managers/owners only)"""
    try:
        jwt_data = get_jwt()
        role = jwt_data.get('role')

        if role not in ['owner', 'manager']:
            return jsonify({'error': 'Insufficient permissions'}), 403

        data = request.json
        denial_reason = data.get('reason', '')

        query = text("""
            UPDATE time_off_requests
            SET status = 'denied',
                approved_by_user_id = :approver_id,
                approved_at = :approved_at,
                denial_reason = :denial_reason,
                updated_at = :updated_at
            WHERE id = :request_id AND tenant_id = :tenant_id
        """)

        g.db.execute(query, {
            'approver_id': g.user_id,
            'approved_at': datetime.utcnow(),
            'denial_reason': denial_reason,
            'updated_at': datetime.utcnow(),
            'request_id': request_id,
            'tenant_id': g.tenant_id
        })
        g.db.commit()

        return jsonify({'message': 'Time off request denied'}), 200

    except Exception as e:
        g.db.rollback()
        return jsonify({'error': str(e)}), 500


@timeoff_bp.route('/<request_id>', methods=['DELETE'])
@jwt_required()
def delete_time_off_request(request_id):
    """Delete a time off request (own requests only or manager)"""
    try:
        jwt_data = get_jwt()
        role = jwt_data.get('role')

        # Check ownership or manager role
        check_query = text("SELECT user_id FROM time_off_requests WHERE id = :request_id AND tenant_id = :tenant_id")
        result = g.db.execute(check_query, {'request_id': request_id, 'tenant_id': g.tenant_id}).fetchone()

        if not result:
            return jsonify({'error': 'Request not found'}), 404

        if result.user_id != g.user_id and role not in ['owner', 'manager']:
            return jsonify({'error': 'Insufficient permissions'}), 403

        delete_query = text("DELETE FROM time_off_requests WHERE id = :request_id AND tenant_id = :tenant_id")
        g.db.execute(delete_query, {'request_id': request_id, 'tenant_id': g.tenant_id})
        g.db.commit()

        return jsonify({'message': 'Time off request deleted'}), 200

    except Exception as e:
        g.db.rollback()
        return jsonify({'error': str(e)}), 500
