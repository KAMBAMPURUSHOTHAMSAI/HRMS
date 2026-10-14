
import { useEffect, useState } from "react";
import {
  CalendarCheck,
  CalendarDays,
  Clock3,
  UserRound,
} from "lucide-react";

import {
  getEmployeeDashboardProfile,
  getEmployeeDashboardAttendance,
  getEmployeeDashboardLeaveBalances,
} from "../../../api/dashboardApi";

import StatCard from "../../../components/common/StatCard";
import { useAuth } from "../../../hooks/useAuth";

export default function EmployeeDashboard() {
  const { user } = useAuth();

  const [profile, setProfile] = useState(null);
  const [attendance, setAttendance] = useState(null);
  const [balances, setBalances] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function loadDashboard() {
      const now = new Date();
      const year = now.getFullYear();
      const month = now.getMonth() + 1;

      const results = await Promise.allSettled([
        getEmployeeDashboardProfile(),

        getEmployeeDashboardAttendance({
          year,
          month,
        }),

        getEmployeeDashboardLeaveBalances({
          year,
        }),
      ]);

      if (cancelled) return;

      if (results[0].status === "fulfilled") {
        setProfile(results[0].value);
      }

      if (results[1].status === "fulfilled") {
        setAttendance(results[1].value);
      }

      if (results[2].status === "fulfilled") {
        setBalances(results[2].value);
      }

      if (results.some((result) => result.status === "rejected")) {
        setError(
          "Some dashboard information could not be loaded. " +
            "Please check the relevant employee APIs."
        );
      } else {
        setError("");
      }
    }

    loadDashboard();

    return () => {
      cancelled = true;
    };
  }, []);

  const availableLeave = balances.reduce(
    (total, balance) =>
      total + Number(balance.available_days || 0),
    0
  );

  return (
    <div className="dashboard-page">
      <div className="page-heading-row">
        <div>
          <p className="section-kicker">MY WORKSPACE</p>

          <h2>
            Welcome, {user?.first_name || "Employee"}
          </h2>

          <p>Here is an overview of your HR information.</p>
        </div>
      </div>

      {error && (
        <div className="alert alert-info" role="status">
          {error}
        </div>
      )}

      <div className="stats-grid">
        <StatCard
          label="Employee Code"
          value={profile?.employee_code || "—"}
          description="Your employee identifier"
          icon={UserRound}
        />

        <StatCard
          label="Working Hours This Month"
          value={
            attendance
              ? `${Number(
                  attendance.total_worked_hours || 0
                ).toFixed(2)} hrs`
              : "—"
          }
          description="Based on recorded check-in/out times"
          icon={Clock3}
        />

        <StatCard
          label="Attendance Days"
          value={attendance?.days_recorded ?? "—"}
          description="Days recorded in the selected month"
          icon={CalendarCheck}
        />

        <StatCard
          label="Available Leave"
          value={
            balances.length
              ? availableLeave.toFixed(2)
              : "—"
          }
          description="Combined available balance across leave types"
          icon={CalendarDays}
        />
      </div>

      <section className="content-card">
        <h3>My Employment Details</h3>

        <div className="profile-summary-grid">
          <div>
            <span>Full Name</span>
            <strong>
              {profile
                ? `${profile.first_name} ${profile.last_name}`
                : (
                    `${user?.first_name || ""} ` +
                    `${user?.last_name || ""}`
                  ).trim() || "—"}
            </strong>
          </div>

          <div>
            <span>Department</span>
            <strong>{profile?.department_name || "—"}</strong>
          </div>

          <div>
            <span>Designation</span>
            <strong>{profile?.designation_name || "—"}</strong>
          </div>

          <div>
            <span>Employment Status</span>
            <strong>{profile?.employment_status || "—"}</strong>
          </div>
        </div>
      </section>
    </div>
  );
}
