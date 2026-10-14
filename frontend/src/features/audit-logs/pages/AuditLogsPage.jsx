
import { useCallback, useEffect, useState } from "react";

import { getAuditLogs } from "../../../api/auditLogApi";

const PAGE_SIZE = 50;

function formatDateTime(value) {
  if (!value) return "—";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) return String(value);

  return date.toLocaleString();
}

export default function AuditLogsPage() {
  const [filters, setFilters] = useState({
    actor_user_id: "",
    action: "",
    entity_type: "",
    entity_id: "",
    start_date: "",
    end_date: "",
  });

  const [appliedFilters, setAppliedFilters] = useState({});
  const [skip, setSkip] = useState(0);

  const [logs, setLogs] = useState([]);
  const [selectedLog, setSelectedLog] = useState(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadLogs = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const params = {
        ...appliedFilters,
        skip,
        limit: PAGE_SIZE,
      };

      const result = await getAuditLogs(params);
      setLogs(Array.isArray(result) ? result : []);
    } catch (err) {
      setLogs([]);
      setError(
        err.response?.data?.detail ||
          "Unable to load audit logs. Admin access is required."
      );
    } finally {
      setLoading(false);
    }
  }, [appliedFilters, skip]);

  useEffect(() => {
    loadLogs();
  }, [loadLogs]);

  function updateFilter(event) {
    const { name, value } = event.target;
    setFilters((current) => ({
      ...current,
      [name]: value,
    }));
  }

  function applyFilters(event) {
    event.preventDefault();

    const params = {};

    if (filters.actor_user_id) {
      params.actor_user_id = Number(filters.actor_user_id);
    }

    if (filters.action.trim()) {
      params.action = filters.action.trim().toUpperCase();
    }

    if (filters.entity_type.trim()) {
      params.entity_type = filters.entity_type.trim();
    }

    if (filters.entity_id.trim()) {
      params.entity_id = filters.entity_id.trim();
    }

    if (filters.start_date) {
      params.start_date = `${filters.start_date}T00:00:00`;
    }

    if (filters.end_date) {
      params.end_date = `${filters.end_date}T23:59:59`;
    }

    setSelectedLog(null);
    setSkip(0);
    setAppliedFilters(params);
  }

  function clearFilters() {
    setFilters({
      actor_user_id: "",
      action: "",
      entity_type: "",
      entity_id: "",
      start_date: "",
      end_date: "",
    });

    setAppliedFilters({});
    setSkip(0);
    setSelectedLog(null);
  }

  return (
    <section className="container-fluid py-3">
      <div className="mb-4">
        <h2>Audit Logs</h2>
        <p className="text-muted">
          Review recorded actions, actors, affected entities, and request details.
        </p>
      </div>

      {error && (
        <div className="alert alert-danger" role="alert">
          {error}
        </div>
      )}

      <div className="card mb-4">
        <div className="card-body">
          <form onSubmit={applyFilters}>
            <div className="row g-3">
              <div className="col-md-4">
                <label className="form-label">Actor User ID</label>
                <input
                  type="number"
                  min="1"
                  name="actor_user_id"
                  className="form-control"
                  value={filters.actor_user_id}
                  onChange={updateFilter}
                />
              </div>

              <div className="col-md-4">
                <label className="form-label">Action</label>
                <input
                  name="action"
                  className="form-control"
                  value={filters.action}
                  onChange={updateFilter}
                  placeholder="e.g. UPDATE"
                />
              </div>

              <div className="col-md-4">
                <label className="form-label">Entity Type</label>
                <input
                  name="entity_type"
                  className="form-control"
                  value={filters.entity_type}
                  onChange={updateFilter}
                  placeholder="e.g. Employee"
                />
              </div>

              <div className="col-md-4">
                <label className="form-label">Entity ID</label>
                <input
                  name="entity_id"
                  className="form-control"
                  value={filters.entity_id}
                  onChange={updateFilter}
                />
              </div>

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

              <div className="col-12 d-flex flex-wrap gap-2">
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={loading}
                >
                  Apply Filters
                </button>

                <button
                  type="button"
                  className="btn btn-outline-secondary"
                  onClick={clearFilters}
                >
                  Clear Filters
                </button>

                <button
                  type="button"
                  className="btn btn-outline-primary"
                  onClick={loadLogs}
                  disabled={loading}
                >
                  Refresh
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>

      <div className="card mb-4">
        <div className="card-body">
          <div className="d-flex flex-wrap justify-content-between align-items-center mb-3 gap-2">
            <h5 className="mb-0">Recorded Events</h5>

            <div className="d-flex gap-2">
              <button
                type="button"
                className="btn btn-outline-secondary btn-sm"
                disabled={loading || skip === 0}
                onClick={() =>
                  setSkip((current) =>
                    Math.max(0, current - PAGE_SIZE)
                  )
                }
              >
                Previous
              </button>

              <button
                type="button"
                className="btn btn-outline-secondary btn-sm"
                disabled={loading || logs.length < PAGE_SIZE}
                onClick={() =>
                  setSkip((current) => current + PAGE_SIZE)
                }
              >
                Next
              </button>
            </div>
          </div>

          {loading ? (
            <p>Loading audit logs...</p>
          ) : logs.length === 0 ? (
            <p className="text-muted mb-0">
              No audit records match these filters.
            </p>
          ) : (
            <div className="table-responsive">
              <table className="table table-hover align-middle">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Time</th>
                    <th>Actor</th>
                    <th>Action</th>
                    <th>Entity</th>
                    <th>Description</th>
                    <th>Details</th>
                  </tr>
                </thead>

                <tbody>
                  {logs.map((log) => (
                    <tr key={log.id}>
                      <td>{log.id}</td>
                      <td>{formatDateTime(log.created_at)}</td>
                      <td>
                        <div>{log.actor_email || "Unknown user"}</div>
                        <small className="text-muted">
                          User ID: {log.actor_user_id ?? "—"}
                        </small>
                      </td>
                      <td>
                        <span className="badge bg-secondary">
                          {log.action}
                        </span>
                      </td>
                      <td>
                        {log.entity_type}
                        {log.entity_id
                          ? ` #${log.entity_id}`
                          : ""}
                      </td>
                      <td>{log.description}</td>
                      <td>
                        <button
                          type="button"
                          className="btn btn-sm btn-outline-primary"
                          onClick={() =>
                            setSelectedLog(
                              selectedLog?.id === log.id
                                ? null
                                : log
                            )
                          }
                        >
                          {selectedLog?.id === log.id
                            ? "Hide"
                            : "View"}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div className="text-muted small mt-3">
            Showing {logs.length ? skip + 1 : 0}
            {"–"}
            {skip + logs.length} records on this page.
          </div>
        </div>
      </div>

      {selectedLog && (
        <div className="card">
          <div className="card-body">
            <h5>Audit Record #{selectedLog.id}</h5>

            <p>
              <strong>Actor roles:</strong>{" "}
              {selectedLog.actor_roles || "—"}
            </p>

            <p>
              <strong>IP address:</strong>{" "}
              {selectedLog.ip_address || "—"}
            </p>

            <p>
              <strong>User agent:</strong>{" "}
              {selectedLog.user_agent || "—"}
            </p>

            <h6>Details</h6>

            <pre className="bg-light text-dark rounded p-3">
              {JSON.stringify(selectedLog.details ?? {}, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </section>
  );
}
