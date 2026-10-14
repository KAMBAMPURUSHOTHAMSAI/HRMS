
import api from "./client";

// Leave Types
export async function getLeaveTypes(params = {}) {
  const response = await api.get("/leave-types", { params });
  return response.data;
}

export async function createLeaveType(data) {
  const response = await api.post("/leave-types", data);
  return response.data;
}

export async function updateLeaveType(leaveTypeId, data) {
  const response = await api.patch(
    `/leave-types/${leaveTypeId}`,
    data
  );
  return response.data;
}

export async function deactivateLeaveType(leaveTypeId) {
  const response = await api.delete(
    `/leave-types/${leaveTypeId}`
  );
  return response.data;
}

// Employee Leave Requests
export async function applyForLeave(data) {
  const response = await api.post("/leaves", data);
  return response.data;
}

export async function getMyLeaves(params = {}) {
  const response = await api.get("/leaves/me", { params });
  return response.data;
}

export async function getMyLeaveBalances(params = {}) {
  const response = await api.get("/leaves/me/balances", {
    params,
  });
  return response.data;
}

// Admin / HR Leave Requests
export async function getLeaveRequests(params = {}) {
  const queryParams = { ...params };

  // The backend expects "leave_status", not "status".
  if (Object.prototype.hasOwnProperty.call(queryParams, "status")) {
    if (
      !queryParams.leave_status &&
      queryParams.status
    ) {
      queryParams.leave_status = queryParams.status;
    }

    delete queryParams.status;
  }

  const response = await api.get("/leaves", {
    params: queryParams,
  });

  return response.data;
}

export async function getLeaveRequest(leaveId) {
  const response = await api.get(`/leaves/${leaveId}`);
  return response.data;
}

export async function approveLeave(leaveId, data = {}) {
  const response = await api.post(
    `/leaves/${leaveId}/approve`,
    data
  );
  return response.data;
}

export async function rejectLeave(leaveId, data = {}) {
  const response = await api.post(
    `/leaves/${leaveId}/reject`,
    data
  );
  return response.data;
}
