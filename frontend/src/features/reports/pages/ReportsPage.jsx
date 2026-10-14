
import { useState } from "react";

import {
  exportAttendanceReport,
  exportLeaveReport,
  exportPayrollReport,
  getAttendanceReport,
  getLeaveReport,
  getPayrollReport,
} from "../../../api/reportApi";

const REPORT_CONFIG = {
  attendance: {
    label: "Attendance",
    load: getAttendanceReport,
    export: exportAttendanceReport,
  },
  leaves: {
    label: "Leave",
    load: getLeaveReport,
    export: exportLeaveReport,
  },
  payroll: {
    label: "Payroll",
    load: getPayrollReport,
    export: exportPayrollReport,
  },
};

const COLUMN_LABELS = {
  id: "ID",
  employee_id: "Employee ID",
  employee_code: "Employee Code",
  employee_name: "Employee",
  department: "Department",
  attendance_date: "Date",
  check_in: "Check In",
  check_out: "Check Out",
  working_minutes: "Working Minutes",
  status: "Status",
  leave_type: "Leave Type",
  start_date: "Start Date",
  end_date: "End Date",
  total_days: "Total Days",
  reason: "Reason",
  created_at: "Created At",
  year: "Year",
  month: "Month",
  gross_salary: "Gross Salary",
  lop_deduction: "LOP Deduction",
  other_deductions: "Other Deductions",
  net_salary: "Net Salary",
  credit_status: "Credit Status",
};

function toParams(filters, reportType) {
  const params = {};

  if (filters.department_id) {
    params.department_id = Number(filters.department_id);
  }

  if (reportType === "attendance") {
    if (filters.start_date) params.start_date = filters.start_date;
    if (filters.end_date) params.end_date = filters.end_date;
    if (filters.employee_id) {
      params.employee_id = Number(filters.employee_id);
    }
  }

  if (reportType === "leaves") {
    if (filters.start_date) params.start_date = filters.start_date;
    if (filters.end_date) params.end_date = filters.end_date;
    if (filters.leave_status) {
      params.leave_status = filters.leave_status;
    }
  }

  if (reportType === "payroll") {
    if (filters.year) params.year = Number(filters.year);
    if (filters.month) params.month = Number(filters.month);
  }

  return params;
}

function displayValue(value) {
  if (value === null || value === undefined || value === "") {
    return "—";
  }

  if (typeof value === "object") {
    return JSON.stringify(value);
  }

  return String(value).replace("T", " ");
}

