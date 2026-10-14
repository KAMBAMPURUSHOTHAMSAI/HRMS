
import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Save } from "lucide-react";

import { getUser, updateUser } from "../../../api/userApi";

function getErrorMessage(error, fallback) {
  const detail = error?.response?.data?.detail;

  if (typeof detail === "string") return detail;

  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg || "Invalid input").join(", ");
  }

  return fallback;
}

export default function UserForm() {
  const { userId } = useParams();
  const navigate = useNavigate();

  const id = Number(userId);

  const [account, setAccount] = useState(null);
  const [form, setForm] = useState({
    first_name: "",
    last_name: "",
  });

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const loadUser = useCallback(async () => {
    if (!Number.isInteger(id) || id <= 0) {
      setError("Invalid user ID.");
      setLoading(false);
      return;
    }

    setLoading(true);
    setError("");

    try {
      const data = await getUser(id);

      setAccount(data);
      setForm({
        first_name: data.first_name || "",
        last_name: data.last_name || "",
      });
    } catch (err) {
      setAccount(null);
      setError(getErrorMessage(err, "Unable to load user details."));
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadUser();
  }, [loadUser]);

  async function handleSubmit(event) {
    event.preventDefault();

    setError("");
    setMessage("");

    const firstName = form.first_name.trim();
    const lastName = form.last_name.trim();

    if (!firstName || !lastName) {
      setError("First name and last name are required.");
      return;
    }

    setSaving(true);

    try {
      const updated = await updateUser(id, {
        first_name: firstName,
        last_name: lastName,
      });

      setAccount(updated);
      setForm({
        first_name: updated.first_name || firstName,
        last_name: updated.last_name || lastName,
      });

      setMessage("User details updated successfully.");
    } catch (err) {
      setError(
        getErrorMessage(err, "Unable to update user details.")
      );
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <section className="container-fluid py-3">
        <p>Loading user details...</p>
      </section>
    );
  }

  if (!account) {
    return (
      <section className="container-fluid py-3">
        <div className="alert alert-danger">
          {error || "User account not found."}
        </div>

        <Link
          to="/admin/users"
          className="btn btn-outline-primary"
        >
          Back to Users
        </Link>
      </section>
    );
  }

  return (
    <section className="container-fluid py-3">
      <div className="mb-4">
        <Link
          to="/admin/users"
          className="text-decoration-none d-inline-block mb-2"
        >
          <ArrowLeft size={16} className="me-1" />
          Back to Users
        </Link>

        <h2 className="mb-1">Edit User</h2>
        <p className="text-muted mb-0">
          Update the basic information for account #{account.id}.
        </p>
      </div>

      {error && (
        <div className="alert alert-danger">{error}</div>
      )}

      {message && (
        <div className="alert alert-success">{message}</div>
      )}

      <div className="row g-4">
        <div className="col-lg-8">
          <div className="card">
            <div className="card-body">
              <h5 className="mb-4">Basic Information</h5>

              <form className="row g-3" onSubmit={handleSubmit}>
                <div className="col-md-6">
                  <label className="form-label">First Name *</label>
                  <input
                    type="text"
                    className="form-control"
                    value={form.first_name}
                    minLength={1}
                    maxLength={100}
                    onChange={(event) =>
                      setForm({
                        ...form,
                        first_name: event.target.value,
                      })
                    }
                    required
                  />
                </div>

                <div className="col-md-6">
                  <label className="form-label">Last Name *</label>
                  <input
                    type="text"
                    className="form-control"
                    value={form.last_name}
                    minLength={1}
                    maxLength={100}
                    onChange={(event) =>
                      setForm({
                        ...form,
                        last_name: event.target.value,
                      })
                    }
                    required
                  />
                </div>

                <div className="col-12">
                  <label className="form-label">Email</label>
                  <input
                    type="email"
                    className="form-control"
                    value={account.email || ""}
                    readOnly
                  />
                  <small className="text-muted">
                    Email is read-only in this form.
                  </small>
                </div>

                <div className="col-12 d-flex flex-wrap gap-2">
                  <button
                    type="submit"
                    className="btn btn-primary"
                    disabled={saving}
                  >
                    <Save size={16} className="me-2" />
                    {saving ? "Saving..." : "Save Changes"}
                  </button>

                  <Link
                    to="/admin/users"
                    className="btn btn-outline-secondary"
                  >
                    Back to List
                  </Link>
                </div>
              </form>
            </div>
          </div>
        </div>

        <div className="col-lg-4">
          <div className="card mb-3">
            <div className="card-body">
              <h5 className="mb-3">Account Details</h5>

              <p className="mb-1 text-muted">User ID</p>
              <p className="fw-semibold">{account.id}</p>

              <p className="mb-1 text-muted">Status</p>
              <p>
                <span
                  className={
                    account.is_active
                      ? "badge bg-success"
                      : "badge bg-secondary"
                  }
                >
                  {account.is_active ? "Active" : "Inactive"}
                </span>
              </p>

              <p className="mb-1 text-muted">Employee Code</p>
              <p className="fw-semibold">
                {account.employee_code || "Not linked to an employee"}
              </p>

              <p className="mb-1 text-muted">Assigned Roles</p>

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
            </div>
          </div>

          <div className="card">
            <div className="card-body">
              <h6>Access Management</h6>
              <p className="text-muted small mb-0">
                Account activation and deactivation are controlled by Admin.
                Role assignments are managed separately in Roles & Permissions.
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
