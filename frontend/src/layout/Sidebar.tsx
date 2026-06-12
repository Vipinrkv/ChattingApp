import { NavLink } from 'react-router-dom';
import { Avatar } from '../ui/Avatar';
import { useAuth } from '../contexts/AuthContext';

const navItems = [
  { label: 'Dashboard', path: '/', icon: '🏠' },
  { label: 'Feed', path: '/feed', icon: '📰' },
  { label: 'Chat', path: '/chat', icon: '💬' },
  { label: 'Groups', path: '/groups', icon: '👥' },
  { label: 'Friends', path: '/friends', icon: '👤' },
  { label: 'Profile', path: '/profile', icon: '👤' },
  { label: 'Settings', path: '/settings', icon: '⚙️' },
  { label: 'Admin', path: '/admin', icon: '🛡️' },
];

function Sidebar() {
  const { user } = useAuth();

  return (
    <nav className="sidebar-nav" aria-label="Main navigation">
      <div className="brand-block">
        <div className="brand-mark">C</div>
        <div className="brand-text">
          <strong>ChattingApp</strong>
          <div className="brand-sub">Social dashboard</div>
        </div>
      </div>

      <ul className="nav-list">
        {navItems.map((item) => (
          <li key={item.path}>
            <NavLink end className={({ isActive }) => (isActive ? 'nav-item active' : 'nav-item')} to={item.path}>
              <span className="nav-icon" aria-hidden="true">{item.icon}</span>
              <span className="nav-label">{item.label}</span>
            </NavLink>
          </li>
        ))}
      </ul>

      <div className="sidebar-footer">
        <div className="user-summary">
          <Avatar src={user?.photoURL || '/assets/default-avatar.png'} alt={user?.displayName || user?.email || 'me'} />
          <div className="user-meta">
            <div className="user-name">{user?.displayName || user?.email?.split('@')[0] || 'Guest'}</div>
            <div className="user-sub">View profile</div>
          </div>
        </div>
      </div>
    </nav>
  );
}

export default Sidebar;
