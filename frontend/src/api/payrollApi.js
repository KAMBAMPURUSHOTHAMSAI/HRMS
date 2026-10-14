
import api from "./client";

export async function generatePayrollRun(data) {
  const response = await api.post("/payroll/runs/generate", data);
  return response.data;
}

export async function getPayrollRuns() {
  const response = await api.get("/payroll/runs");
  return response.data;
}

export async function getPayrollRun(runId) {
  const response = await api.get(`/payroll/runs/${runId}`);
  return response.data;
}

export async function getPayrollRunRecords(runId) {
  const response = await api.get(`/payroll/runs/${runId}/records`);
  return response.data;
}

export async function createPayrollAdjustment(runId, data) {
  const response = await api.post(
    `/payroll/runs/${runId}/adjustments`,
    data
  );

  return response.data;
}

export async function lockPayrollRun(runId) {
  const response = await api.post(`/payroll/runs/${runId}/lock`);
  return response.data;
}

export async function simulateSalaryCredit(runId) {
  const response = await api.post(
    `/payroll/runs/${runId}/simulate-credit`
  );

  return response.data;
}

export async function getMyPayrollRecords() {
  const response = await api.get("/payroll/me");
  return response.data;
}
