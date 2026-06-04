import { FormEvent, useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { apiGet } from '../lib/api';
import { Button } from '../ui/Button';

interface SearchResultUser {
  id: string;
  username: string;
  email?: string | null;
  bio?: string | null;
}

interface SearchResultGroup {
  id: string;
  name: string;
  description?: string | null;
  type: string;
  organization_name?: string | null;
  is_member: boolean;
  membership_status?: string | null;
}

interface SearchResultPost {
  id: string;
  user_id: string;
  content: string;
  visibility: string;
  created_at: string;
}

const RECENT_SEARCH_KEY = 'chattingapp.recentSearches';
const TRENDING_SEARCHES = ['friends', 'events', 'announcements', 'groups', 'popular posts'];

function getQueryParam(search: string) {
  return new URLSearchParams(search).get('q') || '';
}

function uniqueRecentSearches(term: string, existing: string[]) {
  const normalized = term.trim();
  if (!normalized) {
    return existing;
  }

  return [normalized, ...existing.filter((item) => item.toLowerCase() !== normalized.toLowerCase())].slice(0, 8);
}

function Search() {
  const location = useLocation();
  const navigate = useNavigate();
  const initialQuery = useMemo(() => getQueryParam(location.search), [location.search]);
  const [searchTerm, setSearchTerm] = useState(initialQuery);
  const [users, setUsers] = useState<SearchResultUser[]>([]);
  const [groups, setGroups] = useState<SearchResultGroup[]>([]);
  const [posts, setPosts] = useState<SearchResultPost[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recentSearches, setRecentSearches] = useState<string[]>([]);

  useEffect(() => {
    setSearchTerm(initialQuery);
  }, [initialQuery]);

  useEffect(() => {
    const stored = window.localStorage.getItem(RECENT_SEARCH_KEY);
    if (stored) {
      try {
        setRecentSearches(JSON.parse(stored) as string[]);
      } catch {
        setRecentSearches([]);
      }
    }
  }, []);

  useEffect(() => {
    const query = searchTerm.trim();
    if (!query) {
      setUsers([]);
      setGroups([]);
      setPosts([]);
      setError(null);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);

    const timeoutId = window.setTimeout(() => {
      void Promise.all([
        apiGet(`/api/v1/users/search?q=${encodeURIComponent(query)}`),
        apiGet(`/api/v1/groups/search?q=${encodeURIComponent(query)}`),
        apiGet(`/api/v1/posts/search?q=${encodeURIComponent(query)}`),
      ])
        .then(([usersPayload, groupsPayload, postsPayload]) => {
          setUsers(usersPayload as SearchResultUser[]);
          setGroups(groupsPayload as SearchResultGroup[]);
          setPosts((postsPayload as { feed: SearchResultPost[] }).feed || []);
        })
        .catch((err) => {
          setError(err instanceof Error ? err.message : 'Search failed');
          setUsers([]);
          setGroups([]);
          setPosts([]);
        })
        .finally(() => {
          setIsLoading(false);
        });
    }, 250);

    return () => window.clearTimeout(timeoutId);
  }, [searchTerm]);

  const updateRecentSearches = (term: string) => {
    const updated = uniqueRecentSearches(term, recentSearches);
    setRecentSearches(updated);
    window.localStorage.setItem(RECENT_SEARCH_KEY, JSON.stringify(updated));
  };

  const handleSearchSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const query = searchTerm.trim();
    if (!query) {
      return;
    }

    updateRecentSearches(query);
    navigate(`/search?q=${encodeURIComponent(query)}`);
  };

  const handleRecentSearchClick = (term: string) => {
    setSearchTerm(term);
    navigate(`/search?q=${encodeURIComponent(term)}`);
  };

  const handleTrendingClick = (term: string) => {
    setSearchTerm(term);
    navigate(`/search?q=${encodeURIComponent(term)}`);
  };

  return (
    <div className="page-content search-page">
      <div className="page-heading">
        <h1>Search</h1>
        <p>Find users, groups, and feed posts with a single unified search experience.</p>
      </div>

      <form className="search-panel" onSubmit={handleSearchSubmit}>
        <label className="sr-only" htmlFor="global-search-page">Search people, groups, or feed</label>
        <input
          id="global-search-page"
          className="search-input"
          placeholder="Search people, groups, or posts..."
          value={searchTerm}
          onChange={(event) => setSearchTerm(event.target.value)}
          autoComplete="off"
        />
        <Button type="submit" className="search-button">Search</Button>
      </form>

      <div className="search-meta">
        <div>
          <strong>Trending search ideas</strong>
          <div className="pill-list">
            {TRENDING_SEARCHES.map((term) => (
              <button key={term} type="button" className="pill soft" onClick={() => handleTrendingClick(term)}>
                {term}
              </button>
            ))}
          </div>
        </div>
        <div>
          <strong>Recent searches</strong>
          <div className="pill-list">
            {recentSearches.length > 0 ? (
              recentSearches.map((term) => (
                <button key={term} type="button" className="pill soft" onClick={() => handleRecentSearchClick(term)}>
                  {term}
                </button>
              ))
            ) : (
              <span className="muted">No recent searches yet.</span>
            )}
          </div>
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}
      {isLoading && <div className="page-loading">Searching...</div>}

      {!isLoading && !searchTerm.trim() && (
        <div className="search-empty-state">
          <p>Start typing to find people, groups, or posts across the app.</p>
        </div>
      )}

      {!isLoading && searchTerm.trim() && (
        <div className="search-results-grid">
          <section className="search-section">
            <h2>People</h2>
            {users.length > 0 ? (
              <ul className="search-result-list">
                {users.map((user) => (
                  <li key={user.id} className="search-result-item">
                    <strong>{user.username}</strong>
                    <p>{user.bio || user.email || 'No bio available'}</p>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="empty-state">No matching users found.</div>
            )}
          </section>

          <section className="search-section">
            <h2>Groups</h2>
            {groups.length > 0 ? (
              <ul className="search-result-list">
                {groups.map((group) => (
                  <li key={group.id} className="search-result-item">
                    <strong>{group.name}</strong>
                    <p>{group.description || group.organization_name || 'No description available'}</p>
                    <small>{group.is_member ? `Member (${group.membership_status})` : 'Public group'}</small>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="empty-state">No matching groups found.</div>
            )}
          </section>

          <section className="search-section">
            <h2>Posts</h2>
            {posts.length > 0 ? (
              <ul className="search-result-list">
                {posts.map((post) => (
                  <li key={post.id} className="search-result-item">
                    <p>{post.content.length > 180 ? `${post.content.slice(0, 180)}…` : post.content}</p>
                    <small>{new Date(post.created_at).toLocaleString()}</small>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="empty-state">No matching feed posts found.</div>
            )}
          </section>
        </div>
      )}
    </div>
  );
}

export default Search;
