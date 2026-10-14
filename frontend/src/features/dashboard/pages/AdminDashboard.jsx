
import { useCallback, useEffect, useState } from "react";
import {
  Users,
  CalendarCheck,
  CalendarClock,
  Wallet,
  RefreshCw,
} from "lucide-react";

import { getAdminDashboardSummary } from "../../../api/dashboardApi";
import StatCard from "../../../components/common/StatCard";

function formatCurrency(value) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(Number(value || 0));
}

export default function AdminDashboard() {
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const data = await getAdminDashboardSummary();
      setSummary(data);
    } catch (err) {
      console.error("Admin dashboard error:", err);
      setError("Dashboard summary could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  return (
    <div className="dashboard-page">
      <div className="page-heading-row">
        <div>
          <p className="section-kicker">OVERVIEW</p>
          <h2>Admin Dashboard</h2>
          <p>Monitor your workforce and HR operations.</p>
        </div>

        <button
          className="secondary-button"
          type="button"
          onClick={loadDashboard}
          disabled={loading}
        >
          <RefreshCw size={17} />
          Refresh
        </button>
      </div>

      {error && (
        <div className="alert alert-warning" role="alert">
          {error}
        </div>
      )}

      {loading ? (
        <div className="page-loading">
          Loading dashboard...
        </div>
      ) : (
        <div className="stats-grid">
          <StatCard
            label="Active Employees"
            value={summary?.active_employees ?? 0}
            description="Currently active employee records"
            icon={Users}
          />

          <StatCard
            label="Today's Attendance"
            value={summary?.today_attendance_records ?? 0}
            description="Attendance records recorded today"
            icon={CalendarCheck}
          />

          <StatCard
            label="Pending Leave Requests"
            value={summary?.pending_leave_requests ?? 0}
            description="Applications waiting for a decision"
            icon={CalendarClock}
          />

          <StatCard
            label="Current Month Payroll"
            value={formatCurrency(summary?.current_month_net_payroll)}
            description="Net salary across current-month payroll records"
            icon={Wallet}
          />
        </div>
      )}

      <section className="content-card dashboard-note">
        <h3>HR Operations</h3>
        <p>
          Use the navigation menu to manage employees, departments,
          attendance, leave, payroll, reports and audit history.
        </p>
      </section>
    </div>
  );
}
