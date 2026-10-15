
from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    attendance,
    departments,
    designations,
    employees,
    users,
    roles,
    leave_types,
    leaves,
    payroll,
    salary_slips,
    notifications,
    reports,
    audit_logs,
    documents,
    holidays,
    shifts,
    salary_components,
    employee_salary_components,
    compensation_history,
    payroll_component_lines,
)


api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)

# Master data
api_router.include_router(departments.router)
api_router.include_router(designations.router)

# Employee and user management
api_router.include_router(employees.router)
api_router.include_router(users.router)

# Role-based access management
api_router.include_router(roles.router)

# Attendance and leave
api_router.include_router(attendance.router)
api_router.include_router(leave_types.router)
api_router.include_router(leaves.router)


# Holiday and calendar management
api_router.include_router(holidays.router)

# Shift and work schedule management
api_router.include_router(shifts.router)

# Documents
api_router.include_router(documents.router)

# Payroll and salary slips
api_router.include_router(payroll.router)
api_router.include_router(salary_components.router)
api_router.include_router(employee_salary_components.router)
api_router.include_router(compensation_history.router)
api_router.include_router(payroll_component_lines.router)
api_router.include_router(salary_slips.router)


# Notifications, reports and auditing
api_router.include_router(notifications.router)
api_router.include_router(reports.router)
api_router.include_router(audit_logs.router)
