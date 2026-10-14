import { Outlet } from "react-router-dom";

import AdminSidebar from "../components/navigation/AdminSidebar";
import Topbar from "../components/navigation/Topbar";

export default function AdminLayout() {
  return (
    <div className="app-shell">
      <AdminSidebar />

      <div className="app-main">
        <Topbar />

        <main className="page-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}