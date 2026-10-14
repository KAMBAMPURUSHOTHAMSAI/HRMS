import { useEffect, useState } from "react";
import { ArrowRight, LockKeyhole, Mail } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../../../hooks/useAuth";

export default function Login() {
  const { login, user, loading } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (loading || !user) return;

    const target = user.roles?.includes("EMPLOYEE")
      ? "/employee/dashboard"
      : "/admin/dashboard";

    navigate(target, { replace: true });
  }, [user, loading, navigate]);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setSubmitting(true);

    try {
      const authenticatedUser = await login(email.trim(), password);

      const target = authenticatedUser.roles?.includes("EMPLOYEE")
        ? "/employee/dashboard"
        : "/admin/dashboard";

      navigate(target, { replace: true });
    } catch (err) {
      const statusCode = err.response?.status;

      if (statusCode === 401) {
        setError("Incorrect email or password.");
      } else if (statusCode === 403) {
        setError("This account is inactive or access is denied.");
      } else {
        setError(
          "Unable to sign in. Check that the HRMS API is running."
        );
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="login-card">
      <div className="login-heading">
        <span className="login-kicker">WELCOME BACK</span>
        <h2>Sign in to HRMS</h2>
        <p>Enter your account credentials to continue.</p>
      </div>

      {error && (
        <div className="alert alert-danger" role="alert">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <label className="form-label" htmlFor="email">
          Email address
        </label>

        <div className="input-with-icon">
          <Mail size={19} />
          <input
            id="email"
            type="email"
            autoComplete="username"
            placeholder="you@example.com"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
        </div>

        <label className="form-label mt-4" htmlFor="password">
          Password
        </label>

        <div className="input-with-icon">
          <LockKeyhole size={19} />
          <input
            id="password"
            type="password"
            autoComplete="current-password"
            placeholder="Enter your password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </div>

        <button
          className="login-submit"
          type="submit"
          disabled={submitting}
        >
          {submitting ? "Signing in..." : "Sign in"}
          {!submitting && <ArrowRight size={18} />}
        </button>
      </form>

      <p className="login-security">
        Protected access for authorized HRMS users.
      </p>
    </div>
  );
}