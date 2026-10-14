
import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Eye, RefreshCw, Wallet } from "lucide-react";
import {
  generatePayrollRun,
  getPayrollRuns,
} from "../../../api/payrollApi";

function getPreviousMonth() {
  const date = new Date();
  date.setDate(1);
  date.setMonth(date.getMonth() - 1);

  return {
    year: date.getFullYear(),
    month: date.getMonth() + 1,
  };
}

function formatCurrency(value) {
  const amount = Number(value ?? 0);

  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(Number.isFinite(amount) ? amount : 0);
}

function formatDate(value) {
  if (!value) return "—";

  return String(value).slice(0, 10);
}

function getStatusClass(status) {
  return String(status).toUpperCase() === "LOCKED"
    ? "badge bg-success"
    : "badge bg-warning text-dark";
}

export default function PayrollRuns() {
  const navigate = useNavigate();
  const previousMonth = getPreviousMonth();

  const [runs, setRuns] = useState([]);
  const [form, setForm] = useState({
    year: String(previousMonth.year),
    month: String(previousMonth.month),
  });

  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const loadRuns = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const data = await getPayrollRuns();
      setRuns(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          "Unable to retrieve payroll runs."
      );
      setRuns([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadRuns();
  }, [loadRuns]);

  async function handleGenerate(event) {
    event.preventDefault();
    setError("");
    setMessage("");

    const year = Number(form.year);
    const month = Number(form.month);

    if (!Number.isInteger(year) || year < 2000 || year > 2100) {
      setError("Enter a valid year between 2000 and 2100.");
      return;
    }

    if (!Number.isInteger(month) || month < 1 || month > 12) {
      setError("Select a valid month.");
      return;
    }

    setGenerating(true);

    try {
      const run = await generatePayrollRun({ year, month });

      setMessage(
        `Payroll run for ${year}-${String(month).padStart(2, "0")} was generated.`
      );

      await loadRuns();

      if (run?.id) {
        navigate(`/admin/payroll/${run.id}`);
      }
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          "Unable to generate payroll. Please review the selected period."
      );
    } finally {
      setGenerating(false);
    }
  }

  function getPeriodName(year, month) {
    if (!year || !month) return "—";

    return new Date(Number(year), Number(month) - 1, 1)
      .toLocaleDateString("en-IN", {
        month: "long",
        year: "numeric",
      });
  }

  return (
    <section className="container-fluid py-3">
      <div className="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
        <div>
          <h2 className="mb-1">Payroll Management</h2>
          <p className="text-muted mb-0">
            Generate payroll and review salary calculations.
          </p>
        </div>

        <button
          type="button"
          className="btn btn-outline-primary"
          onClick={loadRuns}
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
          <h5 className="mb-3">
            <Wallet size={20} className="me-2" />
            Generate Monthly Payroll
          </h5>

          <form className="row g-3" onSubmit={handleGenerate}>
            <div className="col-md-4">
              <label className="form-label">Payroll Year</label>
              <input
                type="number"
                className="form-control"
                min="2000"
                max="2100"
                value={form.year}
                onChange={(event) =>
                  setForm({ ...form, year: event.target.value })
                }
                required
              />
            </div>

            <div className="col-md-4">
              <label className="form-label">Payroll Month</label>
              <select
                className="form-select"
                value={form.month}
                onChange={(event) =>
                  setForm({ ...form, month: event.target.value })
                }
                required
              >
                {Array.from({ length: 12 }, (_, index) => {
                  const month = index + 1;

                  return (
                    <option key={month} value={month}>
                      {new Date(2000, index, 1).toLocaleDateString(
                        "en-IN",
                        { month: "long" }
                      )}
                    </option>
                  );
                })}
              </select>
            </div>

            <div className="col-md-4 d-flex align-items-end">
              <button
                type="submit"
                className="btn btn-primary w-100"
                disabled={generating}
              >
                {generating ? "Generating..." : "Generate Payroll"}
              </button>
            </div>
          </form>

          <p className="text-muted small mt-3 mb-0">
            Payroll generation depends on employee data, attendance,
            approved paid leave and the backend payroll rules.
          </p>
        </div>
      </div>

      <div className="card">
        <div className="card-body">
          <h5 className="mb-3">Payroll Run History</h5>

          {loading ? (
            <p>Loading payroll runs...</p>
          ) : runs.length === 0 ? (
            <p className="text-muted mb-0">
              No payroll runs are available yet.
            </p>
          ) : (
            <div className="table-responsive">
              <table className="table table-hover align-middle">
                <thead>
                  <tr>
                    <th>Run ID</th>
                    <th>Period</th>
                    <th>Employees</th>
                    <th>Gross Salary</th>
                    <th>LOP Deduction</th>
                    <th>Total Deductions</th>
                    <th>Net Salary</th>
                    <th>Status</th>
                    <th>Generated</th>
                    <th>Details</th>
                  </tr>
                </thead>

                <tbody>
                  {runs.map((run) => (
                    <tr key={run.id}>
                      <td>{run.id}</td>
                      <td>{getPeriodName(run.year, run.month)}</td>
                      <td>{run.record_count ?? 0}</td>
                      <td>{formatCurrency(run.total_gross_salary)}</td>
                      <td>{formatCurrency(run.total_lop_deduction)}</td>
                      <td>{formatCurrency(run.total_deductions)}</td>
                      <td className="fw-semibold">
                        {formatCurrency(run.total_net_salary)}
                      </td>
                      <td>
                        <span className={getStatusClass(run.status)}>
                          {run.status}
                        </span>
                      </td>
                      <td>{formatDate(run.generated_at)}</td>
                      <td>
                        <Link
                          to={`/admin/payroll/${run.id}`}
                          className="btn btn-sm btn-outline-primary"
                        >
                          <Eye size={15} className="me-1" />
                          View
                        </Link>
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
