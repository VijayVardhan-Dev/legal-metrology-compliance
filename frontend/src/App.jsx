import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { AuthProvider } from './hooks/useAuth';
import { ProtectedRoute } from './router/ProtectedRoute';
import AppShell from './components/layout/AppShell';
import DashboardPage from './pages/DashboardPage';
import HistoryPage from './pages/HistoryPage';
import InspectionPage from './pages/InspectionPage';
import LoginPage from './pages/LoginPage';
import NewInspectionPage from './pages/NewInspectionPage';
import NutritionPage from './pages/NutritionPage';
import ReportsPage from './pages/ReportsPage';
import SettingsPage from './pages/SettingsPage';

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            element={
              <ProtectedRoute>
                <AppShell />
              </ProtectedRoute>
            }
          >
            <Route index element={<DashboardPage />} />
            <Route path="inspections/new" element={<NewInspectionPage />} />
            <Route path="nutrition" element={<NutritionPage />} />
            <Route path="inspections/:id" element={<InspectionPage />} />
            <Route path="inspections" element={<HistoryPage />} />
            <Route path="reports" element={<ReportsPage />} />
            <Route path="settings" element={<SettingsPage />} />
          </Route>
          <Route path="*" element={<LoginPage />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
