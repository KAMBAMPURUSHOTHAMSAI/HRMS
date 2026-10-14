
import { useCallback, useEffect, useState } from "react";

import {
  CalendarDays,
  Clock3,
  LogIn,
  LogOut,
  RefreshCw,
} from "lucide-react";

import {
  checkIn,
  checkOut,
  getMyAttendance,
  getMyAttendanceSummary,
} from "../../../api/attendanceApi";

// Get today's date using the local timezone.
function getLocalDate() {
  const now = new Date();

  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");

  return `${year}-${month}-${day}`;
}

// Support the different response formats used by the attendance APIs.
function getRecords(response) {
  if (Array.isArray(response)) return response;

  if (Array.isArray(response?.items)) return response.items;
  if (Array.isArray(response?.records)) return response.records;
  if (Array.isArray(response?.data)) return response.data;

  if (Array.isArray(response?.data?.items)) {
    return response.data.items;
  }

  if (Array.isArray(response?.data?.records)) {
    return response.data.records;
  }

  return [];
}

// Format an attendance timestamp for display.
function formatTime(value) {
  if (!value) return "—";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "—";
  }

  return date.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

// Convert working minutes to hours and minutes.
function formatWorkingTime(minutes = 0) {
  const total = Number(minutes) || 0;

  const hours = Math.floor(total / 60);
  const remainingMinutes = total % 60;

  return `${hours}h ${remainingMinutes}m`;
}

