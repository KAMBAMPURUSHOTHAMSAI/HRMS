
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import Permission, Role, RolePermission


ROLE_DEFINITIONS = {
    "ADMIN": "Full administrative access",
    "HR": "Human resources operations",
    "EMPLOYEE": "Employee self-service access",
}


# Permission codes used by the HRMS backend.
PERMISSIONS = {
    "EMPLOYEES.READ_SELF": "View own employee profile",
    "EMPLOYEES.UPDATE_SELF": "Update own employee profile",
    "EMPLOYEES.READ": "View employee records",
    "EMPLOYEES.CREATE": "Create employee records",
    "EMPLOYEES.UPDATE": "Update employee records",
    "EMPLOYEES.DELETE": "Deactivate employee records",

    "USERS.READ": "View registered users",
    "USERS.UPDATE": "Update user accounts",

    "DEPARTMENTS.READ": "View departments",
    "DEPARTMENTS.CREATE": "Create departments",
    "DEPARTMENTS.UPDATE": "Update departments",
    "DEPARTMENTS.DELETE": "Delete departments",

    "DESIGNATIONS.READ": "View designations",
    "DESIGNATIONS.CREATE": "Create designations",
    "DESIGNATIONS.UPDATE": "Update designations",
    "DESIGNATIONS.DELETE": "Delete designations",

    "ATTENDANCE.CHECK_IN": "Record own check-in",
    "ATTENDANCE.CHECK_OUT": "Record own check-out",
    "ATTENDANCE.READ_SELF": "View own attendance",
    "ATTENDANCE.READ_ALL": "View employee attendance records",
    "ATTENDANCE.CORRECT": "Correct attendance records",

    "LEAVE_TYPES.READ": "View leave types",
    "LEAVE_TYPES.CREATE": "Create leave types",
    "LEAVE_TYPES.UPDATE": "Update leave types",
    "LEAVE_TYPES.DELETE": "Delete leave types",

    "LEAVES.APPLY": "Apply for leave",
    "LEAVES.READ_SELF": "View own leave requests",
    "LEAVES.READ_BALANCES_SELF": "View own leave balances",
    "LEAVES.READ_ALL": "View all employee leave requests",
    "LEAVES.APPROVE": "Approve leave requests",
    "LEAVES.REJECT": "Reject leave requests",

    
    "HOLIDAYS.READ_SELF": "View holidays available to self",
    "HOLIDAYS.READ_ALL": "View all company holidays",
    "HOLIDAYS.MANAGE": "Create, update and deactivate holidays",
    "HOLIDAYS.SELECT": "Select or cancel own optional holidays",

    "PAYROLL.GENERATE": "Generate payroll runs",
    "PAYROLL.READ_RUNS": "View payroll runs",
    "PAYROLL.READ_RECORDS": "View payroll records",
    "PAYROLL.READ_SELF": "View own payroll",
    "PAYROLL.ADJUST": "Create payroll adjustments",
    "PAYROLL.FINALIZE": "Finalize payroll",
    "PAYROLL.SIMULATE_CREDIT": "Simulate payroll credit",
    "PAYROLL.COMPONENTS_READ": "View salary components and assignments",
    "PAYROLL.COMPONENTS_MANAGE": "Create and manage salary components and employee assignments",
    "PAYROLL.COMPENSATION_MANAGE": "Create and manage employee compensation revisions",

    "SALARY_SLIPS.GENERATE": "Generate salary slips",
    "SALARY_SLIPS.READ_ALL": "View all salary slips",
    "SALARY_SLIPS.READ_SELF": "View own salary slips",
    "SALARY_SLIPS.DOWNLOAD": "Download authorized salary slips",

    "NOTIFICATIONS.READ_SELF": "View own notifications",
    "NOTIFICATIONS.UPDATE_SELF": "Update own notification read status",
    "NOTIFICATIONS.EMAIL_LOGS_READ": "View email delivery logs",
    "NOTIFICATIONS.EMAIL_RETRY": "Retry failed email delivery",

    "NOTIFICATIONS.BROADCAST": "Send organization or department notification broadcasts",

    
    "SHIFTS.READ": "View configured shifts and shift assignment history",
    "SHIFTS.MANAGE": "Create, update and deactivate work shifts",
    "SHIFTS.ASSIGN": "Assign shifts to employees and departments",

    "DOCUMENTS.READ_SELF": "View own documents",
    "DOCUMENTS.UPLOAD_SELF": "Upload own documents",
    "DOCUMENTS.READ_ALL": "View employee documents",
    "DOCUMENTS.UPLOAD_FOR_EMPLOYEE": "Upload documents for employees",
    "DOCUMENTS.DOWNLOAD": "Download authorized documents",
    "DOCUMENTS.DELETE": "Delete authorized documents",

    "REPORTS.DASHBOARD": "View administrative dashboard metrics",
    "REPORTS.ATTENDANCE_READ": "View attendance reports",
    "REPORTS.ATTENDANCE_EXPORT": "Export attendance reports",
    "REPORTS.LEAVES_READ": "View leave reports",
    "REPORTS.LEAVES_EXPORT": "Export leave reports",
    "REPORTS.PAYROLL_READ": "View payroll reports",
    "REPORTS.PAYROLL_EXPORT": "Export payroll reports",

    "ROLES.READ": "View roles",
    "ROLES.MANAGE": "Create and manage roles",
    "PERMISSIONS.READ": "View permissions",
    "PERMISSIONS.MANAGE": "Manage permissions and assignments",
    "AUDIT_LOGS.READ": "View audit logs",
}


