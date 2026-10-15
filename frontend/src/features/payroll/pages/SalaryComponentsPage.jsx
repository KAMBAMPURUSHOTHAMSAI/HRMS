
import { useCallback, useEffect, useState } from "react";
import {
  CheckCircle,
  Edit2,
  Plus,
  RefreshCw,
  Save,
  X,
} from "lucide-react";

import {
  createSalaryComponent,
  deactivateSalaryComponent,
  getSalaryComponents,
  updateSalaryComponent,
} from "../../../api/payrollApi";

const initialForm = {
  code: "",
  name: "",
  description: "",
  component_type: "EARNING",
  calculation_type: "FIXED",
  default_amount: "0.00",
  percentage_base: "BASE_PAY",
  is_variable: false,
  is_taxable: true,
};

function formatCurrency(value) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(Number(value ?? 0));
}

function getErrorMessage(error) {
  const detail = error?.response?.data?.detail;

  if (typeof detail === "string") return detail;

  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg || "Invalid value").join(", ");
  }

  return "Something went wrong. Please try again.";
}

export default function SalaryComponentsPage() {
  const [components, setComponents] = useState([]);
  const [form, setForm] = useState(initialForm);
  const [editingId, setEditingId] = useState(null);
  const [showForm, setShowForm] = useState(false);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [includeInactive, setIncludeInactive] = useState(false);

  const loadComponents = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const data = await getSalaryComponents(includeInactive);
      setComponents(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(getErrorMessage(err));
      setComponents([]);
    } finally {
      setLoading(false);
    }
  }, [includeInactive]);

  useEffect(() => {
    loadComponents();
  }, [loadComponents]);

  function openCreateForm() {
    setEditingId(null);
    setForm(initialForm);
    setShowForm(true);
    setError("");
    setMessage("");
  }

  function openEditForm(component) {
    setEditingId(component.id);

    setForm({
      code: component.code ?? "",
      name: component.name ?? "",
      description: component.description ?? "",
      component_type: component.component_type ?? "EARNING",
      calculation_type: component.calculation_type ?? "FIXED",
      default_amount: String(component.default_amount ?? "0.00"),
      percentage_base: component.percentage_base ?? "BASE_PAY",
      is_variable: Boolean(component.is_variable),
      is_taxable: Boolean(component.is_taxable),
    });

    setShowForm(true);
    setError("");
    setMessage("");
  }

  function closeForm() {
    setShowForm(false);
    setEditingId(null);
    setForm(initialForm);
  }

  function updateField(event) {
    const { name, value, checked, type } = event.target;

    setForm((previous) => ({
      ...previous,
      [name]: type === "checkbox" ? checked : value,
    }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setMessage("");

    const code = form.code.trim().toUpperCase();
    const name = form.name.trim();
    const amount = Number(form.default_amount);

    if (!code || !name) {
      setError("Component code and name are required.");
      return;
    }

    if (!Number.isFinite(amount) || amount < 0) {
      setError("Enter a valid non-negative amount.");
      return;
    }

    if (form.calculation_type === "PERCENTAGE" && amount > 100) {
      setError("Percentage must be between 0 and 100.");
      return;
    }

    const payload = {
      code,
      name,
      description: form.description.trim() || null,
      component_type: form.component_type,
      calculation_type: form.calculation_type,
      default_amount: amount.toFixed(2),
      percentage_base: form.percentage_base,
      is_variable: form.is_variable,
      is_taxable: form.is_taxable,
      is_active: true,
    };

    setSaving(true);

    try {
      if (editingId !== null) {
        await updateSalaryComponent(editingId, payload);
        setMessage("Salary component updated successfully.");
      } else {
        await createSalaryComponent(payload);
        setMessage("Salary component created successfully.");
      }

      closeForm();
      await loadComponents();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  async function handleDeactivate(component) {
    const confirmed = window.confirm(
      `Deactivate "${component.name}"? Existing payroll records will be preserved.`
    );

    if (!confirmed) return;

    setError("");
    setMessage("");

    try {
      await deactivateSalaryComponent(component.id);
      setMessage(`${component.name} was deactivated.`);
      await loadComponents();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  const activeCount = components.filter(
    (component) => component.is_active
  ).length;

  return (
    <section className="container-fluid py-3">
      <div className="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
        <div>
          <h2 className="mb-1">Salary Components</h2>
          <p className="text-muted mb-0">
            Configure earnings, deductions, allowances and variable pay.
          </p>
        </div>

        <div className="d-flex flex-wrap gap-2">
          <button
            type="button"
            className="btn btn-outline-primary"
            onClick={loadComponents}
            disabled={loading}
          >
            <RefreshCw size={16} className="me-2" />
            Refresh
          </button>

          <button
            type="button"
            className="btn btn-primary"
            onClick={openCreateForm}
          >
            <Plus size={17} className="me-2" />
            Add Component
          </button>
        </div>
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

      <div className="row g-3 mb-4">
        <div className="col-md-6 col-xl-4">
          <div className="card h-100">
            <div className="card-body">
              <p className="text-muted mb-1">Components displayed</p>
              <h3 className="mb-0">{components.length}</h3>
            </div>
          </div>
        </div>

        <div className="col-md-6 col-xl-4">
          <div className="card h-100">
            <div className="card-body">
              <p className="text-muted mb-1">Active components</p>
              <h3 className="mb-0">{activeCount}</h3>
            </div>
          </div>
        </div>
      </div>

      <div className="card mb-4">
        <div className="card-body">
          <div className="d-flex flex-wrap justify-content-between align-items-center gap-3">
            <div>
              <h5 className="mb-1">Component Configuration</h5>
              <p className="text-muted small mb-0">
                Fixed components use an amount; percentage components use a
                salary base. Variable components require a payroll-period amount.
              </p>
            </div>

            <label className="form-check d-flex align-items-center gap-2 mb-0">
              <input
                className="form-check-input"
                type="checkbox"
                checked={includeInactive}
                onChange={(event) =>
                  setIncludeInactive(event.target.checked)
                }
              />
              <span className="form-check-label">
                Show inactive components
              </span>
            </label>
          </div>
        </div>
      </div>

      {showForm && (
        <div className="card mb-4">
          <div className="card-header bg-body">
            <h5 className="mb-0">
              {editingId !== null
                ? "Edit Salary Component"
                : "Create Salary Component"}
            </h5>
          </div>

          <div className="card-body">
            <form onSubmit={handleSubmit}>
              <div className="row g-3">
                <div className="col-md-4">
                  <label htmlFor="component-code" className="form-label">
                    Component Code
                  </label>
                  <input
                    id="component-code"
                    name="code"
                    className="form-control"
                    maxLength={40}
                    value={form.code}
                    onChange={updateField}
                    disabled={editingId !== null}
                    placeholder="e.g. HRA"
                    required
                  />
                  <small className="text-muted">
                    Use a unique code, such as BASIC_PAY or HRA.
                  </small>
                </div>

                <div className="col-md-4">
                  <label htmlFor="component-name" className="form-label">
                    Component Name
                  </label>
                  <input
                    id="component-name"
                    name="name"
                    className="form-control"
                    maxLength={120}
                    value={form.name}
                    onChange={updateField}
                    required
                  />
                </div>

                <div className="col-md-4">
                  <label htmlFor="component-type" className="form-label">
                    Component Type
                  </label>
                  <select
                    id="component-type"
                    name="component_type"
                    className="form-select"
                    value={form.component_type}
                    onChange={updateField}
                  >
                    <option value="EARNING">Earning</option>
                    <option value="DEDUCTION">Deduction</option>
                  </select>
                </div>

                <div className="col-md-4">
                  <label htmlFor="calculation-type" className="form-label">
                    Calculation Type
                  </label>
                  <select
                    id="calculation-type"
                    name="calculation_type"
                    className="form-select"
                    value={form.calculation_type}
                    onChange={updateField}
                  >
                    <option value="FIXED">Fixed Amount</option>
                    <option value="PERCENTAGE">Percentage</option>
                  </select>
                </div>

                <div className="col-md-4">
                  <label htmlFor="default-amount" className="form-label">
                    {form.calculation_type === "PERCENTAGE"
                      ? "Percentage (%)"
                      : "Default Amount (₹)"}
                  </label>
                  <input
                    id="default-amount"
                    name="default_amount"
                    type="number"
                    className="form-control"
                    min="0"
                    max={
                      form.calculation_type === "PERCENTAGE"
                        ? "100"
                        : undefined
                    }
                    step="0.01"
                    value={form.default_amount}
                    onChange={updateField}
                    required
                  />
                </div>

                {form.calculation_type === "PERCENTAGE" && (
                  <div className="col-md-4">
                    <label htmlFor="percentage-base" className="form-label">
                      Percentage Base
                    </label>
                    <select
                      id="percentage-base"
                      name="percentage_base"
                      className="form-select"
                      value={form.percentage_base}
                      onChange={updateField}
                    >
                      <option value="BASE_PAY">Basic Pay</option>
                      <option value="MONTHLY_SALARY">
                        Monthly Salary
                      </option>
                    </select>
                  </div>
                )}

                <div className="col-12">
                  <label htmlFor="component-description" className="form-label">
                    Description
                  </label>
                  <textarea
                    id="component-description"
                    name="description"
                    className="form-control"
                    rows={2}
                    value={form.description}
                    onChange={updateField}
                    placeholder="Describe the component and its purpose."
                  />
                </div>

                <div className="col-md-6">
                  <label className="form-check">
                    <input
                      className="form-check-input"
                      type="checkbox"
                      name="is_variable"
                      checked={form.is_variable}
                      onChange={updateField}
                    />
                    <span className="form-check-label">
                      Variable component
                    </span>
                  </label>
                  <small className="text-muted">
                    Use for bonus, overtime or other period-based amounts.
                  </small>
                </div>

                <div className="col-md-6">
                  <label className="form-check">
                    <input
                      className="form-check-input"
                      type="checkbox"
                      name="is_taxable"
                      checked={form.is_taxable}
                      onChange={updateField}
                    />
                    <span className="form-check-label">
                      Taxable component
                    </span>
                  </label>
                </div>
              </div>

              <div className="d-flex flex-wrap gap-2 mt-4">
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={saving}
                >
                  <Save size={16} className="me-2" />
                  {saving
                    ? "Saving..."
                    : editingId !== null
                      ? "Save Changes"
                      : "Create Component"}
                </button>

                <button
                  type="button"
                  className="btn btn-outline-secondary"
                  onClick={closeForm}
                  disabled={saving}
                >
                  <X size={16} className="me-2" />
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="card">
        <div className="card-body">
          <h5 className="mb-3">Salary Component List</h5>

          {loading ? (
            <p className="text-muted mb-0">Loading components...</p>
          ) : components.length === 0 ? (
            <div className="text-center py-5">
              <CheckCircle size={32} className="text-muted mb-3" />
              <p className="mb-1">No salary components found.</p>
              <p className="text-muted small">
                Add a component to configure the salary structure.
              </p>
            </div>
          ) : (
            <div className="table-responsive">
              <table className="table table-hover align-middle">
                <thead>
                  <tr>
                    <th>Code</th>
                    <th>Name</th>
                    <th>Type</th>
                    <th>Calculation</th>
                    <th>Default</th>
                    <th>Taxable</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>

                <tbody>
                  {components.map((component) => (
                    <tr key={component.id}>
                      <td>
                        <code>{component.code}</code>
                      </td>

                      <td>
                        <div className="fw-semibold">{component.name}</div>
                        {component.description && (
                          <small className="text-muted">
                            {component.description}
                          </small>
                        )}
                      </td>

                      <td>
                        <span
                          className={
                            component.component_type === "EARNING"
                              ? "badge text-bg-success"
                              : "badge text-bg-warning"
                          }
                        >
                          {component.component_type}
                        </span>
                      </td>

                      <td>
                        {component.calculation_type === "PERCENTAGE"
                          ? `${component.default_amount}% of ${component.percentage_base}`
                          : formatCurrency(component.default_amount)}
                        {component.is_variable && (
                          <div>
                            <small className="text-muted">Variable</small>
                          </div>
                        )}
                      </td>

                      <td>
                        {component.calculation_type === "PERCENTAGE"
                          ? `${component.default_amount}%`
                          : formatCurrency(component.default_amount)}
                      </td>

                      <td>{component.is_taxable ? "Yes" : "No"}</td>

                      <td>
                        <span
                          className={
                            component.is_active
                              ? "badge text-bg-success"
                              : "badge text-bg-secondary"
                          }
                        >
                          {component.is_active ? "Active" : "Inactive"}
                        </span>
                      </td>

                      <td>
                        <div className="d-flex gap-2">
                          <button
                            type="button"
                            className="btn btn-sm btn-outline-primary"
                            onClick={() => openEditForm(component)}
                            title="Edit component"
                          >
                            <Edit2 size={15} />
                          </button>

                          {component.is_active && (
                            <button
                              type="button"
                              className="btn btn-sm btn-outline-danger"
                              onClick={() => handleDeactivate(component)}
                              title="Deactivate component"
                            >
                              <X size={15} />
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