export default function AttendanceHistory() {
  const today = getLocalDate();

  const [startDate, setStartDate] = useState(
    `${today.slice(0, 7)}-01`
  );

  const [endDate, setEndDate] = useState(today);

  const [records, setRecords] = useState([]);
  const [todayRecord, setTodayRecord] = useState(null);
  const [summary, setSummary] = useState({});

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  // Load attendance history, today's attendance and monthly summary.
  const loadAttendance = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const results = await Promise.allSettled([
        getMyAttendance({
          start_date: startDate,
          end_date: endDate,
        }),

        getMyAttendance({
          start_date: today,
          end_date: today,
        }),

        getMyAttendanceSummary({
          year: Number(today.slice(0, 4)),
          month: Number(today.slice(5, 7)),
        }),
      ]);

      // 1. Attendance history for the selected date range.
      if (results[0].status === "fulfilled") {
        setRecords(getRecords(results[0].value));
      } else {
        setRecords([]);

        setError(
          results[0].reason?.response?.data?.detail ||
            "Unable to load your attendance history."
        );
      }

      // 2. Today's attendance record.
      if (results[1].status === "fulfilled") {
        const todayRecords = getRecords(results[1].value);

        const matchingRecord = todayRecords.find(
          (record) =>
            String(record.attendance_date || "").slice(0, 10) ===
            today
        );

        setTodayRecord(matchingRecord || null);
      } else {
        setTodayRecord(null);
      }

      // 3. Monthly attendance summary.
      if (results[2].status === "fulfilled") {
        const summaryResponse = results[2].value;

        // Support both a direct API object and an Axios response.
        const summaryData =
          summaryResponse?.data ?? summaryResponse ?? {};

        setSummary(
          summaryData &&
            typeof summaryData === "object" &&
            !Array.isArray(summaryData)
            ? summaryData
            : {}
        );
      } else {
        setSummary({});
      }
    } catch {
      setError("Unable to load attendance information.");
    } finally {
      setLoading(false);
    }
  }, [startDate, endDate, today]);

  // Load attendance information when the page opens or filters change.
  useEffect(() => {
    loadAttendance();
  }, [loadAttendance]);

  // Handle employee check-in and check-out actions.
  async function handleAttendanceAction(action) {
    setSaving(true);
    setError("");
    setMessage("");

    try {
      if (action === "check-in") {
        await checkIn();

        setMessage("Check-in completed successfully.");
      } else {
        await checkOut();

        setMessage("Check-out completed successfully.");
      }

      // Refresh attendance data after a successful action.
      await loadAttendance();
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          "Attendance action failed. Please try again."
      );
    } finally {
      setSaving(false);
    }
  }

  const alreadyCheckedIn = Boolean(todayRecord?.check_in);
  const alreadyCheckedOut = Boolean(todayRecord?.check_out);

  // FIX: The API returns "days_present".
  // Keep the other names as fallbacks for compatibility.
  const presentDays =
  summary.present_days ??
  summary.days_recorded ??
  summary.present_count ??
  summary.total_present_days ??
  "—";

  return (
    <section className="container-fluid py-3">
      {/* Page heading and refresh button */}
      <div className="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
        <div>
          <h2 className="mb-1">My Attendance</h2>

          <p className="text-muted mb-0">
            Record your daily attendance and view your history.
          </p>
        </div>

        <button
          type="button"
          className="btn btn-outline-primary"
          onClick={loadAttendance}
          disabled={loading}
        >
          <RefreshCw size={16} className="me-2" />
          Refresh
        </button>
      </div>

      {/* Error and success messages */}
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

      {/* Attendance summary cards */}
      <div className="row g-3 mb-4">
        {/* Working time */}
        <div className="col-sm-6 col-xl-3">
          <div className="card h-100">
            <div className="card-body">
              <Clock3
                size={22}
                className="text-primary mb-2"
              />

              <p className="text-muted mb-1">
                Working Time Today
              </p>

              <h4>
                {formatWorkingTime(
                  todayRecord?.working_minutes
                )}
              </h4>
            </div>
          </div>
        </div>

        {/* Present days */}
        <div className="col-sm-6 col-xl-3">
          <div className="card h-100">
            <div className="card-body">
              <CalendarDays
                size={22}
                className="text-success mb-2"
              />

              <p className="text-muted mb-1">
                Present Days
              </p>

              <h4>{presentDays}</h4>
            </div>
          </div>
        </div>

        {/* Today's check-in */}
        <div className="col-sm-6 col-xl-3">
          <div className="card h-100">
            <div className="card-body">
              <p className="text-muted mb-1">
                Today's Check-in
              </p>

              <h4>{formatTime(todayRecord?.check_in)}</h4>
            </div>
          </div>
        </div>

        {/* Today's check-out */}
        <div className="col-sm-6 col-xl-3">
          <div className="card h-100">
            <div className="card-body">
              <p className="text-muted mb-1">
                Today's Check-out
              </p>

              <h4>{formatTime(todayRecord?.check_out)}</h4>
            </div>
          </div>
        </div>
      </div>

      {/* Today's attendance actions */}
      <div className="card mb-4">
        <div className="card-body">
          <h5 className="mb-3">Today's Attendance</h5>

          <p>
            Status:{" "}
            <strong>
              {todayRecord?.status || "Not checked in"}
            </strong>
          </p>

          <div className="d-flex flex-wrap gap-2">
            <button
              type="button"
              className="btn btn-primary"
              disabled={
                saving ||
                loading ||
                alreadyCheckedIn
              }
              onClick={() =>
                handleAttendanceAction("check-in")
              }
            >
              <LogIn size={17} className="me-2" />

              {saving
                ? "Processing..."
                : "Check In"}
            </button>

            <button
              type="button"
              className="btn btn-success"
              disabled={
                saving ||
                loading ||
                !alreadyCheckedIn ||
                alreadyCheckedOut
              }
              onClick={() =>
                handleAttendanceAction("check-out")
              }
            >
              <LogOut size={17} className="me-2" />
              Check Out
            </button>
          </div>
        </div>
      </div>

      {/* Attendance history */}
      <div className="card">
        <div className="card-body">
          <h5 className="mb-3">Attendance History</h5>

          {/* Date filters */}
          <div className="row g-3 mb-3">
            <div className="col-md-4">
              <label
                htmlFor="attendance-start-date"
                className="form-label"
              >
                From Date
              </label>

              <input
                id="attendance-start-date"
                type="date"
                className="form-control"
                value={startDate}
                max={endDate}
                onChange={(event) =>
                  setStartDate(event.target.value)
                }
              />
            </div>

            <div className="col-md-4">
              <label
                htmlFor="attendance-end-date"
                className="form-label"
              >
                To Date
              </label>

              <input
                id="attendance-end-date"
                type="date"
                className="form-control"
                value={endDate}
                min={startDate}
                max={today}
                onChange={(event) =>
                  setEndDate(event.target.value)
                }
              />
            </div>
          </div>

          {/* History loading, empty state and table */}
          {loading ? (
            <p>Loading attendance records...</p>
          ) : records.length === 0 ? (
            <p className="text-muted mb-0">
              No attendance records found for the selected dates.
            </p>
          ) : (
            <div className="table-responsive">
              <table className="table table-hover align-middle">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Check-in</th>
                    <th>Check-out</th>
                    <th>Working Time</th>
                    <th>Status</th>
                  </tr>
                </thead>

                <tbody>
                  {records.map((record) => (
                    <tr key={record.id}>
                      <td>
                        {String(
                          record.attendance_date || ""
                        ).slice(0, 10)}
                      </td>

                      <td>{formatTime(record.check_in)}</td>

                      <td>{formatTime(record.check_out)}</td>

                      <td>
                        {formatWorkingTime(
                          record.working_minutes
                        )}
                      </td>

                      <td>{record.status || "—"}</td>
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
