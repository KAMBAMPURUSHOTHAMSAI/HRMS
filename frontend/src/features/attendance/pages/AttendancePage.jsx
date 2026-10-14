import { useCallback, useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import {
  correctAttendance,
  getAllAttendance,
} from "../../../api/attendanceApi";

function getLocalDate() {
  const now = new Date();

  return [
    now.getFullYear(),
    String(now.getMonth() + 1).padStart(2, "0"),
    String(now.getDate()).padStart(2, "0"),
  ].join("-");
}

function getRecords(response) {
  if (Array.isArray(response)) return response;
  if (Array.isArray(response?.items)) return response.items;
  if (Array.isArray(response?.records)) return response.records;
  if (Array.isArray(response?.data)) return response.data;
  return [];
}

function formatDateTimeInput(value) {
  if (!value) return "";

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";

  const pad = (number) => String(number).padStart(2, "0");

  return (
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}` +
    `T${pad(date.getHours())}:${pad(date.getMinutes())}`
  );
}

function toISOString(value) {
  return value ? new Date(value).toISOString() : null;
}

function formatTime(value) {
  if (!value) return "—";

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";

  return date.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function AttendancePage() {
  const today = getLocalDate();

  const [filters, setFilters] = useState({
    start_date: `${today.slice(0, 7)}-01`,
    end_date: today,
    employee_id: "",
    status: "",
  });

  const [appliedFilters, setAppliedFilters] = useState({
    start_date: `${today.slice(0, 7)}-01`,
    end_date: today,
    employee_id: "",
    status: "",
  });

  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [editingId, setEditingId] = useState(null);

  const [correction, setCorrection] = useState({
    check_in: "",
    check_out: "",
    status: "PRESENT",
    correction_note: "",
  });

  const loadRecords = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const params = {
        start_date: appliedFilters.start_date,
        end_date: appliedFilters.end_date,
      };

      if (appliedFilters.employee_id) {
        params.employee_id = Number(appliedFilters.employee_id);
      }

      if (appliedFilters.status) {
        params.status = appliedFilters.status;
      }

      const response = await getAllAttendance(params);
      setRecords(getRecords(response));
    } catch (err) {
      setRecords([]);
      setError(
        err.response?.data?.detail ||
          "Unable to load attendance records."
      );
    } finally {
      setLoading(false);
    }
  }, [appliedFilters]);

  useEffect(() => {
    loadRecords();
  }, [loadRecords]);

  function startCorrection(record) {
    setEditingId(record.id);
    setError("");
    setMessage("");

    setCorrection({
      check_in: formatDateTimeInput(record.check_in),
      check_out: formatDateTimeInput(record.check_out),
      status: record.status === "HALF_DAY" ? "HALF_DAY" : "PRESENT",
      correction_note: "",
    });
  }

  async function saveCorrection(event) {
    event.preventDefault();

    if (!correction.correction_note.trim()) {
      setError("Please enter a reason for the correction.");
      return;
    }

    setSaving(true);
    setError("");
    setMessage("");

    try {
      await correctAttendance(editingId, {
        check_in: toISOString(correction.check_in),
        check_out: toISOString(correction.check_out),
        status: correction.status,
        correction_note: correction.correction_note.trim(),
      });

      setMessage("Attendance correction saved successfully.");
      setEditingId(null);

      await loadRecords();
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          "Unable to save the attendance correction."
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="container-fluid py-3">
      <div className="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
        <div>
          <h2 className="mb-1">Attendance Management</h2>
          <p className="text-muted mb-0">
            View employee attendance and manage corrections.
          </p>
        </div>

        <button
          type="button"
          className="btn btn-outline-primary"
          onClick={loadRecords}
          disabled={loading}
        >
          <RefreshCw size={16} className="me-2" />
          Refresh
        </button>
      </div>

      {error && <div className="alert alert-danger">{error}</div>}
      {message && <div className="alert alert-success">{message}</div>}

      <div className="card mb-4">
        <div className="card-body">
          <h5 className="mb-3">Filter Attendance</h5>

          <form
            className="row g-3"
            onSubmit={(event) => {
              event.preventDefault();
              setAppliedFilters({ ...filters });
            }}
          >
            <div className="col-md-3">
              <label className="form-label">From Date</label>
              <input
                type="date"
                className="form-control"
                value={filters.start_date}
                max={filters.end_date}
                onChange={(event) =>
                  setFilters({
                    ...filters,
                    start_date: event.target.value,
                  })
                }
                required
              />
            </div>

            <div className="col-md-3">
              <label className="form-label">To Date</label>
              <input
                type="date"
                className="form-control"
                value={filters.end_date}
                min={filters.start_date}
                max={today}
                onChange={(event) =>
                  setFilters({
                    ...filters,
                    end_date: event.target.value,
                  })
                }
                required
              />
            </div>

            <div className="col-md-3">
              <label className="form-label">Employee ID</label>
              <input
                type="number"
                min="1"
                className="form-control"
                placeholder="Employee ID"
                value={filters.employee_id}
                onChange={(event) =>
                  setFilters({
                    ...filters,
                    employee_id: event.target.value,
                  })
                }
              />
            </div>

            <div className="col-md-3">
              <label className="form-label">Status</label>
              <select
                className="form-select"
                value={filters.status}
                onChange={(event) =>
                  setFilters({
                    ...filters,
                    status: event.target.value,
                  })
                }
              >
                <option value="">All statuses</option>
                <option value="PRESENT">Present</option>
                <option value="HALF_DAY">Half Day</option>
                <option value="ABSENT">Absent</option>
                <option value="LEAVE">Leave</option>
              </select>
            </div>

            <div className="col-12">
              <button type="submit" className="btn btn-primary">
                Apply Filters
              </button>
            </div>
          </form>
        </div>
      </div>

      <div className="card">
        <div className="card-body">
          <h5 className="mb-3">Attendance Records</h5>

          {loading ? (
            <p>Loading attendance records...</p>
          ) : records.length === 0 ? (
            <p className="text-muted mb-0">
              No attendance records found.
            </p>
          ) : (
            <div className="table-responsive">
              <table className="table table-hover align-middle">
                <thead>
                  <tr>
                    <th>Record ID</th>
                    <th>Employee</th>
                    <th>Date</th>
                    <th>Check-in</th>
                    <th>Check-out</th>
                    <th>Working Minutes</th>
                    <th>Status</th>
                    <th>Action</th>
                  </tr>
                </thead>

                <tbody>
                  {records.map((record) => (
                    <tr key={record.id}>
                      <td>{record.id}</td>
                      <td>
                        {record.employee_code ||
                          record.employee_name ||
                          record.employee_id ||
                          "—"}
                      </td>
                      <td>
                        {String(record.attendance_date || "").slice(0, 10)}
                      </td>
                      <td>{formatTime(record.check_in)}</td>
                      <td>{formatTime(record.check_out)}</td>
                      <td>{record.working_minutes ?? "—"}</td>
                      <td>{record.status || "—"}</td>
                      <td>
                        <button
                          type="button"
                          className="btn btn-sm btn-outline-primary"
                          onClick={() => startCorrection(record)}
                        >
                          Correct
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {editingId !== null && (
        <div className="card mt-4">
          <div className="card-body">
            <h5 className="mb-3">
              Correct Attendance — #{editingId}
            </h5>

            <form className="row g-3" onSubmit={saveCorrection}>
              <div className="col-md-4">
                <label className="form-label">Check-in</label>
                <input
                  type="datetime-local"
                  className="form-control"
                  value={correction.check_in}
                  onChange={(event) =>
                    setCorrection({
                      ...correction,
                      check_in: event.target.value,
                    })
                  }
                  required
                />
              </div>

              <div className="col-md-4">
                <label className="form-label">Check-out</label>
                <input
                  type="datetime-local"
                  className="form-control"
                  value={correction.check_out}
                  onChange={(event) =>
                    setCorrection({
                      ...correction,
                      check_out: event.target.value,
                    })
                  }
                />
              </div>

              <div className="col-md-4">
                <label className="form-label">Status</label>
                <select
                  className="form-select"
                  value={correction.status}
                  onChange={(event) =>
                    setCorrection({
                      ...correction,
                      status: event.target.value,
                    })
                  }
                >
                  <option value="PRESENT">Present</option>
                  <option value="HALF_DAY">Half Day</option>
                </select>
              </div>

              <div className="col-12">
                <label className="form-label">Correction Reason</label>
                <textarea
                  className="form-control"
                  rows={3}
                  minLength={3}
                  maxLength={500}
                  value={correction.correction_note}
                  onChange={(event) =>
                    setCorrection({
                      ...correction,
                      correction_note: event.target.value,
                    })
                  }
                  required
                />
              </div>

              <div className="col-12 d-flex gap-2">
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={saving}
                >
                  {saving ? "Saving..." : "Save Correction"}
                </button>

                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setEditingId(null)}
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </section>
  );
}