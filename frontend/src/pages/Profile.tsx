import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from 'react';
import { apiDelete, apiGet, apiPost, apiPut } from '../lib/api';
import { useAuth } from '../contexts/AuthContext';
import { Badge, Tabs } from '../ui';

type UserProfile = {
  id: string;
  firebase_uid: string;
  username: string;
  email?: string | null;
  bio?: string | null;
};

type LocalProfile = {
  avatarUrl: string;
  bannerUrl: string;
  displayName: string;
  links: Array<{ label: string; url: string }>;
  activityStatus: 'online' | 'busy' | 'away' | 'offline';
  privacy: {
    profileVisibility: 'public' | 'friends' | 'private' | 'anonymous';
    showActivity: boolean;
    allowMessages: boolean;
  };
  savedPosts: Array<{ id: string; title: string; savedAt: string }>;
  drafts: Array<{ id: string; content: string; updatedAt: string }>;
};

const LOCAL_PROFILE_KEY = 'chattingapp:user-features';

const defaultLocalProfile: LocalProfile = {
  avatarUrl: '',
  bannerUrl: '',
  displayName: '',
  links: [{ label: 'Portfolio', url: '' }],
  activityStatus: 'online',
  privacy: {
    profileVisibility: 'public',
    showActivity: true,
    allowMessages: true,
  },
  savedPosts: [],
  drafts: [],
};

function readLocalProfile(): LocalProfile {
  try {
    const raw = localStorage.getItem(LOCAL_PROFILE_KEY);
    if (!raw) return defaultLocalProfile;
    return { ...defaultLocalProfile, ...JSON.parse(raw) };
  } catch {
    return defaultLocalProfile;
  }
}

function fileToDataUrl(file: File) {
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result ?? ''));
    reader.onerror = () => reject(new Error('Could not read selected file'));
    reader.readAsDataURL(file);
  });
}