export default function ReportsPage() {
  const [reportType, setReportType] = useState("attendance");

  const [filters, setFilters] = useState({
    start_date: "",
    end_date: "",
    department_id: "",
    employee_id: "",
    leave_status: "",
    year: String(new Date().getFullYear()),
    month: "",
  });

  const [loadedType, setLoadedType] = useState("");
  const [loadedParams, setLoadedParams] = useState({});
  const [rows, setRows] = useState([]);
  const [hasRun, setHasRun] = useState(false);

  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  function updateFilter(event) {
    const { name, value } = event.target;
    setFilters((current) => ({ ...current, [name]: value }));
  }

  function changeReportType(value) {
    setReportType(value);
    setRows([]);
    setHasRun(false);
    setLoadedType("");
    setError("");
    setMessage("");
  }

  async function runReport(event) {
    event.preventDefault();

    setLoading(true);
    setError("");
    setMessage("");

    try {
      const params = toParams(filters, reportType);
      const data = await REPORT_CONFIG[reportType].load(params);

      setRows(Array.isArray(data) ? data : []);
      setLoadedType(reportType);
      setLoadedParams(params);
      setHasRun(true);
    } catch (err) {
      setRows([]);
      setHasRun(false);
      setError(
        err.response?.data?.detail ||
          "Unable to load report. Check your access and filters."
      );
    } finally {
      setLoading(false);
    }
  }

  async function downloadReport(format) {
    if (!hasRun || !loadedType) return;

    setExporting(true);
    setError("");
    setMessage("");

    try {
      const response = await REPORT_CONFIG[loadedType].export(
        loadedParams,
        format
      );

      const blobUrl = window.URL.createObjectURL(response.data);
      const anchor = document.createElement("a");
      const disposition = response.headers["content-disposition"] || "";
      const match = disposition.match(/filename="?([^"]+)"?/i);

      anchor.href = blobUrl;
      anchor.download =
        match?.[1] ||
        `${loadedType}_report.${format}`;

      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();

      window.URL.revokeObjectURL(blobUrl);
      setMessage(`${format.toUpperCase()} export completed.`);
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          "Unable to export report."
      );
    } finally {
      setExporting(false);
    }
  }

  const columns =
    rows.length > 0 ? Object.keys(rows[0]) : [];

  return (
    <section className="container-fluid py-3">
      <div className="mb-4">
        <h2>Reports & Analytics</h2>
        <p className="text-muted">
          View HR reports and export filtered results.
        </p>
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

      <div className="card mb-4">
        <div className="card-body">
          <form onSubmit={runReport}>
            <div className="row g-3">
              <div className="col-md-4">
                <label className="form-label">Report Type</label>
                <select
                  className="form-select"
                  value={reportType}
                  onChange={(event) =>
                    changeReportType(event.target.value)
                  }
                >
                  <option value="attendance">Attendance</option>
                  <option value="leaves">Leave</option>
                  <option value="payroll">Payroll</option>
                </select>
              </div>

              {reportType !== "payroll" && (
                <>
                  <div className="col-md-4">
                    <label className="form-label">Start Date</label>
                    <input
                      type="date"
                      name="start_date"
                      className="form-control"
                      value={filters.start_date}
                      onChange={updateFilter}
                    />
                  </div>

                  <div className="col-md-4">
                    <label className="form-label">End Date</label>
                    <input
                      type="date"
                      name="end_date"
                      className="form-control"
                      value={filters.end_date}
                      onChange={updateFilter}
                    />
                  </div>
                </>
              )}

              <div className="col-md-4">
                <label className="form-label">Department ID</label>
                <input
                  type="number"
                  min="1"
                  name="department_id"
                  className="form-control"
                  value={filters.department_id}
                  onChange={updateFilter}
                  placeholder="All departments"
                />
              </div>

              {reportType === "attendance" && (
                <div className="col-md-4">
                  <label className="form-label">Employee ID</label>
                  <input
                    type="number"
                    min="1"
                    name="employee_id"
                    className="form-control"
                    value={filters.employee_id}
                    onChange={updateFilter}
                    placeholder="All employees"
                  />
                </div>
              )}

              {reportType === "leaves" && (
                <div className="col-md-4">
                  <label className="form-label">Leave Status</label>
                  <select
                    className="form-select"
                    name="leave_status"
                    value={filters.leave_status}
                    onChange={updateFilter}
                  >
                    <option value="">All statuses</option>
                    <option value="PENDING">Pending</option>
                    <option value="APPROVED">Approved</option>
                    <option value="REJECTED">Rejected</option>
                    <option value="CANCELLED">Cancelled</option>
                  </select>
                </div>
              )}

              {reportType === "payroll" && (
                <>
                  <div className="col-md-4">
                    <label className="form-label">Year</label>
                    <input
                      type="number"
                      min="2000"
                      max="2100"
                      name="year"
                      className="form-control"
                      value={filters.year}
                      onChange={updateFilter}
                    />
                  </div>

                  <div className="col-md-4">
                    <label className="form-label">Month</label>
                    <select
                      className="form-select"
                      name="month"
                      value={filters.month}
                      onChange={updateFilter}
                    >
                      <option value="">All months</option>
                      {Array.from({ length: 12 }, (_, i) => (
                        <option key={i + 1} value={i + 1}>
                          {new Date(2000, i, 1).toLocaleString(
                            "en",
                            { month: "long" }
                          )}
                        </option>
                      ))}
                    </select>
                  </div>
                </>
              )}

              <div className="col-12 d-flex flex-wrap gap-2">
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={loading}
                >
                  {loading ? "Loading..." : "Run Report"}
                </button>

                <button
                  type="button"
                  className="btn btn-outline-success"
                  disabled={!hasRun || exporting}
                  onClick={() => downloadReport("csv")}
                >
                  Export CSV
                </button>

                <button
                  type="button"
                  className="btn btn-outline-danger"
                  disabled={!hasRun || exporting}
                  onClick={() => downloadReport("pdf")}
                >
                  Export PDF
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>

      <div className="card">
        <div className="card-body">
          <div className="d-flex flex-wrap justify-content-between gap-2 mb-3">
            <h5 className="mb-0">
              {loadedType
                ? `${REPORT_CONFIG[loadedType].label} Report`
                : "Report Results"}
            </h5>

            <span className="text-muted">
              {hasRun ? `${rows.length} rows returned` : "No report run yet"}
            </span>
          </div>

          {!hasRun ? (
            <p className="text-muted mb-0">
              Select the report and filters, then select Run Report.
            </p>
          ) : rows.length === 0 ? (
            <p className="text-muted mb-0">
              No records match these filters.
            </p>
          ) : (
            <div className="table-responsive">
              <table className="table table-hover table-striped align-middle">
                <thead>
                  <tr>
                    {columns.map((column) => (
                      <th key={column}>
                        {COLUMN_LABELS[column] || column}
                      </th>
                    ))}
                  </tr>
                </thead>

                <tbody>
                  {rows.map((row, index) => (
                    <tr key={row.id ?? index}>
                      {columns.map((column) => (
                        <td key={column}>
                          {displayValue(row[column])}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
