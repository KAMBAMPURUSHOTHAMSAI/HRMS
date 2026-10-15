
import api from "./client";

// Get holidays for the employee calendar.
export async function getHolidayCalendar(params = {}) {
  const response = await api.get("/holidays/calendar", { params });
  return response.data;
}

// Admin/HR: list holidays with optional filters.
export async function getHolidays(params = {}) {
  const response = await api.get("/holidays", { params });
  return response.data;
}

// Admin/HR: create a company, regional or optional holiday.
export async function createHoliday(payload) {
  const response = await api.post("/holidays", payload);
  return response.data;
}

// Admin/HR: update an existing holiday.
export async function updateHoliday(holidayId, payload) {
  const response = await api.patch(
    `/holidays/${holidayId}`,
    payload
  );
  return response.data;
}

// Admin/HR: deactivate a holiday without deleting its history.
export async function deactivateHoliday(holidayId) {
  const response = await api.delete(`/holidays/${holidayId}`);
  return response.data;
}

// Employee: view personal optional holiday selections.
export async function getMyHolidaySelections() {
  const response = await api.get("/holidays/me/selections");
  return response.data;
}

// Employee: select an optional holiday.
export async function selectOptionalHoliday(holidayId) {
  const response = await api.post(
    `/holidays/${holidayId}/select`
  );
  return response.data;
}

// Employee: cancel an optional holiday selection.
export async function cancelOptionalHoliday(holidayId) {
  const response = await api.delete(
    `/holidays/${holidayId}/select`
  );
  return response.data;
}
