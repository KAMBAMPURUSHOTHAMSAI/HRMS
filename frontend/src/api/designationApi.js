
import api from "./client";

// Get all designations
export async function getDesignations() {
  const response = await api.get("/designations");
  return response.data;
}

// Get one designation by ID
export async function getDesignation(designationId) {
  const response = await api.get(
    `/designations/${designationId}`
  );

  return response.data;
}

// Create a new designation
export async function createDesignation(data) {
  const response = await api.post("/designations", data);
  return response.data;
}

// Update an existing designation
export async function updateDesignation(designationId, data) {
  const response = await api.patch(
    `/designations/${designationId}`,
    data
  );

  return response.data;
}

// Deactivate a designation
export async function deactivateDesignation(designationId) {
  const response = await api.delete(
    `/designations/${designationId}`
  );

  return response.data;
}
