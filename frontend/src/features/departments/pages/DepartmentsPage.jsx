
import { useCallback, useEffect, useState } from "react";
import {
  Building2,
  Edit,
  Plus,
  RefreshCw,
  Search,
  X,
} from "lucide-react";

import {
  createDepartment,
  deactivateDepartment,
  getDepartments,
  updateDepartment,
} from "../../../api/departmentApi";

function getErrorMessage(error, fallback) {
  const detail = error?.response?.data?.detail;

  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg || "Invalid input").join(", ");
  }

  return fallback;
}

const EMPTY_FORM = {
  name: "",
  description: "",
};

export default function DepartmentsPage() {
  const [departments, setDepartments] = useState([]);
  const [form, setForm] = useState(EMPTY_FORM);
  const [editingId, setEditingId] = useState(null);
  const [search, setSearch] = useState("");

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deactivatingId, setDeactivatingId] = useState(null);

  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const loadDepartments = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const data = await getDepartments();
      setDepartments(Array.isArray(data) ? data : []);
    } catch (err) {
      setDepartments([]);
      setError(
        getErrorMessage(err, "Unable to load departments.")
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDepartments();
  }, [loadDepartments]);

  function resetForm() {
    setForm(EMPTY_FORM);
    setEditingId(null);
  }

  function startEdit(department) {
    setEditingId(department.id);

    setForm({
      name: department.name || "",
      description: department.description || "",
    });

    setError("");
    setMessage("");
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setMessage("");

    const name = form.name.trim();

    if (name.length < 2) {
      setError("Department name must contain at least 2 characters.");
      return;
    }

    setSaving(true);

    try {
      const payload = {
        name,
        description: form.description.trim() || null,
      };

      if (editingId !== null) {
        await updateDepartment(editingId, payload);
        setMessage("Department updated successfully.");
      } else {
        await createDepartment(payload);
        setMessage("Department created successfully.");
      }

      resetForm();
      await loadDepartments();
    } catch (err) {
      setError(
        getErrorMessage(
          err,
          "Unable to save the department."
        )
      );
    } finally {
      setSaving(false);
    }
  }

  async function handleDeactivate(department) {
    if (!department.is_active) return;

    const confirmed = window.confirm(
      `Deactivate the department "${department.name}"?`
    );

    if (!confirmed) return;

    setDeactivatingId(department.id);
    setError("");
    setMessage("");

    try {
      await deactivateDepartment(department.id);

      if (editingId === department.id) {
        resetForm();
      }

      setMessage("Department deactivated successfully.");
      await loadDepartments();
    } catch (err) {
      setError(
        getErrorMessage(
          err,
          "Unable to deactivate the department."
        )
      );
    } finally {
      setDeactivatingId(null);
    }
  }

  const filteredDepartments = departments.filter((department) => {
    const query = search.trim().toLowerCase();

    if (!query) return true;

    return (
      department.name?.toLowerCase().includes(query) ||
      department.description?.toLowerCase().includes(query) ||
      String(department.id).includes(query)
    );
  });

  return (
    <section className="container-fluid py-3">
      <div className="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
        <div>
          <h2 className="mb-1">Department Management</h2>
          <p className="text-muted mb-0">
            Create and manage organizational departments.
          </p>
        </div>

        <button
          type="button"
          className="btn btn-outline-primary"
          onClick={loadDepartments}
          disabled={loading}
        >
          <RefreshCw size={16} className="me-2" />
          Refresh
        </button>
      </div>

      {error && (
        <div className="alert alert-danger">{error}</div>
      )}

      {message && (
        <div className="alert alert-success">{message}</div>
      )}

      <div className="card mb-4">
        <div className="card-body">
          <h5 className="mb-3">
            <Building2 size={20} className="me-2" />
            {editingId !== null ? "Edit Department" : "Add Department"}
          </h5>

          <form className="row g-3" onSubmit={handleSubmit}>
            <div className="col-md-5">
              <label className="form-label">Department Name *</label>

              <input
                type="text"
                className="form-control"
                value={form.name}
                minLength={2}
                maxLength={120}
                onChange={(event) =>
                  setForm({ ...form, name: event.target.value })
                }
                placeholder="e.g. Engineering"
                required
              />
            </div>

            <div className="col-md-7">
              <label className="form-label">Description</label>

              <input
                type="text"
                className="form-control"
                value={form.description}
                maxLength={500}
                onChange={(event) =>
                  setForm({
                    ...form,
                    description: event.target.value,
                  })
                }
                placeholder="Brief department description"
              />
            </div>

            <div className="col-12 d-flex flex-wrap gap-2">
              <button
                type="submit"
                className="btn btn-primary"
                disabled={saving}
              >
                <Plus size={16} className="me-2" />
                {saving
                  ? "Saving..."
                  : editingId !== null
                    ? "Update Department"
                    : "Create Department"}
              </button>

              {editingId !== null && (
                <button
                  type="button"
                  className="btn btn-outline-secondary"
                  onClick={resetForm}
                  disabled={saving}
                >
                  <X size={16} className="me-1" />
                  Cancel Edit
                </button>
              )}
            </div>
          </form>
        </div>
      </div>

      <div className="card">
        <div className="card-body">
          <div className="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-3">
            <h5 className="mb-0">
              Departments ({departments.length})
            </h5>

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
                placeholder="Search departments"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />
            </div>
          </div>

          {loading ? (
            <p>Loading departments...</p>
          ) : filteredDepartments.length === 0 ? (
            <p className="text-muted mb-0">
              No departments found.
            </p>
          ) : (
            <div className="table-responsive">
              <table className="table table-hover align-middle">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Department</th>
                    <th>Description</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>

                <tbody>
                  {filteredDepartments.map((department) => (
                    <tr key={department.id}>
                      <td>{department.id}</td>
                      <td className="fw-semibold">{department.name}</td>
                      <td>{department.description || "—"}</td>

                      <td>
                        <span
                          className={
                            department.is_active
                              ? "badge bg-success"
                              : "badge bg-secondary"
                          }
                        >
                          {department.is_active ? "Active" : "Inactive"}
                        </span>
                      </td>

                      <td>
                        <div className="d-flex flex-wrap gap-2">
                          <button
                            type="button"
                            className="btn btn-sm btn-outline-primary"
                            onClick={() => startEdit(department)}
                          >
                            <Edit size={14} className="me-1" />
                            Edit
                          </button>

                          {department.is_active && (
                            <button
                              type="button"
                              className="btn btn-sm btn-outline-danger"
                              onClick={() => handleDeactivate(department)}
                              disabled={deactivatingId === department.id}
                            >
                              {deactivatingId === department.id
                                ? "Deactivating..."
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
      </div>
    </section>
  );
}
