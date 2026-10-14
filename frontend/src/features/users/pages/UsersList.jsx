
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Edit,
  RefreshCw,
  Search,
  Users,
  UserCheck,
  UserX,
} from "lucide-react";

import { getUsers, updateUser } from "../../../api/userApi";
import { useAuth } from "../../../hooks/useAuth";

function errorMessage(error, fallback) {
  const detail = error?.response?.data?.detail;

  if (typeof detail === "string") return detail;

  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg || "Invalid input").join(", ");
  }

  return fallback;
}

export default function UsersList() {
  const navigate = useNavigate();
  const { user: currentUser } = useAuth();

  const isAdmin = currentUser?.roles?.includes("ADMIN") ?? false;

  const [users, setUsers] = useState([]);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");

  const [loading, setLoading] = useState(true);
  const [updatingId, setUpdatingId] = useState(null);

  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const loadUsers = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const data = await getUsers();
      setUsers(Array.isArray(data) ? data : []);
    } catch (err) {
      setUsers([]);
      setError(errorMessage(err, "Unable to load users."));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  const filteredUsers = useMemo(() => {
    const query = search.trim().toLowerCase();

    return users.filter((item) => {
      const matchesSearch =
        !query ||
        `${item.first_name || ""} ${item.last_name || ""}`
          .toLowerCase()
          .includes(query) ||
        item.email?.toLowerCase().includes(query) ||
        item.employee_code?.toLowerCase().includes(query) ||
        (item.roles || []).some((role) =>
          role.toLowerCase().includes(query)
        ) ||
        String(item.id).includes(query);

      const matchesStatus =
        statusFilter === "ALL" ||
        (statusFilter === "ACTIVE" && item.is_active) ||
        (statusFilter === "INACTIVE" && !item.is_active);

      return matchesSearch && matchesStatus;
    });
  }, [users, search, statusFilter]);

  async function handleStatusChange(account) {
    const nextActiveStatus = !account.is_active;

    if (
      !nextActiveStatus &&
      account.id === currentUser?.id
    ) {
      setError("You cannot deactivate your own account.");
      return;
    }

    const confirmed = window.confirm(
      `${nextActiveStatus ? "Activate" : "Deactivate"} the account for ${account.email}?`
    );

    if (!confirmed) return;

    setUpdatingId(account.id);
    setError("");
    setMessage("");

    try {
      await updateUser(account.id, {
        is_active: nextActiveStatus,
      });

      setMessage(
        `Account ${nextActiveStatus ? "activated" : "deactivated"} successfully.`
      );

      await loadUsers();
    } catch (err) {
      setError(
        errorMessage(err, "Unable to change the user account status.")
      );
    } finally {
      setUpdatingId(null);
    }
  }

  const activeCount = users.filter((item) => item.is_active).length;
  const inactiveCount = users.length - activeCount;

  return (
    <section className="container-fluid py-3">
      <div className="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
        <div>
          <h2 className="mb-1">User Management</h2>
          <p className="text-muted mb-0">
            View user accounts, update names, and manage account status.
          </p>
        </div>

        <button
          type="button"
          className="btn btn-outline-primary"
          onClick={loadUsers}
          disabled={loading}
        >
          <RefreshCw size={16} className="me-2" />
          Refresh
        </button>
      </div>

      {error && <div className="alert alert-danger">{error}</div>}
      {message && <div className="alert alert-success">{message}</div>}

      <div className="row g-3 mb-4">
        <div className="col-sm-6 col-xl-4">
          <div className="card h-100">
            <div className="card-body">
              <Users size={22} className="text-primary mb-2" />
              <p className="text-muted mb-1">Total Accounts</p>
              <h3 className="mb-0">{users.length}</h3>
            </div>
          </div>
        </div>

        <div className="col-sm-6 col-xl-4">
          <div className="card h-100">
            <div className="card-body">
              <UserCheck size={22} className="text-success mb-2" />
              <p className="text-muted mb-1">Active Accounts</p>
              <h3 className="mb-0">{activeCount}</h3>
            </div>
          </div>
        </div>

        <div className="col-sm-6 col-xl-4">
          <div className="card h-100">
            <div className="card-body">
              <UserX size={22} className="text-secondary mb-2" />
              <p className="text-muted mb-1">Inactive Accounts</p>
              <h3 className="mb-0">{inactiveCount}</h3>
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-body">
          <div className="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-3">
            <h5 className="mb-0">User Accounts</h5>

            <div className="d-flex flex-wrap gap-2">
              <div
                className="input-group"
                style={{ maxWidth: "320px" }}
              >
                <span className="input-group-text">
                  <Search size={16} />
                </span>

                <input
                  type="search"
                  className="form-control"
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Search users"
                />
              </div>

              <select
                className="form-select"
                style={{ maxWidth: "160px" }}
                value={statusFilter}
                onChange={(event) =>
                  setStatusFilter(event.target.value)
                }
                aria-label="Filter by user status"
              >
                <option value="ALL">All statuses</option>
                <option value="ACTIVE">Active</option>
                <option value="INACTIVE">Inactive</option>
              </select>
            </div>
          </div>

          {loading ? (
            <p>Loading user accounts...</p>
          ) : filteredUsers.length === 0 ? (
            <p className="text-muted mb-0">
              No user accounts found.
            </p>
          ) : (
            <div className="table-responsive">
              <table className="table table-hover align-middle">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Name</th>
                    <th>Email</th>
                    <th>Employee Code</th>
                    <th>Roles</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>

                <tbody>
                  {filteredUsers.map((account) => (
                    <tr key={account.id}>
                      <td>{account.id}</td>

                      <td className="fw-semibold">
                        {[account.first_name, account.last_name]
                          .filter(Boolean)
                          .join(" ")}
                      </td>

                      <td>{account.email}</td>

                      <td>{account.employee_code || "—"}</td>

                      <td>
                        <div className="d-flex flex-wrap gap-1">
                          {(account.roles || []).length > 0 ? (
                            account.roles.map((role) => (
                              <span
                                key={role}
                                className="badge bg-light text-dark border"
                              >
                                {role}
                              </span>
                            ))
                          ) : (
                            <span className="text-muted">No active role</span>
                          )}
                        </div>
                      </td>

                      <td>
                        <span
                          className={
                            account.is_active
                              ? "badge bg-success"
                              : "badge bg-secondary"
                          }
                        >
                          {account.is_active ? "Active" : "Inactive"}
                        </span>
                      </td>

                      <td>
                        <div className="d-flex flex-wrap gap-2">
                          <button
                            type="button"
                            className="btn btn-sm btn-outline-primary"
                            onClick={() =>
                              navigate(`/admin/users/${account.id}/edit`)
                            }
                          >
                            <Edit size={14} className="me-1" />
                            Edit
                          </button>

                          {isAdmin ? (
                            <button
                              type="button"
                              className={
                                account.is_active
                                  ? "btn btn-sm btn-outline-danger"
                                  : "btn btn-sm btn-outline-success"
                              }
                              onClick={() => handleStatusChange(account)}
                              disabled={
                                updatingId === account.id ||
                                (account.id === currentUser?.id &&
                                  account.is_active)
                              }
                            >
                              {updatingId === account.id
                                ? "Updating..."
                                : account.is_active
                                  ? "Deactivate"
                                  : "Activate"}
                            </button>
                          ) : (
                            <span className="text-muted small">
                              Status changes require Admin
                            </span>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <p className="text-muted small mt-3 mb-0">
            New employee accounts are created through Employee Management.
            Role assignments are managed separately in Roles & Permissions.
          </p>
        </div>
      </div>
    </section>
  );
}
