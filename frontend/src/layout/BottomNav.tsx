import { NavLink } from 'react-router-dom';

const items = [
  { label: 'Home', path: '/', icon: 'H' },
  { label: 'Feed', path: '/feed', icon: 'F' },
  { label: 'Chats', path: '/chat', icon: 'M' },
  { label: 'Groups', path: '/groups', icon: 'G' },
  { label: 'Profile', path: '/profile', icon: 'P' },
  { label: 'Settings', path: '/settings', icon: 'S' },
];

export default function BottomNav() {
  return (
    <nav className="bottom-nav" aria-label="Mobile navigation">
      {items.map((it) => (
        <NavLink key={it.path} to={it.path} className={({ isActive }) => (isActive ? 'bn-item active' : 'bn-item')}>
          <span className="bn-icon" aria-hidden="true">{it.icon}</span>
          <span className="bn-label">{it.label}</span>
        </NavLink>
      ))}
    </nav>
  );
}
