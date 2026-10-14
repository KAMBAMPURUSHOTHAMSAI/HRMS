from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class SalarySlipRead(BaseModel):
    id: int
    payroll_record_id: int
    employee_id: int
    employee_code: str
    employee_name: str
    employee_email: str
    year: int
    month: int
    file_name: str
    generated_at: datetime
    net_salary: Decimal
    credit_status: str