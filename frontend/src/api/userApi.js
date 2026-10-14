
import api from "./client";

// Get all existing users.
export async function getUsers() {
  const response = await api.get("/users");
  return response.data;
}

// Get a single user by ID.
export async function getUser(userId) {
  const response = await api.get(`/users/${userId}`);
  return response.data;
}

// Update a user's name or account status.
export async function updateUser(userId, data) {
  const response = await api.patch(`/users/${userId}`, data);
  return response.data;
}
