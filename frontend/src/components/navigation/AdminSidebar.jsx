
import {
  LayoutDashboard,
  Users,
  Building2,
  BriefcaseBusiness,
  ShieldCheck,
  CalendarCheck,
  CalendarDays,
  Wallet,
  Bell,
  FileBarChart,
  ScrollText,
} from "lucide-react";

import { NavLink } from "react-router-dom";

const links = [
  {
    to: "/admin/dashboard",
    label: "Dashboard",
    icon: LayoutDashboard,
  },
  {
    to: "/admin/employees",
    label: "Employees",
    icon: Users,
  },
  {
    to: "/admin/departments",
    label: "Departments",
    icon: Building2,
  },
  {
    to: "/admin/designations",
    label: "Designations",
    icon: BriefcaseBusiness,
  },
  {
    to: "/admin/roles",
    label: "Roles & Permissions",
    icon: ShieldCheck,
  },
  {
    to: "/admin/attendance",
    label: "Attendance",
    icon: CalendarCheck,
  },
  {
    to: "/admin/leave-types",
    label: "Leave Types",
    icon: CalendarDays,
  },
  {
    to: "/admin/leaves",
    label: "Leave Management",
    icon: CalendarDays,
  },
  {
    to: "/admin/payroll",
    label: "Payroll",
    icon: Wallet,
  },
  {
    to: "/admin/notifications",
    label: "Notifications",
    icon: Bell,
  },
  {
    to: "/admin/reports",
    label: "Reports",
    icon: FileBarChart,
  },
  {
    to: "/admin/audit-logs",
    label: "Audit Logs",
    icon: ScrollText,
  },
];

export default function AdminSidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <span className="brand-mark">H</span>
        <div>
          <strong>HRMS</strong>
          <small>Management Portal</small>
        </div>
      </div>

      <div className="sidebar-label">WORKSPACE</div>

      <nav className="sidebar-nav">
        {links.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `sidebar-link ${isActive ? "active" : ""}`
            }
          >
            <Icon size={19} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        <span className="status-dot" />
        System workspace
      </div>
    </aside>
  );
}
