"""
Schedule Management API
Handles employee shift scheduling with automated scheduling support
"""
import sys
import os
from flask import Blueprint, request, jsonify, g
from flask_jwt_extended import jwt_required
from models import Schedule, User
from datetime import datetime, timedelta
from sqlalchemy import and_

# Add services to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.automated_scheduling import AutomatedScheduler

schedule_bp = Blueprint('schedule', __name__)


@schedule_bp.route('', methods=['GET'])
@jwt_required()
def get_shifts():
    """Get shifts for a week"""
    try:
        week_start = request.args.get('week_start')

        if week_start:
            start_date = datetime.strptime(week_start, '%Y-%m-%d')
            end_date = start_date + timedelta(days=7)

            shifts = g.db.query(Schedule).filter(
                and_(
                    Schedule.tenant_id == g.tenant_id,
                    Schedule.date >= start_date,
                    Schedule.date < end_date
                )
            ).all()
        else:
            # Get current week
            today = datetime.utcnow().date()
            start_date = today - timedelta(days=today.weekday())
            end_date = start_date + timedelta(days=7)

            shifts = g.db.query(Schedule).filter(
                and_(
                    Schedule.tenant_id == g.tenant_id,
                    Schedule.date >= start_date,
                    Schedule.date < end_date
                )
            ).all()

        return jsonify({
            'shifts': [{
                'id': shift.id,
                'employee_id': shift.employee_id,
                'date': shift.date.isoformat(),
                'start_time': shift.start_time,
                'end_time': shift.end_time,
                'notes': shift.notes
            } for shift in shifts]
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@schedule_bp.route('', methods=['POST'])
@jwt_required()
def create_shift():
    """Create a new shift"""
    try:
        data = request.get_json()

        # Check if user is owner or manager
        current_user = g.db.query(User).filter_by(id=g.user_id).first()
        if current_user.role not in ['owner', 'manager']:
            return jsonify({'error': 'Unauthorized'}), 403

        # Create shift
        shift = Schedule(
            tenant_id=g.tenant_id,
            employee_id=data['employee_id'],
            date=datetime.strptime(data['date'], '%Y-%m-%d').date(),
            start_time=data['start_time'],
            end_time=data['end_time'],
            notes=data.get('notes')
        )

        g.db.add(shift)
        g.db.commit()

        return jsonify({
            'message': 'Shift created successfully',
            'shift': {
                'id': shift.id,
                'employee_id': shift.employee_id,
                'date': shift.date.isoformat(),
                'start_time': shift.start_time,
                'end_time': shift.end_time
            }
        }), 201
    except Exception as e:
        g.db.rollback()
        return jsonify({'error': str(e)}), 500


@schedule_bp.route('/<int:shift_id>', methods=['PUT'])
@jwt_required()
def update_shift(shift_id):
    """Update a shift"""
    try:
        data = request.get_json()

        # Check if user is owner or manager
        current_user = g.db.query(User).filter_by(id=g.user_id).first()
        if current_user.role not in ['owner', 'manager']:
            return jsonify({'error': 'Unauthorized'}), 403

        shift = g.db.query(Schedule).filter_by(
            id=shift_id,
            tenant_id=g.tenant_id
        ).first()

        if not shift:
            return jsonify({'error': 'Shift not found'}), 404

        # Update fields
        if 'employee_id' in data:
            shift.employee_id = data['employee_id']
        if 'date' in data:
            shift.date = datetime.strptime(data['date'], '%Y-%m-%d').date()
        if 'start_time' in data:
            shift.start_time = data['start_time']
        if 'end_time' in data:
            shift.end_time = data['end_time']
        if 'notes' in data:
            shift.notes = data['notes']

        g.db.commit()

        return jsonify({
            'message': 'Shift updated successfully',
            'shift': {
                'id': shift.id,
                'employee_id': shift.employee_id,
                'date': shift.date.isoformat(),
                'start_time': shift.start_time,
                'end_time': shift.end_time
            }
        }), 200
    except Exception as e:
        g.db.rollback()
        return jsonify({'error': str(e)}), 500


@schedule_bp.route('/<int:shift_id>', methods=['DELETE'])
@jwt_required()
def delete_shift(shift_id):
    """Delete a shift"""
    try:
        # Check if user is owner or manager
        current_user = g.db.query(User).filter_by(id=g.user_id).first()
        if current_user.role not in ['owner', 'manager']:
            return jsonify({'error': 'Unauthorized'}), 403

        shift = g.db.query(Schedule).filter_by(
            id=shift_id,
            tenant_id=g.tenant_id
        ).first()

        if not shift:
            return jsonify({'error': 'Shift not found'}), 404

        g.db.delete(shift)
        g.db.commit()

        return jsonify({'message': 'Shift deleted successfully'}), 200
    except Exception as e:
        g.db.rollback()
        return jsonify({'error': str(e)}), 500


# ============= AUTOMATED SCHEDULING =============

@schedule_bp.route('/auto-suggestions/<employee_id>', methods=['GET'])
@jwt_required()
def get_auto_suggestions(employee_id):
    """
    Get automated schedule suggestions for an employee

    Query params:
    - start_date: ISO date to start from (default: next Monday)
    - weeks: Number of weeks to generate (default: 4)
    """
    try:
        # Check if user is owner or manager
        current_user = g.db.query(User).filter_by(id=g.user_id).first()
        if current_user.role not in ['owner', 'manager']:
            return jsonify({'error': 'Unauthorized'}), 403

        # Parse query params
        start_date_str = request.args.get('start_date')
        if start_date_str:
            start_date = datetime.fromisoformat(start_date_str)
        else:
            # Default to next Monday
            today = datetime.utcnow()
            days_until_monday = (7 - today.weekday()) % 7
            start_date = today + timedelta(days=days_until_monday)

        weeks = request.args.get('weeks', 4, type=int)

        # Generate suggestions
        suggestions = AutomatedScheduler.generate_recurring_schedule(
            tenant_id=g.tenant_id,
            employee_id=employee_id,
            start_date=start_date,
            weeks=weeks
        )

        if not suggestions:
            return jsonify({
                'message': 'Not enough historical data to generate suggestions. Need at least 3 past shifts.',
                'suggestions': []
            }), 200

        return jsonify({
            'employee_id': employee_id,
            'start_date': start_date.isoformat(),
            'weeks': weeks,
            'suggestions': suggestions
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@schedule_bp.route('/auto-create/<employee_id>', methods=['POST'])
@jwt_required()
def auto_create_schedule(employee_id):
    """
    Automatically create recurring schedule for employee

    Request body:
    - start_date: ISO date to start from (optional)
    - weeks: Number of weeks to generate (default: 4)
    - auto_confirm: Auto-confirm generated schedules (default: false)
    """
    try:
        # Check if user is owner or manager
        current_user = g.db.query(User).filter_by(id=g.user_id).first()
        if current_user.role not in ['owner', 'manager']:
            return jsonify({'error': 'Unauthorized'}), 403

        data = request.json or {}

        # Parse params
        start_date_str = data.get('start_date')
        if start_date_str:
            start_date = datetime.fromisoformat(start_date_str)
        else:
            # Default to next Monday
            today = datetime.utcnow()
            days_until_monday = (7 - today.weekday()) % 7
            start_date = today + timedelta(days=days_until_monday)

        weeks = data.get('weeks', 4)
        auto_confirm = data.get('auto_confirm', False)

        # Create schedules
        created_count = AutomatedScheduler.create_recurring_schedules(
            tenant_id=g.tenant_id,
            employee_id=employee_id,
            start_date=start_date,
            weeks=weeks,
            auto_confirm=auto_confirm
        )

        if created_count == 0:
            return jsonify({
                'message': 'No new schedules created. Either not enough historical data or schedules already exist.',
                'created_count': 0
            }), 200

        return jsonify({
            'message': f'Successfully created {created_count} automated schedules',
            'created_count': created_count,
            'employee_id': employee_id,
            'start_date': start_date.isoformat(),
            'weeks': weeks
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@schedule_bp.route('/auto-team-suggestions', methods=['GET'])
@jwt_required()
def get_team_suggestions():
    """
    Get automated schedule suggestions for entire team

    Query params:
    - start_date: ISO date to start from (default: next Monday)
    - weeks: Number of weeks to generate (default: 4)
    """
    try:
        # Check if user is owner or manager
        current_user = g.db.query(User).filter_by(id=g.user_id).first()
        if current_user.role not in ['owner', 'manager']:
            return jsonify({'error': 'Unauthorized'}), 403

        # Parse query params
        start_date_str = request.args.get('start_date')
        if start_date_str:
            start_date = datetime.fromisoformat(start_date_str)
        else:
            # Default to next Monday
            today = datetime.utcnow()
            days_until_monday = (7 - today.weekday()) % 7
            start_date = today + timedelta(days=days_until_monday)

        weeks = request.args.get('weeks', 4, type=int)

        # Get team suggestions
        team_suggestions = AutomatedScheduler.get_schedule_suggestions_for_team(
            tenant_id=g.tenant_id,
            start_date=start_date,
            weeks=weeks
        )

        return jsonify({
            'start_date': start_date.isoformat(),
            'weeks': weeks,
            'team_suggestions': team_suggestions
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@schedule_bp.route('/coverage-analysis', methods=['GET'])
@jwt_required()
def analyze_coverage():
    """
    Analyze team coverage and identify gaps

    Query params:
    - start_date: ISO date to start analysis
    - end_date: ISO date to end analysis
    - target_hours: Target hours per day (default: 8)
    """
    try:
        # Check if user is owner or manager
        current_user = g.db.query(User).filter_by(id=g.user_id).first()
        if current_user.role not in ['owner', 'manager']:
            return jsonify({'error': 'Unauthorized'}), 403

        # Parse query params
        start_date = datetime.fromisoformat(request.args.get('start_date'))
        end_date = datetime.fromisoformat(request.args.get('end_date'))
        target_hours = request.args.get('target_hours', 8, type=int)

        # Analyze coverage
        coverage_analysis = AutomatedScheduler.optimize_coverage(
            tenant_id=g.tenant_id,
            start_date=start_date,
            end_date=end_date,
            target_hours_per_day=target_hours
        )

        return jsonify({
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'target_hours_per_day': target_hours,
            'coverage_by_day': coverage_analysis
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
