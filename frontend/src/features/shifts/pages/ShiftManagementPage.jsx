
import { useCallback, useEffect, useState } from "react";
import {
  Clock3,
  Plus,
  RefreshCw,
  Save,
  X,
  CalendarClock,
  Users,
  ClipboardList,
} from "lucide-react";

import {
  getShifts,
  createShift,
  updateShift,
  deactivateShift,
  getShiftAssignments,
  assignShift,
  getShiftAttendanceReport,
} from "../../../api/shiftApi";

import { getDepartments } from "../../../api/departmentApi";
import { getEmployees } from "../../../api/employeeApi";

const EMPTY_SHIFT = {
  name: "",
  shift_type: "GENERAL",
  start_time: "09:00",
  end_time: "18:00",
  break_minutes: "60",
  grace_minutes: "10",
  expected_work_minutes: "480",
  overtime_multiplier: "1.50",
  is_active: true,
};

function localDateString(date = new Date()) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");

  return `${year}-${month}-${day}`;
}

function firstDayOfCurrentMonth() {
  const date = new Date();
  date.setDate(1);
  return localDateString(date);
}

function getErrorMessage(error, fallback) {
  const detail = error?.response?.data?.detail;

  if (typeof detail === "string") return detail;

  if (Array.isArray(detail)) {
    return detail
      .map((item) => item.msg || "Invalid input")
      .join(", ");
  }

  return error?.message || fallback;
}

function formatTime(value) {
  return value ? String(value).slice(0, 5) : "Flexible";
}

function shiftTypeLabel(type) {
  const labels = {
    GENERAL: "General",
    NIGHT: "Night",
    FLEXIBLE: "Flexible",
    REMOTE: "Remote",
  };

  return labels[type] || type;
}

const today = localDateString();

const INITIAL_ASSIGNMENT = {
  shift_id: "",
  target_type: "DEPARTMENT",
  target_id: "",
  effective_from: today,
  effective_to: "",
};

const INITIAL_REPORT = {
  start_date: firstDayOfCurrentMonth(),
  end_date: today,
  scope: "ALL",
  employee_id: "",
  department_id: "",
};

