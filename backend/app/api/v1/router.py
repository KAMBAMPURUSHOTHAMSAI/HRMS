
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

# Documents
api_router.include_router(documents.router)

# Payroll and salary slips
api_router.include_router(payroll.router)
api_router.include_router(salary_slips.router)

# Notifications, reports and auditing
api_router.include_router(notifications.router)
api_router.include_router(reports.router)
api_router.include_router(audit_logs.router)
