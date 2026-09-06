import { useAuth } from '../hooks/useAuth';
import { formatDate } from '../utils/format';
import PageHeader from '../components/ui/PageHeader';

export default function SettingsPage() {
  const { user, logout } = useAuth();

  return (
    <>
      <PageHeader eyebrow="WORKSPACE" title="Settings" />

      <section className="card settings-container">
        <div className="settings-section">
          <p className="eyebrow">PROFILE</p>
          <h2>{user?.email}</h2>
          <p>
            Role: {user?.role || '—'} · Account created {formatDate(user?.created_at)}
          </p>
        </div>

        <div className="settings-section">
          <p className="eyebrow">SESSION</p>
          <p>Sign out of your current workspace session.</p>
          <button className="btn" onClick={logout}>
            Log out
          </button>
        </div>
      </section>
    </>
  );
}
