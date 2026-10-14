import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

export default function RoleRoute({ allowedRoles }) {
  const { user } = useAuth();

  const roles = user?.roles ?? [];
  const permitted = roles.some((role) =>
    allowedRoles.includes(role)
  );

  if (!permitted) {
    const target = roles.includes("EMPLOYEE")
      ? "/employee/dashboard"
      : "/admin/dashboard";

    return <Navigate to={target} replace />;
  }

  return <Outlet />;
}