export default function ShiftManagementPage() {
  const [shifts, setShifts] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [assignments, setAssignments] = useState([]);
  const [report, setReport] = useState(null);

  const [shiftForm, setShiftForm] = useState(EMPTY_SHIFT);
  const [editingId, setEditingId] = useState(null);
  const [assignmentForm, setAssignmentForm] =
    useState(INITIAL_ASSIGNMENT);
  const [reportFilters, setReportFilters] =
    useState(INITIAL_REPORT);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [assigning, setAssigning] = useState(false);
  const [reportLoading, setReportLoading] = useState(false);
  const [actionId, setActionId] = useState(null);

  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [assignmentError, setAssignmentError] = useState("");
  const [assignmentMessage, setAssignmentMessage] = useState("");
  const [reportError, setReportError] = useState("");

  const loadPageData = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const [
        shiftData,
        departmentData,
        employeeData,
        assignmentData,
      ] = await Promise.all([
        getShifts({ include_inactive: true }),
        getDepartments(),
        getEmployees(),
        getShiftAssignments({ include_history: true }),
      ]);

      setShifts(Array.isArray(shiftData) ? shiftData : []);

      setDepartments(
        Array.isArray(departmentData)
          ? departmentData.filter((item) => item.is_active)
          : []
      );

      setEmployees(
        Array.isArray(employeeData)
          ? employeeData.filter(
              (item) =>
                item.is_active &&
                item.employment_status === "ACTIVE"
            )
          : []
      );

      setAssignments(
        Array.isArray(assignmentData) ? assignmentData : []
      );
    } catch (err) {
      setError(
        getErrorMessage(
          err,
          "Unable to load shift management data."
        )
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadPageData();
  }, [loadPageData]);

  function resetShiftForm() {
    setShiftForm(EMPTY_SHIFT);
    setEditingId(null);
  }

  function startEditShift(shift) {
    setEditingId(shift.id);

    setShiftForm({
      name: shift.name || "",
      shift_type: shift.shift_type || "GENERAL",
      start_time: formatTime(shift.start_time) === "Flexible"
        ? ""
        : formatTime(shift.start_time),
      end_time: formatTime(shift.end_time) === "Flexible"
        ? ""
        : formatTime(shift.end_time),
      break_minutes: String(shift.break_minutes ?? 60),
      grace_minutes: String(shift.grace_minutes ?? 10),
      expected_work_minutes: String(
        shift.expected_work_minutes ?? 480
      ),
      overtime_multiplier: String(
        shift.overtime_multiplier ?? "1.50"
      ),
      is_active: Boolean(shift.is_active),
    });

    setError("");
    setMessage("");
  }

  function handleShiftFormChange(event) {
    const { name, value, checked, type } = event.target;

    setShiftForm((current) => ({
      ...current,
      [name]: type === "checkbox" ? checked : value,
    }));
  }

  async function handleSaveShift(event) {
    event.preventDefault();

    setError("");
    setMessage("");

    const name = shiftForm.name.trim();

    if (name.length < 2) {
      setError("Shift name must contain at least 2 characters.");
      return;
    }

    if (
      ["GENERAL", "NIGHT"].includes(shiftForm.shift_type) &&
      (!shiftForm.start_time || !shiftForm.end_time)
    ) {
      setError(
        "Start and end times are required for General and Night shifts."
      );
      return;
    }

    if (
      shiftForm.shift_type === "GENERAL" &&
      shiftForm.start_time >= shiftForm.end_time
    ) {
      setError(
        "General shift end time must be after the start time."
      );
      return;
    }

    if (
      ["GENERAL", "NIGHT"].includes(shiftForm.shift_type) &&
      shiftForm.start_time === shiftForm.end_time
    ) {
      setError("Shift start and end times cannot be identical.");
      return;
    }

    setSaving(true);

    const hasFixedTimes = ["GENERAL", "NIGHT"].includes(
      shiftForm.shift_type
    );

    const payload = {
      name,
      shift_type: shiftForm.shift_type,
      start_time: hasFixedTimes
        ? `${shiftForm.start_time}:00`
        : null,
      end_time: hasFixedTimes
        ? `${shiftForm.end_time}:00`
        : null,
      break_minutes: Number(shiftForm.break_minutes),
      grace_minutes: Number(shiftForm.grace_minutes),
      expected_work_minutes: Number(
        shiftForm.expected_work_minutes
      ),
      overtime_multiplier: Number(
        shiftForm.overtime_multiplier
      ),
      is_active: shiftForm.is_active,
    };

    try {
      if (editingId !== null) {
        await updateShift(editingId, payload);
        setMessage("Shift updated successfully.");
      } else {
        await createShift(payload);
        setMessage("Shift created successfully.");
      }

      resetShiftForm();
      await loadPageData();
    } catch (err) {
      setError(
        getErrorMessage(err, "Unable to save the shift.")
      );
    } finally {
      setSaving(false);
    }
  }

  async function handleDeactivateShift(shift) {
    if (!shift.is_active) return;

    const confirmed = window.confirm(
      `Deactivate "${shift.name}"? Existing assignment history will be retained.`
    );

    if (!confirmed) return;

    setActionId(shift.id);
    setError("");
    setMessage("");

    try {
      await deactivateShift(shift.id);
      setMessage("Shift deactivated successfully.");
      await loadPageData();
    } catch (err) {
      setError(
        getErrorMessage(err, "Unable to deactivate the shift.")
      );
    } finally {
      setActionId(null);
    }
  }

  function handleAssignmentChange(event) {
    const { name, value } = event.target;

    setAssignmentForm((current) => ({
      ...current,
      [name]: value,
      ...(name === "target_type" ? { target_id: "" } : {}),
    }));
  }

  async function handleAssignShift(event) {
    event.preventDefault();

    setAssignmentError("");
    setAssignmentMessage("");

    if (!assignmentForm.shift_id) {
      setAssignmentError("Select a shift.");
      return;
    }

    if (!assignmentForm.target_id) {
      setAssignmentError(
        "Select an employee or department."
      );
      return;
    }

    if (
      assignmentForm.effective_to &&
      assignmentForm.effective_to <
        assignmentForm.effective_from
    ) {
      setAssignmentError(
        "Assignment end date cannot be before its start date."
      );
      return;
    }

    setAssigning(true);

    const payload = {
      shift_id: Number(assignmentForm.shift_id),
      employee_id:
        assignmentForm.target_type === "EMPLOYEE"
          ? Number(assignmentForm.target_id)
          : null,
      department_id:
        assignmentForm.target_type === "DEPARTMENT"
          ? Number(assignmentForm.target_id)
          : null,
      effective_from: assignmentForm.effective_from,
      effective_to: assignmentForm.effective_to || null,
    };

    try {
      await assignShift(payload);

      setAssignmentMessage(
        "Shift assignment created successfully."
      );

      setAssignmentForm({
        ...INITIAL_ASSIGNMENT,
        effective_from: localDateString(),
      });

      await loadPageData();
    } catch (err) {
      setAssignmentError(
        getErrorMessage(
          err,
          "Unable to assign the shift."
        )
      );
    } finally {
      setAssigning(false);
    }
  }

  function handleReportFilterChange(event) {
    const { name, value } = event.target;

    setReportFilters((current) => ({
      ...current,
      [name]: value,
    }));

    setReportError("");
  }

  async function handleRunReport(event) {
    event.preventDefault();
    setReportError("");
    setReport(null);

    if (
      !reportFilters.start_date ||
      !reportFilters.end_date ||
      reportFilters.start_date > reportFilters.end_date
    ) {
      setReportError(
        "Choose a valid report date range."
      );
      return;
    }

    const params = {
      start_date: reportFilters.start_date,
      end_date: reportFilters.end_date,
      skip: 0,
      limit: 200,
    };

    if (reportFilters.scope === "EMPLOYEE") {
      if (!reportFilters.employee_id) {
        setReportError("Select an employee.");
        return;
      }

      params.employee_id = Number(
        reportFilters.employee_id
      );
    }

    if (reportFilters.scope === "DEPARTMENT") {
      if (!reportFilters.department_id) {
        setReportError("Select a department.");
        return;
      }

      params.department_id = Number(
        reportFilters.department_id
      );
    }

    setReportLoading(true);

    try {
      const data = await getShiftAttendanceReport(params);
      setReport(data);
    } catch (err) {
      setReportError(
        getErrorMessage(
          err,
          "Unable to generate the attendance report."
        )
      );
    } finally {
      setReportLoading(false);
    }
  }

  function assignmentTargetLabel(assignment) {
    if (assignment.employee_id !== null) {
      const employee = employees.find(
        (item) => item.id === assignment.employee_id
      );

      return employee
        ? `${employee.employee_code} — ${employee.first_name} ${employee.last_name}`
        : `Employee #${assignment.employee_id}`;
    }

    const department = departments.find(
      (item) => item.id === assignment.department_id
    );

    return department
      ? `Department: ${department.name}`
      : `Department #${assignment.department_id}`;
  }

  function shiftName(shiftId) {
    return (
      shifts.find((item) => item.id === shiftId)?.name ||
      `Shift #${shiftId}`
    );
  }

  const activeShifts = shifts.filter(
    (shift) => shift.is_active
  );

  return (
    <section className="dashboard-page">
      <div className="page-heading-row">
        <div>
          <p className="section-kicker">WORKFORCE MANAGEMENT</p>
          <h2>Shift Management</h2>
          <p>
            Configure shifts, assign work schedules and review
            shift-wise attendance.
          </p>
        </div>

        <button
          type="button"
          className="secondary-button"
          onClick={loadPageData}
          disabled={loading}
        >
          <RefreshCw size={16} />
          Refresh
        </button>
      </div>

      {error && (
        <div className="alert alert-danger" role="alert">
          {error}
        </div>
      )}

      {message && (
        <div className="alert alert-success" role="status">
          {message}
        </div>
      )}

      {/* Shift configuration */}
      <div className="content-card">
        <div className="d-flex align-items-center gap-2 mb-3">
          <Clock3 size={21} />
          <h3 className="mb-0">
            {editingId !== null ? "Edit Shift" : "Create Shift"}
          </h3>
        </div>

        <form onSubmit={handleSaveShift}>
          <div className="employee-form-grid">
            <div className="form-field">
              <label htmlFor="shift-name">Shift name *</label>
              <input
                id="shift-name"
                name="name"
                value={shiftForm.name}
                onChange={handleShiftFormChange}
                minLength={2}
                maxLength={100}
                required
              />
            </div>

            <div className="form-field">
              <label htmlFor="shift-type">Shift type *</label>
              <select
                id="shift-type"
                name="shift_type"
                value={shiftForm.shift_type}
                onChange={handleShiftFormChange}
                required
              >
                <option value="GENERAL">General</option>
                <option value="NIGHT">Night</option>
                <option value="FLEXIBLE">Flexible</option>
                <option value="REMOTE">Remote</option>
              </select>
            </div>

            <div className="form-field">
              <label htmlFor="shift-start">Start time</label>
              <input
                id="shift-start"
                name="start_time"
                type="time"
                value={shiftForm.start_time}
                onChange={handleShiftFormChange}
                disabled={
                  !["GENERAL", "NIGHT"].includes(
                    shiftForm.shift_type
                  )
                }
                required={
                  ["GENERAL", "NIGHT"].includes(
                    shiftForm.shift_type
                  )
                }
              />
            </div>

            <div className="form-field">
              <label htmlFor="shift-end">End time</label>
              <input
                id="shift-end"
                name="end_time"
                type="time"
                value={shiftForm.end_time}
                onChange={handleShiftFormChange}
                disabled={
                  !["GENERAL", "NIGHT"].includes(
                    shiftForm.shift_type
                  )
                }
                required={
                  ["GENERAL", "NIGHT"].includes(
                    shiftForm.shift_type
                  )
                }
              />
              <small>
                Night shifts may end on the following day.
              </small>
            </div>

            <div className="form-field">
              <label htmlFor="shift-break">Break (minutes)</label>
              <input
                id="shift-break"
                name="break_minutes"
                type="number"
                min="0"
                max="720"
                value={shiftForm.break_minutes}
                onChange={handleShiftFormChange}
                required
              />
            </div>

            <div className="form-field">
              <label htmlFor="shift-grace">
                Late grace period (minutes)
              </label>
              <input
                id="shift-grace"
                name="grace_minutes"
                type="number"
                min="0"
                max="240"
                value={shiftForm.grace_minutes}
                onChange={handleShiftFormChange}
                required
              />
            </div>

            <div className="form-field">
              <label htmlFor="shift-work">
                Expected work (minutes)
              </label>
              <input
                id="shift-work"
                name="expected_work_minutes"
                type="number"
                min="1"
                max="1440"
                value={shiftForm.expected_work_minutes}
                onChange={handleShiftFormChange}
                required
              />
            </div>

            <div className="form-field">
              <label htmlFor="shift-overtime">
                Overtime multiplier
              </label>
              <input
                id="shift-overtime"
                name="overtime_multiplier"
                type="number"
                min="1"
                max="10"
                step="0.01"
                value={shiftForm.overtime_multiplier}
                onChange={handleShiftFormChange}
                required
              />
            </div>

            {editingId !== null && (
              <div className="form-field">
                <label className="form-check mt-4">
                  <input
                    className="form-check-input"
                    type="checkbox"
                    name="is_active"
                    checked={shiftForm.is_active}
                    onChange={handleShiftFormChange}
                  />
                  <span className="form-check-label">
                    Active shift
                  </span>
                </label>
              </div>
            )}
          </div>

          <div className="form-actions">
            {editingId !== null && (
              <button
                type="button"
                className="secondary-button"
                onClick={resetShiftForm}
                disabled={saving}
              >
                <X size={15} />
                Cancel
              </button>
            )}

            <button
              type="submit"
              className="primary-button"
              disabled={saving}
            >
              <Save size={16} />
              {saving
                ? "Saving..."
                : editingId !== null
                  ? "Update Shift"
                  : "Create Shift"}
            </button>
          </div>
        </form>
      </div>

      {/* Existing shifts */}
      <div className="content-card">
        <h3>Configured Shifts</h3>

        {loading ? (
          <p>Loading shifts...</p>
        ) : shifts.length === 0 ? (
          <p>No shifts have been configured yet.</p>
        ) : (
          <div className="table-responsive">
            <table className="table table-hover align-middle">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Type</th>
                  <th>Timing</th>
                  <th>Break</th>
                  <th>Grace</th>
                  <th>Expected Work</th>
                  <th>OT Multiplier</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {shifts.map((shift) => (
                  <tr key={shift.id}>
                    <td>{shift.name}</td>
                    <td>{shiftTypeLabel(shift.shift_type)}</td>
                    <td>
                      {shift.start_time
                        ? `${formatTime(shift.start_time)} – ${formatTime(shift.end_time)}`
                        : "Flexible"}
                    </td>
                    <td>{shift.break_minutes} min</td>
                    <td>{shift.grace_minutes} min</td>
                    <td>{shift.expected_work_minutes} min</td>
                    <td>{shift.overtime_multiplier}×</td>
                    <td>
                      <span
                        className={
                          shift.is_active
                            ? "badge bg-success"
                            : "badge bg-secondary"
                        }
                      >
                        {shift.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td>
                      <div className="d-flex flex-wrap gap-2">
                        <button
                          type="button"
                          className="btn btn-sm btn-outline-primary"
                          onClick={() => startEditShift(shift)}
                        >
                          Edit
                        </button>

                        {shift.is_active && (
                          <button
                            type="button"
                            className="btn btn-sm btn-outline-danger"
                            disabled={actionId === shift.id}
                            onClick={() =>
                              handleDeactivateShift(shift)
                            }
                          >
                            {actionId === shift.id
                              ? "Working..."
                              : "Deactivate"}
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Shift assignment */}
      <div className="content-card">
        <div className="d-flex align-items-center gap-2 mb-3">
          <Users size={21} />
          <h3 className="mb-0">Assign Work Schedule</h3>
        </div>

        {assignmentError && (
          <div className="alert alert-danger">
            {assignmentError}
          </div>
        )}

        {assignmentMessage && (
          <div className="alert alert-success">
            {assignmentMessage}
          </div>
        )}

        <form onSubmit={handleAssignShift}>
          <div className="employee-form-grid">
            <div className="form-field">
              <label htmlFor="assignment-shift">Shift *</label>
              <select
                id="assignment-shift"
                name="shift_id"
                value={assignmentForm.shift_id}
                onChange={handleAssignmentChange}
                required
              >
                <option value="">Select shift</option>
                {activeShifts.map((shift) => (
                  <option key={shift.id} value={shift.id}>
                    {shift.name} ({shiftTypeLabel(shift.shift_type)})
                  </option>
                ))}
              </select>
            </div>

            <div className="form-field">
              <label htmlFor="assignment-target-type">
                Assign to *
              </label>
              <select
                id="assignment-target-type"
                name="target_type"
                value={assignmentForm.target_type}
                onChange={handleAssignmentChange}
              >
                <option value="DEPARTMENT">Department</option>
                <option value="EMPLOYEE">Individual employee</option>
              </select>
            </div>

            <div className="form-field">
              <label htmlFor="assignment-target">
                {assignmentForm.target_type === "EMPLOYEE"
                  ? "Employee *"
                  : "Department *"}
              </label>
              <select
                id="assignment-target"
                name="target_id"
                value={assignmentForm.target_id}
                onChange={handleAssignmentChange}
                required
              >
                <option value="">Select target</option>

                {assignmentForm.target_type === "DEPARTMENT"
                  ? departments.map((department) => (
                      <option
                        key={department.id}
                        value={department.id}
                      >
                        {department.name}
                      </option>
                    ))
                  : employees.map((employee) => (
                      <option
                        key={employee.id}
                        value={employee.id}
                      >
                        {employee.employee_code} —{" "}
                        {employee.first_name} {employee.last_name}
                      </option>
                    ))}
              </select>
            </div>

            <div className="form-field">
              <label htmlFor="assignment-from">Effective From *</label>
              <input
                id="assignment-from"
                type="date"
                name="effective_from"
                value={assignmentForm.effective_from}
                onChange={handleAssignmentChange}
                required
              />
            </div>

            <div className="form-field">
              <label htmlFor="assignment-to">
                Effective To (optional)
              </label>
              <input
                id="assignment-to"
                type="date"
                name="effective_to"
                value={assignmentForm.effective_to}
                onChange={handleAssignmentChange}
              />
              <small>Leave blank for an open-ended assignment.</small>
            </div>
          </div>

          <div className="form-actions">
            <button
              type="submit"
              className="primary-button"
              disabled={assigning || activeShifts.length === 0}
            >
              <CalendarClock size={16} />
              {assigning ? "Assigning..." : "Assign Shift"}
            </button>
          </div>
        </form>
      </div>

      {/* Shift assignment history */}
      <div className="content-card">
        <h3>Assignment History</h3>

        {assignments.length === 0 ? (
          <p>No shift assignments found.</p>
        ) : (
          <div className="table-responsive">
            <table className="table table-hover align-middle">
              <thead>
                <tr>
                  <th>Shift</th>
                  <th>Target</th>
                  <th>Effective From</th>
                  <th>Effective To</th>
                  <th>Assigned By</th>
                </tr>
              </thead>
              <tbody>
                {assignments.map((assignment) => (
                  <tr key={assignment.id}>
                    <td>{shiftName(assignment.shift_id)}</td>
                    <td>{assignmentTargetLabel(assignment)}</td>
                    <td>{assignment.effective_from}</td>
                    <td>{assignment.effective_to || "Ongoing"}</td>
                    <td>
                      {assignment.assigned_by_user_id ?? "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Shift-wise attendance report */}
      <div className="content-card">
        <div className="d-flex align-items-center gap-2 mb-3">
          <ClipboardList size={21} />
          <h3 className="mb-0">Shift Attendance Report</h3>
        </div>

        {reportError && (
          <div className="alert alert-danger">
            {reportError}
          </div>
        )}

        <form onSubmit={handleRunReport}>
          <div className="employee-form-grid">
            <div className="form-field">
              <label htmlFor="report-start">From *</label>
              <input
                id="report-start"
                name="start_date"
                type="date"
                value={reportFilters.start_date}
                onChange={handleReportFilterChange}
                required
              />
            </div>

            <div className="form-field">
              <label htmlFor="report-end">To *</label>
              <input
                id="report-end"
                name="end_date"
                type="date"
                value={reportFilters.end_date}
                onChange={handleReportFilterChange}
                required
              />
            </div>

            <div className="form-field">
              <label htmlFor="report-scope">Report filter</label>
              <select
                id="report-scope"
                name="scope"
                value={reportFilters.scope}
                onChange={handleReportFilterChange}
              >
                <option value="ALL">All attendance</option>
                <option value="DEPARTMENT">Department</option>
                <option value="EMPLOYEE">Employee</option>
              </select>
            </div>

            {reportFilters.scope === "DEPARTMENT" && (
              <div className="form-field">
                <label htmlFor="report-department">Department *</label>
                <select
                  id="report-department"
                  name="department_id"
                  value={reportFilters.department_id}
                  onChange={handleReportFilterChange}
                  required
                >
                  <option value="">Select department</option>
                  {departments.map((department) => (
                    <option key={department.id} value={department.id}>
                      {department.name}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {reportFilters.scope === "EMPLOYEE" && (
              <div className="form-field">
                <label htmlFor="report-employee">Employee *</label>
                <select
                  id="report-employee"
                  name="employee_id"
                  value={reportFilters.employee_id}
                  onChange={handleReportFilterChange}
                  required
                >
                  <option value="">Select employee</option>
                  {employees.map((employee) => (
                    <option key={employee.id} value={employee.id}>
                      {employee.employee_code} —{" "}
                      {employee.first_name} {employee.last_name}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>

          <div className="form-actions">
            <button
              type="submit"
              className="primary-button"
              disabled={reportLoading}
            >
              <ClipboardList size={16} />
              {reportLoading ? "Generating..." : "Generate Report"}
            </button>
          </div>
        </form>

        {report && (
          <>
            <div className="row g-3 mt-3 mb-3">
              {[
                ["Total Records", report.total_records],
                ["Late Records", report.late_records],
                ["Early Checkouts", report.early_checkout_records],
                ["Overtime Records", report.overtime_records],
                [
                  "Overtime Minutes",
                  report.total_overtime_minutes,
                ],
              ].map(([label, value]) => (
                <div className="col-sm-6 col-xl-4" key={label}>
                  <div className="border rounded p-3 h-100">
                    <small className="text-muted">{label}</small>
                    <h4 className="mb-0 mt-1">{value}</h4>
                  </div>
                </div>
              ))}
            </div>

            {report.records?.length === 0 ? (
              <div className="alert alert-info">
                No attendance records were found for this date range.
              </div>
            ) : (
              <div className="table-responsive mt-3">
                <table className="table table-hover align-middle">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Employee</th>
                      <th>Shift</th>
                      <th>Check In</th>
                      <th>Check Out</th>
                      <th>Late (min)</th>
                      <th>Early (min)</th>
                      <th>Overtime (min)</th>
                      <th>Admin Override</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.records.map((record) => (
                      <tr key={record.attendance_id}>
                        <td>{record.attendance_date}</td>
                        <td>
                          {record.employee_name}
                          <br />
                          <small className="text-muted">
                            {record.employee_code}
                          </small>
                        </td>
                        <td>{record.shift_name || "Not assigned"}</td>
                        <td>{record.check_in || "—"}</td>
                        <td>{record.check_out || "—"}</td>
                        <td>{record.late_minutes}</td>
                        <td>{record.early_checkout_minutes}</td>
                        <td>{record.overtime_minutes}</td>
                        <td>
                          {record.is_overridden ? "Yes" : "No"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </div>
    </section>
  );
}
