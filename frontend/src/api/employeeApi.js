
import api from "./client";

export async function getEmployees() {
  const response = await api.get("/employees");
  return response.data;
}

export async function getEmployee(employeeId) {
  const response = await api.get(`/employees/${employeeId}`);
  return response.data;
}

export async function createEmployee(payload) {
  const response = await api.post("/employees", payload);
  return response.data;
}

export async function updateEmployee(employeeId, payload) {
  const response = await api.patch(`/employees/${employeeId}`, payload);
  return response.data;
}

export async function deactivateEmployee(employeeId) {
  const response = await api.delete(`/employees/${employeeId}`);
  return response.data;
}

export async function getMyEmployeeProfile() {
  const response = await api.get("/employees/me");
  return response.data;
}
export async function updateMyEmployeeProfile(payload) {
  const response = await api.patch("/employees/me", payload);
  return response.data;
}