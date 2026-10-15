
import api from "./client";

// ── Existing payroll run APIs ──────────────────────────

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

// ── Salary component configuration ─────────────────────

export async function getSalaryComponents(includeInactive = false) {
  const response = await api.get("/salary-components", {
    params: { include_inactive: includeInactive },
  });
  return response.data;
}

export async function createSalaryComponent(data) {
  const response = await api.post("/salary-components", data);
  return response.data;
}

export async function updateSalaryComponent(componentId, data) {
  const response = await api.patch(
    `/salary-components/${componentId}`,
    data
  );
  return response.data;
}

export async function deactivateSalaryComponent(componentId) {
  const response = await api.delete(
    `/salary-components/${componentId}`
  );
  return response.data;
}

// ── Employee salary structure ──────────────────────────

export async function getEmployeeSalaryComponents({
  employeeId,
  asOfDate,
} = {}) {
  const response = await api.get("/employee-salary-components", {
    params: {
      employee_id: employeeId || undefined,
      as_of_date: asOfDate || undefined,
    },
  });

  return response.data;
}

export async function assignEmployeeSalaryComponent(data) {
  const response = await api.post(
    "/employee-salary-components",
    data
  );
  return response.data;
}

export async function updateEmployeeSalaryComponent(assignmentId, data) {
  const response = await api.patch(
    `/employee-salary-components/${assignmentId}`,
    data
  );
  return response.data;
}

// ── Compensation history ───────────────────────────────

export async function getCompensationHistory(employeeId) {
  const response = await api.get(
    `/compensation-history/${employeeId}`
  );
  return response.data;
}

export async function createCompensationRevision(data) {
  const response = await api.post("/compensation-history", data);
  return response.data;
}

// ── Payslip component breakdown ────────────────────────

export async function getPayrollComponentLines(payrollRecordId) {
  const response = await api.get(
    `/payroll-component-lines/${payrollRecordId}`
  );
  return response.data;
}

export async function createPayrollComponentSnapshot(payrollRecordId) {
  const response = await api.post(
    `/payroll-component-lines/${payrollRecordId}/snapshot`
  );
  return response.data;
}
