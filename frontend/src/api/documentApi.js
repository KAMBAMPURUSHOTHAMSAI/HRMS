
import api from "./client";

// Employee: list own documents
export async function getMyDocuments() {
  const response = await api.get("/documents/me");
  return response.data;
}

// Admin / HR: list all documents, optionally filtered by employee ID
export async function getAllDocuments(params = {}) {
  const response = await api.get("/documents", { params });
  return response.data;
}

// Employee: upload a document to their own profile
export async function uploadMyDocument(formData) {
  const response = await api.post("/documents/me", formData);
  return response.data;
}

// Admin / HR: upload a document for an employee
export async function uploadEmployeeDocument(employeeId, formData) {
  const response = await api.post(
    `/documents/employees/${employeeId}`,
    formData
  );

  return response.data;
}

// Download an authorized document as a PDF/image blob
export async function downloadEmployeeDocument(documentId) {
  const response = await api.get(
    `/documents/${documentId}/download`,
    { responseType: "blob" }
  );

  return {
    blob: response.data,
    contentDisposition: response.headers?.["content-disposition"],
  };
}

// Delete a document when the logged-in user is authorized
export async function deleteEmployeeDocument(documentId) {
  const response = await api.delete(`/documents/${documentId}`);
  return response.data;
}
