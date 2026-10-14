
import { useCallback, useEffect, useState } from "react";
import {
  Edit,
  Plus,
  RefreshCw,
  Search,
  X,
  BriefcaseBusiness,
} from "lucide-react";

import {
  createDesignation,
  deactivateDesignation,
  getDesignations,
  updateDesignation,
} from "../../../api/designationApi";

import { getDepartments } from "../../../api/departmentApi";

const EMPTY_FORM = {
  name: "",
  department_id: "",
  level: "",
};

function getErrorMessage(error, fallback) {
  const detail = error?.response?.data?.detail;

  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg || "Invalid input").join(", ");
  }

  return fallback;
}

export default function DesignationsPage() {
  const [designations, setDesignations] = useState([]);
  const [departments, setDepartments] = useState([]);

  const [form, setForm] = useState(EMPTY_FORM);
  const [editingId, setEditingId] = useState(null);
  const [search, setSearch] = useState("");

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deactivatingId, setDeactivatingId] = useState(null);

  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const loadData = useCallback(async () => {
    setLoading(true);
    setError("");

    const [designationResult, departmentResult] =
      await Promise.allSettled([
        getDesignations(),
        getDepartments(),
      ]);

    if (designationResult.status === "fulfilled") {
      setDesignations(
        Array.isArray(designationResult.value)
          ? designationResult.value
          : []
      );
    } else {
      setDesignations([]);
      setError(
        getErrorMessage(
          designationResult.reason,
          "Unable to load designations."
        )
      );
    }

    if (departmentResult.status === "fulfilled") {
      setDepartments(
        Array.isArray(departmentResult.value)
          ? departmentResult.value
          : []
      );
    } else {
      setDepartments([]);
      setError((current) =>
        current ||
        getErrorMessage(
          departmentResult.reason,
          "Unable to load departments for designation selection."
        )
      );
    }

    setLoading(false);
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  function resetForm() {
    setForm(EMPTY_FORM);
    setEditingId(null);
  }

  function startEdit(designation) {
    setEditingId(designation.id);

    setForm({
      name: designation.name || "",
      department_id: String(designation.department_id ?? ""),
      level: designation.level || "",
    });

    setError("");
    setMessage("");
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setMessage("");

    const name = form.name.trim();
    const departmentId = Number(form.department_id);
    const level = form.level.trim();

    if (name.length < 2) {
      setError("Designation name must contain at least 2 characters.");
      return;
    }

    if (!Number.isInteger(departmentId) || departmentId <= 0) {
      setError("Please select a valid department.");
      return;
    }

    const selectedDepartment = departments.find(
      (department) => department.id === departmentId
    );

    if (!selectedDepartment || !selectedDepartment.is_active) {
      setError("Please select an active department.");
      return;
    }

    setSaving(true);

    try {
      const payload = {
        name,
        department_id: departmentId,
        level: level || null,
      };

      if (editingId !== null) {
        await updateDesignation(editingId, payload);
        setMessage("Designation updated successfully.");
      } else {
        await createDesignation(payload);
        setMessage("Designation created successfully.");
      }

      resetForm();
      await loadData();
    } catch (err) {
      setError(
        getErrorMessage(err, "Unable to save the designation.")
      );
    } finally {
      setSaving(false);
    }
  }

  async function handleDeactivate(designation) {
    if (!designation.is_active) return;

    const confirmed = window.confirm(
      `Deactivate the designation "${designation.name}"?`
    );

    if (!confirmed) return;

    setDeactivatingId(designation.id);
    setError("");
    setMessage("");

    try {
      await deactivateDesignation(designation.id);

      if (editingId === designation.id) {
        resetForm();
      }

      setMessage("Designation deactivated successfully.");
      await loadData();
    } catch (err) {
      setError(
        getErrorMessage(
          err,
          "Unable to deactivate the designation."
        )
      );
    } finally {
      setDeactivatingId(null);
    }
  }

  const departmentNames = Object.fromEntries(
    departments.map((department) => [
      String(department.id),
      department.name,
    ])
  );

  const filteredDesignations = designations.filter((designation) => {
    const query = search.trim().toLowerCase();

    if (!query) return true;

    const departmentName =
      departmentNames[String(designation.department_id)] || "";

    return (
      designation.name?.toLowerCase().includes(query) ||
      designation.level?.toLowerCase().includes(query) ||
      departmentName.toLowerCase().includes(query) ||
      String(designation.id).includes(query)
    );
  });

  const activeDepartments = departments.filter(
    (department) => department.is_active
  );

  return (
    <section className="container-fluid py-3">
      <div className="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
        <div>
          <h2 className="mb-1">Designation Management</h2>
          <p className="text-muted mb-0">
            Manage designations and their associated departments.
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

      {error && (
        <div className="alert alert-danger">{error}</div>
      )}

      {message && (
        <div className="alert alert-success">{message}</div>
      )}

      <div className="card mb-4">
        <div className="card-body">
          <h5 className="mb-3">
            <BriefcaseBusiness size={20} className="me-2" />
            {editingId !== null ? "Edit Designation" : "Add Designation"}
          </h5>

          <form className="row g-3" onSubmit={handleSubmit}>
            <div className="col-md-4">
              <label className="form-label">Designation Name *</label>

              <input
                type="text"
                className="form-control"
                value={form.name}
                minLength={2}
                maxLength={120}
                onChange={(event) =>
                  setForm({ ...form, name: event.target.value })
                }
                placeholder="e.g. Software Engineer"
                required
              />
            </div>

            <div className="col-md-4">
              <label className="form-label">Department *</label>

              <select
                className="form-select"
                value={form.department_id}
                onChange={(event) =>
                  setForm({
                    ...form,
                    department_id: event.target.value,
                  })
                }
                required
              >
                <option value="">Select department</option>

                {activeDepartments.map((department) => (
                  <option key={department.id} value={department.id}>
                    {department.name}
                  </option>
                ))}
              </select>

              {activeDepartments.length === 0 && (
                <small className="text-muted">
                  Create or activate a department before adding a designation.
                </small>
              )}
            </div>

            <div className="col-md-4">
              <label className="form-label">Level</label>

              <input
                type="text"
                className="form-control"
                value={form.level}
                maxLength={50}
                onChange={(event) =>
                  setForm({ ...form, level: event.target.value })
                }
                placeholder="e.g. Junior, Mid, Senior"
              />
            </div>

            <div className="col-12 d-flex flex-wrap gap-2">
              <button
                type="submit"
                className="btn btn-primary"
                disabled={saving || activeDepartments.length === 0}
              >
                <Plus size={16} className="me-2" />
                {saving
                  ? "Saving..."
                  : editingId !== null
                    ? "Update Designation"
                    : "Create Designation"}
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
              Designations ({designations.length})
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
                placeholder="Search designations"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />
            </div>
          </div>

          {loading ? (
            <p>Loading designations...</p>
          ) : filteredDesignations.length === 0 ? (
            <p className="text-muted mb-0">
              No designations found.
            </p>
          ) : (
            <div className="table-responsive">
              <table className="table table-hover align-middle">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Designation</th>
                    <th>Department</th>
                    <th>Level</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>

                <tbody>
                  {filteredDesignations.map((designation) => (
                    <tr key={designation.id}>
                      <td>{designation.id}</td>

                      <td className="fw-semibold">
                        {designation.name}
                      </td>

                      <td>
                        {departmentNames[
                          String(designation.department_id)
                        ] || `Department #${designation.department_id}`}
                      </td>

                      <td>{designation.level || "—"}</td>

                      <td>
                        <span
                          className={
                            designation.is_active
                              ? "badge bg-success"
                              : "badge bg-secondary"
                          }
                        >
                          {designation.is_active ? "Active" : "Inactive"}
                        </span>
                      </td>

                      <td>
                        <div className="d-flex flex-wrap gap-2">
                          <button
                            type="button"
                            className="btn btn-sm btn-outline-primary"
                            onClick={() => startEdit(designation)}
                          >
                            <Edit size={14} className="me-1" />
                            Edit
                          </button>

                          {designation.is_active && (
                            <button
                              type="button"
                              className="btn btn-sm btn-outline-danger"
                              onClick={() =>
                                handleDeactivate(designation)
                              }
                              disabled={
                                deactivatingId === designation.id
                              }
                            >
                              {deactivatingId === designation.id
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
