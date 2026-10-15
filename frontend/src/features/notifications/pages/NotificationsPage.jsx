
import { useCallback, useEffect, useState } from "react";
import {
  CheckCheck,
  Mail,
  RefreshCw,
  Bell,
  ChevronLeft,
  ChevronRight,
  RotateCw,
  Settings2,
  Save,
  Send,
  Users,
} from "lucide-react";

import {
  getMyNotifications,
  getUnreadNotificationCount,
  markNotificationRead,
  markAllNotificationsRead,
  getEmailDeliveryLogs,
  retryEmailDelivery,
  getMyNotificationPreferences,
  updateMyNotificationPreferences,
  sendAdminBroadcast,
} from "../../../api/notificationApi";

import { getDepartments } from "../../../api/departmentApi";
import { useAuth } from "../../../hooks/useAuth";

const PAGE_SIZE = 20;
const EMAIL_LOG_LIMIT = 100;

const DEFAULT_PREFERENCES = {
  in_app_enabled: true,
  leave_updates_enabled: true,
  payroll_updates_enabled: true,
  attendance_alerts_enabled: true,
  announcements_enabled: true,
  other_updates_enabled: true,
};

function getArray(data) {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.items)) return data.items;
  return [];
}

function getErrorMessage(error, fallback) {
  const detail = error?.response?.data?.detail;

  if (typeof detail === "string") return detail;

  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg || "Invalid input").join(", ");
  }

  return error?.message || fallback;
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

const PREFERENCE_FIELDS = [
  {
    key: "in_app_enabled",
    label: "Enable in-app notifications",
    description: "Master switch for all in-app notifications.",
  },
  {
    key: "leave_updates_enabled",
    label: "Leave updates",
    description: "Leave application, approval and rejection alerts.",
  },
  {
    key: "payroll_updates_enabled",
    label: "Payroll updates",
    description: "Payroll processing and salary slip notifications.",
  },
  {
    key: "attendance_alerts_enabled",
    label: "Attendance alerts",
    description: "Attendance-related notifications and reminders.",
  },
  {
    key: "announcements_enabled",
    label: "Admin announcements",
    description: "Broadcast messages from the HRMS administrator.",
  },
  {
    key: "other_updates_enabled",
    label: "Other updates",
    description: "Other HRMS notification categories.",
  },
];

