import React, { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../ui/theme';
import { Avatar } from '../ui/Avatar';
import { Button } from '../ui/Button';
import NotificationDropdown from '../ui/NotificationDropdown';
import Modal from '../ui/Modal';

function Topbar() {
  const navigate = useNavigate();
  const location = useLocation();
  const { logout, user } = useAuth();
  const themeCtx = useTheme();
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearchOpen, setIsSearchOpen] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    setSearchQuery(params.get('q') || '');
  }, [location.search]);

  const handleSignOut = async () => {
    await logout();
    navigate('/login');
  };

  const toggle = () => {
    themeCtx.toggle();
  };

  const handleSearchSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = searchQuery.trim();
    if (trimmed) {
      navigate(`/search?q=${encodeURIComponent(trimmed)}`);
    }
  };

  const handleMobileSearchSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = searchQuery.trim();
    if (trimmed) {
      setIsSearchOpen(false);
      navigate(`/search?q=${encodeURIComponent(trimmed)}`);
    }
  };

  return (
    <header className="topbar" role="banner">
      <div className="topbar-left" aria-hidden="true">
        <div className="brand-mark">C</div>
        <div className="brand-text">
          <strong>ChattingApp</strong>
          <div className="brand-sub">Social dashboard</div>
        </div>
      </div>

      <div className="topbar-center">
        <form className="topbar-search-form" onSubmit={handleSearchSubmit}>
          <label className="sr-only" htmlFor="global-search">Search</label>
          <input
            id="global-search"
            className="topbar-search"
            placeholder="Search people, messages, posts..."
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
            autoComplete="off"
          />
        </form>
        <button className="icon-btn mobile-search-trigger" type="button" onClick={() => setIsSearchOpen(true)} aria-label="Open search">
          🔍
        </button>
      </div>

      <div className="topbar-actions">
        <Button variant="ghost" onClick={toggle} aria-label="Toggle theme">
          {themeCtx.theme === 'dark' ? 'Light mode' : 'Dark mode'}
        </Button>

        <NotificationDropdown />

        <div className="user-block">
          <Avatar src={user?.photoURL || '/assets/default-avatar.png'} alt={user?.displayName || user?.email || 'me'} size={36} />
          <button className="ghost-link" onClick={handleSignOut} aria-label="Sign out">Sign out</button>
        </div>
      </div>

      <Modal title="Search ChattingApp" isOpen={isSearchOpen} onClose={() => setIsSearchOpen(false)}>
        <form className="mobile-search-sheet" onSubmit={handleMobileSearchSubmit}>
          <label htmlFor="mobile-global-search">Search users, friends, groups, and posts</label>
          <input
            id="mobile-global-search"
            autoFocus
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
            placeholder="Search everything..."
          />
          <div className="search-scope-grid" aria-label="Search scopes">
            <span>Users</span>
            <span>Friends</span>
            <span>Groups</span>
            <span>Posts</span>
          </div>
          <button className="primary-button" type="submit">Search</button>
        </form>
      </Modal>
    </header>
  );
}

export default Topbar;
