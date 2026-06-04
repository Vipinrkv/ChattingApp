import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { apiGet } from '../lib/api';
import { useNotifications } from '../hooks/useNotifications';

type Friend = { id: string; username: string };
type Group = { id: string; name: string; description?: string | null; is_member?: boolean; type?: string };
type Post = { id: string; content: string; created_at: string };

function extractTags(posts: Post[]) {
  const counts = new Map<string, number>();
  posts.forEach((post) => {
    for (const match of post.content.matchAll(/#([a-z0-9_]+)/gi)) {
      const tag = `#${match[1].toLowerCase()}`;
      counts.set(tag, (counts.get(tag) ?? 0) + 1);
    }
  });
  return Array.from(counts.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 4)
    .map(([tag]) => tag);
}

export default function RightSidebar() {
  const { notifications, unreadCount } = useNotifications();
  const [friends, setFriends] = useState<Friend[]>([]);
  const [groups, setGroups] = useState<Group[]>([]);
  const [trends, setTrends] = useState<string[]>([]);

  useEffect(() => {
    let isMounted = true;

    void Promise.allSettled([
      apiGet('/api/v1/friends') as Promise<Friend[]>,
      apiGet('/api/v1/groups') as Promise<Group[]>,
      apiGet('/api/v1/posts/search?q=%23&limit=12') as Promise<{ feed: Post[] }>,
    ]).then(([friendResult, groupResult, postResult]) => {
      if (!isMounted) return;
      if (friendResult.status === 'fulfilled') setFriends(friendResult.value);
      if (groupResult.status === 'fulfilled') setGroups(groupResult.value);
      if (postResult.status === 'fulfilled') setTrends(extractTags(postResult.value.feed ?? []));
    });

    return () => {
      isMounted = false;
    };
  }, []);

  const activeGroups = useMemo(() => groups.filter((group) => group.is_member).slice(0, 3), [groups]);
  const discoverGroups = useMemo(() => groups.filter((group) => !group.is_member).slice(0, 3), [groups]);

  return (
    <aside className="right-sidebar" aria-label="Activity and suggestions">
      <section className="rail-panel">
        <div className="rail-header">
          <span className="hero-label">Notifications</span>
          <span className="rail-count">{unreadCount}</span>
        </div>
        <div className="suggestion-list">
          {notifications.slice(0, 3).map((notification) => (
            <div className="suggestion-row" key={notification.id}>
              <div>
                <strong>{notification.type}</strong>
                <small>{notification.text || new Date(notification.timestamp).toLocaleString()}</small>
              </div>
            </div>
          ))}
          {notifications.length === 0 ? <small className="soft-muted">No recent notifications.</small> : null}
        </div>
      </section>

      <section className="rail-panel">
        <span className="hero-label">Trending</span>
        <div className="trend-list">
          {trends.length > 0 ? trends.map((trend) => (
            <Link className="trend-chip" to={`/search?q=${encodeURIComponent(trend)}`} key={trend}>
              {trend}
            </Link>
          )) : <small className="soft-muted">No hashtag activity yet.</small>}
        </div>
      </section>

      <section className="rail-panel">
        <span className="hero-label">Suggested friends</span>
        <div className="active-user-list">
          {friends.slice(0, 3).map((friend) => (
            <Link className="active-user" to="/friends" key={friend.id}>
              <span className="presence-dot online" aria-hidden="true" />
              <div>
                <strong>{friend.username}</strong>
                <small>Friend</small>
              </div>
            </Link>
          ))}
          {friends.length === 0 ? <Link className="mini-button" to="/friends">Find friends</Link> : null}
        </div>
      </section>

      <section className="rail-panel">
        <span className="hero-label">Active groups</span>
        <div className="suggestion-list">
          {(activeGroups.length ? activeGroups : discoverGroups).map((group) => (
            <div className="suggestion-row" key={group.id}>
              <div>
                <strong>{group.name}</strong>
                <small>{group.type || group.description || 'Group'}</small>
              </div>
              <Link className="mini-button" to="/groups">View</Link>
            </div>
          ))}
          {groups.length === 0 ? <small className="soft-muted">No groups available.</small> : null}
        </div>
      </section>
    </aside>
  );
}
