
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { CalendarDays, Send } from "lucide-react";
import {
  applyForLeave,
  getLeaveTypes,
  getMyLeaveBalances,
} from "../../../api/leaveApi";

function getArray(data) {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.items)) return data.items;
  if (Array.isArray(data?.balances)) return data.balances;
  if (Array.isArray(data?.data)) return data.data;
  return [];
}

function getToday() {
  const date = new Date();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");

  return `${date.getFullYear()}-${month}-${day}`;
}

export default function ApplyLeave() {
  const navigate = useNavigate();
  const today = getToday();

  const [leaveTypes, setLeaveTypes] = useState([]);
  const [balances, setBalances] = useState([]);

  const [form, setForm] = useState({
    leave_type_id: "",
    start_date: "",
    end_date: "",
    reason: "",
  });

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    let active = true;

    async function loadFormData() {
      setLoading(true);
      setError("");

      const [typesResult, balancesResult] = await Promise.allSettled([
        getLeaveTypes(),
        getMyLeaveBalances({ year: Number(today.slice(0, 4)) }),
      ]);

      if (!active) return;

      if (typesResult.status === "fulfilled") {
        setLeaveTypes(
          getArray(typesResult.value).filter(
            (type) => type.is_active !== false
          )
        );
      } else {
        setError(
          typesResult.reason?.response?.data?.detail ||
            "Unable to load leave types."
        );
      }

      if (balancesResult.status === "fulfilled") {
        setBalances(getArray(balancesResult.value));
      }

      setLoading(false);
    }

    loadFormData();

    return () => {
      active = false;
    };
  }, [today]);

  function updateField(event) {
    const { name, value } = event.target;

    setForm((current) => ({
      ...current,
      [name]: value,
      ...(name === "start_date" &&
      current.end_date &&
      current.end_date < value
        ? { end_date: value }
        : {}),
    }));
  }

  const selectedType = leaveTypes.find(
    (type) => String(type.id) === form.leave_type_id
  );

  const selectedBalance = balances.find(
    (balance) =>
      String(balance.leave_type_id) === form.leave_type_id
  );

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setMessage("");

    if (!form.leave_type_id) {
      setError("Please select a leave type.");
      return;
    }

    if (!form.start_date || !form.end_date) {
      setError("Please select both leave dates.");
      return;
    }

    if (form.start_date < today) {
      setError("Leave start date cannot be in the past.");
      return;
    }

    if (form.end_date < form.start_date) {
      setError("End date cannot be before start date.");
      return;
    }

    if (form.reason.trim().length < 5) {
      setError("Please provide a reason with at least 5 characters.");
      return;
    }

    setSubmitting(true);

    try {
      await applyForLeave({
        leave_type_id: Number(form.leave_type_id),
        start_date: form.start_date,
        end_date: form.end_date,
        reason: form.reason.trim(),
      });

      setMessage("Leave request submitted successfully.");
      setForm({
        leave_type_id: "",
        start_date: "",
        end_date: "",
        reason: "",
      });

      const updatedBalances = await getMyLeaveBalances({
        year: Number(today.slice(0, 4)),
      }).catch(() => null);

      if (updatedBalances) {
        setBalances(getArray(updatedBalances));
      }
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          "Unable to submit the leave request."
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="container-fluid py-3">
      <div className="mb-4">
        <h2 className="mb-1">Apply for Leave</h2>
        <p className="text-muted mb-0">
          Submit a leave request for approval.
        </p>
      </div>

      {error && <div className="alert alert-danger">{error}</div>}

      {message && (
        <div className="alert alert-success">
          {message}
          <button
            type="button"
            className="btn btn-sm btn-outline-success ms-3"
            onClick={() => navigate("/employee/leaves")}
          >
            View My Leaves
          </button>
        </div>
      )}

      {loading ? (
        <p>Loading leave information...</p>
      ) : (
        <div className="row g-4">
          <div className="col-lg-8">
            <div className="card">
              <div className="card-body">
                <h5 className="mb-4">
                  <CalendarDays size={20} className="me-2" />
                  Leave Application
                </h5>

                <form className="row g-3" onSubmit={handleSubmit}>
                  <div className="col-12">
                    <label className="form-label">Leave Type *</label>
                    <select
                      name="leave_type_id"
                      className="form-select"
                      value={form.leave_type_id}
                      onChange={updateField}
                      required
                    >
                      <option value="">Select leave type</option>
                      {leaveTypes.map((type) => (
                        <option key={type.id} value={type.id}>
                          {type.name} ({type.code})
                        </option>
                      ))}
                    </select>

                    {leaveTypes.length === 0 && (
                      <small className="text-muted">
                        No active leave types are available.
                      </small>
                    )}
                  </div>

                  <div className="col-md-6">
                    <label className="form-label">Start Date *</label>
                    <input
                      type="date"
                      name="start_date"
                      className="form-control"
                      value={form.start_date}
                      min={today}
                      onChange={updateField}
                      required
                    />
                  </div>

                  <div className="col-md-6">
                    <label className="form-label">End Date *</label>
                    <input
                      type="date"
                      name="end_date"
                      className="form-control"
                      value={form.end_date}
                      min={form.start_date || today}
                      onChange={updateField}
                      required
                    />
                  </div>

                  <div className="col-12">
                    <label className="form-label">Reason *</label>
                    <textarea
                      name="reason"
                      className="form-control"
                      rows={4}
                      minLength={5}
                      maxLength={1000}
                      placeholder="Explain why you need leave..."
                      value={form.reason}
                      onChange={updateField}
                      required
                    />
                    <small className="text-muted">
                      Minimum 5 characters; maximum 1000.
                    </small>
                  </div>

                  <div className="col-12 d-flex flex-wrap gap-2">
                    <button
                      type="submit"
                      className="btn btn-primary"
                      disabled={
                        submitting ||
                        leaveTypes.length === 0
                      }
                    >
                      <Send size={16} className="me-2" />
                      {submitting
                        ? "Submitting..."
                        : "Submit Leave Request"}
                    </button>

                    <button
                      type="button"
                      className="btn btn-outline-secondary"
                      onClick={() => navigate("/employee/leaves")}
                    >
                      My Leave History
                    </button>
                  </div>
                </form>
              </div>
            </div>
          </div>

          <div className="col-lg-4">
            <div className="card">
              <div className="card-body">
                <h5 className="mb-3">Selected Leave Balance</h5>

                {!selectedType ? (
                  <p className="text-muted mb-0">
                    Select a leave type to view its balance.
                  </p>
                ) : !selectedBalance ? (
                  <div>
                    <p className="mb-1">{selectedType.name}</p>
                    <p className="text-muted mb-0">
                      Balance information is unavailable.
                    </p>
                  </div>
                ) : (
                  <>
                    <p className="text-muted mb-1">
                      {selectedType.name}
                    </p>
                    <h3>
                      {selectedBalance.remaining_days ??
                        (
                          Number(selectedBalance.entitled_days ?? 0) -
                          Number(selectedBalance.used_days ?? 0)
                        ).toFixed(1)}
                    </h3>
                    <p className="text-muted mb-0">
                      Remaining days
                    </p>
                    <hr />
                    <p className="mb-1">
                      Entitled: {selectedBalance.entitled_days ?? "—"}
                    </p>
                    <p className="mb-0">
                      Used: {selectedBalance.used_days ?? "—"}
                    </p>
                  </>
                )}
              </div>
            </div>

            <div className="card mt-3">
              <div className="card-body">
                <h6>Before you submit</h6>
                <p className="text-muted small mb-0">
                  Your request may need approval from HR or an
                  administrator. The backend validates the leave dates,
                  overlap rules and paid-leave balance.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
