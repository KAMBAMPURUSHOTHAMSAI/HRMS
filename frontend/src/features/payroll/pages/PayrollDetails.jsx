
import { Fragment, useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, RefreshCw } from "lucide-react";

import {
  createPayrollAdjustment,
  getPayrollRun,
  getPayrollRunRecords,
  getPayrollComponentLines,
  lockPayrollRun,
  simulateSalaryCredit,
} from "../../../api/payrollApi";

import { generateSalarySlips } from "../../../api/salarySlipApi";
import { useAuth } from "../../../hooks/useAuth";

function formatCurrency(value) {
  const amount = Number(value ?? 0);

  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(Number.isFinite(amount) ? amount : 0);
}

function formatDate(value) {
  return value ? String(value).slice(0, 10) : "—";
}

function getRecords(data) {
  return Array.isArray(data) ? data : [];
}

export default function PayrollDetails() {
  const { runId } = useParams();
  const id = Number(runId);
  const { user } = useAuth();

  const isAdmin = user?.roles?.includes("ADMIN") ?? false;

  const [run, setRun] = useState(null);
  const [records, setRecords] = useState([]);

  const [expandedRecordId, setExpandedRecordId] = useState(null);
  const [componentLinesByRecordId, setComponentLinesByRecordId] = useState({});
  const [breakdownLoadingId, setBreakdownLoadingId] = useState(null);
  const [breakdownErrors, setBreakdownErrors] = useState({});

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const [adjustment, setAdjustment] = useState({
    employee_id: "",
    adjustment_type: "EARNING",
    amount: "",
    description: "",
  });

  const loadPayroll = useCallback(async () => {
    if (!Number.isInteger(id) || id <= 0) {
      setError("Invalid payroll run ID.");
      setLoading(false);
      return;
    }

    setLoading(true);
    setError("");

    try {
      const [runData, recordsData] = await Promise.all([
        getPayrollRun(id),
        getPayrollRunRecords(id),
      ]);

      setRun(runData);
      setRecords(getRecords(recordsData));
      // Refresh the breakdown cache when payroll records are reloaded.
      setComponentLinesByRecordId({});
      setBreakdownErrors({});
      setExpandedRecordId(null);
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          "Unable to load payroll details."
      );

      setRun(null);
      setRecords([]);
      setComponentLinesByRecordId({});
      setBreakdownErrors({});
      setExpandedRecordId(null);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadPayroll();
  }, [loadPayroll]);

  const isLocked =
    String(run?.status || "").toUpperCase() === "LOCKED";

  async function handleAdjustment(event) {
    event.preventDefault();
    setError("");
    setMessage("");

    if (!isAdmin) {
      setError("Only an Admin can add payroll adjustments.");
      return;
    }

    if (isLocked) {
      setError("A locked payroll run cannot receive new adjustments.");
      return;
    }

    const amount = Number(adjustment.amount);

    if (!adjustment.employee_id) {
      setError("Please select an employee.");
      return;
    }

    if (!Number.isFinite(amount) || amount <= 0) {
      setError("Adjustment amount must be greater than zero.");
      return;
    }

    if (adjustment.description.trim().length < 3) {
      setError("Please enter a description of at least 3 characters.");
      return;
    }

    setSaving(true);

    try {
      await createPayrollAdjustment(id, {
        employee_id: Number(adjustment.employee_id),
        adjustment_type: adjustment.adjustment_type,
        amount: amount.toFixed(2),
        description: adjustment.description.trim(),
      });

      setMessage("Payroll adjustment added successfully.");

      setAdjustment({
        employee_id: "",
        adjustment_type: "EARNING",
        amount: "",
        description: "",
      });

      await loadPayroll();
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          "Unable to add the payroll adjustment."
      );
    } finally {
      setSaving(false);
    }
  }

  async function handleLock() {
    if (!isAdmin) {
      setError("Only an Admin can lock payroll.");
      return;
    }

    setSaving(true);
    setError("");
    setMessage("");

    try {
      await lockPayrollRun(id);

      setMessage("Payroll run locked successfully.");

      await loadPayroll();
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          "Unable to lock this payroll run."
      );
    } finally {
      setSaving(false);
    }
  }

  async function handleSimulateCredit() {
    if (!isAdmin) {
      setError("Only an Admin can simulate salary credit.");
      return;
    }

    setSaving(true);
    setError("");
    setMessage("");

    try {
      await simulateSalaryCredit(id);

      setMessage("Salary credit simulation completed.");

      await loadPayroll();
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          "Unable to simulate salary credit."
      );
    } finally {
      setSaving(false);
    }
  }

  async function handleGenerateSalarySlips() {
    if (!isLocked) {
      setError("Lock the payroll run before generating salary slips.");
      return;
    }

    setSaving(true);
    setError("");
    setMessage("");

    try {
      const result = await generateSalarySlips(id);

      const count = Array.isArray(result) ? result.length : 0;

      setMessage(
        `${count} salary slip(s) returned by the generation service.`
      );
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          "Unable to generate salary slips."
      );
    } finally {
      setSaving(false);
    }
  }



  async function toggleComponentBreakdown(recordId) {
    if (expandedRecordId === recordId) {
      setExpandedRecordId(null);
      return;
    }

    setExpandedRecordId(recordId);

    if (Object.prototype.hasOwnProperty.call(componentLinesByRecordId, recordId)) {
      return;
    }

    setBreakdownLoadingId(recordId);
    setBreakdownErrors((previous) => ({
      ...previous,
      [recordId]: "",
    }));

    try {
      const result = await getPayrollComponentLines(recordId);
      setComponentLinesByRecordId((previous) => ({
        ...previous,
        [recordId]: Array.isArray(result) ? result : [],
      }));
    } catch (err) {
      setBreakdownErrors((previous) => ({
        ...previous,
        [recordId]:
          err.response?.data?.detail ||
          "Unable to load salary component breakdown.",
      }));
    } finally {
      setBreakdownLoadingId(null);
    }
  }

  if (loading) {
    return (
      <section className="container-fluid py-3">
        <p>Loading payroll details...</p>
      </section>
    );
  }

  if (!run) {
    return (
      <section className="container-fluid py-3">
        <div className="alert alert-danger">
          {error || "Payroll run not found."}
        </div>

        <Link
          to="/admin/payroll"
          className="btn btn-outline-primary"
        >
          Back to Payroll Runs
        </Link>
      </section>
    );
  }

  const period = new Date(
    Number(run.year),
    Number(run.month) - 1,
    1
  ).toLocaleDateString("en-IN", {
    month: "long",
    year: "numeric",
  });

  return (
    <section className="container-fluid py-3">
      <div className="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
        <div>
          <Link
            to="/admin/payroll"
            className="text-decoration-none d-inline-block mb-2"
          >
            <ArrowLeft size={16} className="me-1" />
            Back to Payroll Runs
          </Link>

          <h2 className="mb-1">Payroll Run #{run.id}</h2>

          <p className="text-muted mb-0">
            Pay period: {period}
          </p>
        </div>

        <div className="d-flex align-items-center flex-wrap gap-2">
          <span
            className={
              isLocked
                ? "badge bg-success"
                : "badge bg-warning text-dark"
            }
          >
            {run.status}
          </span>

          <button
            type="button"
            className="btn btn-outline-primary"
            onClick={loadPayroll}
            disabled={loading || saving}
          >
            <RefreshCw size={16} className="me-2" />
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="alert alert-danger">{error}</div>
      )}

      {message && (
        <div className="alert alert-success">{message}</div>
      )}

      <div className="row g-3 mb-4">
        <div className="col-sm-6 col-xl-3">
          <div className="card h-100">
            <div className="card-body">
              <p className="text-muted mb-1">Employees</p>
              <h4>{run.record_count ?? records.length}</h4>
            </div>
          </div>
        </div>

        <div className="col-sm-6 col-xl-3">
          <div className="card h-100">
            <div className="card-body">
              <p className="text-muted mb-1">Gross Salary</p>
              <h4>{formatCurrency(run.total_gross_salary)}</h4>
            </div>
          </div>
        </div>

        <div className="col-sm-6 col-xl-3">
          <div className="card h-100">
            <div className="card-body">
              <p className="text-muted mb-1">Total Deductions</p>
              <h4>{formatCurrency(run.total_deductions)}</h4>
            </div>
          </div>
        </div>

        <div className="col-sm-6 col-xl-3">
          <div className="card h-100">
            <div className="card-body">
              <p className="text-muted mb-1">Net Payroll</p>
              <h4>{formatCurrency(run.total_net_salary)}</h4>
            </div>
          </div>
        </div>
      </div>

      <div className="card mb-4">
        <div className="card-body">
          <h5 className="mb-3">Payroll Employees</h5>

          {records.length === 0 ? (
            <p className="text-muted mb-0">
              No payroll records are available for this run.
            </p>
          ) : (
            <div className="table-responsive">
              <table className="table table-hover align-middle">
                <thead>
                  <tr>
                    <th>Employee Code</th>
                    <th>Employee</th>
                    <th>Monthly Salary</th>
                    <th>Eligible Days</th>
                    <th>Present Days</th>
                    <th>Paid Leave</th>
                    <th>Payable Days</th>
                    <th>LOP Days</th>
                    <th>LOP Deduction</th>
                    <th>Other Earnings</th>
                    <th>Other Deductions</th>
                    <th>Gross Salary</th>
                    <th>Net Salary</th>
                    <th>Credit Status</th>
                    <th>Component Breakdown</th>
                  </tr>
                </thead>

                <tbody>
                  {records.map((record) => (
                    <Fragment key={record.id}>
                      <tr>
                        <td>{record.employee_code}</td>

                        <td>
                          <div className="fw-semibold">
                            {record.employee_name}
                          </div>

                          <small className="text-muted">
                            {record.employee_email}
                          </small>
                        </td>

                        <td>{formatCurrency(record.monthly_salary)}</td>
                        <td>{record.eligible_working_days}</td>
                        <td>{record.present_days}</td>
                        <td>{record.paid_leave_days}</td>
                        <td>{record.payable_days}</td>
                        <td>{record.lop_days}</td>
                        <td>{formatCurrency(record.lop_deduction)}</td>
                        <td>{formatCurrency(record.other_earnings)}</td>
                        <td>{formatCurrency(record.other_deductions)}</td>
                        <td>{formatCurrency(record.gross_salary)}</td>

                        <td className="fw-semibold">
                          {formatCurrency(record.net_salary)}
                        </td>

                        <td>{record.credit_status}</td>

                        <td>
                          <button
                            type="button"
                            className="btn btn-sm btn-outline-primary"
                            onClick={() => toggleComponentBreakdown(record.id)}
                            disabled={breakdownLoadingId === record.id}
                          >
                            {breakdownLoadingId === record.id
                              ? "Loading..."
                              : expandedRecordId === record.id
                                ? "Hide Breakdown"
                                : "View Breakdown"}
                          </button>
                        </td>
                      </tr>

                      {expandedRecordId === record.id && (
                        <tr>
                          <td colSpan={15}>
                            <div className="p-3 bg-body-tertiary rounded">
                              <h6 className="mb-3">
                                Salary Component Breakdown — {record.employee_name}
                              </h6>

                              {breakdownErrors[record.id] && (
                                <div className="alert alert-danger mb-2">
                                  {breakdownErrors[record.id]}
                                </div>
                              )}

                              {breakdownLoadingId === record.id ? (
                                <p className="mb-0">Loading component details...</p>
                              ) : breakdownErrors[record.id] ? null : (
                                (componentLinesByRecordId[record.id] || []).length === 0 ? (
                                  <p className="text-muted mb-0">
                                    No component breakdown is available for this payroll record.
                                  </p>
                                ) : (
                                  <div className="table-responsive">
                                    <table className="table table-sm table-hover align-middle mb-0">
                                      <thead>
                                        <tr>
                                          <th>Code</th>
                                          <th>Component</th>
                                          <th>Type</th>
                                          <th>Amount</th>
                                          <th>Taxable</th>
                                          <th>Calculation Details</th>
                                        </tr>
                                      </thead>
                                      <tbody>
                                        {(componentLinesByRecordId[record.id] || []).map((line) => (
                                          <tr key={line.id}>
                                            <td><code>{line.component_code}</code></td>
                                            <td>{line.component_name}</td>
                                            <td>{line.component_type}</td>
                                            <td>{formatCurrency(line.amount)}</td>
                                            <td>{line.is_taxable ? "Yes" : "No"}</td>
                                            <td>{line.calculation_details || "—"}</td>
                                          </tr>
                                        ))}
                                      </tbody>
                                    </table>
                                  </div>
                                )
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {!isLocked && isAdmin && (
        <div className="card mb-4">
          <div className="card-body">
            <h5 className="mb-3">Add Payroll Adjustment</h5>

            <p className="text-muted small">
              Earnings increase salary; deductions reduce salary.
              The backend recalculates payroll totals.
            </p>

            <form
              className="row g-3"
              onSubmit={handleAdjustment}
            >
              <div className="col-md-3">
                <label className="form-label">Employee *</label>

                <select
                  className="form-select"
                  value={adjustment.employee_id}
                  onChange={(event) =>
                    setAdjustment({
                      ...adjustment,
                      employee_id: event.target.value,
                    })
                  }
                  required
                >
                  <option value="">Select employee</option>

                  {records.map((record) => (
                    <option
                      key={record.employee_id}
                      value={record.employee_id}
                    >
                      {record.employee_code} - {record.employee_name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="col-md-2">
                <label className="form-label">Type *</label>

                <select
                  className="form-select"
                  value={adjustment.adjustment_type}
                  onChange={(event) =>
                    setAdjustment({
                      ...adjustment,
                      adjustment_type: event.target.value,
                    })
                  }
                >
                  <option value="EARNING">Earning</option>
                  <option value="DEDUCTION">Deduction</option>
                </select>
              </div>

              <div className="col-md-2">
                <label className="form-label">Amount (₹) *</label>

                <input
                  type="number"
                  className="form-control"
                  min="0.01"
                  step="0.01"
                  value={adjustment.amount}
                  onChange={(event) =>
                    setAdjustment({
                      ...adjustment,
                      amount: event.target.value,
                    })
                  }
                  required
                />
              </div>

              <div className="col-md-5">
                <label className="form-label">Description *</label>

                <input
                  type="text"
                  className="form-control"
                  minLength={3}
                  maxLength={1000}
                  value={adjustment.description}
                  onChange={(event) =>
                    setAdjustment({
                      ...adjustment,
                      description: event.target.value,
                    })
                  }
                  placeholder="For example: Performance bonus"
                  required
                />
              </div>

              <div className="col-12">
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={saving || records.length === 0}
                >
                  {saving ? "Saving..." : "Add Adjustment"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="card">
        <div className="card-body">
          <h5 className="mb-3">Payroll Actions</h5>

          <p className="text-muted">
            Generated: {formatDate(run.generated_at)}
            {" | "}
            Locked: {formatDate(run.locked_at)}
          </p>

          <div className="d-flex flex-wrap gap-2">
            {!isLocked && isAdmin && (
              <button
                type="button"
                className="btn btn-warning"
                onClick={handleLock}
                disabled={saving}
              >
                {saving ? "Processing..." : "Lock Payroll"}
              </button>
            )}

            {isLocked && isAdmin && (
              <button
                type="button"
                className="btn btn-success"
                onClick={handleSimulateCredit}
                disabled={
                  saving ||
                  records.length === 0 ||
                  records.every(
                    (record) =>
                      String(record.credit_status).toUpperCase() ===
                      "SIMULATED"
                  )
                }
              >
                {saving ? "Processing..." : "Simulate Salary Credit"}
              </button>
            )}

            {isLocked && (
              <>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={handleGenerateSalarySlips}
                  disabled={saving || records.length === 0}
                >
                  {saving
                    ? "Processing..."
                    : "Generate Salary Slips"}
                </button>

                <Link
                  to="/admin/salary-slips"
                  className="btn btn-outline-primary"
                >
                  View Salary Slips
                </Link>
              </>
            )}
          </div>

          <p className="text-muted small mt-3 mb-0">
            Salary credit is a simulation, not an actual bank transfer.
            A payroll run must be locked before salary slips can be
            generated. Only an Admin can adjust, lock or simulate credit.
          </p>
        </div>
      </div>
    </section>
  );
}
