
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Plus, RefreshCw } from "lucide-react";
import {
  getLeaveTypes,
  getMyLeaves,
  getMyLeaveBalances,
} from "../../../api/leaveApi";

function getArray(data) {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.items)) return data.items;
  if (Array.isArray(data?.balances)) return data.balances;
  if (Array.isArray(data?.data)) return data.data;
  return [];
}

function displayDate(value) {
  if (!value) return "—";
  return String(value).slice(0, 10);
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

export default function MyLeaves() {
  const [requests, setRequests] = useState([]);
  const [leaveTypes, setLeaveTypes] = useState([]);
  const [balances, setBalances] = useState([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadData = useCallback(async () => {
    setLoading(true);
    setError("");

    const year = new Date().getFullYear();

    const [requestsResult, typesResult, balancesResult] =
      await Promise.allSettled([
        getMyLeaves(),
        getLeaveTypes(),
        getMyLeaveBalances({ year }),
      ]);

    if (requestsResult.status === "fulfilled") {
      setRequests(getArray(requestsResult.value));
    } else {
      setRequests([]);
      setError(
        requestsResult.reason?.response?.data?.detail ||
          "Unable to load your leave requests."
      );
    }

    if (typesResult.status === "fulfilled") {
      setLeaveTypes(getArray(typesResult.value));
    } else {
      setLeaveTypes([]);
    }

    if (balancesResult.status === "fulfilled") {
      setBalances(getArray(balancesResult.value));
    } else {
      setBalances([]);
    }

    setLoading(false);
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const typeNames = Object.fromEntries(
    leaveTypes.map((type) => [String(type.id), type.name])
  );

  const filteredRequests = requests.filter((request) => {
    return (
      !statusFilter ||
      String(request.status).toUpperCase() === statusFilter
    );
  });

  return (
    <section className="container-fluid py-3">
      <div className="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
        <div>
          <h2 className="mb-1">My Leaves</h2>
          <p className="text-muted mb-0">
            Review your leave requests and remaining balance.
          </p>
        </div>

        <div className="d-flex gap-2">
          <button
            type="button"
            className="btn btn-outline-primary"
            onClick={loadData}
            disabled={loading}
          >
            <RefreshCw size={16} className="me-2" />
            Refresh
          </button>

          <Link
            to="/employee/leaves/apply"
            className="btn btn-primary"
          >
            <Plus size={16} className="me-2" />
            Apply Leave
          </Link>
        </div>
      </div>

      {error && <div className="alert alert-danger">{error}</div>}

      <div className="card mb-4">
        <div className="card-body">
          <h5 className="mb-3">Leave Balances</h5>

          {balances.length === 0 ? (
            <p className="text-muted mb-0">
              No leave balance information is available.
            </p>
          ) : (
            <div className="row g-3">
              {balances.map((balance) => {
                const leaveName =
                  balance.leave_type_name ||
                  balance.leave_type?.name ||
                  typeNames[String(balance.leave_type_id)] ||
                  `Leave Type ${balance.leave_type_id}`;

                const entitled = Number(balance.entitled_days ?? 0);
                const used = Number(balance.used_days ?? 0);
                const remaining =
                  balance.remaining_days ?? Math.max(0, entitled - used);

                return (
                  <div
                    className="col-sm-6 col-xl-4"
                    key={`${balance.leave_type_id}-${balance.year}`}
                  >
                    <div className="card h-100">
                      <div className="card-body">
                        <p className="text-muted mb-1">{leaveName}</p>
                        <h3 className="mb-2">{remaining}</h3>
                        <p className="text-muted small mb-0">
                          Remaining days
                        </p>
                        <hr />
                        <div className="d-flex justify-content-between">
                          <span>Entitled</span>
                          <strong>{entitled}</strong>
                        </div>
                        <div className="d-flex justify-content-between mt-1">
                          <span>Used</span>
                          <strong>{used}</strong>
                        </div>
                        <div className="d-flex justify-content-between mt-1">
                          <span>Year</span>
                          <strong>{balance.year ?? "—"}</strong>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      <div className="card">
        <div className="card-body">
          <div className="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-3">
            <h5 className="mb-0">Leave Request History</h5>

            <select
              className="form-select"
              style={{ maxWidth: "200px" }}
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value)}
            >
              <option value="">All statuses</option>
              <option value="PENDING">Pending</option>
              <option value="APPROVED">Approved</option>
              <option value="REJECTED">Rejected</option>
              <option value="CANCELLED">Cancelled</option>
            </select>
          </div>

          {loading ? (
            <p>Loading leave requests...</p>
          ) : filteredRequests.length === 0 ? (
            <p className="text-muted mb-0">
              No matching leave requests found.
            </p>
          ) : (
            <div className="table-responsive">
              <table className="table table-hover align-middle">
                <thead>
                  <tr>
                    <th>Leave Type</th>
                    <th>Start Date</th>
                    <th>End Date</th>
                    <th>Days</th>
                    <th>Reason</th>
                    <th>Status</th>
                    <th>Decision Note</th>
                  </tr>
                </thead>

                <tbody>
                  {filteredRequests.map((request) => (
                    <tr key={request.id}>
                      <td>
                        {request.leave_type_name ||
                          request.leave_type?.name ||
                          typeNames[String(request.leave_type_id)] ||
                          `Type ${request.leave_type_id}`}
                      </td>
                      <td>{displayDate(request.start_date)}</td>
                      <td>{displayDate(request.end_date)}</td>
                      <td>{request.total_days ?? "—"}</td>
                      <td>{request.reason || "—"}</td>
                      <td>
                        <span className={statusClass(request.status)}>
                          {request.status || "Unknown"}
                        </span>
                      </td>
                      <td>{request.decision_note || "—"}</td>
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
