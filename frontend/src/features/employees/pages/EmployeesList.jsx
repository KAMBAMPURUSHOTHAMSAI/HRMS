
import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  Link,
  useLocation,
} from "react-router-dom";

import {
  Building2,
  Eye,
  Pencil,
  Plus,
  RefreshCw,
  Search,
  UserCheck,
  Users,
  UserX,
} from "lucide-react";

import {
  getEmployees,
  deactivateEmployee,
} from "../../../api/employeeApi";


function errorMessage(error) {
  return error.response?.data?.detail ||
    "An unexpected error occurred.";
}


function MetricCard({ icon: Icon, label, value }) {
  return (
    <div className="employee-mini-stat">
      <span className="employee-mini-stat-icon">
        <Icon size={22} />
      </span>

      <div>
        <span>{label}</span>
        <strong>{value}</strong>
      </div>
    </div>
  );
}


export default function EmployeesList() {
  const location = useLocation();

  const [employees, setEmployees] = useState([]);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState(
    location.state?.message || ""
  );

  const loadEmployees = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const data = await getEmployees();

      setEmployees(
        Array.isArray(data) ? data : []
      );
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadEmployees();
  }, [loadEmployees]);

  const activeCount = useMemo(
    () => employees.filter((employee) => employee.is_active).length,
    [employees]
  );

  const inactiveCount = employees.length - activeCount;

  const filteredEmployees = useMemo(() => {
    const query = search.trim().toLowerCase();

    return employees.filter((employee) => {
      const matchesSearch = !query || [
        employee.employee_code,
        employee.first_name,
        employee.last_name,
        employee.email,
        employee.department_name,
        employee.designation_name,
      ]
        .filter(Boolean)
        .some((value) =>
          String(value).toLowerCase().includes(query)
        );

      const matchesStatus =
        statusFilter === "all" ||
        (statusFilter === "active" && employee.is_active) ||
        (statusFilter === "inactive" && !employee.is_active);

      return matchesSearch && matchesStatus;
    });
  }, [employees, search, statusFilter]);

  async function handleDeactivate(employee) {
    const confirmed = window.confirm(
      `Deactivate ${employee.first_name} ${employee.last_name}?`
    );

    if (!confirmed) return;

    setError("");
    setNotice("");

    try {
      await deactivateEmployee(employee.id);

      setNotice(
        `Employee ${employee.employee_code} was deactivated successfully.`
      );

      await loadEmployees();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <div className="dashboard-page hr-employee-directory">
      <div className="page-heading-row">
        <div>
          <p className="section-kicker">PEOPLE MANAGEMENT</p>
          <h2>Employees</h2>
          <p>
            Manage employee profiles, teams, job details, and employment status.
          </p>
        </div>

        <Link
          className="primary-button"
          to="/admin/employees/new"
        >
          <Plus size={17} />
          Add Employee
        </Link>
      </div>

      {error && (
        <div className="alert alert-danger" role="alert">
          {error}
        </div>
      )}

      {notice && (
        <div className="alert alert-success" role="status">
          {notice}
        </div>
      )}

      <section className="employee-list-stats">
        <MetricCard
          icon={Users}
          label="Total Employees"
          value={employees.length}
        />

        <MetricCard
          icon={UserCheck}
          label="Active Employees"
          value={activeCount}
        />

        <MetricCard
          icon={UserX}
          label="Inactive Employees"
          value={inactiveCount}
        />
      </section>

      <section className="content-card employee-list-card">
        <div className="table-toolbar">
          <div>
            <h3>Employee Directory</h3>
            <p>
              {filteredEmployees.length} of {employees.length} employees shown
            </p>
          </div>

          <div className="table-toolbar-actions">
            <div className="search-field">
              <Search size={18} />

              <input
                type="search"
                placeholder="Search name, ID, email..."
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                aria-label="Search employees"
              />
            </div>

            <select
              className="employee-directory-filter"
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value)}
              aria-label="Filter employees by status"
            >
              <option value="all">All employees</option>
              <option value="active">Active only</option>
              <option value="inactive">Inactive only</option>
            </select>

            <button
              className="secondary-button"
              type="button"
              onClick={loadEmployees}
              disabled={loading}
            >
              <RefreshCw
                size={16}
                className={loading ? "hr-refresh-spinning" : ""}
              />
              Refresh
            </button>
          </div>
        </div>

        {loading ? (
          <div className="page-loading" role="status">
            Loading employee directory...
          </div>
        ) : (
          <div className="table-responsive">
            <table className="table align-middle employee-table">
              <thead>
                <tr>
                  <th>Employee</th>
                  <th>Department</th>
                  <th>Designation</th>
                  <th>Joining Date</th>
                  <th>Status</th>
                  <th className="text-end">Actions</th>
                </tr>
              </thead>

              <tbody>
                {filteredEmployees.map((employee) => (
                  <tr key={employee.id}>
                    <td>
                      <div className="employee-cell">
                        <span
                          className="employee-avatar"
                          aria-hidden="true"
                        >
                          {(employee.first_name || "?")[0].toUpperCase()}
                        </span>

                        <div>
                          <strong>
                            {employee.first_name} {employee.last_name}
                          </strong>

                          <small>
                            {employee.employee_code}
                          </small>

                          <small>
                            {employee.email}
                          </small>
                        </div>
                      </div>
                    </td>

                    <td>
                      <span className="hr-table-secondary">
                        <Building2 size={14} />
                        {employee.department_name || "Not assigned"}
                      </span>
                    </td>

                    <td>
                      {employee.designation_name || "Not assigned"}
                    </td>

                    <td>
                      {employee.joining_date || "—"}
                    </td>

                    <td>
                      <span
                        className={`status-pill ${
                          employee.is_active
                            ? "status-active"
                            : "status-inactive"
                        }`}
                      >
                        {employee.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>

                    <td>
                      <div className="table-actions">
                        <Link
                          className="table-icon-button"
                          to={`/admin/employees/${employee.id}`}
                          title="View employee profile"
                          aria-label={`View ${employee.first_name}'s profile`}
                        >
                          <Eye size={17} />
                        </Link>

                        {employee.is_active && (
                          <>
                            <Link
                              className="table-icon-button"
                              to={`/admin/employees/${employee.id}/edit`}
                              title="Edit employee"
                              aria-label={`Edit ${employee.first_name}`}
                            >
                              <Pencil size={17} />
                            </Link>

                            <button
                              className="table-icon-button danger-action"
                              type="button"
                              title="Deactivate employee"
                              aria-label={`Deactivate ${employee.first_name}`}
                              onClick={() => handleDeactivate(employee)}
                            >
                              <UserX size={17} />
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}

                {filteredEmployees.length === 0 && (
                  <tr>
                    <td colSpan={6} className="empty-table">
                      {search || statusFilter !== "all"
                        ? "No employees match these filters."
                        : "No employees have been added yet. Select Add Employee to create the first profile."}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
