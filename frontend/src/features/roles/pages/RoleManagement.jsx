
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ShieldCheck,
  Plus,
  RefreshCw,
  Edit,
  Users,
  KeyRound,
  X,
} from "lucide-react";

import {
  assignPermissionToRole,
  assignUserToRole,
  createPermission,
  createRole,
  deactivateRole,
  deletePermission,
  getPermissions,
  getRoles,
  removePermissionFromRole,
  removeUserFromRole,
  updatePermission,
  updateRole,
} from "../../../api/roleApi";

import { getUsers } from "../../../api/userApi";
import { useAuth } from "../../../hooks/useAuth";

const EMPTY_ROLE = { name: "", description: "" };
const EMPTY_PERMISSION = { code: "", description: "" };

function getErrorMessage(error, fallback) {
  const detail = error?.response?.data?.detail;

  if (typeof detail === "string") return detail;

  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg || "Invalid input").join(", ");
  }

  return fallback;
}

function getName(user) {
  return [user.first_name, user.last_name].filter(Boolean).join(" ");
}

export default function RoleManagement() {
  const { user: currentUser } = useAuth();
  const isAdmin = currentUser?.roles?.includes("ADMIN") ?? false;

  const [roles, setRoles] = useState([]);
  const [permissions, setPermissions] = useState([]);
  const [users, setUsers] = useState([]);

  const [roleForm, setRoleForm] = useState(EMPTY_ROLE);
  const [editingRoleId, setEditingRoleId] = useState(null);

  const [permissionForm, setPermissionForm] = useState(EMPTY_PERMISSION);
  const [editingPermissionId, setEditingPermissionId] = useState(null);

  const [activeRoleId, setActiveRoleId] = useState(null);
  const [selectedUserId, setSelectedUserId] = useState("");

  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [actionKey, setActionKey] = useState("");

  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const loadData = useCallback(async () => {
    setLoading(true);
    setError("");

    const results = await Promise.allSettled([
      getRoles(),
      getPermissions(),
      getUsers(),
    ]);

    if (results[0].status === "fulfilled") {
      setRoles(
        Array.isArray(results[0].value) ? results[0].value : []
      );
    } else {
      setRoles([]);
      setError(
        getErrorMessage(results[0].reason, "Unable to load roles.")
      );
    }

    if (results[1].status === "fulfilled") {
      setPermissions(
        Array.isArray(results[1].value) ? results[1].value : []
      );
    } else {
      setPermissions([]);
      setError((current) =>
        current ||
        getErrorMessage(
          results[1].reason,
          "Unable to load permissions."
        )
      );
    }

    if (results[2].status === "fulfilled") {
      setUsers(
        Array.isArray(results[2].value) ? results[2].value : []
      );
    } else {
      setUsers([]);
      setError((current) =>
        current ||
        getErrorMessage(results[2].reason, "Unable to load users.")
      );
    }

    setLoading(false);
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const activeRole = roles.find((role) => role.id === activeRoleId);

  const filteredRoles = useMemo(() => {
    const query = search.trim().toLowerCase();

    return roles.filter((role) => {
      return (
        !query ||
        role.name.toLowerCase().includes(query) ||
        (role.description || "").toLowerCase().includes(query)
      );
    });
  }, [roles, search]);

  function resetRoleForm() {
    setRoleForm(EMPTY_ROLE);
    setEditingRoleId(null);
  }

  function resetPermissionForm() {
    setPermissionForm(EMPTY_PERMISSION);
    setEditingPermissionId(null);
  }

  function startRoleEdit(role) {
    setEditingRoleId(role.id);
    setRoleForm({
      name: role.name || "",
      description: role.description || "",
    });
    setError("");
    setMessage("");
  }

  async function handleRoleSubmit(event) {
    event.preventDefault();
    setError("");
    setMessage("");

    const name = roleForm.name.trim();
    if (name.length < 2) {
      setError("Role name must contain at least 2 characters.");
      return;
    }

    setSaving(true);

    try {
      const payload = {
        name,
        description: roleForm.description.trim() || null,
      };

      if (editingRoleId !== null) {
        await updateRole(editingRoleId, payload);
        setMessage("Role updated successfully.");
      } else {
        await createRole(payload);
        setMessage("Role created successfully.");
      }

      resetRoleForm();
      await loadData();
    } catch (err) {
      setError(getErrorMessage(err, "Unable to save role."));
    } finally {
      setSaving(false);
    }
  }

  async function handleDeactivateRole(role) {
    if (role.name === "ADMIN") {
      setError("The built-in ADMIN role cannot be deactivated.");
      return;
    }

    if ((role.user_ids || []).length > 0) {
      setError(
        "Remove this role from assigned users before deactivating it."
      );
      return;
    }

    if (
      !window.confirm(
        `Deactivate role "${role.name}"? This role will remain in the database.`
      )
    ) {
      return;
    }

    setActionKey(`role-${role.id}`);
    setError("");
    setMessage("");

    try {
      await deactivateRole(role.id);
      setMessage("Role deactivated successfully.");

      if (activeRoleId === role.id) {
        setActiveRoleId(null);
      }

      await loadData();
    } catch (err) {
      setError(getErrorMessage(err, "Unable to deactivate role."));
    } finally {
      setActionKey("");
    }
  }

  async function handlePermissionSubmit(event) {
    event.preventDefault();
    setError("");
    setMessage("");

    const code = permissionForm.code.trim();

    if (code.length < 2) {
      setError("Permission code must contain at least 2 characters.");
      return;
    }

    setSaving(true);

    try {
      const payload = {
        code,
        description: permissionForm.description.trim() || null,
      };

      if (editingPermissionId !== null) {
        await updatePermission(editingPermissionId, payload);
        setMessage("Permission updated successfully.");
      } else {
        await createPermission(payload);
        setMessage("Permission created successfully.");
      }

      resetPermissionForm();
      await loadData();
    } catch (err) {
      setError(getErrorMessage(err, "Unable to save permission."));
    } finally {
      setSaving(false);
    }
  }

  function startPermissionEdit(permission) {
    setEditingPermissionId(permission.id);
    setPermissionForm({
      code: permission.code || "",
      description: permission.description || "",
    });
    setError("");
    setMessage("");
  }

  async function handleDeletePermission(permission) {
    const assigned = roles.some((role) =>
      (role.permission_ids || []).includes(permission.id)
    );

    if (assigned) {
      setError(
        "Remove this permission from every role before deleting it."
      );
      return;
    }

    if (
      !window.confirm(
        `Delete permission "${permission.code}"?`
      )
    ) {
      return;
    }

    setActionKey(`permission-${permission.id}`);
    setError("");
    setMessage("");

    try {
      await deletePermission(permission.id);
      setMessage("Permission deleted successfully.");
      await loadData();
    } catch (err) {
      setError(getErrorMessage(err, "Unable to delete permission."));
    } finally {
      setActionKey("");
    }
  }

  async function handlePermissionToggle(role, permissionId, checked) {
    setActionKey(`mapping-${role.id}-${permissionId}`);
    setError("");
    setMessage("");

    try {
      if (checked) {
        await assignPermissionToRole(role.id, permissionId);
      } else {
        await removePermissionFromRole(role.id, permissionId);
      }

      setMessage("Role permissions updated.");
      await loadData();
    } catch (err) {
      setError(
        getErrorMessage(err, "Unable to update role permissions.")
      );
    } finally {
      setActionKey("");
    }
  }

  async function handleAssignUser(event) {
    event.preventDefault();

    if (!activeRole || !selectedUserId) {
      setError("Select a user to assign to this role.");
      return;
    }

    setActionKey(`assign-user-${activeRole.id}`);
    setError("");
    setMessage("");

    try {
      await assignUserToRole(activeRole.id, Number(selectedUserId));
      setSelectedUserId("");
      setMessage("User assigned to role successfully.");
      await loadData();
    } catch (err) {
      setError(
        getErrorMessage(err, "Unable to assign user to role.")
      );
    } finally {
      setActionKey("");
    }
  }

  async function handleRemoveUser(role, user) {
    if (role.name === "ADMIN" && user.id === currentUser?.id) {
      setError("You cannot remove your own ADMIN role.");
      return;
    }

    if (
      !window.confirm(
        `Remove the "${role.name}" role from ${user.email}?`
      )
    ) {
      return;
    }

    setActionKey(`remove-user-${role.id}-${user.id}`);
    setError("");
    setMessage("");

    try {
      await removeUserFromRole(role.id, user.id);
      setMessage("Role assignment removed.");
      await loadData();
    } catch (err) {
      setError(
        getErrorMessage(err, "Unable to remove the role assignment.")
      );
    } finally {
      setActionKey("");
    }
  }

  const assignedUserIds = activeRole?.user_ids || [];
  const assignedUsers = users.filter((item) =>
    assignedUserIds.includes(item.id)
  );
  const availableUsers = users.filter(
    (item) =>
      item.is_active && !assignedUserIds.includes(item.id)
  );

  return (
    <section className="container-fluid py-3">
      <div className="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
        <div>
          <h2 className="mb-1">Roles & Permissions</h2>
          <p className="text-muted mb-0">
            Manage access roles, assign users, and configure permissions.
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

      {!isAdmin && (
        <div className="alert alert-info">
          You can view roles and permissions. Only an Admin can make changes.
        </div>
      )}

      <div className="row g-4">
        <div className="col-xl-5">
          <div className="card mb-4">
            <div className="card-body">
              <h5 className="mb-3">
                <ShieldCheck size={20} className="me-2" />
                {editingRoleId ? "Edit Role" : "Create Role"}
              </h5>

              {isAdmin && (
                <form className="row g-3" onSubmit={handleRoleSubmit}>
                  <div className="col-12">
                    <label className="form-label">Role Name *</label>
                    <input
                      className="form-control"
                      value={roleForm.name}
                      minLength={2}
                      maxLength={30}
                      onChange={(event) =>
                        setRoleForm({
                          ...roleForm,
                          name: event.target.value,
                        })
                      }
                      placeholder="e.g. PAYROLL_MANAGER"
                      required
                    />
                  </div>

                  <div className="col-12">
                    <label className="form-label">Description</label>
                    <textarea
                      className="form-control"
                      rows={2}
                      maxLength={250}
                      value={roleForm.description}
                      onChange={(event) =>
                        setRoleForm({
                          ...roleForm,
                          description: event.target.value,
                        })
                      }
                      placeholder="Describe this role's responsibility"
                    />
                  </div>

                  <div className="col-12 d-flex gap-2">
                    <button
                      type="submit"
                      className="btn btn-primary"
                      disabled={saving}
                    >
                      <Plus size={16} className="me-2" />
                      {saving
                        ? "Saving..."
                        : editingRoleId
                          ? "Update Role"
                          : "Create Role"}
                    </button>

                    {editingRoleId && (
                      <button
                        type="button"
                        className="btn btn-outline-secondary"
                        onClick={resetRoleForm}
                      >
                        <X size={16} className="me-1" />
                        Cancel
                      </button>
                    )}
                  </div>
                </form>
              )}

              {!isAdmin && (
                <p className="text-muted mb-0">
                  Role editing is restricted to Admin accounts.
                </p>
              )}
            </div>
          </div>

          <div className="card">
            <div className="card-body">
              <div className="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-3">
                <h5 className="mb-0">Roles ({roles.length})</h5>
                <input
                  type="search"
                  className="form-control"
                  style={{ maxWidth: "220px" }}
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Search roles"
                  aria-label="Search roles"
                />
              </div>

              {loading ? (
                <p>Loading roles...</p>
              ) : filteredRoles.length === 0 ? (
                <p className="text-muted mb-0">No roles found.</p>
              ) : (
                <div className="table-responsive">
                  <table className="table table-hover align-middle">
                    <thead>
                      <tr>
                        <th>Role</th>
                        <th>Users</th>
                        <th>Status</th>
                        <th>Actions</th>
                      </tr>
                    </thead>

                    <tbody>
                      {filteredRoles.map((role) => (
                        <tr key={role.id}>
                          <td>
                            <div className="fw-semibold">{role.name}</div>
                            <small className="text-muted">
                              {role.description || "No description"}
                            </small>
                          </td>

                          <td>{role.user_count ?? role.user_ids?.length ?? 0}</td>

                          <td>
                            <span
                              className={
                                role.is_active
                                  ? "badge bg-success"
                                  : "badge bg-secondary"
                              }
                            >
                              {role.is_active ? "Active" : "Inactive"}
                            </span>
                          </td>

                          <td>
                            <div className="d-flex flex-wrap gap-1">
                              <button
                                type="button"
                                className="btn btn-sm btn-outline-primary"
                                onClick={() =>
                                  setActiveRoleId(
                                    activeRoleId === role.id ? null : role.id
                                  )
                                }
                              >
                                <KeyRound size={14} className="me-1" />
                                Manage
                              </button>

                              {isAdmin && (
                                <>
                                  <button
                                    type="button"
                                    className="btn btn-sm btn-outline-secondary"
                                    onClick={() => startRoleEdit(role)}
                                  >
                                    <Edit size={14} />
                                  </button>

                                  {role.is_active && role.name !== "ADMIN" && (
                                    <button
                                      type="button"
                                      className="btn btn-sm btn-outline-danger"
                                      disabled={
                                        actionKey === `role-${role.id}`
                                      }
                                      onClick={() =>
                                        handleDeactivateRole(role)
                                      }
                                    >
                                      Deactivate
                                    </button>
                                  )}
                                </>
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
          </div>
        </div>

        <div className="col-xl-7">
          <div className="card mb-4">
            <div className="card-body">
              <h5 className="mb-3">
                <KeyRound size={20} className="me-2" />
                Permission Catalogue
              </h5>

              {isAdmin && (
                <form
                  className="row g-3 mb-4"
                  onSubmit={handlePermissionSubmit}
                >
                  <div className="col-md-5">
                    <label className="form-label">Permission Code *</label>
                    <input
                      className="form-control"
                      value={permissionForm.code}
                      minLength={2}
                      maxLength={100}
                      onChange={(event) =>
                        setPermissionForm({
                          ...permissionForm,
                          code: event.target.value,
                        })
                      }
                      placeholder="e.g. EMPLOYEE_READ"
                      required
                    />
                  </div>

                  <div className="col-md-7">
                    <label className="form-label">Description</label>
                    <input
                      className="form-control"
                      value={permissionForm.description}
                      maxLength={250}
                      onChange={(event) =>
                        setPermissionForm({
                          ...permissionForm,
                          description: event.target.value,
                        })
                      }
                      placeholder="Describe the permission"
                    />
                  </div>

                  <div className="col-12 d-flex gap-2">
                    <button
                      type="submit"
                      className="btn btn-primary"
                      disabled={saving}
                    >
                      {saving
                        ? "Saving..."
                        : editingPermissionId
                          ? "Update Permission"
                          : "Create Permission"}
                    </button>

                    {editingPermissionId && (
                      <button
                        type="button"
                        className="btn btn-outline-secondary"
                        onClick={resetPermissionForm}
                      >
                        Cancel
                      </button>
                    )}
                  </div>
                </form>
              )}

              {permissions.length === 0 ? (
                <p className="text-muted mb-0">
                  No permissions have been created yet.
                </p>
              ) : (
                <div className="table-responsive">
                  <table className="table table-hover align-middle">
                    <thead>
                      <tr>
                        <th>Code</th>
                        <th>Description</th>
                        {isAdmin && <th>Actions</th>}
                      </tr>
                    </thead>

                    <tbody>
                      {permissions.map((permission) => {
                        const assigned = roles.some((role) =>
                          (role.permission_ids || []).includes(permission.id)
                        );

                        return (
                          <tr key={permission.id}>
                            <td className="fw-semibold">{permission.code}</td>
                            <td>{permission.description || "—"}</td>

                            {isAdmin && (
                              <td>
                                <div className="d-flex gap-1">
                                  <button
                                    type="button"
                                    className="btn btn-sm btn-outline-primary"
                                    onClick={() =>
                                      startPermissionEdit(permission)
                                    }
                                  >
                                    <Edit size={14} />
                                  </button>

                                  <button
                                    type="button"
                                    className="btn btn-sm btn-outline-danger"
                                    disabled={
                                      assigned ||
                                      actionKey ===
                                        `permission-${permission.id}`
                                    }
                                    title={
                                      assigned
                                        ? "Remove from all roles before deleting"
                                        : "Delete permission"
                                    }
                                    onClick={() =>
                                      handleDeletePermission(permission)
                                    }
                                  >
                                    Delete
                                  </button>
                                </div>
                              </td>
                            )}
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>

          {activeRole && (
            <div className="card">
              <div className="card-body">
                <h5 className="mb-1">
                  Manage: {activeRole.name}
                </h5>

                <p className="text-muted small mb-4">
                  Assign permissions and users to this role.
                </p>

                <h6>Permissions</h6>

                {permissions.length === 0 ? (
                  <p className="text-muted">
                    Create permissions before assigning them.
                  </p>
                ) : (
                  <div className="row g-2 mb-4">
                    {permissions.map((permission) => {
                      const checked = (
                        activeRole.permission_ids || []
                      ).includes(permission.id);

                      return (
                        <div className="col-md-6" key={permission.id}>
                          <label className="form-check border rounded p-3">
                            <input
                              type="checkbox"
                              className="form-check-input me-2"
                              checked={checked}
                              disabled={
                                !isAdmin ||
                                !activeRole.is_active ||
                                actionKey ===
                                  `mapping-${activeRole.id}-${permission.id}`
                              }
                              onChange={(event) =>
                                handlePermissionToggle(
                                  activeRole,
                                  permission.id,
                                  event.target.checked
                                )
                              }
                            />

                            <span className="form-check-label">
                              <strong>{permission.code}</strong>
                              <br />
                              <small className="text-muted">
                                {permission.description || "No description"}
                              </small>
                            </span>
                          </label>
                        </div>
                      );
                    })}
                  </div>
                )}

                <hr />

                <h6>
                  <Users size={17} className="me-2" />
                  Assigned Users ({assignedUsers.length})
                </h6>

                {isAdmin && activeRole.is_active && (
                  <form
                    className="d-flex flex-wrap gap-2 mb-3"
                    onSubmit={handleAssignUser}
                  >
                    <select
                      className="form-select"
                      style={{ maxWidth: "360px" }}
                      value={selectedUserId}
                      onChange={(event) =>
                        setSelectedUserId(event.target.value)
                      }
                      required
                    >
                      <option value="">Select an active user</option>

                      {availableUsers.map((item) => (
                        <option key={item.id} value={item.id}>
                          {getName(item) || item.email} — {item.email}
                        </option>
                      ))}
                    </select>

                    <button
                      type="submit"
                      className="btn btn-primary"
                      disabled={
                        !selectedUserId ||
                        actionKey === `assign-user-${activeRole.id}`
                      }
                    >
                      Assign Role
                    </button>
                  </form>
                )}

                {assignedUsers.length === 0 ? (
                  <p className="text-muted mb-0">
                    No users are assigned to this role.
                  </p>
                ) : (
                  <div className="table-responsive">
                    <table className="table table-sm align-middle">
                      <thead>
                        <tr>
                          <th>User</th>
                          <th>Status</th>
                          {isAdmin && <th>Action</th>}
                        </tr>
                      </thead>

                      <tbody>
                        {assignedUsers.map((item) => (
                          <tr key={item.id}>
                            <td>
                              <div>{getName(item) || item.email}</div>
                              <small className="text-muted">
                                {item.email}
                              </small>
                            </td>

                            <td>
                              <span
                                className={
                                  item.is_active
                                    ? "badge bg-success"
                                    : "badge bg-secondary"
                                }
                              >
                                {item.is_active ? "Active" : "Inactive"}
                              </span>
                            </td>

                            {isAdmin && (
                              <td>
                                <button
                                  type="button"
                                  className="btn btn-sm btn-outline-danger"
                                  disabled={
                                    actionKey ===
                                      `remove-user-${activeRole.id}-${item.id}` ||
                                    (activeRole.name === "ADMIN" &&
                                      item.id === currentUser?.id)
                                  }
                                  onClick={() =>
                                    handleRemoveUser(activeRole, item)
                                  }
                                >
                                  Remove Role
                                </button>
                              </td>
                            )}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {!isAdmin && (
                  <p className="text-muted small mt-3 mb-0">
                    Only Admin can change role assignments.
                  </p>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
