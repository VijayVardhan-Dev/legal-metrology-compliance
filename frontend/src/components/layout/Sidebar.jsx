import { NavLink, useLocation } from 'react-router-dom';

const NAV_ITEMS = [
  { to: '/',             label: 'Dashboard',    icon: '⌂' },
  { to: '/inspections/new', label: 'New inspection', icon: '+' },
  { to: '/nutrition',    label: 'Nutrition',    icon: '✦' },
  { to: '/inspections',  label: 'Inspections',  icon: '≡' },
  { to: '/reports',      label: 'Reports',      icon: '▤' },
];

const NAV_BOTTOM = [
  { to: '/settings',     label: 'Settings',     icon: '⚙' },
];

export default function Sidebar({ open, onClose }) {
  const location = useLocation();

  const isActive = (to) => {
    if (to === '/') return location.pathname === '/';
    return location.pathname.startsWith(to);
  };

  return (
    <>
      <div
        className={`sidebar-backdrop${open ? ' sidebar-open' : ''}`}
        onClick={onClose}
        aria-hidden="true"
      />
      <aside className={`sidebar${open ? ' sidebar-open' : ''}`} role="navigation" aria-label="Main navigation">
        <nav className="sidebar-nav">
          {NAV_ITEMS.map(({ to, label, icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/' || to === '/inspections'}
              className={`nav-item${isActive(to) ? ' active' : ''}`}
              onClick={onClose}
            >
              <span className="nav-item-icon" aria-hidden="true">{icon}</span>
              {label}
            </NavLink>
          ))}
          <div className="sidebar-section">
            {NAV_BOTTOM.map(({ to, label, icon }) => (
              <NavLink
                key={to}
                to={to}
                className={`nav-item${isActive(to) ? ' active' : ''}`}
                onClick={onClose}
              >
                <span className="nav-item-icon" aria-hidden="true">{icon}</span>
                {label}
              </NavLink>
            ))}
          </div>
        </nav>
      </aside>
    </>
  );
}
