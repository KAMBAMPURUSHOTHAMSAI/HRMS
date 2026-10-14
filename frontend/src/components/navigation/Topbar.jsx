import { Bell, LogOut, UserRound } from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../../hooks/useAuth";

function pageTitle(pathname) {
  const lastPart = pathname.split("/").filter(Boolean).pop() || "dashboard";

  return lastPart
    .replaceAll("-", " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

export default function Topbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  function handleLogout() {
    logout();
    navigate("/login", { replace: true });
  }

  return (
    <header className="topbar">
      <div>
        <div className="topbar-eyebrow">HRMS WORKSPACE</div>
        <h1>{pageTitle(location.pathname)}</h1>
      </div>

      <div className="topbar-actions">
        <button
          className="icon-button"
          type="button"
          aria-label="Notifications"
          onClick={() =>
            navigate(
              user?.roles?.includes("EMPLOYEE")
                ? "/employee/notifications"
                : "/admin/notifications"
            )
          }
        >
          <Bell size={19} />
        </button>

        <div className="user-chip">
          <span className="avatar">
            <UserRound size={18} />
          </span>
          <div className="user-chip-text">
            <strong>
              {user?.first_name} {user?.last_name}
            </strong>
            <small>{user?.roles?.join(", ")}</small>
          </div>
        </div>

        <button
          className="logout-button"
          type="button"
          onClick={handleLogout}
        >
          <LogOut size={17} />
          <span>Logout</span>
        </button>
      </div>
    </header>
  );
}