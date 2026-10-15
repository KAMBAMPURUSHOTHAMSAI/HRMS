
import { useCallback, useEffect, useState } from "react";
import {
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  Plus,
  RefreshCw,
  CheckCircle2,
  XCircle,
} from "lucide-react";

import {
  getHolidayCalendar,
  getHolidays,
  createHoliday,
  deactivateHoliday,
  getMyHolidaySelections,
  selectOptionalHoliday,
  cancelOptionalHoliday,
} from "../../../api/holidayApi";

function pad(value) {
  return String(value).padStart(2, "0");
}

function toDateString(date) {
  return [
    date.getFullYear(),
    pad(date.getMonth() + 1),
    pad(date.getDate()),
  ].join("-");
}

function getMonthName(date, style = "long") {
  return date.toLocaleDateString("en-IN", {
    month: style,
    year: style === "long" ? "numeric" : undefined,
  });
}

function getCalendarDays(year, month) {
  const firstDay = new Date(year, month, 1);
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  const days = Array(firstDay.getDay()).fill(null);

  for (let day = 1; day <= daysInMonth; day += 1) {
    days.push(new Date(year, month, day));
  }

  while (days.length % 7 !== 0) {
    days.push(null);
  }

  return days;
}

function getRange(view, selectedDate) {
  if (view === "year") {
    return {
      start_date: `${selectedDate.getFullYear()}-01-01`,
      end_date: `${selectedDate.getFullYear()}-12-31`,
    };
  }

  return {
    start_date: toDateString(
      new Date(
        selectedDate.getFullYear(),
        selectedDate.getMonth(),
        1
      )
    ),
    end_date: toDateString(
      new Date(
        selectedDate.getFullYear(),
        selectedDate.getMonth() + 1,
        0
      )
    ),
  };
}

function getErrorMessage(error, fallback) {
  const detail = error?.response?.data?.detail;

  return (
    (typeof detail === "string" ? detail : null) ||
    error?.message ||
    fallback
  );
}

function holidayColor(type) {
  switch (type) {
    case "COMPANY":
      return "#2563eb";
    case "REGIONAL":
      return "#7c3aed";
    case "OPTIONAL":
      return "#0f766e";
    default:
      return "#64748b";
  }
}

function HolidayCalendarGrid({
  year,
  month,
  holidaysByDate,
  selectedDate,
  onSelectDate,
  compact = false,
}) {
  const days = getCalendarDays(year, month);
  const today = toDateString(new Date());

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(7, minmax(0, 1fr))",
        gap: compact ? 3 : 6,
      }}
    >
      {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map(
        (day) => (
          <div
            key={day}
            style={{
              padding: compact ? "5px 0" : "9px 0",
              textAlign: "center",
              color: "#78859a",
              fontSize: compact ? 10 : 12,
              fontWeight: 700,
            }}
          >
            {compact ? day[0] : day}
          </div>
        )
      )}

      {days.map((date, index) => {
        if (!date) {
          return (
            <div
              key={`empty-${index}`}
              style={{ minHeight: compact ? 22 : 95 }}
            />
          );
        }

        const dateKey = toDateString(date);
        const dayHolidays = holidaysByDate[dateKey] || [];
        const isToday = dateKey === today;
        const isSelected =
          selectedDate && dateKey === toDateString(selectedDate);

        return (
          <button
            key={dateKey}
            type="button"
            title={
              dayHolidays.length
                ? dayHolidays.map((item) => item.name).join(", ")
                : dateKey
            }
            onClick={() => onSelectDate?.(date)}
            style={{
              minWidth: 0,
              minHeight: compact ? 27 : 95,
              padding: compact ? 3 : 8,
              border: isSelected
                ? "2px solid #3155a3"
                : isToday
                  ? "1px solid #3155a3"
                  : "1px solid #e5eaf2",
              borderRadius: 8,
              background: dayHolidays.length ? "#f1f5ff" : "#fff",
              color: "#243650",
              cursor: onSelectDate ? "pointer" : "default",
              textAlign: "left",
              display: "flex",
              flexDirection: "column",
              alignItems: "flex-start",
              gap: 4,
            }}
          >
            <span
              style={{
                alignSelf: compact ? "center" : "flex-start",
                fontSize: compact ? 10 : 12,
                fontWeight: isToday ? 800 : 600,
              }}
            >
              {date.getDate()}
            </span>

            {!compact &&
              dayHolidays.slice(0, 2).map((holiday) => (
                <span
                  key={holiday.id}
                  style={{
                    display: "block",
                    maxWidth: "100%",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                    borderRadius: 4,
                    padding: "3px 5px",
                    background: holidayColor(holiday.holiday_type),
                    color: "#fff",
                    fontSize: 10,
                  }}
                >
                  {holiday.name}
                </span>
              ))}

            {!compact && dayHolidays.length > 2 && (
              <small style={{ color: "#64748b", fontSize: 10 }}>
                +{dayHolidays.length - 2} more
              </small>
            )}

            {compact && dayHolidays.length > 0 && (
              <span
                style={{
                  width: 5,
                  height: 5,
                  margin: "0 auto",
                  borderRadius: "50%",
                  background: holidayColor(
                    dayHolidays[0].holiday_type
                  ),
                }}
              />
            )}
          </button>
        );
      })}
    </div>
  );
}

