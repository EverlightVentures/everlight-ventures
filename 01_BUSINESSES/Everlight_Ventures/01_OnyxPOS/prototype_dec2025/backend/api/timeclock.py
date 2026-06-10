"""
Time Clock API
Handles clock in/out, breaks, and shift tracking
"""
from flask import Blueprint, request, jsonify, g
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from models import TimeClockEntry, User
from datetime import datetime, timedelta
from sqlalchemy import and_

timeclock_bp = Blueprint('timeclock', __name__)


@timeclock_bp.route('/current', methods=['GET'])
@jwt_required()
def get_current_shift():
    """Get current active shift for the user"""
    try:
        shift = g.db.query(TimeClockEntry).filter(
            and_(
                TimeClockEntry.user_id == g.user_id,
                TimeClockEntry.tenant_id == g.tenant_id,
                TimeClockEntry.clock_out.is_(None)
            )
        ).first()

        if shift:
            return jsonify({
                'shift': {
                    'id': shift.id,
                    'clock_in': shift.clock_in.isoformat(),
                    'on_break': shift.break_start is not None and shift.break_end is None
                }
            }), 200
        else:
            return jsonify({'shift': None}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@timeclock_bp.route('/recent', methods=['GET'])
@jwt_required()
def get_recent_shifts():
    """Get recent shifts for the user"""
    try:
        # Get last 30 days
        since = datetime.utcnow() - timedelta(days=30)

        shifts = g.db.query(TimeClockEntry).filter(
            and_(
                TimeClockEntry.user_id == g.user_id,
                TimeClockEntry.tenant_id == g.tenant_id,
                TimeClockEntry.clock_in >= since
            )
        ).order_by(TimeClockEntry.clock_in.desc()).limit(20).all()

        return jsonify({
            'shifts': [{
                'id': shift.id,
                'clock_in': shift.clock_in.isoformat(),
                'clock_out': shift.clock_out.isoformat() if shift.clock_out else None,
                'break_minutes': shift.break_minutes or 0
            } for shift in shifts]
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@timeclock_bp.route('/clock-in', methods=['POST'])
@jwt_required()
def clock_in():
    """Clock in for a shift"""
    try:
        # Check if already clocked in
        existing = g.db.query(TimeClockEntry).filter(
            and_(
                TimeClockEntry.user_id == g.user_id,
                TimeClockEntry.tenant_id == g.tenant_id,
                TimeClockEntry.clock_out.is_(None)
            )
        ).first()

        if existing:
            return jsonify({'error': 'Already clocked in'}), 400

        # Create new shift
        shift = TimeClockEntry(
            tenant_id=g.tenant_id,
            user_id=g.user_id,
            clock_in=datetime.utcnow()
        )

        g.db.add(shift)
        g.db.commit()

        return jsonify({
            'message': 'Clocked in successfully',
            'shift': {
                'id': shift.id,
                'clock_in': shift.clock_in.isoformat()
            }
        }), 201
    except Exception as e:
        g.db.rollback()
        return jsonify({'error': str(e)}), 500


@timeclock_bp.route('/clock-out', methods=['POST'])
@jwt_required()
def clock_out():
    """Clock out from current shift"""
    try:
        shift = g.db.query(TimeClockEntry).filter(
            and_(
                TimeClockEntry.user_id == g.user_id,
                TimeClockEntry.tenant_id == g.tenant_id,
                TimeClockEntry.clock_out.is_(None)
            )
        ).first()

        if not shift:
            return jsonify({'error': 'Not clocked in'}), 400

        # End any active break
        if shift.break_start and not shift.break_end:
            shift.break_end = datetime.utcnow()
            break_duration = (shift.break_end - shift.break_start).total_seconds() / 60
            shift.break_minutes = (shift.break_minutes or 0) + break_duration

        # Clock out
        shift.clock_out = datetime.utcnow()

        # Calculate total hours
        total_seconds = (shift.clock_out - shift.clock_in).total_seconds()
        break_seconds = (shift.break_minutes or 0) * 60
        work_seconds = total_seconds - break_seconds
        total_hours = work_seconds / 3600

        g.db.commit()

        return jsonify({
            'message': 'Clocked out successfully',
            'total_hours': round(total_hours, 2),
            'shift': {
                'id': shift.id,
                'clock_in': shift.clock_in.isoformat(),
                'clock_out': shift.clock_out.isoformat()
            }
        }), 200
    except Exception as e:
        g.db.rollback()
        return jsonify({'error': str(e)}), 500


@timeclock_bp.route('/start-break', methods=['POST'])
@jwt_required()
def start_break():
    """Start a break during current shift"""
    try:
        shift = g.db.query(TimeClockEntry).filter(
            and_(
                TimeClockEntry.user_id == g.user_id,
                TimeClockEntry.tenant_id == g.tenant_id,
                TimeClockEntry.clock_out.is_(None)
            )
        ).first()

        if not shift:
            return jsonify({'error': 'Not clocked in'}), 400

        if shift.break_start and not shift.break_end:
            return jsonify({'error': 'Break already in progress'}), 400

        shift.break_start = datetime.utcnow()
        g.db.commit()

        return jsonify({'message': 'Break started'}), 200
    except Exception as e:
        g.db.rollback()
        return jsonify({'error': str(e)}), 500


@timeclock_bp.route('/end-break', methods=['POST'])
@jwt_required()
def end_break():
    """End the current break"""
    try:
        shift = g.db.query(TimeClockEntry).filter(
            and_(
                TimeClockEntry.user_id == g.user_id,
                TimeClockEntry.tenant_id == g.tenant_id,
                TimeClockEntry.clock_out.is_(None)
            )
        ).first()

        if not shift:
            return jsonify({'error': 'Not clocked in'}), 400

        if not shift.break_start or shift.break_end:
            return jsonify({'error': 'No active break'}), 400

        shift.break_end = datetime.utcnow()

        # Calculate break duration and add to total
        break_duration = (shift.break_end - shift.break_start).total_seconds() / 60
        shift.break_minutes = (shift.break_minutes or 0) + break_duration

        # Reset break times for next break
        shift.break_start = None
        shift.break_end = None

        g.db.commit()

        return jsonify({'message': 'Break ended'}), 200
    except Exception as e:
        g.db.rollback()
        return jsonify({'error': str(e)}), 500


@timeclock_bp.route('/realtime-payroll', methods=['GET'])
@jwt_required()
def get_realtime_payroll():
    """
    Get real-time payroll cost for currently clocked-in employees
    Shows current labor cost accumulating in real-time
    """
    try:
        jwt_data = get_jwt()
        role = jwt_data.get('role')

        # Only owners and managers can view payroll costs
        if role not in ['owner', 'manager']:
            return jsonify({'error': 'Insufficient permissions'}), 403

        # Get all currently clocked-in employees
        active_shifts = g.db.query(TimeClockEntry).filter(
            and_(
                TimeClockEntry.tenant_id == g.tenant_id,
                TimeClockEntry.clock_out.is_(None)
            )
        ).all()

        now = datetime.utcnow()
        employees_working = []
        total_cost_so_far = 0.0
        total_hours_so_far = 0.0

        for shift in active_shifts:
            # Get employee details
            user = g.db.query(User).filter_by(id=shift.user_id).first()
            if not user:
                continue

            # Calculate time worked so far
            time_worked = now - shift.clock_in
            hours_worked = time_worked.total_seconds() / 3600

            # Subtract break time
            break_hours = (shift.break_minutes or 0) / 60

            # If currently on break, add current break duration
            if shift.break_start and not shift.break_end:
                current_break = (now - shift.break_start).total_seconds() / 3600
                break_hours += current_break

            billable_hours = hours_worked - break_hours

            # Calculate cost based on pay type
            cost_so_far = 0.0
            hourly_rate = 0.0

            if user.pay_type == 'hourly' and user.hourly_rate:
                hourly_rate = float(user.hourly_rate)
                cost_so_far = billable_hours * hourly_rate
            elif user.pay_type == 'salary' and user.salary:
                # Assume 40 hour work week, calculate hourly equivalent
                hourly_rate = float(user.salary) / (52 * 40)
                cost_so_far = billable_hours * hourly_rate
            else:
                # Default to minimum wage if not set (adjust for your state)
                hourly_rate = 15.00  # Default hourly rate
                cost_so_far = billable_hours * hourly_rate

            total_cost_so_far += cost_so_far
            total_hours_so_far += billable_hours

            employees_working.append({
                'user_id': user.id,
                'name': f'{user.first_name} {user.last_name}',
                'role': user.role,
                'clock_in': shift.clock_in.isoformat(),
                'hours_worked': round(billable_hours, 2),
                'hourly_rate': round(hourly_rate, 2),
                'cost_so_far': round(cost_so_far, 2),
                'on_break': shift.break_start is not None and shift.break_end is None
            })

        return jsonify({
            'employees_working': employees_working,
            'employee_count': len(employees_working),
            'total_hours': round(total_hours_so_far, 2),
            'total_cost': round(total_cost_so_far, 2),
            'timestamp': now.isoformat()
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
