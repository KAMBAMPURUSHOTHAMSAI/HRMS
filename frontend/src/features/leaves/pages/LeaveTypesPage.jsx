
import { useCallback, useEffect, useState } from "react";

import {
  createLeaveType,
  deactivateLeaveType,
  getLeaveTypes,
  updateLeaveType,
} from "../../../api/leaveApi";

const EMPTY_FORM = {
  code: "",
  name: "",
  description: "",
  is_paid: true,
  annual_quota: "12",
  is_active: true,
};

function getArray(data) {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.items)) return data.items;
  if (Array.isArray(data?.data)) return data.data;
  return [];
}

export default function LeaveTypesPage() {
  const [leaveTypes, setLeaveTypes] = useState([]);
  const [form, setForm] = useState({ ...EMPTY_FORM });
  const [editingId, setEditingId] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [includeInactive, setIncludeInactive] = useState(false);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const loadData = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const result = await getLeaveTypes(
        includeInactive ? { include_inactive: true } : {}
      );

      setLeaveTypes(getArray(result));
    } catch (err) {
      setLeaveTypes([]);
      setError(
        err.response?.data?.detail ||
          "Unable to load leave types."
      );
    } finally {
      setLoading(false);
    }
  }, [includeInactive]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  function startCreate() {
    setEditingId(null);
    setForm({ ...EMPTY_FORM });
    setShowForm(true);
    setError("");
    setMessage("");
  }

  function startEdit(item) {
    setEditingId(item.id);
    setForm({
      code: item.code,
      name: item.name,
      description: item.description || "",
      is_paid: item.is_paid,
      annual_quota: String(item.annual_quota ?? 0),
      is_active: item.is_active,
    });
    setShowForm(true);
    setError("");
    setMessage("");
  }

  function closeForm() {
    setShowForm(false);
    setEditingId(null);
    setForm({ ...EMPTY_FORM });
  }

  function updateField(event) {
    const { name, value, type, checked } = event.target;

    setForm((current) => ({
      ...current,
      [name]: type === "checkbox" ? checked : value,
    }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setMessage("");

    const quota = Number(form.annual_quota);

    if (!form.name.trim()) {
      setError("Leave type name is required.");
      return;
    }

    if (!Number.isFinite(quota) || quota < 0) {
      setError("Annual quota must be a non-negative number.");
      return;
    }

    if (form.is_paid && quota <= 0) {
      setError("Paid leave types must have a quota greater than zero.");
      return;
    }

    const payload = {
      name: form.name.trim(),
      description: form.description.trim() || null,
      is_paid: form.is_paid,
      annual_quota: quota,
    };

    setSaving(true);

    try {
      if (editingId !== null) {
        await updateLeaveType(editingId, {
          ...payload,
          is_active: form.is_active,
        });

        setMessage("Leave type updated successfully.");
      } else {
        if (!form.code.trim()) {
          setError("Leave type code is required.");
          return;
        }

        await createLeaveType({
          ...payload,
          code: form.code.trim().toUpperCase(),
        });

        setMessage("Leave type created successfully.");
      }

      closeForm();
      await loadData();
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          "Unable to save leave type."
      );
    } finally {
      setSaving(false);
    }
  }

  async function toggleActive(item) {
    setError("");
    setMessage("");

    const activate = !item.is_active;

    if (
      !activate &&
      !window.confirm(
        `Deactivate leave type "${item.name}"?`
      )
    ) {
      return;
    }

    try {
      if (activate) {
        await updateLeaveType(item.id, {
          is_active: true,
        });
      } else {
        await deactivateLeaveType(item.id);
      }

      setMessage(
        activate
          ? "Leave type activated successfully."
          : "Leave type deactivated successfully."
      );

      await loadData();
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          "Unable to update leave type status."
      );
    }
  }

  return (
    <section className="container-fluid py-3">
      <div className="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
        <div>
          <h2 className="mb-1">Leave Types</h2>
          <p className="text-muted mb-0">
            Configure leave categories and annual entitlements.
          </p>
        </div>

        <button
          type="button"
          className="btn btn-primary"
          onClick={startCreate}
        >
          + Create Leave Type
        </button>
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
        <div className="card-body d-flex flex-wrap justify-content-between align-items-center gap-3">
          <label className="form-check d-flex align-items-center gap-2 mb-0">
            <input
              type="checkbox"
              className="form-check-input"
              checked={includeInactive}
              onChange={(event) =>
                setIncludeInactive(event.target.checked)
              }
            />
            <span>Show inactive leave types</span>
          </label>

          <button
            type="button"
            className="btn btn-outline-primary"
            onClick={loadData}
            disabled={loading}
          >
            Refresh
          </button>
        </div>
      </div>

      {showForm && (
        <div className="card mb-4">
          <div className="card-body">
            <h5 className="mb-3">
              {editingId === null
                ? "Create Leave Type"
                : "Edit Leave Type"}
            </h5>

            <form className="row g-3" onSubmit={handleSubmit}>
              {editingId === null && (
                <div className="col-md-4">
                  <label className="form-label">
                    Code *
                  </label>
                  <input
                    className="form-control"
                    name="code"
                    value={form.code}
                    onChange={updateField}
                    minLength={2}
                    maxLength={30}
                    pattern="[A-Za-z][A-Za-z0-9_]*"
                    placeholder="e.g. CASUAL"
                    required
                  />
                </div>
              )}

              <div className="col-md-4">
                <label className="form-label">
                  Name *
                </label>
                <input
                  className="form-control"
                  name="name"
                  value={form.name}
                  onChange={updateField}
                  minLength={2}
                  maxLength={100}
                  required
                />
              </div>

              <div className="col-md-4">
                <label className="form-label">
                  Annual Quota (days) *
                </label>
                <input
                  type="number"
                  className="form-control"
                  name="annual_quota"
                  value={form.annual_quota}
                  onChange={updateField}
                  min="0"
                  max="9999"
                  step="0.5"
                  required={form.is_paid}
                />
              </div>

              <div className="col-12">
                <label className="form-label">
                  Description
                </label>
                <textarea
                  className="form-control"
                  name="description"
                  rows={3}
                  maxLength={2000}
                  value={form.description}
                  onChange={updateField}
                />
              </div>

              <div className="col-md-6">
                <label className="form-check">
                  <input
                    type="checkbox"
                    className="form-check-input"
                    name="is_paid"
                    checked={form.is_paid}
                    onChange={updateField}
                  />
                  <span className="form-check-label">
                    Paid leave
                  </span>
                </label>
              </div>

              {editingId !== null && (
                <div className="col-md-6">
                  <label className="form-check">
                    <input
                      type="checkbox"
                      className="form-check-input"
                      name="is_active"
                      checked={form.is_active}
                      onChange={updateField}
                    />
                    <span className="form-check-label">
                      Active
                    </span>
                  </label>
                </div>
              )}

              <div className="col-12 d-flex gap-2">
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={saving}
                >
                  {saving ? "Saving..." : "Save Leave Type"}
                </button>

                <button
                  type="button"
                  className="btn btn-outline-secondary"
                  onClick={closeForm}
                  disabled={saving}
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="card">
        <div className="card-body">
          <h5 className="mb-3">Configured Leave Types</h5>

          {loading ? (
            <p>Loading leave types...</p>
          ) : leaveTypes.length === 0 ? (
            <p className="text-muted mb-0">
              No leave types found.
            </p>
          ) : (
            <div className="table-responsive">
              <table className="table table-hover align-middle">
                <thead>
                  <tr>
                    <th>Code</th>
                    <th>Name</th>
                    <th>Paid?</th>
                    <th>Annual Quota</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>

                <tbody>
                  {leaveTypes.map((item) => (
                    <tr key={item.id}>
                      <td>{item.code}</td>
                      <td>
                        <strong>{item.name}</strong>
                        {item.description && (
                          <div className="text-muted small">
                            {item.description}
                          </div>
                        )}
                      </td>
                      <td>{item.is_paid ? "Yes" : "No"}</td>
                      <td>{item.annual_quota}</td>
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
                      <td>
                        <div className="d-flex flex-wrap gap-2">
                          <button
                            type="button"
                            className="btn btn-sm btn-outline-primary"
                            onClick={() => startEdit(item)}
                          >
                            Edit
                          </button>

                          <button
                            type="button"
                            className={
                              item.is_active
                                ? "btn btn-sm btn-outline-danger"
                                : "btn btn-sm btn-outline-success"
                            }
                            onClick={() => toggleActive(item)}
                          >
                            {item.is_active
                              ? "Deactivate"
                              : "Activate"}
                          </button>
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
