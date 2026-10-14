
import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft,
  BadgeCheck,
  BriefcaseBusiness,
  Building2,
  CalendarDays,
  IdCard,
  Mail,
  Pencil,
  Phone,
  ShieldCheck,
  UserRound,
  UserX,
  Wallet,
} from "lucide-react";

import {
  deactivateEmployee,
  getEmployee,
} from "../../../api/employeeApi";


function errorMessage(error) {
  return error.response?.data?.detail ||
    "Unable to load employee details.";
}


function formatCurrency(value) {
  if (value === null || value === undefined || value === "") {
    return "—";
  }

  const amount = Number(value);

  if (!Number.isFinite(amount)) {
    return "—";
  }

  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(amount);
}


function formatDate(value) {
  if (!value) return "—";

  const [year, month, day] = String(value).split("-");

  if (!year || !month || !day) return String(value);

  return `${day}-${month}-${year}`;
}


function getInitials(firstName, lastName) {
  const first = String(firstName || "").trim()[0] || "";
  const last = String(lastName || "").trim()[0] || "";

  return `${first}${last}`.toUpperCase() || "EM";
}


function DetailItem({ icon: Icon, label, value, positive }) {
  return (
    <div className="hr-employee-detail-item">
      <span className="hr-info-icon">
        <Icon size={17} />
      </span>

      <div className="hr-info-content">
        <span>{label}</span>
        <strong
          className={
            positive === true
              ? "hr-value-positive"
              : positive === false
                ? "hr-value-inactive"
                : ""
          }
        >
          {value || "—"}
        </strong>
      </div>
    </div>
  );
}


export default function EmployeeDetails() {
  const { employeeId } = useParams();
  const navigate = useNavigate();

  const [employee, setEmployee] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [deactivating, setDeactivating] = useState(false);

  const loadEmployee = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const data = await getEmployee(employeeId);
      setEmployee(data);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [employeeId]);

  useEffect(() => {
    loadEmployee();
  }, [loadEmployee]);

  async function handleDeactivate() {
    if (!employee || deactivating) return;

    const confirmed = window.confirm(
      `Deactivate ${employee.first_name} ${employee.last_name}?`
    );

    if (!confirmed) return;

    setDeactivating(true);
    setError("");

    try {
      await deactivateEmployee(employee.id);

      navigate("/admin/employees", {
        replace: true,
        state: {
          message: `Employee ${employee.employee_code} was deactivated.`,
        },
      });
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setDeactivating(false);
    }
  }

  if (loading) {
    return (
      <div className="page-loading" role="status">
        Loading employee profile...
      </div>
    );
  }

  if (error || !employee) {
    return (
      <div className="dashboard-page">
        <section className="content-card">
          <div className="hr-section-heading">
            <span className="hr-section-icon">
              <UserRound size={21} />
            </span>

            <div>
              <h3>Employee Profile</h3>
              <p>Unable to open this employee record.</p>
            </div>
          </div>

          <div className="alert alert-danger" role="alert">
            {error || "Employee not found."}
          </div>

          <Link
            className="secondary-button"
            to="/admin/employees"
          >
            <ArrowLeft size={16} />
            Back to Employees
          </Link>
        </section>
      </div>
    );
  }

  const fullName =
    `${employee.first_name || ""} ${employee.last_name || ""}`.trim() ||
    "Employee";

  const isActive = Boolean(employee.is_active);

  return (
    <div className="dashboard-page hr-employee-profile">
      <div className="page-heading-row">
        <div>
          <p className="section-kicker">PEOPLE MANAGEMENT</p>
          <h2>Employee Profile</h2>
          <p>
            View personal information, employment details, and account status.
          </p>
        </div>

        <Link
          className="secondary-button"
          to="/admin/employees"
        >
          <ArrowLeft size={16} />
          Back to Employees
        </Link>
      </div>

      {error && (
        <div className="alert alert-danger" role="alert">
          {error}
        </div>
      )}

      <section className="hr-employee-hero">
        <div className="hr-employee-hero-main">
          <div className="hr-employee-avatar" aria-hidden="true">
            {getInitials(employee.first_name, employee.last_name)}
          </div>

          <div className="hr-employee-identity">
            <div className="hr-employee-eyebrow">
              <BadgeCheck size={15} />
              Employee record
            </div>

            <h2>{fullName}</h2>

            <p>
              {employee.designation_name || "Designation not assigned"}
              {employee.department_name
                ? ` · ${employee.department_name}`
                : ""}
            </p>

            <div className="hr-profile-meta">
              <span className="hr-profile-code">
                <IdCard size={14} />
                {employee.employee_code || "Code unavailable"}
              </span>

              <span
                className={`status-pill ${
                  isActive ? "status-active" : "status-inactive"
                }`}
              >
                {isActive ? "Active" : "Inactive"}
              </span>
            </div>

            <div className="hr-profile-contact-row">
              <span className="hr-profile-contact">
                <Mail size={15} />
                {employee.email || "No email available"}
              </span>

              <span className="hr-profile-contact">
                <Phone size={15} />
                {employee.phone || "No phone number"}
              </span>
            </div>
          </div>
        </div>

        <div className="hr-employee-hero-actions">
          <Link
            className="primary-button"
            to={`/admin/employees/${employee.id}/edit`}
          >
            <Pencil size={16} />
            Edit Profile
          </Link>

          {isActive && (
            <button
              className="secondary-button danger-action"
              type="button"
              onClick={handleDeactivate}
              disabled={deactivating}
            >
              <UserX size={16} />
              {deactivating ? "Deactivating..." : "Deactivate"}
            </button>
          )}
        </div>
      </section>

      <section className="content-card">
        <div className="hr-employee-detail-section">
          <div className="hr-section-heading">
            <span className="hr-section-icon">
              <UserRound size={21} />
            </span>

            <div>
              <h3>Personal & Contact Information</h3>
              <p>Employee identity and contact details.</p>
            </div>
          </div>

          <div className="hr-employee-detail-grid">
            <DetailItem
              icon={UserRound}
              label="First Name"
              value={employee.first_name}
            />

            <DetailItem
              icon={UserRound}
              label="Last Name"
              value={employee.last_name}
            />

            <DetailItem
              icon={Mail}
              label="Email Address"
              value={employee.email}
            />

            <DetailItem
              icon={Phone}
              label="Phone Number"
              value={employee.phone}
            />
          </div>
        </div>

        <hr className="section-divider my-4" />

        <div className="hr-employee-detail-section">
          <div className="hr-section-heading">
            <span className="hr-section-icon">
              <BriefcaseBusiness size={21} />
            </span>

            <div>
              <h3>Employment & Compensation</h3>
              <p>Official department, role, joining date, and salary details.</p>
            </div>
          </div>

          <div className="hr-employee-detail-grid">
            <DetailItem
              icon={IdCard}
              label="Employee Code"
              value={employee.employee_code}
            />

            <DetailItem
              icon={Building2}
              label="Department"
              value={employee.department_name}
            />

            <DetailItem
              icon={BriefcaseBusiness}
              label="Designation"
              value={employee.designation_name}
            />

            <DetailItem
              icon={CalendarDays}
              label="Joining Date"
              value={formatDate(employee.joining_date)}
            />

            <DetailItem
              icon={Wallet}
              label="Monthly Salary"
              value={formatCurrency(employee.monthly_salary)}
            />

            <DetailItem
              icon={ShieldCheck}
              label="Employment Status"
              value={
                employee.employment_status ||
                (isActive ? "ACTIVE" : "INACTIVE")
              }
              positive={isActive}
            />
          </div>
        </div>
      </section>
    </div>
  );
}
