
import api from "./client";

// Get notifications for the logged-in user.
export async function getMyNotifications(params = {}) {
  const response = await api.get("/notifications/me", { params });
  return response.data;
}

// Get unread notification count.
export async function getUnreadNotificationCount() {
  const response = await api.get("/notifications/me/unread-count");
  return response.data;
}

// Mark a single notification as read.
export async function markNotificationRead(notificationId) {
  const response = await api.patch(
    `/notifications/${notificationId}/read`
  );

  return response.data;
}

// Mark all notifications as read.
export async function markAllNotificationsRead() {
  const response = await api.post("/notifications/me/read-all");
  return response.data;
}

// Admin / HR: get email delivery logs.
export async function getEmailDeliveryLogs(params = {}) {
  const response = await api.get("/notifications/admin/email-logs", {
    params,
  });

  return response.data;
}

// Admin only: retry a failed email delivery log.
export async function retryEmailDelivery(emailLogId) {
  const response = await api.post(
    `/notifications/admin/email-logs/${emailLogId}/retry`
  );

  return response.data;
}
