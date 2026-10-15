
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.security import hash_password
from app.models.department import Department
from app.models.designation import Designation
from app.models.employee import Employee
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.schemas.employee import (
    EmployeeCreate,
    EmployeeRead,
    EmployeeSelfUpdate,
    EmployeeUpdate,
)


def get_employee_or_404(db: Session, employee_id: int) -> Employee:
    statement = (
        select(Employee)
        .options(
            selectinload(Employee.user),
            selectinload(Employee.department),
            selectinload(Employee.designation),
        )
        .where(Employee.id == employee_id)
    )

    employee = db.scalar(statement)

    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found",
        )

    return employee


def get_active_department(db: Session, department_id: int) -> Department:
    department = db.get(Department, department_id)

    if department is None or not department.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Department does not exist or is inactive",
        )

    return department


def get_valid_designation(
    db: Session,
    designation_id: int,
    department_id: int,
) -> Designation:
    designation = db.get(Designation, designation_id)

    if designation is None or not designation.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Designation does not exist or is inactive",
        )

    if designation.department_id != department_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Designation must belong to the selected department",
        )

    return designation


def serialize_employee(employee: Employee) -> EmployeeRead:
    return EmployeeRead(
        id=employee.id,
        user_id=employee.user_id,
        employee_code=employee.employee_code,
        email=employee.user.email,
        first_name=employee.user.first_name,
        last_name=employee.user.last_name,
        phone=employee.phone,
        region=employee.region,
        department_id=employee.department_id,
        department_name=employee.department.name,
        designation_id=employee.designation_id,
        designation_name=employee.designation.name,
        joining_date=employee.joining_date,
        monthly_salary=employee.monthly_salary,
        employment_status=employee.employment_status,
        is_active=employee.user.is_active,
        created_at=employee.created_at,
    )


def list_employees(db: Session) -> list[EmployeeRead]:
    statement = (
        select(Employee)
        .options(
            selectinload(Employee.user),
            selectinload(Employee.department),
            selectinload(Employee.designation),
        )
        .order_by(Employee.id)
    )

    employees = db.scalars(statement).all()

    return [serialize_employee(employee) for employee in employees]


def create_employee(
    db: Session,
    payload: EmployeeCreate,
) -> EmployeeRead:
    email = str(payload.email).strip().lower()
    employee_code = payload.employee_code.strip()

    existing_user = db.scalar(
        select(User).where(User.email == email)
    )

    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    existing_employee = db.scalar(
        select(Employee).where(
            Employee.employee_code == employee_code
        )
    )

    if existing_employee is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Employee code already exists",
        )

    get_active_department(db, payload.department_id)

    get_valid_designation(
        db,
        payload.designation_id,
        payload.department_id,
    )

    employee_role = db.scalar(
        select(Role).where(Role.name == "EMPLOYEE")
    )

    if employee_role is None or not employee_role.is_active:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Employee role is not configured",
        )

    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        first_name=payload.first_name.strip(),
        last_name=payload.last_name.strip(),
        is_active=True,
    )

    # Normalize optional region without changing existing employee fields.
    region = (
        payload.region.strip()
        if payload.region and payload.region.strip()
        else None
    )

    try:
        db.add(user)
        db.flush()

        db.add(
            UserRole(
                user_id=user.id,
                role_id=employee_role.id,
            )
        )

        employee = Employee(
            user_id=user.id,
            employee_code=employee_code,
            phone=payload.phone,
            region=region,
            department_id=payload.department_id,
            designation_id=payload.designation_id,
            joining_date=payload.joining_date,
            monthly_salary=payload.monthly_salary,
            employment_status="ACTIVE",
        )

        db.add(employee)
        db.flush()

        employee_id = employee.id

        db.commit()

        return serialize_employee(
            get_employee_or_404(db, employee_id)
        )

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Duplicate employee data or a database "
                "constraint was violated"
            ),
        ) from None


def update_employee(
    db: Session,
    employee_id: int,
    payload: EmployeeUpdate,
) -> EmployeeRead:
    employee = get_employee_or_404(db, employee_id)
    changes = payload.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide at least one field to update",
        )

    for field in ("first_name", "last_name"):
        if field in changes:
            value = changes[field]

            if value is None or not value.strip():
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"{field} cannot be empty",
                )

            changes[field] = value.strip()

    # Allow admins/HR to normalize or clear an employee's region.
    if "region" in changes:
        region = changes["region"]

        if region is not None:
            region = region.strip() or None

        changes["region"] = region

    target_department_id = (
        changes.get("department_id")
        if changes.get("department_id") is not None
        else employee.department_id
    )

    target_designation_id = (
        changes.get("designation_id")
        if changes.get("designation_id") is not None
        else employee.designation_id
    )

    if "department_id" in changes or "designation_id" in changes:
        get_active_department(db, target_department_id)

        get_valid_designation(
            db,
            target_designation_id,
            target_department_id,
        )

    try:
        for field, value in changes.items():
            if field in ("first_name", "last_name"):
                setattr(employee.user, field, value)

            # Explicit None is permitted for optional phone/region.
            elif value is not None or field in ("phone", "region"):
                setattr(employee, field, value)

        db.commit()

        return serialize_employee(
            get_employee_or_404(db, employee_id)
        )

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Unable to update employee because of a data constraint"
            ),
        ) from None


def update_my_employee_profile(
    db: Session,
    employee_id: int,
    payload: EmployeeSelfUpdate,
) -> EmployeeRead:
    employee = get_employee_or_404(db, employee_id)

    changes = payload.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide at least one field to update",
        )

    for field in ("first_name", "last_name"):
        if field in changes:
            value = changes[field]

            if value is None or not value.strip():
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"{field} cannot be empty",
                )

            setattr(employee.user, field, value.strip())

    if "phone" in changes:
        phone = changes["phone"]

        if phone is None or not phone.strip():
            employee.phone = None
        else:
            employee.phone = phone.strip()

    # Employee self-update intentionally cannot change region.
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unable to update your profile",
        ) from None

    updated_employee = get_employee_or_404(db, employee_id)
    return serialize_employee(updated_employee)


def deactivate_employee(
    db: Session,
    employee_id: int,
) -> EmployeeRead:
    employee = get_employee_or_404(db, employee_id)

    employee.employment_status = "INACTIVE"
    employee.user.is_active = False

    db.commit()

    return serialize_employee(
        get_employee_or_404(db, employee_id)
    )
