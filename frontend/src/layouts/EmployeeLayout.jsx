import { Outlet } from "react-router-dom";

import EmployeeSidebar from "../components/navigation/EmployeeSidebar";
import Topbar from "../components/navigation/Topbar";

export default function EmployeeLayout() {
  return (
    <div className="app-shell">
      <EmployeeSidebar />

      <div className="app-main">
        <Topbar />

        <main className="page-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}