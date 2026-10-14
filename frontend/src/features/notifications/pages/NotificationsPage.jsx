
import { useCallback, useEffect, useState } from "react";
import {
  CheckCheck,
  Mail,
  RefreshCw,
  Bell,
  ChevronLeft,
  ChevronRight,
  RotateCw,
} from "lucide-react";

import {
  getMyNotifications,
  getUnreadNotificationCount,
  markNotificationRead,
  markAllNotificationsRead,
  getEmailDeliveryLogs,
  retryEmailDelivery,
} from "../../../api/notificationApi";

import { useAuth } from "../../../hooks/useAuth";

const PAGE_SIZE = 20;
const EMAIL_LOG_LIMIT = 100;

function getArray(data) {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.items)) return data.items;
  return [];
}

function formatDate(value) {
  if (!value) return "—";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return String(value);
  }

  return date.toLocaleString("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function notificationStatusClass(isRead) {
  return isRead
    ? "badge bg-secondary"
    : "badge bg-primary";
}

function emailStatusClass(status) {
  switch (String(status || "").toUpperCase()) {
    case "SENT":
      return "badge bg-success";
    case "FAILED":
      return "badge bg-danger";
    case "PENDING":
      return "badge bg-warning text-dark";
    case "SKIPPED":
      return "badge bg-secondary";
    default:
      return "badge bg-light text-dark";
  }
}

function getErrorMessage(error, fallback) {
  return (
    error?.response?.data?.detail ||
    error?.message ||
    fallback
  );
}

