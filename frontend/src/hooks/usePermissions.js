import { useAuth } from "./useAuth";

export function usePermissions() {
  const { user } = useAuth();

  const roles = user?.roles ?? [];

  return {
    roles,
    isAdmin: roles.includes("ADMIN"),
    isHR: roles.includes("HR"),
    isEmployee: roles.includes("EMPLOYEE"),
    canManageEmployees:
      roles.includes("ADMIN") || roles.includes("HR"),
    canManagePayroll: roles.includes("ADMIN"),
  };
}