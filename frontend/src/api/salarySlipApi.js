
import api from "./client";

// Generate PDF salary slips for a locked payroll run (Admin / HR).
export async function generateSalarySlips(runId) {
  const response = await api.post(
    `/salary-slips/payroll-runs/${runId}/generate`
  );

  return response.data;
}

// Retrieve all salary slips (Admin / HR).
export async function getAllSalarySlips() {
  const response = await api.get("/salary-slips");
  return response.data;
}

// Retrieve salary slips belonging to the logged-in employee.
export async function getMySalarySlips() {
  const response = await api.get("/salary-slips/me");
  return response.data;
}

// Download a salary slip PDF.
export async function downloadSalarySlip(slipId) {
  const response = await api.get(
    `/salary-slips/${slipId}/download`,
    { responseType: "blob" }
  );

  return {
    blob: response.data,
    contentDisposition: response.headers?.["content-disposition"],
  };
}
