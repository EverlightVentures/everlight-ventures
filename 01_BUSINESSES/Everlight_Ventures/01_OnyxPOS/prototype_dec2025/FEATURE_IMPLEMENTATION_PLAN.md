# OnyxPOS Feature Implementation Plan

## Priority Queue

### 🔴 CRITICAL (In Progress)

#### 1. ✅ CSV Import Fix
**Status:** COMPLETED
- Added FormData handling to axios interceptor
- Removes Content-Type header for multipart uploads

#### 2. 🟡 Payroll Run Tracking
**Status:** IN PROGRESS
**Scope:**
- Add "Payroll Run" status to track processed payroll periods
- Show accumulated hours for upcoming payroll period
- Mark payroll as "run" to lock in the hours/amounts
- Visual indicator: Green checkmark if ran, Red warning if pending

**Implementation:**
- [ ] Create PayrollPeriod model (start_date, end_date, status, total_amount)
- [ ] Add endpoint POST /api/v1/payroll/run-payroll
- [ ] Update frontend to show "Next Period" and "Run Payroll" button
- [ ] Add visual indicators for payroll status

---

### 🟠 HIGH PRIORITY

#### 3. Time Off Request System
**Scope:**
- Employees can submit time-off requests
- Managers/Owners can approve/deny
- Shows on schedule as "Requested" vs "Approved"
- Email notifications on approval/denial

**Implementation:**
- [ ] Create TimeOffRequest model (user_id, start_date, end_date, reason, status, approved_by)
- [ ] Add endpoints: POST /time-off/request, PUT /time-off/{id}/approve, PUT /time-off/{id}/deny
- [ ] Add "Request Time Off" button to Schedule page
- [ ] Show pending requests with approve/deny actions
- [ ] Integrate with calendar view

#### 4. Task Management System (Asana-style)
**Scope:**
- Create tasks with title, description, assignee, due date
- Statuses: Received → Acknowledged → In Progress → Complete
- Role-based visibility (owners create, employees complete)
- Daily task list view

**Implementation:**
- [ ] Create Task model (title, description, assigned_to, created_by, status, due_date, priority)
- [ ] Add CRUD endpoints for tasks
- [ ] Create new "Tasks" page in navigation
- [ ] Kanban board view with status columns
- [ ] Daily digest of tasks

#### 5. Real-Time Analytics Dashboard
**Scope:**
- Pull actual sales data from transactions
- Show today's revenue, transactions, top items
- Live graphs that update as sales happen
- Employee performance metrics

**Implementation:**
- [ ] Fix /api/v1/analytics/dashboard endpoint
- [ ] Query actual Transaction data
- [ ] Add WebSocket or polling for real-time updates
- [ ] Charts: Sales trend, top items, hourly breakdown

---

### 🟡 MEDIUM PRIORITY

#### 6. Visual Effects & Polish
**Scope:**
- Add micro-interactions (hover states, click animations)
- Gradient overlays on cards
- Smooth transitions between pages
- Loading skeletons
- Success/error animations
- Glassmorphism effects on modals

**Implementation:**
- [ ] Add framer-motion animations to all cards
- [ ] Gradient borders on interactive elements
- [ ] Page transition animations
- [ ] Skeleton loaders for all data fetches
- [ ] Toast notification animations
- [ ] Modal slide-in effects

---

## Database Schema Changes Needed

### New Models:

```python
class PayrollPeriod(Base):
    id, tenant_id
    period_start, period_end
    status (pending, processing, completed)
    total_amount, total_hours
    run_date, run_by_user_id
    notes

class TimeOffRequest(Base):
    id, tenant_id, user_id
    start_date, end_date
    reason, type (vacation, sick, personal)
    status (pending, approved, denied)
    approved_by_user_id, approved_at
    notes

class Task(Base):
    id, tenant_id
    title, description
    assigned_to_user_id, created_by_user_id
    status (received, acknowledged, in_progress, complete)
    priority (low, medium, high)
    due_date
    completed_at
```

---

## API Endpoints to Add

### Payroll
- POST /api/v1/payroll/run-payroll
- GET /api/v1/payroll/periods
- GET /api/v1/payroll/current-period

### Time Off
- POST /api/v1/time-off/request
- GET /api/v1/time-off
- PUT /api/v1/time-off/{id}/approve
- PUT /api/v1/time-off/{id}/deny
- DELETE /api/v1/time-off/{id}

### Tasks
- POST /api/v1/tasks
- GET /api/v1/tasks
- PUT /api/v1/tasks/{id}
- DELETE /api/v1/tasks/{id}
- PUT /api/v1/tasks/{id}/status

### Analytics (Fix existing)
- GET /api/v1/analytics/dashboard (fix to use real data)
- GET /api/v1/analytics/realtime

---

## UI Pages to Create/Update

### New Pages:
1. Tasks page (Kanban board)

### Pages to Update:
1. Payroll - Add period selector, "Run Payroll" button, status indicators
2. Schedule - Add "Request Time Off" button, show approved/pending requests
3. Dashboard - Fix to show real transaction data
4. All pages - Add visual polish and animations

---

## Timeline Estimate

**Phase 1 (Critical):**
- Payroll Run Tracking: 2-3 hours
- CSV Import: ✅ DONE

**Phase 2 (High Priority):**
- Time Off System: 3-4 hours
- Task Management: 4-5 hours
- Analytics Fix: 2-3 hours

**Phase 3 (Polish):**
- Visual Effects: 3-4 hours

**Total:** ~15-20 hours of development

---

## Next Steps (Immediate)

1. ✅ Fix CSV import
2. 🔄 Add payroll run tracking
3. Create time off request system
4. Build task management
5. Fix analytics
6. Polish UI