const EMPTY_BROADCAST = {
  title: "",
  message: "",
  scope: "ALL",
  department_ids: [],
};

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

  const [preferences, setPreferences] = useState(DEFAULT_PREFERENCES);
  const [preferencesLoading, setPreferencesLoading] = useState(true);
  const [preferencesSaving, setPreferencesSaving] = useState(false);
  const [preferencesError, setPreferencesError] = useState("");
  const [preferencesMessage, setPreferencesMessage] = useState("");

  const [departments, setDepartments] = useState([]);
  const [departmentsError, setDepartmentsError] = useState([]);

  const [broadcast, setBroadcast] = useState(EMPTY_BROADCAST);
  const [broadcastSaving, setBroadcastSaving] = useState(false);
  const [broadcastError, setBroadcastError] = useState("");
  const [broadcastMessage, setBroadcastMessage] = useState("");

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
      setNotifications(getArray(notificationsResult.value));
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

  const loadPreferences = useCallback(async () => {
    setPreferencesLoading(true);
    setPreferencesError("");

    try {
      const data = await getMyNotificationPreferences();

      setPreferences({
        ...DEFAULT_PREFERENCES,
        ...data,
      });
    } catch (err) {
      setPreferencesError(
        getErrorMessage(
          err,
          "Unable to load notification preferences."
        )
      );
    } finally {
      setPreferencesLoading(false);
    }
  }, []);

  const loadDepartments = useCallback(async () => {
    if (!isAdminPage || !isAdmin) return;

    setDepartmentsError("");

    try {
      const data = await getDepartments();

      setDepartments(
        getArray(data).filter((department) => department.is_active)
      );
    } catch (err) {
      setDepartments([]);
      setDepartmentsError(
        getErrorMessage(err, "Unable to load departments.")
      );
    }
  }, [isAdminPage, isAdmin]);

  useEffect(() => {
    loadNotifications();
  }, [loadNotifications]);

  useEffect(() => {
    loadPreferences();
  }, [loadPreferences]);

  useEffect(() => {
    if (isAdminPage) {
      loadEmailLogs();
    }
  }, [isAdminPage, loadEmailLogs]);

  useEffect(() => {
    loadDepartments();
  }, [loadDepartments]);

  async function handleRefresh() {
    setRefreshing(true);
    setError("");
    setMessage("");
    setEmailError("");
    setEmailMessage("");

    try {
      await Promise.all([
        loadNotifications(),
        loadPreferences(),
        isAdminPage ? loadEmailLogs() : Promise.resolve(),
        isAdmin && isAdminPage
          ? loadDepartments()
          : Promise.resolve(),
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
              ? {
                  ...item,
                  is_read: true,
                  read_at: new Date().toISOString(),
                }
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

  function handlePreferenceChange(key, checked) {
    setPreferences((current) => ({
      ...current,
      [key]: checked,
    }));

    setPreferencesMessage("");
    setPreferencesError("");
  }

  async function handleSavePreferences(event) {
    event.preventDefault();

    setPreferencesSaving(true);
    setPreferencesError("");
    setPreferencesMessage("");

    try {
      const saved = await updateMyNotificationPreferences(
        preferences
      );

      setPreferences({
        ...DEFAULT_PREFERENCES,
        ...saved,
      });

      setPreferencesMessage(
        "Notification preferences saved successfully."
      );
    } catch (err) {
      setPreferencesError(
        getErrorMessage(
          err,
          "Unable to save notification preferences."
        )
      );
    } finally {
      setPreferencesSaving(false);
    }
  }

  function handleBroadcastChange(event) {
    const { name, value } = event.target;

    setBroadcast((current) => {
      if (name === "scope") {
        return {
          ...current,
          scope: value,
          department_ids: [],
        };
      }

      return {
        ...current,
        [name]: value,
      };
    });

    setBroadcastError("");
    setBroadcastMessage("");
  }

  function handleDepartmentToggle(departmentId, checked) {
    setBroadcast((current) => {
      const currentIds = current.department_ids;

      return {
        ...current,
        department_ids: checked
          ? [...new Set([...currentIds, departmentId])]
          : currentIds.filter((id) => id !== departmentId),
      };
    });

    setBroadcastError("");
    setBroadcastMessage("");
  }

  async function handleSendBroadcast(event) {
    event.preventDefault();

    setBroadcastError("");
    setBroadcastMessage("");

    if (broadcast.scope === "DEPARTMENTS") {
      if (broadcast.department_ids.length === 0) {
        setBroadcastError("Select at least one department.");
        return;
      }

      if (
        !broadcast.department_ids.every((id) =>
          departments.some((department) => department.id === id)
        )
      ) {
        setBroadcastError(
          "A selected department is no longer available. Refresh and try again."
        );
        return;
      }
    }

    const confirmed = window.confirm(
      broadcast.scope === "ALL"
        ? "Send this announcement to all active user accounts?"
        : `Send this announcement to employees in ${broadcast.department_ids.length} selected department(s)?`
    );

    if (!confirmed) return;

    setBroadcastSaving(true);

    try {
      const result = await sendAdminBroadcast({
        title: broadcast.title.trim(),
        message: broadcast.message.trim(),
        scope: broadcast.scope,
        department_ids:
          broadcast.scope === "DEPARTMENTS"
            ? broadcast.department_ids
            : [],
      });

      setBroadcastMessage(
        `${result.message} Targeted: ${result.target_count}; created: ${result.notifications_created}; skipped by preferences: ${result.skipped_by_preferences}.`
      );

      setBroadcast({
        ...EMPTY_BROADCAST,
        department_ids: [],
      });

      await loadNotifications();
    } catch (err) {
      setBroadcastError(
        getErrorMessage(err, "Unable to send the announcement.")
      );
    } finally {
      setBroadcastSaving(false);
    }
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
              ? "Review notifications, manage broadcasts and monitor email delivery."
              : "View updates and manage your notification preferences."}
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

      {error && <div className="alert alert-danger">{error}</div>}
      {message && <div className="alert alert-success">{message}</div>}

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

      {/* Notification preferences for the authenticated user */}
      <div className="card mb-4">
        <div className="card-body">
          <div className="d-flex align-items-center gap-2 mb-3">
            <Settings2 size={21} className="text-primary" />
            <div>
              <h5 className="mb-1">Notification Preferences</h5>
              <p className="text-muted small mb-0">
                Control which categories can create in-app notifications.
                Email settings are managed separately.
              </p>
            </div>
          </div>

          {preferencesError && (
            <div className="alert alert-danger">
              {preferencesError}
            </div>
          )}

          {preferencesMessage && (
            <div className="alert alert-success">
              {preferencesMessage}
            </div>
          )}

          {preferencesLoading ? (
            <p>Loading preferences...</p>
          ) : (
            <form onSubmit={handleSavePreferences}>
              <div className="row g-3">
                {PREFERENCE_FIELDS.map((field) => (
                  <div className="col-md-6" key={field.key}>
                    <div className="border rounded p-3 h-100">
                      <label
                        className="form-check d-flex align-items-start gap-2 mb-0"
                        htmlFor={`preference-${field.key}`}
                      >
                        <input
                          id={`preference-${field.key}`}
                          type="checkbox"
                          className="form-check-input mt-1"
                          checked={Boolean(preferences[field.key])}
                          onChange={(event) =>
                            handlePreferenceChange(
                              field.key,
                              event.target.checked
                            )
                          }
                        />

                        <span>
                          <strong className="d-block">
                            {field.label}
                          </strong>
                          <small className="text-muted">
                            {field.description}
                          </small>
                        </span>
                      </label>
                    </div>
                  </div>
                ))}
              </div>

              <div className="d-flex justify-content-end mt-3">
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={preferencesSaving || preferencesLoading}
                >
                  <Save size={16} className="me-2" />
                  {preferencesSaving ? "Saving..." : "Save Preferences"}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>

      {/* Admin-only announcement broadcast */}
      {isAdminPage && isAdmin && (
        <div className="card mb-4">
          <div className="card-body">
            <div className="d-flex align-items-center gap-2 mb-3">
              <Send size={21} className="text-primary" />
              <div>
                <h5 className="mb-1">Broadcast Announcement</h5>
                <p className="text-muted small mb-0">
                  Send an in-app announcement to the organization or
                  selected departments. This form does not send email.
                </p>
              </div>
            </div>

            {broadcastError && (
              <div className="alert alert-danger">
                {broadcastError}
              </div>
            )}

            {broadcastMessage && (
              <div className="alert alert-success">
                {broadcastMessage}
              </div>
            )}

            {departmentsError && (
              <div className="alert alert-warning">
                {departmentsError}
              </div>
            )}

            <form onSubmit={handleSendBroadcast}>
              <div className="row g-3">
                <div className="col-md-6">
                  <label className="form-label" htmlFor="broadcast-title">
                    Announcement title *
                  </label>
                  <input
                    id="broadcast-title"
                    name="title"
                    className="form-control"
                    minLength={2}
                    maxLength={200}
                    value={broadcast.title}
                    onChange={handleBroadcastChange}
                    required
                  />
                </div>

                <div className="col-md-6">
                  <label className="form-label" htmlFor="broadcast-scope">
                    Recipients *
                  </label>
                  <select
                    id="broadcast-scope"
                    name="scope"
                    className="form-select"
                    value={broadcast.scope}
                    onChange={handleBroadcastChange}
                  >
                    <option value="ALL">Entire organization</option>
                    <option value="DEPARTMENTS">
                      Selected departments
                    </option>
                  </select>
                </div>

                {broadcast.scope === "DEPARTMENTS" && (
                  <div className="col-12">
                    <label className="form-label">
                      Select departments *
                    </label>

                    {departments.length === 0 ? (
                      <p className="text-muted small">
                        No active departments are available.
                      </p>
                    ) : (
                      <div className="row g-2">
                        {departments.map((department) => (
                          <div
                            className="col-md-6 col-xl-4"
                            key={department.id}
                          >
                            <label className="form-check border rounded p-3 ps-5 h-100">
                              <input
                                className="form-check-input"
                                type="checkbox"
                                checked={broadcast.department_ids.includes(
                                  department.id
                                )}
                                onChange={(event) =>
                                  handleDepartmentToggle(
                                    department.id,
                                    event.target.checked
                                  )
                                }
                              />
                              <span className="form-check-label">
                                <Users size={15} className="me-2" />
                                {department.name}
                              </span>
                            </label>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                <div className="col-12">
                  <label
                    className="form-label"
                    htmlFor="broadcast-message"
                  >
                    Announcement message *
                  </label>
                  <textarea
                    id="broadcast-message"
                    name="message"
                    className="form-control"
                    rows={4}
                    minLength={2}
                    maxLength={5000}
                    value={broadcast.message}
                    onChange={handleBroadcastChange}
                    required
                  />
                </div>
              </div>

              <div className="d-flex justify-content-end mt-3">
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={
                    broadcastSaving ||
                    (
                      broadcast.scope === "DEPARTMENTS" &&
                      departments.length === 0
                    )
                  }
                >
                  <Send size={16} className="me-2" />
                  {broadcastSaving ? "Sending..." : "Send Announcement"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Existing notification inbox */}
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
                <span className="form-check-label">Unread only</span>
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

                      <p className="mb-2">{notification.message}</p>

                      <div className="text-muted small">
                        <span className="me-3">
                          Type: {notification.event_type}
                        </span>
                        <span>{formatDate(notification.created_at)}</span>
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

            <span className="text-muted small">Page {page + 1}</span>

            <button
              type="button"
              className="btn btn-outline-secondary"
              onClick={() => setPage((current) => current + 1)}
              disabled={loading || notifications.length < PAGE_SIZE}
            >
              Next
              <ChevronRight size={16} className="ms-1" />
            </button>
          </div>
        </div>
      </div>

      {/* Existing Admin email delivery logs and retry actions */}
      {isAdminPage && (
        <div className="card">
          <div className="card-body">
            <div className="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-3">
              <div>
                <h5 className="mb-1">Email Delivery Logs</h5>
                <p className="text-muted small mb-0">
                  View delivery status and retry eligible emails.
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
                                  disabled={actionId === `email-${log.id}`}
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
