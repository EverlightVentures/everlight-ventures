"""
Payroll API
Handles payroll calculations and reports
"""
from flask import Blueprint, request, jsonify, g, make_response
from flask_jwt_extended import jwt_required, get_jwt
from models import TimeClockEntry, User
from sqlalchemy import and_, func, text
from datetime import datetime, timedelta
import csv
import io
import uuid

payroll_bp = Blueprint('payroll', __name__)


def generate_uuid():
    return str(uuid.uuid4())


@payroll_bp.route('', methods=['GET'])
@jwt_required()
def get_payroll():
    """Get payroll data for a date range"""
    try:
        # Check if user is owner or manager
        current_user = g.db.query(User).filter_by(id=g.user_id).first()
        if current_user.role not in ['owner', 'manager']:
            return jsonify({'error': 'Unauthorized'}), 403

        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        if not start_date or not end_date:
            return jsonify({'error': 'start_date and end_date required'}), 400

        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)

        # Get all completed shifts in date range
        shifts = g.db.query(TimeClockEntry).filter(
            and_(
                TimeClockEntry.tenant_id == g.tenant_id,
                TimeClockEntry.clock_in >= start,
                TimeClockEntry.clock_in < end,
                TimeClockEntry.clock_out.isnot(None)
            )
        ).all()

        # Calculate hours per employee
        employee_hours = {}
        for shift in shifts:
            if shift.user_id not in employee_hours:
                employee_hours[shift.user_id] = 0

            # Calculate shift duration minus breaks
            duration_seconds = (shift.clock_out - shift.clock_in).total_seconds()
            break_seconds = (shift.break_minutes or 0) * 60
            work_seconds = duration_seconds - break_seconds
            hours = work_seconds / 3600

            employee_hours[shift.user_id] += hours

        # Get employee details and calculate pay
        payroll_data = []
        total_payroll = 0
        total_hours = 0

        for user_id, hours in employee_hours.items():
            employee = g.db.query(User).filter_by(id=user_id).first()
            if not employee:
                continue

            hourly_rate = float(employee.hourly_rate) if employee.hourly_rate else 0

            payroll_data.append({
                'id': employee.id,
                'first_name': employee.first_name,
                'last_name': employee.last_name,
                'email': employee.email,
                'role': employee.role,
                'total_hours': round(hours, 2),
                'hourly_rate': hourly_rate
            })

            total_payroll += hours * hourly_rate
            total_hours += hours

        return jsonify({
            'employees': payroll_data,
            'summary': {
                'total_payroll': round(total_payroll, 2),
                'total_hours': round(total_hours, 2),
                'employee_count': len(payroll_data)
            }
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@payroll_bp.route('/export', methods=['GET'])
@jwt_required()
def export_payroll():
    """Export payroll data as CSV"""
    try:
        # Check if user is owner or manager
        current_user = g.db.query(User).filter_by(id=g.user_id).first()
        if current_user.role not in ['owner', 'manager']:
            return jsonify({'error': 'Unauthorized'}), 403

        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        if not start_date or not end_date:
            return jsonify({'error': 'start_date and end_date required'}), 400

        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)

        # Get all completed shifts in date range
        shifts = g.db.query(TimeClockEntry).filter(
            and_(
                TimeClockEntry.tenant_id == g.tenant_id,
                TimeClockEntry.clock_in >= start,
                TimeClockEntry.clock_in < end,
                TimeClockEntry.clock_out.isnot(None)
            )
        ).all()

        # Calculate hours per employee
        employee_hours = {}
        for shift in shifts:
            if shift.user_id not in employee_hours:
                employee_hours[shift.user_id] = 0

            duration_seconds = (shift.clock_out - shift.clock_in).total_seconds()
            break_seconds = (shift.break_minutes or 0) * 60
            work_seconds = duration_seconds - break_seconds
            hours = work_seconds / 3600

            employee_hours[shift.user_id] += hours

        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            'Employee ID',
            'First Name',
            'Last Name',
            'Email',
            'Role',
            'Total Hours',
            'Hourly Rate',
            'Regular Hours',
            'Overtime Hours',
            'Regular Pay',
            'Overtime Pay',
            'Total Pay'
        ])

        for user_id, hours in employee_hours.items():
            employee = g.db.query(User).filter_by(id=user_id).first()
            if not employee:
                continue

            hourly_rate = float(employee.hourly_rate) if employee.hourly_rate else 0
            regular_hours = min(hours, 40)
            overtime_hours = max(0, hours - 40)
            regular_pay = regular_hours * hourly_rate
            overtime_pay = overtime_hours * hourly_rate * 1.5
            total_pay = regular_pay + overtime_pay

            writer.writerow([
                employee.id,
                employee.first_name,
                employee.last_name,
                employee.email,
                employee.role,
                round(hours, 2),
                hourly_rate,
                round(regular_hours, 2),
                round(overtime_hours, 2),
                round(regular_pay, 2),
                round(overtime_pay, 2),
                round(total_pay, 2)
            ])

        # Create response
        output.seek(0)
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename=payroll-{start_date}-{end_date}.csv'

        return response
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@payroll_bp.route('/periods', methods=['GET'])
@jwt_required()
def get_payroll_periods():
    """Get all payroll periods"""
    try:
        jwt_data = get_jwt()
        role = jwt_data.get('role')

        if role not in ['owner', 'manager']:
            return jsonify({'error': 'Unauthorized'}), 403

        query = text("""
            SELECT * FROM payroll_periods
            WHERE tenant_id = :tenant_id
            ORDER BY period_start DESC
            LIMIT 50
        """)

        result = g.db.execute(query, {'tenant_id': g.tenant_id})
        periods = []

        for row in result:
            periods.append({
                'id': row.id,
                'period_start': row.period_start.isoformat(),
                'period_end': row.period_end.isoformat(),
                'status': row.status,
                'total_amount': float(row.total_amount) if row.total_amount else 0,
                'total_hours': float(row.total_hours) if row.total_hours else 0,
                'run_date': row.run_date.isoformat() if row.run_date else None,
                'run_by_user_id': row.run_by_user_id
            })

        return jsonify({'periods': periods}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@payroll_bp.route('/run-payroll', methods=['POST'])
@jwt_required()
def run_payroll():
    """Mark payroll period as run and lock in hours/amounts"""
    try:
        jwt_data = get_jwt()
        role = jwt_data.get('role')

        if role not in ['owner', 'manager']:
            return jsonify({'error': 'Only owners and managers can run payroll'}), 403

        data = request.json
        period_start = datetime.fromisoformat(data['period_start'].replace('Z', '+00:00'))
        period_end = datetime.fromisoformat(data['period_end'].replace('Z', '+00:00'))

        # Calculate totals for the period
        shifts = g.db.query(TimeClockEntry).filter(
            and_(
                TimeClockEntry.tenant_id == g.tenant_id,
                TimeClockEntry.clock_in >= period_start,
                TimeClockEntry.clock_in < period_end,
                TimeClockEntry.clock_out.isnot(None)
            )
        ).all()

        total_hours = 0.0
        total_amount = 0.0

        for shift in shifts:
            user = g.db.query(User).filter_by(id=shift.user_id).first()
            if not user:
                continue

            # Calculate hours
            duration_seconds = (shift.clock_out - shift.clock_in).total_seconds()
            break_seconds = (shift.break_minutes or 0) * 60
            work_seconds = duration_seconds - break_seconds
            hours = work_seconds / 3600

            # Calculate amount
            if user.pay_type == 'hourly' and user.hourly_rate:
                amount = hours * float(user.hourly_rate)
            elif user.pay_type == 'salary' and user.salary:
                hourly_rate = float(user.salary) / (52 * 40)
                amount = hours * hourly_rate
            else:
                amount = hours * 15.00  # Default rate

            total_hours += hours
            total_amount += amount

        # Create or update payroll period
        period_id = generate_uuid()
        query = text("""
            INSERT INTO payroll_periods
            (id, tenant_id, period_start, period_end, status, total_amount, total_hours, run_date, run_by_user_id, created_at, updated_at)
            VALUES
            (:id, :tenant_id, :period_start, :period_end, 'completed', :total_amount, :total_hours, :run_date, :run_by, :created_at, :updated_at)
        """)

        g.db.execute(query, {
            'id': period_id,
            'tenant_id': g.tenant_id,
            'period_start': period_start,
            'period_end': period_end,
            'total_amount': total_amount,
            'total_hours': total_hours,
            'run_date': datetime.utcnow(),
            'run_by': g.user_id,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        })
        g.db.commit()

        return jsonify({
            'message': 'Payroll processed successfully',
            'period_id': period_id,
            'total_hours': round(total_hours, 2),
            'total_amount': round(total_amount, 2)
        }), 201

    except Exception as e:
        g.db.rollback()
        return jsonify({'error': str(e)}), 500
