import { Link } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';

export default function Topbar({ onToggleSidebar }) {
  const { user, logout } = useAuth();

  return (
    <header className="topbar">
      <button
        className="topbar-mobile-toggle"
        onClick={onToggleSidebar}
        aria-label="Toggle navigation"
      >
        ☰
      </button>

      <Link to="/" className="brand" aria-label="Legal Metrology home">
        <span className="brand-mark" aria-hidden="true">LM</span>
        <span>LEGAL METROLOGY</span>
      </Link>

      <div className="topbar-right">
        <span className="topbar-user">{user?.email}</span>
        <button className="btn btn-ghost btn-sm" onClick={logout}>
          Log out
        </button>
      </div>
    </header>
  );
}
