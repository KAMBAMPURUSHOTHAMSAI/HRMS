
import {
  LayoutDashboard,
  UserRound,
  Clock,
  CalendarDays,
  ReceiptText,
  Bell,
} from "lucide-react";

import { NavLink } from "react-router-dom";

const links = [
  {
    to: "/employee/dashboard",
    label: "Dashboard",
    icon: LayoutDashboard,
  },
  {
    to: "/employee/profile",
    label: "My Profile",
    icon: UserRound,
  },
  {
    to: "/employee/attendance",
    label: "Attendance",
    icon: Clock,
  },
  {
    to: "/employee/holidays",
    label: "Holiday Calendar",
    icon: CalendarDays,
  },
  {
    to: "/employee/leaves",
    label: "My Leaves",
    icon: CalendarDays,
  },
  {
    to: "/employee/salary-slips",
    label: "Salary Slips",
    icon: ReceiptText,
  },
  {
    to: "/employee/notifications",
    label: "Notifications",
    icon: Bell,
  },
];

export default function EmployeeSidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <span className="brand-mark">H</span>
        <div>
          <strong>HRMS</strong>
          <small>Employee Portal</small>
        </div>
      </div>

      <div className="sidebar-label">MY WORKSPACE</div>

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
        Employee workspace
      </div>
    </aside>
  );
}
