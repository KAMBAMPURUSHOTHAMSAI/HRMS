
import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Save } from "lucide-react";

import {
  createEmployee,
  getEmployee,
  updateEmployee,
} from "../../../api/employeeApi";

import { getDepartments } from "../../../api/departmentApi";
import { getDesignations } from "../../../api/designationApi";

const initialForm = {
  email: "",
  password: "",
  first_name: "",
  last_name: "",
  employee_code: "",
  phone: "",
  department_id: "",
  designation_id: "",
  joining_date: "",
  monthly_salary: "",
};

function messageFromError(error) {
  const detail = error.response?.data?.detail;

  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg).join(", ");
  }

  return detail || "Unable to save employee.";
}

export default function EmployeeForm() {
  const { employeeId } = useParams();
  const editing = Boolean(employeeId);

  const navigate = useNavigate();

  const [form, setForm] = useState(initialForm);
  const [departments, setDepartments] = useState([]);
  const [designations, setDesignations] = useState([]);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function loadFormData() {
      setLoading(true);
      setError("");

      try {
        const [departmentData, designationData, employeeData] =
          await Promise.all([
            getDepartments(),
            getDesignations(),
            editing ? getEmployee(employeeId) : Promise.resolve(null),
          ]);

        if (cancelled) return;

        setDepartments(departmentData);
        setDesignations(designationData);

        if (employeeData) {
          setForm({
            ...initialForm,
            email: employeeData.email,
            first_name: employeeData.first_name,
            last_name: employeeData.last_name,
            employee_code: employeeData.employee_code,
            phone: employeeData.phone || "",
            department_id: String(employeeData.department_id),
            designation_id: String(employeeData.designation_id),
            joining_date: employeeData.joining_date,
            monthly_salary: String(employeeData.monthly_salary),
          });
        } else {
          const localDate = new Date(
            Date.now() - new Date().getTimezoneOffset() * 60000
          )
            .toISOString()
            .slice(0, 10);

          setForm((previous) => ({
            ...previous,
            joining_date: localDate,
          }));
        }
      } catch (err) {
        if (!cancelled) setError(messageFromError(err));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadFormData();

    return () => {
      cancelled = true;
    };
  }, [editing, employeeId]);

  const activeDepartments = useMemo(
    () => departments.filter((department) => department.is_active),
    [departments]
  );

  const activeDesignations = useMemo(
    () =>
      designations.filter(
        (designation) =>
          designation.is_active &&
          String(designation.department_id) === String(form.department_id)
      ),
    [designations, form.department_id]
  );

  function handleChange(event) {
    const { name, value } = event.target;

    setForm((previous) => {
      const updated = { ...previous, [name]: value };

      if (name === "department_id") {
        updated.designation_id = "";
      }

      return updated;
    });
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setSaving(true);
    setError("");

    const payload = {
      first_name: form.first_name.trim(),
      last_name: form.last_name.trim(),
      phone: form.phone.trim() || null,
      department_id: Number(form.department_id),
      designation_id: Number(form.designation_id),
      joining_date: form.joining_date,
      monthly_salary: form.monthly_salary,
    };

    try {
      if (editing) {
        await updateEmployee(employeeId, payload);
        navigate(`/admin/employees/${employeeId}`);
      } else {
        await createEmployee({
          ...payload,
          email: form.email.trim().toLowerCase(),
          password: form.password,
          employee_code: form.employee_code.trim(),
        });

        navigate("/admin/employees");
      }
    } catch (err) {
      setError(messageFromError(err));
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return <div className="page-loading">Loading employee form...</div>;
  }

  return (
    <div className="dashboard-page">
      <div className="page-heading-row">
        <div>
          <p className="section-kicker">PEOPLE MANAGEMENT</p>
          <h2>{editing ? "Edit Employee" : "Add Employee"}</h2>
          <p>
            {editing
              ? "Update employment and profile information."
              : "Create a login account and employee profile."}
          </p>
        </div>

        <Link className="secondary-button" to="/admin/employees">
          <ArrowLeft size={16} />
          Back to Employees
        </Link>
      </div>

      {error && <div className="alert alert-danger">{error}</div>}

      <form className="content-card employee-form" onSubmit={handleSubmit}>
        <h3>Personal Information</h3>

        <div className="employee-form-grid">
          <div className="form-field">
            <label htmlFor="first_name">First Name *</label>
            <input
              id="first_name"
              name="first_name"
              required
              maxLength={100}
              value={form.first_name}
              onChange={handleChange}
            />
          </div>

          <div className="form-field">
            <label htmlFor="last_name">Last Name *</label>
            <input
              id="last_name"
              name="last_name"
              required
              maxLength={100}
              value={form.last_name}
              onChange={handleChange}
            />
          </div>

          <div className="form-field">
            <label htmlFor="phone">Phone</label>
            <input
              id="phone"
              name="phone"
              maxLength={20}
              value={form.phone}
              onChange={handleChange}
            />
          </div>

          <div className="form-field">
            <label htmlFor="email">Email *</label>
            <input
              id="email"
              name="email"
              type="email"
              required
              disabled={editing}
              value={form.email}
              onChange={handleChange}
            />
          </div>

          {!editing && (
            <>
              <div className="form-field">
                <label htmlFor="password">Initial Password *</label>
                <input
                  id="password"
                  name="password"
                  type="password"
                  minLength={12}
                  maxLength={128}
                  autoComplete="new-password"
                  required
                  value={form.password}
                  onChange={handleChange}
                />
                <small>At least 12 characters. Share it securely.</small>
              </div>

              <div className="form-field">
                <label htmlFor="employee_code">Employee Code *</label>
                <input
                  id="employee_code"
                  name="employee_code"
                  pattern="[A-Za-z0-9_-]+"
                  minLength={2}
                  maxLength={30}
                  required
                  value={form.employee_code}
                  onChange={handleChange}
                />
              </div>
            </>
          )}
        </div>

        <hr className="section-divider" />

        <h3>Employment Details</h3>

        <div className="employee-form-grid">
          <div className="form-field">
            <label htmlFor="department_id">Department *</label>
            <select
              id="department_id"
              name="department_id"
              required
              value={form.department_id}
              onChange={handleChange}
            >
              <option value="">Select department</option>
              {activeDepartments.map((department) => (
                <option key={department.id} value={department.id}>
                  {department.name}
                </option>
              ))}
            </select>
          </div>

          <div className="form-field">
            <label htmlFor="designation_id">Designation *</label>
            <select
              id="designation_id"
              name="designation_id"
              required
              disabled={!form.department_id}
              value={form.designation_id}
              onChange={handleChange}
            >
              <option value="">Select designation</option>
              {activeDesignations.map((designation) => (
                <option key={designation.id} value={designation.id}>
                  {designation.name}
                </option>
              ))}
            </select>
          </div>

          <div className="form-field">
            <label htmlFor="joining_date">Joining Date *</label>
            <input
              id="joining_date"
              name="joining_date"
              type="date"
              required
              value={form.joining_date}
              onChange={handleChange}
            />
          </div>

          <div className="form-field">
            <label htmlFor="monthly_salary">Monthly Salary (INR) *</label>
            <input
              id="monthly_salary"
              name="monthly_salary"
              type="number"
              min="0.01"
              step="0.01"
              required
              value={form.monthly_salary}
              onChange={handleChange}
            />
          </div>
        </div>

        {editing && (
          <div className="form-field employee-code-readonly">
            <label>Employee Code</label>
            <input value={form.employee_code} disabled />
          </div>
        )}

        <div className="form-actions">
          <Link className="secondary-button" to="/admin/employees">
            Cancel
          </Link>

          <button
            className="primary-button"
            type="submit"
            disabled={saving}
          >
            <Save size={17} />
            {saving
              ? "Saving..."
              : editing
                ? "Save Changes"
                : "Create Employee"}
          </button>
        </div>
      </form>
    </div>
  );
}
