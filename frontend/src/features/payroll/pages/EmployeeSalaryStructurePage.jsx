
import { useCallback, useEffect, useState } from "react";
import {
  History,
  RefreshCw,
  Save,
  UserRound,
  Wallet,
} from "lucide-react";

import { getEmployees } from "../../../api/employeeApi";
import {
  assignEmployeeSalaryComponent,
  createCompensationRevision,
  getCompensationHistory,
  getEmployeeSalaryComponents,
  getSalaryComponents,
} from "../../../api/payrollApi";

const today = () => {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};

const initialAssignment = {
  component_id: "",
  amount_override: "",
  effective_from: today(),
  effective_to: "",
  notes: "",
};

const initialRevision = {
  previous_monthly_salary: "",
  new_monthly_salary: "",
  effective_from: today(),
  effective_to: "",
  reason: "",
  notes: "",
};

function messageFromError(error) {
  const detail = error?.response?.data?.detail;

  if (typeof detail === "string") return detail;

  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg || "Invalid field").join(", ");
  }

  return "Request failed. Please check the data and try again.";
}

function currency(value) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(Number(value ?? 0));
}

export default function EmployeeSalaryStructurePage() {
  const [employees, setEmployees] = useState([]);
  const [components, setComponents] = useState([]);
  const [selectedEmployeeId, setSelectedEmployeeId] = useState("");

  const [assignments, setAssignments] = useState([]);
  const [history, setHistory] = useState([]);

  const [assignment, setAssignment] = useState(initialAssignment);
  const [revision, setRevision] = useState(initialRevision);

  const [loading, setLoading] = useState(true);
  const [savingAssignment, setSavingAssignment] = useState(false);
  const [savingRevision, setSavingRevision] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const loadReferenceData = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const [employeeData, componentData] = await Promise.all([
        getEmployees(),
        getSalaryComponents(false),
      ]);

      const employeeList = Array.isArray(employeeData)
        ? employeeData
        : [];

      setEmployees(employeeList);
      setComponents(
        Array.isArray(componentData) ? componentData : []
      );

      if (!selectedEmployeeId && employeeList.length > 0) {
        setSelectedEmployeeId(String(employeeList[0].id));
      }
    } catch (err) {
      setError(messageFromError(err));
    } finally {
      setLoading(false);
    }
  }, [selectedEmployeeId]);

  const loadEmployeeData = useCallback(async () => {
    if (!selectedEmployeeId) {
      setAssignments([]);
      setHistory([]);
      return;
    }

    setError("");

    try {
      const [assignmentData, historyData] = await Promise.all([
        getEmployeeSalaryComponents({
          employeeId: Number(selectedEmployeeId),
        }),
        getCompensationHistory(Number(selectedEmployeeId)),
      ]);

      setAssignments(
        Array.isArray(assignmentData) ? assignmentData : []
      );

      setHistory(
        Array.isArray(historyData) ? historyData : []
      );
    } catch (err) {
      setError(messageFromError(err));
    }
  }, [selectedEmployeeId]);

  useEffect(() => {
    loadReferenceData();
  }, [loadReferenceData]);

  useEffect(() => {
    loadEmployeeData();
  }, [loadEmployeeData]);

  const selectedEmployee = employees.find(
    (employee) => String(employee.id) === String(selectedEmployeeId)
  );

  function updateAssignment(event) {
    const { name, value } = event.target;
    setAssignment((previous) => ({
      ...previous,
      [name]: value,
    }));
  }

  function updateRevision(event) {
    const { name, value } = event.target;
    setRevision((previous) => ({
      ...previous,
      [name]: value,
    }));
  }

  async function handleAssign(event) {
    event.preventDefault();
    setError("");
    setNotice("");

    if (!selectedEmployeeId) {
      setError("Select an employee first.");
      return;
    }

    if (!assignment.component_id) {
      setError("Select a salary component.");
      return;
    }

    const effectiveFrom = assignment.effective_from;
    const effectiveTo = assignment.effective_to || null;

    if (effectiveTo && effectiveTo < effectiveFrom) {
      setError("End date cannot be earlier than start date.");
      return;
    }

    const override = assignment.amount_override.trim();

    if (override !== "" && (
      !Number.isFinite(Number(override)) ||
      Number(override) < 0
    )) {
      setError("Enter a valid non-negative override amount.");
      return;
    }

    setSavingAssignment(true);

    try {
      await assignEmployeeSalaryComponent({
        employee_id: Number(selectedEmployeeId),
        component_id: Number(assignment.component_id),
        amount_override: override === "" ? null : Number(override).toFixed(2),
        effective_from: effectiveFrom,
        effective_to: effectiveTo,
        notes: assignment.notes.trim() || null,
      });

      setNotice("Salary component assigned successfully.");
      setAssignment({
        ...initialAssignment,
        effective_from: today(),
      });

      await loadEmployeeData();
    } catch (err) {
      setError(messageFromError(err));
    } finally {
      setSavingAssignment(false);
    }
  }

  async function handleRevision(event) {
    event.preventDefault();
    setError("");
    setNotice("");

    if (!selectedEmployeeId) {
      setError("Select an employee first.");
      return;
    }

    const newSalary = Number(revision.new_monthly_salary);

    if (!Number.isFinite(newSalary) || newSalary <= 0) {
      setError("New monthly salary must be greater than zero.");
      return;
    }

    const effectiveFrom = revision.effective_from;
    const effectiveTo = revision.effective_to || null;

    if (effectiveTo && effectiveTo < effectiveFrom) {
      setError("End date cannot be earlier than start date.");
      return;
    }

    setSavingRevision(true);

    try {
      const previousSalary = revision.previous_monthly_salary.trim();

      await createCompensationRevision({
        employee_id: Number(selectedEmployeeId),
        previous_monthly_salary:
          previousSalary === "" ? null : Number(previousSalary).toFixed(2),
        new_monthly_salary: newSalary.toFixed(2),
        effective_from: effectiveFrom,
        effective_to: effectiveTo,
        reason: revision.reason.trim(),
        notes: revision.notes.trim() || null,
      });

      setNotice("Compensation revision saved successfully.");
      setRevision({
        ...initialRevision,
        effective_from: today(),
      });

      await loadEmployeeData();
    } catch (err) {
      setError(messageFromError(err));
    } finally {
      setSavingRevision(false);
    }
  }

  function componentName(componentId) {
    return (
      components.find(
        (item) => item.id === componentId
      )?.name || `Component #${componentId}`
    );
  }

  return (
    <div className="container-fluid py-3">
      <div className="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
        <div>
          <p className="text-muted small mb-1">PAYROLL MANAGEMENT</p>
          <h2 className="mb-1">Employee Salary Structure</h2>
          <p className="text-muted mb-0">
            Assign salary components and record compensation revisions.
          </p>
        </div>

        <button
          type="button"
          className="btn btn-outline-primary"
          onClick={() => {
            loadReferenceData();
            loadEmployeeData();
          }}
          disabled={loading}
        >
          <RefreshCw size={16} className="me-2" />
          Refresh
        </button>
      </div>

      {error && (
        <div className="alert alert-danger" role="alert">
          {error}
        </div>
      )}

      {notice && (
        <div className="alert alert-success" role="status">
          {notice}
        </div>
      )}

      <div className="card mb-4">
        <div className="card-body">
          <label htmlFor="salary-employee" className="form-label">
            <UserRound size={16} className="me-2" />
            Select Employee
          </label>

          <select
            id="salary-employee"
            className="form-select"
            value={selectedEmployeeId}
            onChange={(event) => setSelectedEmployeeId(event.target.value)}
            disabled={loading}
          >
            <option value="">Select an employee</option>

            {employees.map((employee) => (
              <option key={employee.id} value={employee.id}>
                {employee.employee_code} — {employee.first_name} {employee.last_name}
              </option>
            ))}
          </select>

          {selectedEmployee && (
            <div className="mt-3 text-muted small">
              Employee ID: {selectedEmployee.id}
              {" · "}
              {selectedEmployee.department_name || "No department"}
              {" · "}
              {selectedEmployee.designation_name || "No designation"}
            </div>
          )}
        </div>
      </div>

      <div className="row g-4 mb-4">
        <div className="col-xl-6">
          <div className="card h-100">
            <div className="card-header bg-body">
              <h5 className="mb-0">
                <Wallet size={17} className="me-2" />
                Assign Salary Component
              </h5>
            </div>

            <div className="card-body">
              <form onSubmit={handleAssign}>
                <div className="mb-3">
                  <label htmlFor="salary-component" className="form-label">
                    Salary Component
                  </label>

                  <select
                    id="salary-component"
                    name="component_id"
                    className="form-select"
                    value={assignment.component_id}
                    onChange={updateAssignment}
                    required
                  >
                    <option value="">Select component</option>

                    {components.map((component) => (
                      <option key={component.id} value={component.id}>
                        {component.code} — {component.name} ({component.component_type})
                      </option>
                    ))}
                  </select>
                </div>

                <div className="mb-3">
                  <label htmlFor="salary-override" className="form-label">
                    Employee Amount Override (₹)
                  </label>

                  <input
                    id="salary-override"
                    name="amount_override"
                    type="number"
                    min="0"
                    step="0.01"
                    className="form-control"
                    value={assignment.amount_override}
                    onChange={updateAssignment}
                    placeholder="Leave empty to use component default"
                  />
                </div>

                <div className="row g-3 mb-3">
                  <div className="col-md-6">
                    <label htmlFor="assignment-start" className="form-label">
                      Effective From
                    </label>

                    <input
                      id="assignment-start"
                      name="effective_from"
                      type="date"
                      className="form-control"
                      value={assignment.effective_from}
                      onChange={updateAssignment}
                      required
                    />
                  </div>

                  <div className="col-md-6">
                    <label htmlFor="assignment-end" className="form-label">
                      Effective To
                    </label>

                    <input
                      id="assignment-end"
                      name="effective_to"
                      type="date"
                      className="form-control"
                      value={assignment.effective_to}
                      onChange={updateAssignment}
                    />
                  </div>
                </div>

                <div className="mb-3">
                  <label htmlFor="assignment-notes" className="form-label">
                    Notes
                  </label>

                  <textarea
                    id="assignment-notes"
                    name="notes"
                    className="form-control"
                    rows={2}
                    value={assignment.notes}
                    onChange={updateAssignment}
                  />
                </div>

                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={savingAssignment || !selectedEmployeeId}
                >
                  <Save size={16} className="me-2" />
                  {savingAssignment ? "Saving..." : "Assign Component"}
                </button>
              </form>
            </div>
          </div>
        </div>

        <div className="col-xl-6">
          <div className="card h-100">
            <div className="card-header bg-body">
              <h5 className="mb-0">
                <History size={17} className="me-2" />
                Record Compensation Revision
              </h5>
            </div>

            <div className="card-body">
              <form onSubmit={handleRevision}>
                <div className="row g-3 mb-3">
                  <div className="col-md-6">
                    <label htmlFor="previous-salary" className="form-label">
                      Previous Monthly Salary (₹)
                    </label>

                    <input
                      id="previous-salary"
                      name="previous_monthly_salary"
                      type="number"
                      min="0"
                      step="0.01"
                      className="form-control"
                      value={revision.previous_monthly_salary}
                      onChange={updateRevision}
                      placeholder="Auto-detect when omitted"
                    />
                  </div>

                  <div className="col-md-6">
                    <label htmlFor="new-salary" className="form-label">
                      New Monthly Salary (₹)
                    </label>

                    <input
                      id="new-salary"
                      name="new_monthly_salary"
                      type="number"
                      min="0.01"
                      step="0.01"
                      className="form-control"
                      value={revision.new_monthly_salary}
                      onChange={updateRevision}
                      required
                    />
                  </div>
                </div>

                <div className="row g-3 mb-3">
                  <div className="col-md-6">
                    <label htmlFor="revision-start" className="form-label">
                      Effective From
                    </label>

                    <input
                      id="revision-start"
                      name="effective_from"
                      type="date"
                      className="form-control"
                      value={revision.effective_from}
                      onChange={updateRevision}
                      required
                    />
                  </div>

                  <div className="col-md-6">
                    <label htmlFor="revision-end" className="form-label">
                      Effective To
                    </label>

                    <input
                      id="revision-end"
                      name="effective_to"
                      type="date"
                      className="form-control"
                      value={revision.effective_to}
                      onChange={updateRevision}
                    />
                  </div>
                </div>

                <div className="mb-3">
                  <label htmlFor="revision-reason" className="form-label">
                    Reason for Revision
                  </label>

                  <input
                    id="revision-reason"
                    name="reason"
                    className="form-control"
                    minLength={2}
                    maxLength={500}
                    value={revision.reason}
                    onChange={updateRevision}
                    placeholder="Annual increment, promotion, salary correction..."
                    required
                  />
                </div>

                <div className="mb-3">
                  <label htmlFor="revision-notes" className="form-label">
                    Notes
                  </label>

                  <textarea
                    id="revision-notes"
                    name="notes"
                    className="form-control"
                    rows={2}
                    value={revision.notes}
                    onChange={updateRevision}
                  />
                </div>

                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={savingRevision || !selectedEmployeeId}
                >
                  <Save size={16} className="me-2" />
                  {savingRevision ? "Saving..." : "Save Revision"}
                </button>
              </form>
            </div>
          </div>
        </div>
      </div>

      <div className="card mb-4">
        <div className="card-header bg-body">
          <h5 className="mb-0">Assigned Salary Components</h5>
        </div>

        <div className="card-body">
          {assignments.length === 0 ? (
            <p className="text-muted mb-0">
              No salary component assignments found for this employee.
            </p>
          ) : (
            <div className="table-responsive">
              <table className="table table-hover align-middle">
                <thead>
                  <tr>
                    <th>Component</th>
                    <th>Override</th>
                    <th>Effective From</th>
                    <th>Effective To</th>
                    <th>Notes</th>
                  </tr>
                </thead>

                <tbody>
                  {assignments.map((item) => (
                    <tr key={item.id}>
                      <td>{componentName(item.component_id)}</td>
                      <td>
                        {item.amount_override == null
                          ? "Use default"
                          : currency(item.amount_override)}
                      </td>
                      <td>{item.effective_from}</td>
                      <td>{item.effective_to || "Ongoing"}</td>
                      <td>{item.notes || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      <div className="card">
        <div className="card-header bg-body">
          <h5 className="mb-0">Compensation History</h5>
        </div>

        <div className="card-body">
          {history.length === 0 ? (
            <p className="text-muted mb-0">
              No compensation revisions found for this employee.
            </p>
          ) : (
            <div className="table-responsive">
              <table className="table table-hover align-middle">
                <thead>
                  <tr>
                    <th>Effective From</th>
                    <th>Effective To</th>
                    <th>Previous Salary</th>
                    <th>New Salary</th>
                    <th>Reason</th>
                  </tr>
                </thead>

                <tbody>
                  {history.map((item) => (
                    <tr key={item.id}>
                      <td>{item.effective_from}</td>
                      <td>{item.effective_to || "Ongoing"}</td>
                      <td>
                        {item.previous_monthly_salary == null
                          ? "—"
                          : currency(item.previous_monthly_salary)}
                      </td>
                      <td className="fw-semibold">
                        {currency(item.new_monthly_salary)}
                      </td>
                      <td>
                        <div>{item.reason}</div>
                        {item.notes && (
                          <small className="text-muted">{item.notes}</small>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
