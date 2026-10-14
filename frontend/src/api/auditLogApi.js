
import api from "./client";

export async function getAuditLogs(params = {}) {
  const response = await api.get("/audit-logs", { params });
  return response.data;
}

export async function getAuditLog(logId) {
  const response = await api.get(`/audit-logs/${logId}`);
  return response.data;
}