export default function HolidayCalendarPage({
  mode = "employee",
}) {
  const isAdminPage = mode === "admin";

  const [view, setView] = useState("month");
  const [selectedDate, setSelectedDate] = useState(new Date());

  const [holidays, setHolidays] = useState([]);
  const [selections, setSelections] = useState([]);

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [actionHolidayId, setActionHolidayId] = useState(null);

  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [showForm, setShowForm] = useState(false);

  const [form, setForm] = useState({
    name: "",
    holiday_date: toDateString(new Date()),
    holiday_type: "COMPANY",
    region: "",
    description: "",
  });

  const loadData = useCallback(async () => {
    setLoading(true);
    setError("");

    const range = getRange(view, selectedDate);

    try {
      const data = isAdminPage
        ? await getHolidays(range)
        : await getHolidayCalendar(range);

      setHolidays(Array.isArray(data) ? data : []);
    } catch (err) {
      setHolidays([]);
      setError(
        getErrorMessage(err, "Unable to load holidays.")
      );
    }

    if (!isAdminPage) {
      try {
        const data = await getMyHolidaySelections();
        setSelections(Array.isArray(data) ? data : []);
      } catch {
        setSelections([]);
      }
    }

    setLoading(false);
  }, [isAdminPage, selectedDate, view]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const holidaysByDate = holidays.reduce((result, holiday) => {
    const dateKey = holiday.holiday_date;

    if (!result[dateKey]) {
      result[dateKey] = [];
    }

    result[dateKey].push(holiday);
    return result;
  }, {});

  const selectedHolidayIds = new Set(
    selections
      .filter((selection) => selection.status === "SELECTED")
      .map((selection) => selection.holiday_id)
  );

  const visibleMonths =
    view === "year"
      ? Array.from({ length: 12 }, (_, month) => month)
      : [selectedDate.getMonth()];

  function navigateCalendar(direction) {
    setSelectedDate((current) =>
      view === "year"
        ? new Date(current.getFullYear() + direction, 0, 1)
        : new Date(
            current.getFullYear(),
            current.getMonth() + direction,
            1
          )
    );
  }

  function goToToday() {
    setSelectedDate(new Date());
  }

  async function handleCreateHoliday(event) {
    event.preventDefault();

    setSaving(true);
    setError("");
    setMessage("");

    const payload = {
      name: form.name.trim(),
      holiday_date: form.holiday_date,
      holiday_type: form.holiday_type,
      region:
        form.holiday_type === "REGIONAL"
          ? form.region.trim()
          : null,
      description: form.description.trim() || null,
      is_active: true,
    };

    try {
      await createHoliday(payload);
      setMessage("Holiday created successfully.");
      setShowForm(false);
      setForm({
        name: "",
        holiday_date: toDateString(new Date()),
        holiday_type: "COMPANY",
        region: "",
        description: "",
      });

      await loadData();
    } catch (err) {
      setError(
        getErrorMessage(err, "Unable to create holiday.")
      );
    } finally {
      setSaving(false);
    }
  }

  async function handleDeactivate(holiday) {
    const confirmed = window.confirm(
      `Deactivate "${holiday.name}"?`
    );

    if (!confirmed) return;

    setActionHolidayId(holiday.id);
    setError("");
    setMessage("");

    try {
      await deactivateHoliday(holiday.id);
      setMessage("Holiday deactivated.");
      await loadData();
    } catch (err) {
      setError(
        getErrorMessage(err, "Unable to deactivate holiday.")
      );
    } finally {
      setActionHolidayId(null);
    }
  }

  async function handleOptionalHoliday(holiday) {
    setActionHolidayId(holiday.id);
    setError("");
    setMessage("");

    try {
      if (selectedHolidayIds.has(holiday.id)) {
        await cancelOptionalHoliday(holiday.id);
        setMessage("Optional holiday selection cancelled.");
      } else {
        await selectOptionalHoliday(holiday.id);
        setMessage("Optional holiday selected.");
      }

      await loadData();
    } catch (err) {
      setError(
        getErrorMessage(
          err,
          "Unable to update optional holiday selection."
        )
      );
    } finally {
      setActionHolidayId(null);
    }
  }

  async function handleRefresh() {
    setRefreshing(true);
    try {
      await loadData();
    } finally {
      setRefreshing(false);
    }
  }

  const heading =
    view === "year"
      ? String(selectedDate.getFullYear())
      : getMonthName(selectedDate);

  return (
    <section>
      <div className="page-heading-row">
        <div>
          <p className="section-kicker">WORKFORCE CALENDAR</p>
          <h2>
            {isAdminPage
              ? "Holiday Management"
              : "Holiday Calendar"}
          </h2>
          <p>
            {isAdminPage
              ? "Manage company, regional and optional holidays."
              : "View company holidays and manage your optional selections."}
          </p>
        </div>

        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: 8,
          }}
        >
          <button
            type="button"
            className="secondary-button"
            onClick={handleRefresh}
            disabled={refreshing || loading}
          >
            <RefreshCw size={15} />
            {refreshing ? "Refreshing..." : "Refresh"}
          </button>

          {isAdminPage && (
            <button
              type="button"
              className="primary-button"
              onClick={() => setShowForm((current) => !current)}
            >
              <Plus size={16} />
              Add Holiday
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="alert alert-danger" role="alert">
          {error}
        </div>
      )}

      {message && (
        <div className="alert alert-success" role="status">
          {message}
        </div>
      )}

      {isAdminPage && showForm && (
        <div className="content-card">
          <h3>Add a Holiday</h3>

          <form
            className="employee-form"
            onSubmit={handleCreateHoliday}
          >
            <div className="employee-form-grid">
              <div className="form-field">
                <label htmlFor="holiday-name">Holiday name</label>
                <input
                  id="holiday-name"
                  value={form.name}
                  onChange={(event) =>
                    setForm({
                      ...form,
                      name: event.target.value,
                    })
                  }
                  minLength={2}
                  maxLength={150}
                  required
                />
              </div>

              <div className="form-field">
                <label htmlFor="holiday-date">Date</label>
                <input
                  id="holiday-date"
                  type="date"
                  value={form.holiday_date}
                  onChange={(event) =>
                    setForm({
                      ...form,
                      holiday_date: event.target.value,
                    })
                  }
                  required
                />
              </div>

              <div className="form-field">
                <label htmlFor="holiday-type">Holiday type</label>
                <select
                  id="holiday-type"
                  value={form.holiday_type}
                  onChange={(event) =>
                    setForm({
                      ...form,
                      holiday_type: event.target.value,
                      region: "",
                    })
                  }
                >
                  <option value="COMPANY">Company-wide</option>
                  <option value="REGIONAL">Regional</option>
                  <option value="OPTIONAL">Optional</option>
                </select>
              </div>

              {form.holiday_type === "REGIONAL" && (
                <div className="form-field">
                  <label htmlFor="holiday-region">Region</label>
                  <input
                    id="holiday-region"
                    value={form.region}
                    onChange={(event) =>
                      setForm({
                        ...form,
                        region: event.target.value,
                      })
                    }
                    placeholder="e.g. Andhra Pradesh"
                    maxLength={120}
                    required
                  />
                </div>
              )}

              <div className="form-field">
                <label htmlFor="holiday-description">
                  Description
                </label>
                <input
                  id="holiday-description"
                  value={form.description}
                  onChange={(event) =>
                    setForm({
                      ...form,
                      description: event.target.value,
                    })
                  }
                  maxLength={2000}
                  placeholder="Optional details"
                />
              </div>
            </div>

            <div className="form-actions">
              <button
                type="button"
                className="secondary-button"
                onClick={() => setShowForm(false)}
                disabled={saving}
              >
                Cancel
              </button>

              <button
                type="submit"
                className="primary-button"
                disabled={saving}
              >
                {saving ? "Saving..." : "Save Holiday"}
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="content-card">
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 15,
            marginBottom: 22,
          }}
        >
          <div>
            <h3 style={{ marginBottom: 5 }}>{heading}</h3>
            <p>
              {view === "year"
                ? "Yearly overview of scheduled holidays."
                : "Select a date to review its holidays."}
            </p>
          </div>

          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              alignItems: "center",
              gap: 7,
            }}
          >
            <button
              type="button"
              className="secondary-button"
              onClick={() => setView("month")}
              aria-pressed={view === "month"}
            >
              Month
            </button>

            <button
              type="button"
              className="secondary-button"
              onClick={() => setView("year")}
              aria-pressed={view === "year"}
            >
              Year
            </button>

            <button
              type="button"
              className="secondary-button"
              onClick={() => navigateCalendar(-1)}
              aria-label="Previous period"
            >
              <ChevronLeft size={16} />
            </button>

            <button
              type="button"
              className="secondary-button"
              onClick={goToToday}
            >
              Today
            </button>

            <button
              type="button"
              className="secondary-button"
              onClick={() => navigateCalendar(1)}
              aria-label="Next period"
            >
              <ChevronRight size={16} />
            </button>
          </div>
        </div>

        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: 14,
            marginBottom: 20,
          }}
        >
          {[
            ["COMPANY", "Company-wide"],
            ["REGIONAL", "Regional"],
            ["OPTIONAL", "Optional"],
          ].map(([type, label]) => (
            <span
              key={type}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 7,
                color: "#64748b",
                fontSize: 12,
              }}
            >
              <span
                style={{
                  width: 9,
                  height: 9,
                  borderRadius: 3,
                  background: holidayColor(type),
                }}
              />
              {label}
            </span>
          ))}
        </div>

        {loading ? (
          <div className="page-loading">Loading holidays...</div>
        ) : holidays.length === 0 ? (
          <div className="empty-table">
            No holidays were found for this period.
          </div>
        ) : (
          <div
            style={{
              display: "grid",
              gridTemplateColumns:
                view === "year"
                  ? "repeat(auto-fit, minmax(240px, 1fr))"
                  : "minmax(0, 1fr)",
              gap: 22,
            }}
          >
            {visibleMonths.map((month) => (
              <div key={`${selectedDate.getFullYear()}-${month}`}>
                {view === "year" && (
                  <h3 style={{ fontSize: 15, marginBottom: 10 }}>
                    {new Date(
                      selectedDate.getFullYear(),
                      month,
                      1
                    ).toLocaleDateString("en-IN", {
                      month: "long",
                    })}
                  </h3>
                )}

                <HolidayCalendarGrid
                  year={selectedDate.getFullYear()}
                  month={month}
                  holidaysByDate={holidaysByDate}
                  selectedDate={selectedDate}
                  onSelectDate={
                    view === "month" ? setSelectedDate : undefined
                  }
                  compact={view === "year"}
                />
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="content-card">
        <h3>Holidays in this period</h3>

        {loading ? (
          <div className="page-loading">Loading holiday list...</div>
        ) : holidays.length === 0 ? (
          <p>No active holidays to display.</p>
        ) : (
          <div style={{ display: "grid", gap: 10 }}>
            {holidays.map((holiday) => {
              const isSelected = selectedHolidayIds.has(holiday.id);
              const isActing = actionHolidayId === holiday.id;

              return (
                <div
                  key={holiday.id}
                  style={{
                    display: "flex",
                    flexWrap: "wrap",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: 12,
                    padding: 14,
                    border: "1px solid #e5eaf2",
                    borderRadius: 10,
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      alignItems: "flex-start",
                      gap: 12,
                    }}
                  >
                    <CalendarDays
                      size={19}
                      color={holidayColor(holiday.holiday_type)}
                    />

                    <div>
                      <strong style={{ display: "block" }}>
                        {holiday.name}
                      </strong>

                      <small style={{ color: "#78859a" }}>
                        {holiday.holiday_date}
                        {" · "}
                        {holiday.holiday_type}
                        {holiday.region ? ` · ${holiday.region}` : ""}
                      </small>

                      {holiday.description && (
                        <p style={{ marginTop: 5 }}>
                          {holiday.description}
                        </p>
                      )}
                    </div>
                  </div>

                  <div
                    style={{
                      display: "flex",
                      flexWrap: "wrap",
                      gap: 8,
                    }}
                  >
                    {!isAdminPage &&
                      holiday.holiday_type === "OPTIONAL" && (
                        <button
                          type="button"
                          className="secondary-button"
                          disabled={isActing}
                          onClick={() =>
                            handleOptionalHoliday(holiday)
                          }
                        >
                          {isSelected ? (
                            <XCircle size={15} />
                          ) : (
                            <CheckCircle2 size={15} />
                          )}

                          {isActing
                            ? "Saving..."
                            : isSelected
                              ? "Cancel selection"
                              : "Select holiday"}
                        </button>
                      )}

                    {isAdminPage && (
                      <button
                        type="button"
                        className="secondary-button"
                        disabled={isActing}
                        onClick={() => handleDeactivate(holiday)}
                      >
                        {isActing
                          ? "Saving..."
                          : "Deactivate"}
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </section>
  );
}
