import { useState, useCallback } from 'react';
import { Outlet } from 'react-router-dom';
import Topbar from './Topbar';
import Sidebar from './Sidebar';

export default function AppShell() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const toggleSidebar = useCallback(() => {
    setSidebarOpen(prev => !prev);
  }, []);

  const closeSidebar = useCallback(() => {
    setSidebarOpen(false);
  }, []);

  return (
    <div className="app-shell">
      <Topbar onToggleSidebar={toggleSidebar} />
      <div className="app-body">
        <Sidebar open={sidebarOpen} onClose={closeSidebar} />
        <main className="main-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
