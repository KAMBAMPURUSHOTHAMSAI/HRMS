
import api from "./client";

// Admin / HR dashboard summary
export async function getAdminDashboardSummary() {
  const response = await api.get("/reports/dashboard");
  return response.data;
}

// Logged-in employee profile
export async function getEmployeeDashboardProfile() {
  const response = await api.get("/employees/me");
  return response.data;
}

// Logged-in employee attendance summary
export async function getEmployeeDashboardAttendance({ year, month }) {
  const response = await api.get("/attendance/me/summary", {
    params: { year, month },
  });

  return response.data;
}

// Logged-in employee leave balances
export async function getEmployeeDashboardLeaveBalances({ year }) {
  const response = await api.get("/leaves/me/balances", {
    params: { year },
  });

  return response.data;
}
