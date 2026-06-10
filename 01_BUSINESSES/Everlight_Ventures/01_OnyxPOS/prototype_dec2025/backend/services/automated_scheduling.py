"""
Automated Shift Scheduling Service
After first manual entry, automatically suggests/creates recurring schedules
"""
from datetime import datetime, timedelta
from models import Schedule, User, TimeClockEntry
from database import Session
from sqlalchemy import func


class AutomatedScheduler:
    """Autonomous shift scheduling based on historical patterns"""

    @staticmethod
    def analyze_employee_patterns(tenant_id, employee_id, weeks_to_analyze=4):
        """
        Analyze employee's historical shift patterns

        Returns:
            dict: Pattern analysis with common shifts
        """
        db = Session()

        try:
            # Get historical schedules
            cutoff_date = datetime.utcnow() - timedelta(weeks=weeks_to_analyze)

            schedules = db.query(Schedule).filter(
                Schedule.tenant_id == tenant_id,
                Schedule.employee_id == employee_id,
                Schedule.date >= cutoff_date
            ).order_by(Schedule.date).all()

            if len(schedules) < 3:
                # Not enough data for pattern recognition
                return None

            # Analyze patterns
            patterns = {}

            for schedule in schedules:
                # Get day of week (0=Monday, 6=Sunday)
                day_of_week = schedule.date.weekday()

                if day_of_week not in patterns:
                    patterns[day_of_week] = {
                        "shifts": [],
                        "count": 0
                    }

                patterns[day_of_week]["shifts"].append({
                    "start_time": schedule.start_time,
                    "end_time": schedule.end_time,
                    "date": schedule.date
                })
                patterns[day_of_week]["count"] += 1

            # Find most common shift times for each day
            common_patterns = {}

            for day, data in patterns.items():
                if data["count"] >= 2:  # At least 2 occurrences
                    # Find most common start/end times
                    shift_times = {}
                    for shift in data["shifts"]:
                        key = f"{shift['start_time']}-{shift['end_time']}"
                        shift_times[key] = shift_times.get(key, 0) + 1

                    # Get most common shift
                    most_common = max(shift_times.items(), key=lambda x: x[1])
                    start, end = most_common[0].split("-")

                    common_patterns[day] = {
                        "start_time": start,
                        "end_time": end,
                        "frequency": most_common[1],
                        "confidence": most_common[1] / data["count"]
                    }

            return common_patterns

        finally:
            db.close()

    @staticmethod
    def generate_recurring_schedule(tenant_id, employee_id, start_date, weeks=4):
        """
        Generate recurring schedule based on patterns

        Args:
            tenant_id: Tenant ID
            employee_id: Employee ID
            start_date: Date to start generating from
            weeks: Number of weeks to generate

        Returns:
            list: Suggested schedule entries
        """
        patterns = AutomatedScheduler.analyze_employee_patterns(tenant_id, employee_id)

        if not patterns:
            return []

        suggested_schedules = []
        current_date = start_date

        for week in range(weeks):
            for day in range(7):
                schedule_date = current_date + timedelta(days=day)
                day_of_week = schedule_date.weekday()

                # Check if we have a pattern for this day
                if day_of_week in patterns:
                    pattern = patterns[day_of_week]

                    # Only suggest if confidence is high enough
                    if pattern["confidence"] >= 0.5:  # 50% confidence threshold
                        suggested_schedules.append({
                            "date": schedule_date.isoformat(),
                            "start_time": pattern["start_time"],
                            "end_time": pattern["end_time"],
                            "confidence": pattern["confidence"],
                            "auto_generated": True
                        })

            current_date += timedelta(weeks=1)

        return suggested_schedules

    @staticmethod
    def create_recurring_schedules(tenant_id, employee_id, start_date, weeks=4, auto_confirm=False):
        """
        Actually create recurring schedules in database

        Args:
            tenant_id: Tenant ID
            employee_id: Employee ID
            start_date: Date to start from
            weeks: Number of weeks to generate
            auto_confirm: Auto-confirm generated schedules

        Returns:
            int: Number of schedules created
        """
        db = Session()

        try:
            suggestions = AutomatedScheduler.generate_recurring_schedule(
                tenant_id, employee_id, start_date, weeks
            )

            created_count = 0

            for suggestion in suggestions:
                # Check if schedule already exists for this date
                existing = db.query(Schedule).filter(
                    Schedule.tenant_id == tenant_id,
                    Schedule.employee_id == employee_id,
                    Schedule.date == datetime.fromisoformat(suggestion["date"])
                ).first()

                if not existing:
                    schedule = Schedule(
                        tenant_id=tenant_id,
                        employee_id=employee_id,
                        date=datetime.fromisoformat(suggestion["date"]),
                        start_time=suggestion["start_time"],
                        end_time=suggestion["end_time"],
                        is_confirmed=auto_confirm,
                        notes=f"Auto-generated with {int(suggestion['confidence']*100)}% confidence"
                    )

                    db.add(schedule)
                    created_count += 1

            db.commit()
            return created_count

        finally:
            db.close()

    @staticmethod
    def get_schedule_suggestions_for_team(tenant_id, start_date, weeks=4):
        """
        Generate schedule suggestions for entire team

        Args:
            tenant_id: Tenant ID
            start_date: Date to start from
            weeks: Number of weeks to generate

        Returns:
            dict: Suggestions by employee
        """
        db = Session()

        try:
            # Get all active employees
            employees = db.query(User).filter(
                User.tenant_id == tenant_id,
                User.is_active == True,
                User.role.in_(["cashier", "laborer", "manager"])
            ).all()

            team_suggestions = {}

            for employee in employees:
                suggestions = AutomatedScheduler.generate_recurring_schedule(
                    tenant_id, employee.id, start_date, weeks
                )

                if suggestions:
                    team_suggestions[employee.id] = {
                        "employee_name": employee.full_name,
                        "employee_email": employee.email,
                        "suggestions": suggestions
                    }

            return team_suggestions

        finally:
            db.close()

    @staticmethod
    def optimize_coverage(tenant_id, start_date, end_date, target_hours_per_day=8):
        """
        Optimize team coverage to meet target hours

        Args:
            tenant_id: Tenant ID
            start_date: Start date
            end_date: End date
            target_hours_per_day: Desired coverage hours per day

        Returns:
            dict: Coverage gaps and suggestions
        """
        db = Session()

        try:
            # Get all schedules in date range
            schedules = db.query(Schedule).filter(
                Schedule.tenant_id == tenant_id,
                Schedule.date >= start_date,
                Schedule.date <= end_date
            ).order_by(Schedule.date).all()

            # Calculate coverage by day
            coverage_by_day = {}
            current_date = start_date

            while current_date <= end_date:
                date_str = current_date.strftime("%Y-%m-%d")
                day_schedules = [s for s in schedules if s.date.date() == current_date.date()]

                total_hours = 0
                for schedule in day_schedules:
                    # Calculate hours from start_time to end_time
                    start_hour, start_min = map(int, schedule.start_time.split(":"))
                    end_hour, end_min = map(int, schedule.end_time.split(":"))

                    hours = (end_hour - start_hour) + (end_min - start_min) / 60
                    total_hours += hours

                coverage_by_day[date_str] = {
                    "scheduled_hours": round(total_hours, 2),
                    "target_hours": target_hours_per_day,
                    "gap": round(target_hours_per_day - total_hours, 2),
                    "status": "ok" if total_hours >= target_hours_per_day else "understaffed"
                }

                current_date += timedelta(days=1)

            return coverage_by_day

        finally:
            db.close()
