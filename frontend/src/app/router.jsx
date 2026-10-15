
import {
  createBrowserRouter,
  Navigate,
} from "react-router-dom";

import Login from "../features/auth/pages/Login";
import AdminDashboard from "../features/dashboard/pages/AdminDashboard";
import EmployeeDashboard from "../features/dashboard/pages/EmployeeDashboard";

import AuthLayout from "../layouts/AuthLayout";
import AdminLayout from "../layouts/AdminLayout";
import EmployeeLayout from "../layouts/EmployeeLayout";

import ProtectedRoute from "../routes/ProtectedRoute";
import RoleRoute from "../routes/RoleRoute";
import { useAuth } from "../hooks/useAuth";

import EmployeesList from "../features/employees/pages/EmployeesList";
import EmployeeForm from "../features/employees/pages/EmployeeForm";
import EmployeeDetails from "../features/employees/pages/EmployeeDetails";

import UsersList from "../features/users/pages/UsersList";
import UserForm from "../features/users/pages/UserForm";

import DepartmentsPage from "../features/departments/pages/DepartmentsPage";
import DesignationsPage from "../features/designations/pages/DesignationsPage";

import AttendancePage from "../features/attendance/pages/AttendancePage";
import AttendanceHistory from "../features/attendance/pages/AttendanceHistory";

import HolidayCalendarPage from "../features/holidays/pages/HolidayCalendarPage";
import ShiftManagementPage from "../features/shifts/pages/ShiftManagementPage";

import ApplyLeave from "../features/leaves/pages/ApplyLeave";
import MyLeaves from "../features/leaves/pages/MyLeaves";
import LeaveApprovals from "../features/leaves/pages/LeaveApprovals";
import LeaveTypesPage from "../features/leaves/pages/LeaveTypesPage";

import PayrollRuns from "../features/payroll/pages/PayrollRuns";
import PayrollDetails from "../features/payroll/pages/PayrollDetails";
import MySalarySlips from "../features/payroll/pages/MySalarySlips";

import NotificationsPage from "../features/notifications/pages/NotificationsPage";
import RoleManagement from "../features/roles/pages/RoleManagement";
import EmployeeDocuments from "../features/documents/pages/EmployeeDocuments";
import MyProfile from "../features/profile/pages/MyProfile";

import ReportsPage from "../features/reports/pages/ReportsPage";
import AuditLogsPage from "../features/audit-logs/pages/AuditLogsPage";
import SalaryComponentsPage from "../features/payroll/pages/SalaryComponentsPage";
import EmployeeSalaryStructurePage from "../features/payroll/pages/EmployeeSalaryStructurePage";


function DashboardRedirect() {
  const { user } = useAuth();

  return (
    <Navigate
      to={
        user?.roles?.includes("EMPLOYEE")
          ? "/employee/dashboard"
          : "/admin/dashboard"
      }
      replace
    />
  );
}


function NotFoundPage() {
  return (
    <div className="not-found-page">
      <h1>404</h1>
      <p>This page does not exist.</p>
      <a href="/">Return to HRMS</a>
    </div>
  );
}


export const router = createBrowserRouter([
  {
    path: "/login",
    element: (
      <AuthLayout>
        <Login />
      </AuthLayout>
    ),
  },
  {
    path: "/",
    element: <ProtectedRoute />,
    children: [
      {
        index: true,
        element: <DashboardRedirect />,
      },
      {
        element: <RoleRoute allowedRoles={["ADMIN", "HR"]} />,
        children: [
          {
            path: "admin",
            element: <AdminLayout />,
            children: [
              {
                index: true,
                element: <Navigate to="dashboard" replace />,
              },
              {
                path: "dashboard",
                element: <AdminDashboard />,
              },
              {
                path: "employees",
                element: <EmployeesList />,
              },
              {
                path: "employees/new",
                element: <EmployeeForm />,
              },
              {
                path: "employees/:employeeId/edit",
                element: <EmployeeForm />,
              },
              {
                path: "employees/:employeeId",
                element: <EmployeeDetails />,
              },
              {
                path: "users",
                element: <UsersList />,
              },
              {
                path: "users/:userId/edit",
                element: <UserForm />,
              },
              {
                path: "departments",
                element: <DepartmentsPage />,
              },
              {
                path: "designations",
                element: <DesignationsPage />,
              },
              {
                path: "roles",
                element: <RoleManagement />,
              },
              {
                path: "attendance",
                element: <AttendancePage />,
              },

              // Holiday Management
              {
                path: "holidays",
                element: <HolidayCalendarPage mode="admin" />,
              },

              // Shift and Work Schedule Management
              {
                path: "shifts",
                element: <ShiftManagementPage />,
              },

              {
                path: "leave-types",
                element: <LeaveTypesPage />,
              },
              {
                path: "leaves",
                element: <LeaveApprovals />,
              },
              {
                path: "payroll",
                element: <PayrollRuns />,
              },
              {
                path: "payroll/:runId",
                element: <PayrollDetails />,
              },
              {
                path: "salary-components",
                element: <SalaryComponentsPage />,
              },
              {
                path: "employee-salary-structure",
                element: <EmployeeSalaryStructurePage />,
              },
              {
                path: "salary-slips",
                element: <MySalarySlips mode="admin" />,
              },
              {
                path: "documents",
                element: <EmployeeDocuments mode="admin" />,
              },
              {
                path: "notifications",
                element: <NotificationsPage mode="admin" />,
              },
              {
                path: "reports",
                element: <ReportsPage />,
              },
              {
                element: <RoleRoute allowedRoles={["ADMIN"]} />,
                children: [
                  {
                    path: "audit-logs",
                    element: <AuditLogsPage />,
                  },
                ],
              },
            ],
          },
        ],
      },
      {
        element: <RoleRoute allowedRoles={["EMPLOYEE"]} />,
        children: [
          {
            path: "employee",
            element: <EmployeeLayout />,
            children: [
              {
                index: true,
                element: <Navigate to="dashboard" replace />,
              },
              {
                path: "dashboard",
                element: <EmployeeDashboard />,
              },
              {
                path: "profile",
                element: <MyProfile />,
              },
              {
                path: "attendance",
                element: <AttendanceHistory />,
              },
              {
                path: "holidays",
                element: <HolidayCalendarPage mode="employee" />,
              },
              {
                path: "leaves",
                element: <MyLeaves />,
              },
              {
                path: "leaves/apply",
                element: <ApplyLeave />,
              },
              {
                path: "salary-slips",
                element: <MySalarySlips mode="employee" />,
              },
              {
                path: "documents",
                element: <EmployeeDocuments mode="employee" />,
              },
              {
                path: "notifications",
                element: <NotificationsPage mode="employee" />,
              },
            ],
          },
        ],
      },
    ],
  },
  {
    path: "*",
    element: <NotFoundPage />,
  },
]);