function Profile() {
  const { user } = useAuth();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [localProfile, setLocalProfile] = useState<LocalProfile>(() => readLocalProfile());
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [bio, setBio] = useState('');
  const [newDraft, setNewDraft] = useState('');
  const [blockSearch, setBlockSearch] = useState('');
  const [userResults, setUserResults] = useState<UserProfile[]>([]);
  const [blockedUsers, setBlockedUsers] = useState<UserProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    // Don't store large image data URLs in localStorage - only store non-image data
    const { avatarUrl, bannerUrl, ...rest } = localProfile;
    try {
      localStorage.setItem(LOCAL_PROFILE_KEY, JSON.stringify(rest));
    } catch (err) {
      // If quota exceeded, just warn and skip saving
      console.warn('Could not save profile to localStorage:', err);
    }
  }, [localProfile]);

  useEffect(() => {
    let isMounted = true;

    (async () => {
      try {
        setLoading(true);
        const [me, blocked] = await Promise.all([
          apiGet('/api/v1/users/me') as Promise<UserProfile>,
          apiGet('/api/v1/blocks') as Promise<UserProfile[]>,
        ]);
        if (!isMounted) return;
        setProfile(me);
        setUsername(me.username ?? '');
        setEmail(me.email ?? user?.email ?? '');
        setBio(me.bio ?? '');
        setBlockedUsers(blocked ?? []);
        setLocalProfile((prev) => ({
          ...prev,
          displayName: prev.displayName || me.username || user?.displayName || '',
        }));
      } catch (err) {
        if (!isMounted) return;
        setError(err instanceof Error ? err.message : 'Could not load profile');
      } finally {
        if (isMounted) setLoading(false);
      }
    })();

    return () => {
      isMounted = false;
    };
  }, [user]);

  const initials = useMemo(() => {
    const name = localProfile.displayName || username || user?.email || 'User';
    return name.slice(0, 1).toUpperCase();
  }, [localProfile.displayName, username, user?.email]);

  const publicProfileName = localProfile.privacy.profileVisibility === 'anonymous'
    ? 'Anonymous member'
    : localProfile.displayName || username || 'Profile';

  const visibilityExplainer = {
    public: 'Public profiles are discoverable and can show avatar, bio, mutual context, groups, and allowed posts.',
    friends: 'Friends-only profiles show richer details to accepted friends and a limited preview to everyone else.',
    private: 'Private profiles restrict discovery and show only minimal account signals.',
    anonymous: 'Anonymous mode shows a minimal identity publicly while keeping your real profile visible in account settings.',
  }[localProfile.privacy.profileVisibility];

  const updateLocal = (patch: Partial<LocalProfile>) => {
    setLocalProfile((prev) => ({ ...prev, ...patch }));
  };

  const handleAssetUpload = async (event: ChangeEvent<HTMLInputElement>, target: 'avatarUrl' | 'bannerUrl') => {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      const dataUrl = await fileToDataUrl(file);
      updateLocal({ [target]: dataUrl });
      setMessage(target === 'avatarUrl' ? 'Profile photo updated' : 'Banner updated');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      // Add null check for event.currentTarget
      if (event.currentTarget) {
        event.currentTarget.value = '';
      }
    }
  };

  const handleProfileSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!profile) return;

    try {
      setError('');
      const updated = (await apiPut(`/api/v1/users/${profile.id}`, {
        username,
        email,
        bio,
      })) as UserProfile;
      setProfile(updated);
      setMessage('Profile changes saved');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save profile');
    }
  };

  const addDraft = () => {
    const content = newDraft.trim();
    if (!content) return;
    updateLocal({
      drafts: [
        { id: crypto.randomUUID(), content, updatedAt: new Date().toISOString() },
        ...localProfile.drafts,
      ],
    });
    setNewDraft('');
    setMessage('Draft saved');
  };

  const addSavedProfileSnapshot = () => {
    updateLocal({
      savedPosts: [
        {
          id: crypto.randomUUID(),
          title: `Profile snapshot saved ${new Date().toLocaleDateString()}`,
          savedAt: new Date().toISOString(),
        },
        ...localProfile.savedPosts,
      ],
    });
  };

  const searchUsersToBlock = async () => {
    const query = blockSearch.trim();
    if (!query) return;
    try {
      setUserResults((await apiGet(`/api/v1/users/search?q=${encodeURIComponent(query)}`)) as UserProfile[]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not search users');
    }
  };

  const blockUser = async (target: UserProfile) => {
    try {
      await apiPost(`/api/v1/blocks/${target.id}`, {});
      setBlockedUsers((prev) => (prev.some((item) => item.id === target.id) ? prev : [target, ...prev]));
      setMessage(`${target.username} blocked`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not block user');
    }
  };

  const unblockUser = async (target: UserProfile) => {
    try {
      await apiDelete(`/api/v1/blocks/${target.id}`);
      setBlockedUsers((prev) => prev.filter((item) => item.id !== target.id));
      setMessage(`${target.username} unblocked`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not unblock user');
    }
  };

  return (
    <div className="page-panel glass-panel profile-page">
      <div className="panel-header">
        <div>
          <span className="hero-label">Profile</span>
          <h2>Account hub</h2>
        </div>
        <Badge tone={localProfile.activityStatus === 'online' ? 'success' : 'neutral'}>
          {localProfile.activityStatus}
        </Badge>
      </div>

      {loading ? <div className="page-loading">Loading profile...</div> : null}
      {error ? <div className="error-message">{error}</div> : null}
      {message ? <div className="success-message">{message}</div> : null}

      <div className="profile-hero">
        <div className="profile-banner">
          {localProfile.bannerUrl && (
            <img
              src={localProfile.bannerUrl}
              alt="Banner"
              className="profile-banner-image"
            />
          )}
        </div>
        <div className="profile-identity">
          <div className="avatar-shell profile-avatar">
            {localProfile.avatarUrl ? <img src={localProfile.avatarUrl} alt="Profile" /> : initials}
          </div>
          <div>
            <h3>{publicProfileName}</h3>
            <p>@{localProfile.privacy.profileVisibility === 'anonymous' ? 'anonymous' : username || 'username'}</p>
          </div>
        </div>
      </div>

      <section className="profile-stats-grid">
        <div className="profile-stat-column">
          <span className="stat-label-hero">Mutual Friends</span>
          <span className="stat-value-bold">Visible</span>
          <small className="stat-desc-muted">When permitted by peers</small>
        </div>
        <div className="profile-stat-column">
          <span className="stat-label-hero">Groups Visibility</span>
          <span className="stat-value-bold">
            {localProfile.privacy.profileVisibility === 'private' ? 'Restricted' : 'Previewable'}
          </span>
          <small className="stat-desc-muted">Based on privacy level</small>
        </div>
        <div className="profile-stat-column">
          <span className="stat-label-hero">Feed Visibility</span>
          <span className="stat-value-bold">Controlled</span>
          <small className="stat-desc-muted">Follows post settings</small>
        </div>
      </section>

      <Tabs
        ariaLabel="Profile sections"
        items={[
          {
            id: 'profile',
            label: 'Profile',
            content: (
              <form className="profile-edit glass-panel" onSubmit={handleProfileSubmit}>
                <h3>Profile editing</h3>
                <label>
                  Display name
                  <input
                    value={localProfile.displayName}
                    onChange={(event) => updateLocal({ displayName: event.target.value })}
                    placeholder="Public display name"
                  />
                </label>
                <label>
                  Username
                  <input value={username} onChange={(event) => setUsername(event.target.value)} />
                </label>
                <label>
                  Bio
                  <textarea value={bio} onChange={(event) => setBio(event.target.value)} />
                </label>
                <div className="profile-upload-grid">
                  <label className="upload-tile">
                    Profile photo
                    <input type="file" accept="image/*" onChange={(event) => void handleAssetUpload(event, 'avatarUrl')} />
                  </label>
                  <label className="upload-tile">
                    Banner image
                    <input type="file" accept="image/*" onChange={(event) => void handleAssetUpload(event, 'bannerUrl')} />
                  </label>
                </div>
                <button className="primary-button" type="submit">Save profile</button>
              </form>
            ),
          },
          {
            id: 'links',
            label: 'Links',
            content: (
              <section className="profile-edit glass-panel">
                <h3>Bio and social links</h3>
                {localProfile.links.map((link, index) => (
                  <div className="settings-row" key={index}>
                    <input
                      value={link.label}
                      placeholder="Label"
                      onChange={(event) => {
                        const links = [...localProfile.links];
                        links[index] = { ...links[index], label: event.target.value };
                        updateLocal({ links });
                      }}
                    />
                    <input
                      value={link.url}
                      placeholder="https://..."
                      onChange={(event) => {
                        const links = [...localProfile.links];
                        links[index] = { ...links[index], url: event.target.value };
                        updateLocal({ links });
                      }}
                    />
                  </div>
                ))}
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => updateLocal({ links: [...localProfile.links, { label: '', url: '' }] })}
                >
                  Add link
                </button>
              </section>
            ),
          },
          {
            id: 'account',
            label: 'Account',
            content: (
              <section className="profile-edit glass-panel">
                <h3>Account settings</h3>
                <label>
                  Email
                  <input value={email} onChange={(event) => setEmail(event.target.value)} />
                </label>
                <label>
                  Activity status
                  <select
                    value={localProfile.activityStatus}
                    onChange={(event) =>
                      updateLocal({ activityStatus: event.target.value as LocalProfile['activityStatus'] })
                    }
                  >
                    <option value="online">Online</option>
                    <option value="busy">Busy</option>
                    <option value="away">Away</option>
                    <option value="offline">Offline</option>
                  </select>
                </label>
              </section>
            ),
          },
          {
            id: 'privacy',
            label: 'Privacy',
            content: (
              <section className="profile-edit glass-panel">
                <h3>Privacy settings</h3>
                <label>
                  Profile visibility
                  <div className="privacy-selector" role="radiogroup" aria-label="Profile visibility">
                    {(['public', 'friends', 'private', 'anonymous'] as const).map((mode) => (
                      <button
                        key={mode}
                        type="button"
                        role="radio"
                        aria-checked={localProfile.privacy.profileVisibility === mode}
                        className={localProfile.privacy.profileVisibility === mode ? 'secondary-button active' : 'ghost-button'}
                        onClick={() =>
                          updateLocal({
                            privacy: {
                              ...localProfile.privacy,
                              profileVisibility: mode,
                            },
                          })
                        }
                      >
                        {mode[0].toUpperCase() + mode.slice(1)}
                      </button>
                    ))}
                  </div>
                </label>
                <p className="privacy-explainer">{visibilityExplainer}</p>
                <div className="security-trust-advisory glass-panel">
                  <h4>🛡️ Security & Trust Advisor</h4>
                  <p className="small-note">Ensure your profile settings align with your personal privacy goals:</p>
                  <ul className="security-checklist-ul">
                    <li>
                      <span className="check-bullet">✓</span>
                      <span><strong>Visibility Guard:</strong> "{localProfile.privacy.profileVisibility}" mode is active. {
                        localProfile.privacy.profileVisibility === 'anonymous' ? 'Your real name is hidden from peer discoverability.' :
                        localProfile.privacy.profileVisibility === 'private' ? 'Search listings will exclude your account details.' :
                        localProfile.privacy.profileVisibility === 'friends' ? 'Only verified friends see rich bio content.' :
                        'Your account profile is open to all users.'
                      }</span>
                    </li>
                    <li>
                      <span className="check-bullet">✓</span>
                      <span><strong>Activity Signals:</strong> Currently {localProfile.privacy.showActivity ? 'sharing status' : 'hiding status'}. {
                        localProfile.privacy.showActivity ? 'Peers see when you are online/busy/away.' : 'Your active status remains completely hidden.'
                      }</span>
                    </li>
                    <li>
                      <span className="check-bullet">✓</span>
                      <span><strong>Inbound Message Security:</strong> {
                        localProfile.privacy.allowMessages ? 'Open to receive new messages from non-friends.' : 'Restricted. Incoming chats from stranger accounts will be blocked.'
                      }</span>
                    </li>
                  </ul>
                </div>
                <label className="toggle-row">
                  <input
                    type="checkbox"
                    checked={localProfile.privacy.showActivity}
                    onChange={(event) =>
                      updateLocal({ privacy: { ...localProfile.privacy, showActivity: event.target.checked } })
                    }
                  />
                  Show activity status
                </label>
                <label className="toggle-row">
                  <input
                    type="checkbox"
                    checked={localProfile.privacy.allowMessages}
                    onChange={(event) =>
                      updateLocal({ privacy: { ...localProfile.privacy, allowMessages: event.target.checked } })
                    }
                  />
                  Allow new messages
                </label>
              </section>
            ),
          },
          {
            id: 'saved',
            label: 'Saved',
            content: (
              <section className="profile-edit glass-panel">
                <h3>Saved posts and drafts</h3>
                <button className="secondary-button" type="button" onClick={addSavedProfileSnapshot}>Save profile snapshot</button>
                <div className="settings-list">
                  {localProfile.savedPosts.length === 0 ? <p>No saved posts yet.</p> : null}
                  {localProfile.savedPosts.map((post) => (
                    <div className="settings-row" key={post.id}>
                      <span>{post.title}</span>
                      <button
                        className="ghost-button"
                        type="button"
                        onClick={() =>
                          updateLocal({ savedPosts: localProfile.savedPosts.filter((item) => item.id !== post.id) })
                        }
                      >
                        Remove
                      </button>
                    </div>
                  ))}
                </div>
                <div className="draft-composer">
                  <textarea
                    value={newDraft}
                    onChange={(event) => setNewDraft(event.target.value)}
                    placeholder="Draft a post..."
                  />
                  <button className="primary-button" type="button" onClick={addDraft}>Save draft</button>
                </div>
                <div className="settings-list">
                  {localProfile.drafts.map((draft) => (
                    <div className="draft-card" key={draft.id}>
                      <p>{draft.content}</p>
                      <small>{new Date(draft.updatedAt).toLocaleString()}</small>
                    </div>
                  ))}
                </div>
              </section>
            ),
          },
          {
            id: 'blocks',
            label: 'Blocks',
            content: (
              <section className="profile-edit glass-panel">
                <h3>Block management</h3>
                <form
                  className="settings-row"
                  onSubmit={(event) => {
                    event.preventDefault();
                    void searchUsersToBlock();
                  }}
                >
                  <input value={blockSearch} onChange={(event) => setBlockSearch(event.target.value)} placeholder="Search users" />
                  <button className="secondary-button" type="submit">Search</button>
                </form>
                <div className="settings-list">
                  {userResults.map((result) => (
                    <div className="settings-row" key={result.id}>
                      <span>{result.username}</span>
                      <button className="ghost-button" type="button" onClick={() => void blockUser(result)}>Block</button>
                    </div>
                  ))}
                </div>
                <h4>Blocked users</h4>
                <div className="settings-list">
                  {blockedUsers.length === 0 ? <p>No blocked users.</p> : null}
                  {blockedUsers.map((blocked) => (
                    <div className="settings-row" key={blocked.id}>
                      <span>{blocked.username}</span>
                      <button className="ghost-button" type="button" onClick={() => void unblockUser(blocked)}>Unblock</button>
                    </div>
                  ))}
                </div>
              </section>
            ),
          },
        ]}
      />
    </div>
  );
}

export default Profile;
