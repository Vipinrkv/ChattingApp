import { FormEvent, useEffect, useMemo, useState } from 'react';
import { apiGet, apiPost } from '../lib/api';

interface UserResult {
  id: string;
  username: string;
  email?: string | null;
  bio?: string | null;
}

interface FriendRequest {
  id: string;
  requester_id: string;
  addressee_id: string;
  status: string;
  created_at: string;
  requester_username?: string | null;
}

type RequestStatus = 'idle' | 'pending' | 'accepted' | 'rejected' | 'blocked';

const NICKNAME_KEY = 'chattingapp.friendNicknames';
const LOCAL_REQUEST_KEY = 'chattingapp.friendRequestDrafts';

function readJsonRecord<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) as T : fallback;
  } catch {
    return fallback;
  }
}

function Friends() {
  const [friends, setFriends] = useState<UserResult[]>([]);
  const [requests, setRequests] = useState<FriendRequest[]>([]);
  const [query, setQuery] = useState('');
  const [message, setMessage] = useState('');
  const [results, setResults] = useState<UserResult[]>([]);
  const [statusByUserId, setStatusByUserId] = useState<Record<string, RequestStatus>>(() =>
    readJsonRecord<Record<string, RequestStatus>>(LOCAL_REQUEST_KEY, {}),
  );
  const [nicknames, setNicknames] = useState<Record<string, string>>(() =>
    readJsonRecord<Record<string, string>>(NICKNAME_KEY, {}),
  );
  const [feedback, setFeedback] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    localStorage.setItem(LOCAL_REQUEST_KEY, JSON.stringify(statusByUserId));
  }, [statusByUserId]);

  useEffect(() => {
    localStorage.setItem(NICKNAME_KEY, JSON.stringify(nicknames));
  }, [nicknames]);

  const refresh = async () => {
    setLoading(true);
    setFeedback('');
    try {
      const [friendPayload, requestPayload] = await Promise.all([
        apiGet('/api/v1/friends') as Promise<UserResult[]>,
        apiGet('/api/v1/friends/requests') as Promise<FriendRequest[]>,
      ]);
      setFriends(friendPayload);
      setRequests(requestPayload);
      setStatusByUserId((prev) => {
        const next = { ...prev };
        friendPayload.forEach((friend) => {
          next[friend.id] = 'accepted';
        });
        requestPayload.forEach((request) => {
          next[request.requester_id] = request.status === 'pending' ? 'pending' : next[request.requester_id] ?? 'idle';
        });
        return next;
      });
    } catch (err) {
      setFeedback(err instanceof Error ? err.message : 'Could not load friends');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refresh();
  }, []);

  const friendIds = useMemo(() => new Set(friends.map((friend) => friend.id)), [friends]);

  const handleSearch = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) return;

    setFeedback('');
    try {
      setResults(await apiGet(`/api/v1/users/search?q=${encodeURIComponent(trimmed)}`) as UserResult[]);
    } catch (err) {
      setFeedback(err instanceof Error ? err.message : 'Could not search users');
    }
  };

  const sendRequest = async (userId: string) => {
    if (statusByUserId[userId] === 'blocked') {
      setFeedback('This user is blocked. Unblock them before sending another request.');
      return;
    }

    setStatusByUserId((prev) => ({ ...prev, [userId]: 'pending' }));
    setFeedback(message.trim() ? `Request note saved locally: ${message.trim()}` : 'Friend request sent.');
    try {
      await apiPost(`/api/v1/friends/requests/${userId}`, {});
      setMessage('');
    } catch (err) {
      setStatusByUserId((prev) => ({ ...prev, [userId]: 'idle' }));
      setFeedback(err instanceof Error ? err.message : 'Could not send request');
    }
  };

  const respondToRequest = async (request: FriendRequest, action: 'accept' | 'reject') => {
    try {
      await apiPost(`/api/v1/friends/requests/${request.id}/respond`, { action });
      setStatusByUserId((prev) => ({ ...prev, [request.requester_id]: action === 'accept' ? 'accepted' : 'rejected' }));
      await refresh();
    } catch (err) {
      setFeedback(err instanceof Error ? err.message : 'Could not update request');
    }
  };

  const blockLocally = (userId: string) => {
    setStatusByUserId((prev) => ({ ...prev, [userId]: 'blocked' }));
    setFeedback('Blocked locally. They will not appear as chat-ready in this browser.');
  };

  const inviteLink = `${window.location.origin}/register?invite=friend`;

  return (
    <div className="page-panel glass-panel friends-page">
      <div className="panel-header">
        <div>
          <span className="hero-label">Friends</span>
          <h2>Add friends</h2>
          <p className="small-note">Find people, manage requests, add local nicknames, or share an invite link.</p>
        </div>
        <button className="ghost-button" type="button" onClick={() => void refresh()} disabled={loading}>
          {loading ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      {feedback ? <div className="success-message" role="status">{feedback}</div> : null}

      <div className="friends-grid">
        <section className="glass-panel friends-panel">
          <h3>Find by username or email</h3>
          <form className="friend-search-form" onSubmit={handleSearch}>
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search username or email" />
            <input value={message} onChange={(event) => setMessage(event.target.value)} placeholder="Optional request message" />
            <button className="primary-button" type="submit">Search</button>
          </form>

          <div className="friend-method-grid">
            <div className="friend-method-card">
              <strong>Invite link / QR source</strong>
              <input readOnly value={inviteLink} aria-label="Invite link" />
              <p className="small-note">Use this link in any QR generator or share it directly.</p>
            </div>
            <div className="friend-method-card">
              <strong>Nearby discovery</strong>
              <p className="small-note">Optional discovery only. Location is never requested unless you choose it.</p>
            </div>
          </div>

          <div className="friend-result-list">
            {results.map((result) => {
              const status = friendIds.has(result.id) ? 'accepted' : statusByUserId[result.id] ?? 'idle';
              return (
                <article className="friend-card" key={result.id}>
                  <div>
                    <strong>{result.username}</strong>
                    <p>{result.bio || result.email || 'No profile details yet.'}</p>
                    <span className={`pill ${status === 'accepted' ? 'success' : 'soft'}`}>{status}</span>
                  </div>
                  <div className="friend-card-actions">
                    <button
                      className="primary-button"
                      type="button"
                      disabled={status === 'pending' || status === 'accepted' || status === 'blocked'}
                      onClick={() => void sendRequest(result.id)}
                    >
                      {status === 'rejected' ? 'Request again' : 'Add friend'}
                    </button>
                    <button className="ghost-button" type="button" onClick={() => blockLocally(result.id)}>Block</button>
                  </div>
                </article>
              );
            })}
          </div>
        </section>

        <section className="glass-panel friends-panel">
          <h3>My friends</h3>
          {friends.length === 0 ? <p className="small-note">Accepted friends will appear here.</p> : null}
          <div className="friend-result-list">
            {friends.map((friend) => (
              <article className="friend-card" key={friend.id}>
                <div>
                  <strong>{nicknames[friend.id] || friend.username}</strong>
                  {nicknames[friend.id] ? <p className="small-note">Real profile: {friend.username}</p> : null}
                </div>
                <input
                  value={nicknames[friend.id] ?? ''}
                  placeholder="Local nickname"
                  onChange={(event) => setNicknames((prev) => ({ ...prev, [friend.id]: event.target.value }))}
                />
              </article>
            ))}
          </div>
        </section>

        <section className="glass-panel friends-panel">
          <h3>Friend requests</h3>
          {requests.length === 0 ? <p className="small-note">No pending requests.</p> : null}
          <div className="friend-result-list">
            {requests.map((request) => (
              <article className="friend-card" key={request.id}>
                <div>
                  <strong>Request from @{request.requester_username || request.requester_id}</strong>
                  <p className="small-note">Received {new Date(request.created_at).toLocaleString()}</p>
                </div>
                <div className="friend-card-actions">
                  <button className="primary-button" type="button" onClick={() => void respondToRequest(request, 'accept')}>Accept</button>
                  <button className="secondary-button" type="button" onClick={() => void respondToRequest(request, 'reject')}>Reject</button>
                  <button className="ghost-button" type="button" onClick={() => blockLocally(request.requester_id)}>Block</button>
                </div>
              </article>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

export default Friends;
