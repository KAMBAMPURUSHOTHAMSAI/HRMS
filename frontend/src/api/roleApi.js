
import api from "./client";

// Role CRUD
export async function getRoles() {
  const response = await api.get("/roles");
  return response.data;
}

export async function getRole(roleId) {
  const response = await api.get(`/roles/${roleId}`);
  return response.data;
}

export async function createRole(data) {
  const response = await api.post("/roles", data);
  return response.data;
}

export async function updateRole(roleId, data) {
  const response = await api.patch(`/roles/${roleId}`, data);
  return response.data;
}

export async function deactivateRole(roleId) {
  const response = await api.delete(`/roles/${roleId}`);
  return response.data;
}

// Permission CRUD
export async function getPermissions() {
  const response = await api.get("/roles/permissions");
  return response.data;
}

export async function createPermission(data) {
  const response = await api.post("/roles/permissions", data);
  return response.data;
}

export async function updatePermission(permissionId, data) {
  const response = await api.patch(
    `/roles/permissions/${permissionId}`,
    data
  );

  return response.data;
}

export async function deletePermission(permissionId) {
  const response = await api.delete(
    `/roles/permissions/${permissionId}`
  );

  return response.data;
}

// Assign/remove a user from a role
export async function assignUserToRole(roleId, userId) {
  const response = await api.post(
    `/roles/${roleId}/users/${userId}`
  );

  return response.data;
}

export async function removeUserFromRole(roleId, userId) {
  const response = await api.delete(
    `/roles/${roleId}/users/${userId}`
  );

  return response.data;
}

// Assign/remove a permission from a role
export async function assignPermissionToRole(roleId, permissionId) {
  const response = await api.post(
    `/roles/${roleId}/permissions/${permissionId}`
  );

  return response.data;
}

export async function removePermissionFromRole(roleId, permissionId) {
  const response = await api.delete(
    `/roles/${roleId}/permissions/${permissionId}`
  );

  return response.data;
}
