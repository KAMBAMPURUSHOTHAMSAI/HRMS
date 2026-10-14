
import { useCallback, useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import {
  approveLeave,
  getLeaveRequests,
  getLeaveTypes,
  rejectLeave,
} from "../../../api/leaveApi";

function getArray(data) {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.items)) return data.items;
  if (Array.isArray(data?.requests)) return data.requests;
  if (Array.isArray(data?.data)) return data.data;
  return [];
}

function statusClass(status) {
  switch (String(status || "").toUpperCase()) {
    case "APPROVED":
      return "badge bg-success";
    case "REJECTED":
      return "badge bg-danger";
    case "PENDING":
      return "badge bg-warning text-dark";
    case "CANCELLED":
      return "badge bg-secondary";
    default:
      return "badge bg-light text-dark";
  }
}

export default function LeaveApprovals() {
  const [requests, setRequests] = useState([]);
  const [leaveTypes, setLeaveTypes] = useState([]);

  const [statusFilter, setStatusFilter] = useState("PENDING");
  const [employeeId, setEmployeeId] = useState("");

  const [selectedRequest, setSelectedRequest] = useState(null);
  const [decisionNote, setDecisionNote] = useState("");
  const [decision, setDecision] = useState("");

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const loadData = useCallback(async () => {
    setLoading(true);
    setError("");

    const params = {};

    if (statusFilter) params.status = statusFilter;
    if (employeeId.trim()) params.employee_id = Number(employeeId);

    const [requestsResult, typesResult] = await Promise.allSettled([
      getLeaveRequests(params),
      getLeaveTypes(),
    ]);

    if (requestsResult.status === "fulfilled") {
      setRequests(getArray(requestsResult.value));
    } else {
      setRequests([]);
      setError(
        requestsResult.reason?.response?.data?.detail ||
          "Unable to load leave requests."
      );
    }

    if (typesResult.status === "fulfilled") {
      setLeaveTypes(getArray(typesResult.value));
    } else {
      setLeaveTypes([]);
    }

    setLoading(false);
  }, [statusFilter, employeeId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const typeNames = Object.fromEntries(
    leaveTypes.map((type) => [String(type.id), type.name])
  );

  function openDecision(request, action) {
    setSelectedRequest(request);
    setDecision(action);
    setDecisionNote("");
    setError("");
    setMessage("");
  }

  async function submitDecision(event) {
    event.preventDefault();

    if (!selectedRequest || !decision) return;

    setSaving(true);
    setError("");
    setMessage("");

    try {
      const data = {
        decision_note: decisionNote.trim() || null,
      };

      if (decision === "APPROVED") {
        await approveLeave(selectedRequest.id, data);
      } else {
        await rejectLeave(selectedRequest.id, data);
      }

      setMessage(
        decision === "APPROVED"
          ? "Leave request approved successfully."
          : "Leave request rejected successfully."
      );

      setSelectedRequest(null);
      setDecision("");
      setDecisionNote("");

      await loadData();
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          "Unable to update this leave request."
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="container-fluid py-3">
      <div className="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
        <div>
          <h2 className="mb-1">Leave Approvals</h2>
          <p className="text-muted mb-0">
            Review employee leave requests and record decisions.
          </p>
        </div>

        <button
          type="button"
          className="btn btn-outline-primary"
          onClick={loadData}
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
          <h5 className="mb-3">Filters</h5>

          <form
            className="row g-3"
            onSubmit={(event) => {
              event.preventDefault();
              loadData();
            }}
          >
            <div className="col-md-5">
              <label className="form-label">Request Status</label>
              <select
                className="form-select"
                value={statusFilter}
                onChange={(event) => setStatusFilter(event.target.value)}
              >
                <option value="PENDING">Pending</option>
                <option value="APPROVED">Approved</option>
                <option value="REJECTED">Rejected</option>
                <option value="CANCELLED">Cancelled</option>
                <option value="">All statuses</option>
              </select>
            </div>

            <div className="col-md-5">
              <label className="form-label">Employee ID</label>
              <input
                type="number"
                min="1"
                className="form-control"
                placeholder="Optional employee ID"
                value={employeeId}
                onChange={(event) => setEmployeeId(event.target.value)}
              />
            </div>

            <div className="col-md-2 d-flex align-items-end">
              <button type="submit" className="btn btn-primary w-100">
                Apply
              </button>
            </div>
          </form>
        </div>
      </div>

      <div className="card">
        <div className="card-body">
          <h5 className="mb-3">Leave Requests</h5>

          {loading ? (
            <p>Loading leave requests...</p>
          ) : requests.length === 0 ? (
            <p className="text-muted mb-0">
              No leave requests match these filters.
            </p>
          ) : (
            <div className="table-responsive">
              <table className="table table-hover align-middle">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Employee</th>
                    <th>Leave Type</th>
                    <th>Dates</th>
                    <th>Days</th>
                    <th>Reason</th>
                    <th>Status</th>
                    <th>Decision</th>
                  </tr>
                </thead>

                <tbody>
                  {requests.map((request) => {
                    const employee =
                      request.employee_name ||
                      request.employee?.full_name ||
                      request.employee?.first_name ||
                      request.employee_email ||
                      request.employee_id;

                    const pending =
                      String(request.status).toUpperCase() === "PENDING";

                    return (
                      <tr key={request.id}>
                        <td>{request.id}</td>
                        <td>{employee || "—"}</td>
                        <td>
                          {request.leave_type_name ||
                            request.leave_type?.name ||
                            typeNames[String(request.leave_type_id)] ||
                            `Type ${request.leave_type_id}`}
                        </td>
                        <td>
                          {String(request.start_date || "").slice(0, 10)}
                          {" — "}
                          {String(request.end_date || "").slice(0, 10)}
                        </td>
                        <td>{request.total_days ?? "—"}</td>
                        <td>{request.reason || "—"}</td>
                        <td>
                          <span className={statusClass(request.status)}>
                            {request.status || "Unknown"}
                          </span>
                        </td>
                        <td>
                          {pending ? (
                            <div className="d-flex gap-2">
                              <button
                                type="button"
                                className="btn btn-sm btn-success"
                                onClick={() =>
                                  openDecision(request, "APPROVED")
                                }
                              >
                                Approve
                              </button>

                              <button
                                type="button"
                                className="btn btn-sm btn-outline-danger"
                                onClick={() =>
                                  openDecision(request, "REJECTED")
                                }
                              >
                                Reject
                              </button>
                            </div>
                          ) : (
                            <span className="text-muted">Completed</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {selectedRequest && (
        <div
          className="modal d-block"
          tabIndex="-1"
          role="dialog"
          aria-modal="true"
          style={{ backgroundColor: "rgba(0, 0, 0, 0.45)" }}
        >
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content">
              <form onSubmit={submitDecision}>
                <div className="modal-header">
                  <h5 className="modal-title">
                    {decision === "APPROVED"
                      ? "Approve Leave Request"
                      : "Reject Leave Request"}
                  </h5>

                  <button
                    type="button"
                    className="btn-close"
                    aria-label="Close"
                    onClick={() => setSelectedRequest(null)}
                    disabled={saving}
                  />
                </div>

                <div className="modal-body">
                  <p>
                    Request #{selectedRequest.id} —{" "}
                    {String(selectedRequest.start_date || "").slice(0, 10)}
                    {" to "}
                    {String(selectedRequest.end_date || "").slice(0, 10)}
                  </p>

                  <label className="form-label">
                    Decision Note
                  </label>

                  <textarea
                    className="form-control"
                    rows={3}
                    maxLength={500}
                    value={decisionNote}
                    onChange={(event) =>
                      setDecisionNote(event.target.value)
                    }
                    placeholder="Optional note for the employee"
                  />
                </div>

                <div className="modal-footer">
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={() => setSelectedRequest(null)}
                    disabled={saving}
                  >
                    Cancel
                  </button>

                  <button
                    type="submit"
                    className={
                      decision === "APPROVED"
                        ? "btn btn-success"
                        : "btn btn-danger"
                    }
                    disabled={saving}
                  >
                    {saving
                      ? "Saving..."
                      : decision === "APPROVED"
                        ? "Confirm Approval"
                        : "Confirm Rejection"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