export default function NotificationsPage({ mode = "employee" }) {
  const { user } = useAuth();

  const isAdminPage = mode === "admin";
  const isAdmin = user?.roles?.includes("ADMIN") ?? false;

  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [page, setPage] = useState(0);

  const [emailLogs, setEmailLogs] = useState([]);
  const [emailStatusFilter, setEmailStatusFilter] = useState("");
  const [emailLogsLoading, setEmailLogsLoading] = useState(false);

  const [loading, setLoading] = useState(true);
  const [actionId, setActionId] = useState(null);
  const [markingAll, setMarkingAll] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [emailError, setEmailError] = useState("");
  const [emailMessage, setEmailMessage] = useState("");

  const loadNotifications = useCallback(async () => {
    setLoading(true);
    setError("");

    const skip = page * PAGE_SIZE;

    const [notificationsResult, countResult] =
      await Promise.allSettled([
        getMyNotifications({
          unread_only: unreadOnly,
          skip,
          limit: PAGE_SIZE,
        }),
        getUnreadNotificationCount(),
      ]);

    if (notificationsResult.status === "fulfilled") {
      setNotifications(
        getArray(notificationsResult.value)
      );
    } else {
      setNotifications([]);
      setError(
        getErrorMessage(
          notificationsResult.reason,
          "Unable to load notifications."
        )
      );
    }

    if (countResult.status === "fulfilled") {
      setUnreadCount(
        Number(countResult.value?.unread_count ?? 0)
      );
    }

    setLoading(false);
  }, [page, unreadOnly]);

  const loadEmailLogs = useCallback(async () => {
    if (!isAdminPage) return;

    setEmailLogsLoading(true);
    setEmailError("");

    try {
      const params = {
        skip: 0,
        limit: EMAIL_LOG_LIMIT,
      };

      if (emailStatusFilter) {
        params.status_filter = emailStatusFilter;
      }

      const data = await getEmailDeliveryLogs(params);
      setEmailLogs(getArray(data));
    } catch (err) {
      setEmailLogs([]);
      setEmailError(
        getErrorMessage(
          err,
          "Unable to load email delivery logs."
        )
      );
    } finally {
      setEmailLogsLoading(false);
    }
  }, [isAdminPage, emailStatusFilter]);

  useEffect(() => {
    loadNotifications();
  }, [loadNotifications]);

  useEffect(() => {
    if (isAdminPage) {
      loadEmailLogs();
    }
  }, [isAdminPage, loadEmailLogs]);

  async function handleRefresh() {
    setRefreshing(true);
    setError("");
    setMessage("");
    setEmailError("");
    setEmailMessage("");

    try {
      await Promise.all([
        loadNotifications(),
        isAdminPage ? loadEmailLogs() : Promise.resolve(),
      ]);
    } finally {
      setRefreshing(false);
    }
  }

  async function handleMarkRead(notification) {
    if (notification.is_read) return;

    setActionId(notification.id);
    setError("");
    setMessage("");

    try {
      await markNotificationRead(notification.id);

      if (unreadOnly) {
        setNotifications((current) =>
          current.filter((item) => item.id !== notification.id)
        );
      } else {
        setNotifications((current) =>
          current.map((item) =>
            item.id === notification.id
              ? { ...item, is_read: true, read_at: new Date().toISOString() }
              : item
          )
        );
      }

      setUnreadCount((current) => Math.max(0, current - 1));
      setMessage("Notification marked as read.");
    } catch (err) {
      setError(
        getErrorMessage(err, "Unable to mark notification as read.")
      );
    } finally {
      setActionId(null);
    }
  }

  async function handleMarkAllRead() {
    if (unreadCount === 0) return;

    setMarkingAll(true);
    setError("");
    setMessage("");

    try {
      const result = await markAllNotificationsRead();

      setUnreadCount(0);

      if (unreadOnly) {
        setNotifications([]);
      } else {
        setNotifications((current) =>
          current.map((item) => ({
            ...item,
            is_read: true,
            read_at: item.read_at || new Date().toISOString(),
          }))
        );
      }

      setMessage(
        `${Number(result?.updated_count ?? 0)} notification(s) marked as read.`
      );
    } catch (err) {
      setError(
        getErrorMessage(
          err,
          "Unable to mark all notifications as read."
        )
      );
    } finally {
      setMarkingAll(false);
    }
  }

  async function handleRetryEmail(log) {
    setActionId(`email-${log.id}`);
    setEmailError("");
    setEmailMessage("");

    try {
      await retryEmailDelivery(log.id);

      setEmailMessage(
        `Retry request submitted for email log #${log.id}.`
      );

      await loadEmailLogs();
    } catch (err) {
      setEmailError(
        getErrorMessage(
          err,
          "Unable to retry this email delivery."
        )
      );
    } finally {
      setActionId(null);
    }
  }

  function handleUnreadFilterChange(event) {
    setUnreadOnly(event.target.checked);
    setPage(0);
    setMessage("");
    setError("");
  }

  return (
    <section className="container-fluid py-3">
      <div className="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
        <div>
          <h2 className="mb-1">
            {isAdminPage ? "Notification Management" : "My Notifications"}
          </h2>

          <p className="text-muted mb-0">
            {isAdminPage
              ? "Review your notifications and monitor email delivery."
              : "View updates and keep track of important HR activities."}
          </p>
        </div>

        <button
          type="button"
          className="btn btn-outline-primary"
          onClick={handleRefresh}
          disabled={refreshing || loading}
        >
          <RefreshCw size={16} className="me-2" />
          {refreshing ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      {error && (
        <div className="alert alert-danger">{error}</div>
      )}

      {message && (
        <div className="alert alert-success">{message}</div>
      )}

      <div className="row g-3 mb-4">
        <div className="col-sm-6 col-xl-4">
          <div className="card h-100">
            <div className="card-body">
              <Bell size={22} className="text-primary mb-2" />
              <p className="text-muted mb-1">Unread Notifications</p>
              <h3 className="mb-0">{unreadCount}</h3>
            </div>
          </div>
        </div>

        {isAdminPage && (
          <div className="col-sm-6 col-xl-4">
            <div className="card h-100">
              <div className="card-body">
                <Mail size={22} className="text-info mb-2" />
                <p className="text-muted mb-1">Email Logs Loaded</p>
                <h3 className="mb-0">{emailLogs.length}</h3>
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="card mb-4">
        <div className="card-body">
          <div className="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-3">
            <div>
              <h5 className="mb-1">Notifications</h5>
              <p className="text-muted small mb-0">
                Page {page + 1} · Up to {PAGE_SIZE} notifications per page
              </p>
            </div>

            <div className="d-flex flex-wrap align-items-center gap-3">
              <label className="form-check d-flex align-items-center gap-2 mb-0">
                <input
                  type="checkbox"
                  className="form-check-input mt-0"
                  checked={unreadOnly}
                  onChange={handleUnreadFilterChange}
                />
                <span className="form-check-label">
                  Unread only
                </span>
              </label>

              <button
                type="button"
                className="btn btn-outline-success btn-sm"
                onClick={handleMarkAllRead}
                disabled={markingAll || unreadCount === 0}
              >
                <CheckCheck size={15} className="me-1" />
                {markingAll ? "Updating..." : "Mark all as read"}
              </button>
            </div>
          </div>

          {loading ? (
            <p>Loading notifications...</p>
          ) : notifications.length === 0 ? (
            <div className="text-center py-5">
              <Bell size={36} className="text-muted mb-2" />
              <h6>No notifications found</h6>
              <p className="text-muted mb-0">
                New HR updates will appear here when available.
              </p>
            </div>
          ) : (
            <div className="d-flex flex-column gap-3">
              {notifications.map((notification) => (
                <article
                  key={notification.id}
                  className="border rounded p-3"
                >
                  <div className="d-flex flex-wrap justify-content-between align-items-start gap-2">
                    <div className="flex-grow-1">
                      <div className="d-flex flex-wrap align-items-center gap-2 mb-2">
                        <h6 className="mb-0">
                          {notification.title}
                        </h6>

                        <span
                          className={notificationStatusClass(
                            notification.is_read
                          )}
                        >
                          {notification.is_read ? "Read" : "Unread"}
                        </span>
                      </div>

                      <p className="mb-2">
                        {notification.message}
                      </p>

                      <div className="text-muted small">
                        <span className="me-3">
                          Type: {notification.event_type}
                        </span>

                        <span>
                          {formatDate(notification.created_at)}
                        </span>
                      </div>
                    </div>

                    {!notification.is_read && (
                      <button
                        type="button"
                        className="btn btn-sm btn-outline-primary"
                        onClick={() => handleMarkRead(notification)}
                        disabled={actionId === notification.id}
                      >
                        <CheckCheck size={15} className="me-1" />
                        {actionId === notification.id
                          ? "Updating..."
                          : "Mark read"}
                      </button>
                    )}
                  </div>
                </article>
              ))}
            </div>
          )}

          <div className="d-flex justify-content-between align-items-center mt-4">
            <button
              type="button"
              className="btn btn-outline-secondary"
              onClick={() => setPage((current) => Math.max(0, current - 1))}
              disabled={loading || page === 0}
            >
              <ChevronLeft size={16} className="me-1" />
              Previous
            </button>

            <span className="text-muted small">
              Page {page + 1}
            </span>

            <button
              type="button"
              className="btn btn-outline-secondary"
              onClick={() => setPage((current) => current + 1)}
              disabled={
                loading || notifications.length < PAGE_SIZE
              }
            >
              Next
              <ChevronRight size={16} className="ms-1" />
            </button>
          </div>
        </div>
      </div>

      {isAdminPage && (
        <div className="card">
          <div className="card-body">
            <div className="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-3">
              <div>
                <h5 className="mb-1">Email Delivery Logs</h5>
                <p className="text-muted small mb-0">
                  View the delivery status and retry eligible emails.
                </p>
              </div>

              <div className="d-flex gap-2 align-items-center">
                <select
                  className="form-select"
                  style={{ maxWidth: "180px" }}
                  value={emailStatusFilter}
                  onChange={(event) =>
                    setEmailStatusFilter(event.target.value)
                  }
                  aria-label="Filter email logs by status"
                >
                  <option value="">All statuses</option>
                  <option value="PENDING">Pending</option>
                  <option value="SENT">Sent</option>
                  <option value="FAILED">Failed</option>
                  <option value="SKIPPED">Skipped</option>
                </select>

                <button
                  type="button"
                  className="btn btn-outline-primary"
                  onClick={loadEmailLogs}
                  disabled={emailLogsLoading}
                  aria-label="Refresh email logs"
                >
                  <RefreshCw size={16} />
                </button>
              </div>
            </div>

            {emailError && (
              <div className="alert alert-danger">{emailError}</div>
            )}

            {emailMessage && (
              <div className="alert alert-success">{emailMessage}</div>
            )}

            {emailLogsLoading ? (
              <p>Loading email logs...</p>
            ) : emailLogs.length === 0 ? (
              <p className="text-muted mb-0">
                No email delivery logs match this filter.
              </p>
            ) : (
              <div className="table-responsive">
                <table className="table table-hover align-middle">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Recipient</th>
                      <th>Subject</th>
                      <th>Template</th>
                      <th>Status</th>
                      <th>Attempts</th>
                      <th>Created</th>
                      <th>Last Error</th>
                      {isAdmin && <th>Action</th>}
                    </tr>
                  </thead>

                  <tbody>
                    {emailLogs.map((log) => {
                      const canRetry =
                        isAdmin &&
                        ["FAILED", "SKIPPED"].includes(
                          String(log.status).toUpperCase()
                        );

                      return (
                        <tr key={log.id}>
                          <td>{log.id}</td>
                          <td>{log.recipient_email}</td>
                          <td>{log.subject}</td>
                          <td>{log.template_name}</td>

                          <td>
                            <span className={emailStatusClass(log.status)}>
                              {log.status}
                            </span>
                          </td>

                          <td>{log.attempt_count}</td>
                          <td>{formatDate(log.created_at)}</td>

                          <td style={{ minWidth: "180px" }}>
                            {log.error_message || "—"}
                          </td>

                          {isAdmin && (
                            <td>
                              {canRetry ? (
                                <button
                                  type="button"
                                  className="btn btn-sm btn-outline-primary"
                                  onClick={() => handleRetryEmail(log)}
                                  disabled={
                                    actionId === `email-${log.id}`
                                  }
                                >
                                  <RotateCw size={14} className="me-1" />
                                  {actionId === `email-${log.id}`
                                    ? "Retrying..."
                                    : "Retry"}
                                </button>
                              ) : (
                                <span className="text-muted">—</span>
                              )}
                            </td>
                          )}
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}

            <p className="text-muted small mt-3 mb-0">
              Showing at most {EMAIL_LOG_LIMIT} records. Email delivery
              depends on SMTP configuration. Retrying an email requests
              backend processing; delivery is not guaranteed.
            </p>
          </div>
        </div>
      )}
    </section>
  );
}