# HR receives operational permissions, but not full system administration.
HR_PERMISSIONS = {
    code for code in PERMISSIONS
    if code.startswith((
        "EMPLOYEES.",
        "DEPARTMENTS.",
        "DESIGNATIONS.",
        "ATTENDANCE.",
        "LEAVE_TYPES.",
        "LEAVES.",
        "REPORTS.",
    ))
} | {
    "USERS.READ",
    "USERS.UPDATE",
    
    "HOLIDAYS.READ_ALL",
    "HOLIDAYS.MANAGE",

    "PAYROLL.GENERATE",
    "PAYROLL.READ_RUNS",
    "PAYROLL.READ_RECORDS",
    "PAYROLL.COMPONENTS_READ",
    "PAYROLL.COMPONENTS_MANAGE",
    "PAYROLL.COMPENSATION_MANAGE",
    "SALARY_SLIPS.GENERATE",
    "SALARY_SLIPS.READ_ALL",
    "SALARY_SLIPS.DOWNLOAD",
    "NOTIFICATIONS.EMAIL_LOGS_READ",
    
    "SHIFTS.READ",
    "SHIFTS.MANAGE",
    "SHIFTS.ASSIGN",

    "DOCUMENTS.READ_ALL",
    "DOCUMENTS.UPLOAD_FOR_EMPLOYEE",
    "DOCUMENTS.DOWNLOAD",
    "DOCUMENTS.DELETE",
    "ROLES.READ",
    "PERMISSIONS.READ",
}


# Employees can perform self-service actions only.
EMPLOYEE_PERMISSIONS = {
    "EMPLOYEES.READ_SELF",
    "EMPLOYEES.UPDATE_SELF",
    "ATTENDANCE.CHECK_IN",
    "ATTENDANCE.CHECK_OUT",
    "ATTENDANCE.READ_SELF",
    "LEAVE_TYPES.READ",
    
    "HOLIDAYS.READ_SELF",
    "HOLIDAYS.SELECT",

    "LEAVES.APPLY",
    "LEAVES.READ_SELF",
    "LEAVES.READ_BALANCES_SELF",
    "PAYROLL.READ_SELF",
    "SALARY_SLIPS.READ_SELF",
    "SALARY_SLIPS.DOWNLOAD",
    "NOTIFICATIONS.READ_SELF",
    "NOTIFICATIONS.UPDATE_SELF",
    "DOCUMENTS.READ_SELF",
    "DOCUMENTS.UPLOAD_SELF",
    "DOCUMENTS.DOWNLOAD",
    "DOCUMENTS.DELETE",
}


ROLE_PERMISSION_CODES = {
    "ADMIN": set(PERMISSIONS),
    "HR": HR_PERMISSIONS,
    "EMPLOYEE": EMPLOYEE_PERMISSIONS,
}


def seed_rbac() -> None:
    created_permissions = 0
    created_assignments = 0

    with SessionLocal() as db:
        try:
            # Ensure built-in roles exist without replacing existing records.
            roles = {}

            for name, description in ROLE_DEFINITIONS.items():
                role = db.scalar(
                    select(Role).where(Role.name == name)
                )

                if role is None:
                    role = Role(
                        name=name,
                        description=description,
                        is_active=True,
                    )
                    db.add(role)
                    db.flush()

                roles[name] = role

            # Create missing permissions. Existing permissions are preserved.
            permissions = {}

            for code, description in PERMISSIONS.items():
                permission = db.scalar(
                    select(Permission).where(
                        Permission.code == code
                    )
                )

                if permission is None:
                    permission = Permission(
                        code=code,
                        description=description,
                    )
                    db.add(permission)
                    db.flush()
                    created_permissions += 1

                permissions[code] = permission

            # Grant only the explicitly listed permissions to each role.
            for role_name, permission_codes in ROLE_PERMISSION_CODES.items():
                role = roles[role_name]

                for code in permission_codes:
                    permission = permissions[code]

                    existing = db.get(
                        RolePermission,
                        (role.id, permission.id),
                    )

                    if existing is None:
                        db.add(
                            RolePermission(
                                role_id=role.id,
                                permission_id=permission.id,
                            )
                        )
                        created_assignments += 1

            db.commit()

        except Exception:
            db.rollback()
            raise

    print("RBAC seeding completed successfully.")
    print("New permissions created:", created_permissions)
    print("New role-permission assignments:", created_assignments)


if __name__ == "__main__":
    seed_rbac()
