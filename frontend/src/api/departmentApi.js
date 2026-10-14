
import api from "./client";

// Get all departments
export async function getDepartments() {
  const response = await api.get("/departments");
  return response.data;
}

// Get one department by ID
export async function getDepartment(departmentId) {
  const response = await api.get(`/departments/${departmentId}`);
  return response.data;
}

// Create a new department
export async function createDepartment(data) {
  const response = await api.post("/departments", data);
  return response.data;
}

// Update an existing department
export async function updateDepartment(departmentId, data) {
  const response = await api.patch(
    `/departments/${departmentId}`,
    data
  );

  return response.data;
}

// Deactivate a department
export async function deactivateDepartment(departmentId) {
  const response = await api.delete(`/departments/${departmentId}`);
  return response.data;
}
