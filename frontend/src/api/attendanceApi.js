
import api from "./client";

export async function checkIn() {
  const response = await api.post("/attendance/check-in");
  return response.data;
}

export async function checkOut() {
  const response = await api.post("/attendance/check-out");
  return response.data;
}

export async function getMyAttendance(params = {}) {
  const response = await api.get("/attendance/me", { params });
  return response.data;
}

export async function getMyAttendanceSummary(params = {}) {
  const response = await api.get("/attendance/me/summary", { params });
  return response.data;
}

export async function getAllAttendance(params = {}) {
  const response = await api.get("/attendance", { params });
  return response.data;
}

export async function correctAttendance(attendanceId, data) {
  const response = await api.patch(
    `/attendance/${attendanceId}/correction`,
    data
  );
  return response.data;
}
