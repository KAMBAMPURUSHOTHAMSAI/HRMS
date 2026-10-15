
import api from "./client";

// List active shifts. Admin/HR can also request inactive shifts.
export async function getShifts(params = {}) {
  const response = await api.get("/shifts", { params });
  return response.data;
}

// Create a new work shift.
export async function createShift(payload) {
  const response = await api.post("/shifts", payload);
  return response.data;
}

// Update shift configuration.
export async function updateShift(shiftId, payload) {
  const response = await api.patch(
    `/shifts/${shiftId}`,
    payload
  );
  return response.data;
}

// Deactivate a shift without deleting its history.
export async function deactivateShift(shiftId) {
  const response = await api.delete(`/shifts/${shiftId}`);
  return response.data;
}

// List assignments or historical assignments.
export async function getShiftAssignments(params = {}) {
  const response = await api.get("/shifts/assignments", {
    params,
  });

  return response.data;
}

// Assign a shift to an employee or department.
export async function assignShift(payload) {
  const response = await api.post(
    "/shifts/assignments",
    payload
  );

  return response.data;
}

// Retrieve shift-wise attendance, late arrivals, early checkouts,
// overtime and admin correction indicators.
export async function getShiftAttendanceReport(params) {
  const response = await api.get(
    "/shifts/reports/attendance",
    { params }
  );

  return response.data;
}
