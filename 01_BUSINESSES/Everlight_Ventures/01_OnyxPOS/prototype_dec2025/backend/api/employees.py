"""
Employee Management API
Handles CRUD operations for employees
"""
from flask import Blueprint, request, jsonify, g
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import User, Tenant
from bcrypt import hashpw, gensalt
from datetime import datetime

employees_bp = Blueprint('employees', __name__)


@employees_bp.route('', methods=['GET'])
@jwt_required()
def get_employees():
    """Get all employees for the current tenant"""
    try:
        employees = g.db.query(User).filter_by(tenant_id=g.tenant_id).all()

        return jsonify({
            'employees': [{
                'id': emp.id,
                'email': emp.email,
                'first_name': emp.first_name,
                'last_name': emp.last_name,
                'role': emp.role,
                'phone': emp.phone,
                'hourly_rate': float(emp.hourly_rate) if emp.hourly_rate else None,
                'is_active': emp.is_active,
                'created_at': emp.created_at.isoformat()
            } for emp in employees]
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@employees_bp.route('', methods=['POST'])
@jwt_required()
def create_employee():
    """Create a new employee"""
    try:
        data = request.get_json()

        # Check if user is owner or manager
        current_user = g.db.query(User).filter_by(id=g.user_id).first()
        if current_user.role not in ['owner', 'manager']:
            return jsonify({'error': 'Unauthorized'}), 403

        # Check team size limit
        tenant = g.db.query(Tenant).filter_by(id=g.tenant_id).first()
        team_limit = tenant.get_team_size_limit()

        if team_limit > 0:
            current_team_size = g.db.query(User).filter_by(
                tenant_id=g.tenant_id,
                is_active=True
            ).count()

            if current_team_size >= team_limit:
                return jsonify({
                    'error': 'Team size limit reached',
                    'message': f'Your {tenant.plan_tier} plan allows {team_limit} team members. Upgrade to add more.',
                    'current_team_size': current_team_size,
                    'team_limit': team_limit,
                    'upgrade_recommended': 'growth' if tenant.plan_tier == 'core' else 'prime'
                }), 403

        # Check if email already exists
        existing = g.db.query(User).filter_by(
            tenant_id=g.tenant_id,
            email=data['email']
        ).first()

        if existing:
            return jsonify({'error': 'Email already exists'}), 400

        # Hash password
        password_hash = hashpw(data['password'].encode('utf-8'), gensalt()).decode('utf-8')

        # Create employee
        employee = User(
            tenant_id=g.tenant_id,
            email=data['email'],
            password_hash=password_hash,
            first_name=data['first_name'],
            last_name=data['last_name'],
            role=data.get('role', 'cashier'),
            phone=data.get('phone'),
            hourly_rate=data.get('hourly_rate'),
            is_active=True
        )

        g.db.add(employee)
        g.db.commit()

        return jsonify({
            'message': 'Employee created successfully',
            'employee': {
                'id': employee.id,
                'email': employee.email,
                'first_name': employee.first_name,
                'last_name': employee.last_name,
                'role': employee.role
            }
        }), 201
    except Exception as e:
        g.db.rollback()
        return jsonify({'error': str(e)}), 500


@employees_bp.route('/<int:employee_id>', methods=['PUT'])
@jwt_required()
def update_employee(employee_id):
    """Update an employee"""
    try:
        data = request.get_json()

        # Check if user is owner or manager
        current_user = g.db.query(User).filter_by(id=g.user_id).first()
        if current_user.role not in ['owner', 'manager']:
            return jsonify({'error': 'Unauthorized'}), 403

        employee = g.db.query(User).filter_by(
            id=employee_id,
            tenant_id=g.tenant_id
        ).first()

        if not employee:
            return jsonify({'error': 'Employee not found'}), 404

        # Don't allow changing owner role
        if employee.role == 'owner':
            return jsonify({'error': 'Cannot modify owner'}), 403

        # Update fields
        if 'first_name' in data:
            employee.first_name = data['first_name']
        if 'last_name' in data:
            employee.last_name = data['last_name']
        if 'email' in data:
            employee.email = data['email']
        if 'phone' in data:
            employee.phone = data['phone']
        if 'role' in data and current_user.role == 'owner':
            employee.role = data['role']
        if 'hourly_rate' in data:
            employee.hourly_rate = data['hourly_rate']
        if 'password' in data and data['password']:
            employee.password_hash = hashpw(data['password'].encode('utf-8'), gensalt()).decode('utf-8')

        g.db.commit()

        return jsonify({
            'message': 'Employee updated successfully',
            'employee': {
                'id': employee.id,
                'email': employee.email,
                'first_name': employee.first_name,
                'last_name': employee.last_name,
                'role': employee.role
            }
        }), 200
    except Exception as e:
        g.db.rollback()
        return jsonify({'error': str(e)}), 500


@employees_bp.route('/<int:employee_id>', methods=['DELETE'])
@jwt_required()
def delete_employee(employee_id):
    """Delete an employee"""
    try:
        # Check if user is owner or manager
        current_user = g.db.query(User).filter_by(id=g.user_id).first()
        if current_user.role not in ['owner', 'manager']:
            return jsonify({'error': 'Unauthorized'}), 403

        employee = g.db.query(User).filter_by(
            id=employee_id,
            tenant_id=g.tenant_id
        ).first()

        if not employee:
            return jsonify({'error': 'Employee not found'}), 404

        # Don't allow deleting owner
        if employee.role == 'owner':
            return jsonify({'error': 'Cannot delete owner'}), 403

        g.db.delete(employee)
        g.db.commit()

        return jsonify({'message': 'Employee deleted successfully'}), 200
    except Exception as e:
        g.db.rollback()
        return jsonify({'error': str(e)}), 500
