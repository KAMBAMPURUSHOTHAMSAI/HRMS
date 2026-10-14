
import api from "./client";

export async function getDashboardSummary() {
  const response = await api.get("/reports/dashboard");
  return response.data;
}

export async function getAttendanceReport(params = {}) {
  const response = await api.get("/reports/attendance", { params });
  return response.data;
}

export async function exportAttendanceReport(params = {}, format = "csv") {
  return api.get("/reports/attendance/export", {
    params: { ...params, file_format: format },
    responseType: "blob",
  });
}

export async function getLeaveReport(params = {}) {
  const response = await api.get("/reports/leaves", { params });
  return response.data;
}

export async function exportLeaveReport(params = {}, format = "csv") {
  return api.get("/reports/leaves/export", {
    params: { ...params, file_format: format },
    responseType: "blob",
  });
}

export async function getPayrollReport(params = {}) {
  const response = await api.get("/reports/payroll", { params });
  return response.data;
}

export async function exportPayrollReport(params = {}, format = "csv") {
  return api.get("/reports/payroll/export", {
    params: { ...params, file_format: format },
    responseType: "blob",
  });
}
