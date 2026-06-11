/* eslint-disable react/no-unescaped-entities */
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { apiGet, apiPatch, apiPost } from '../lib/api';
import { useAuth } from '../contexts/AuthContext';
import { useGroupWebSocket } from '../hooks/useGroupWebSocket';
import { useModal } from '../hooks';
import { useLoadingError } from '../hooks';
import { useGroupStore } from '../stores';
import { useRenderCount } from '../hooks/useRenderCount';
import { ConfirmationDialog } from '../ui';
import VirtualizedList from '../ui/VirtualizedList';
import { displayMessageContent, isEncryptedToken } from '../lib/messageContent';
import ReconnectBanner from '../components/ReconnectBanner';

type GroupType = 'public' | 'private' | 'anonymous' | 'organization';

interface GroupCreatePayload {
  name: string;
  description?: string | null;
  type: GroupType;
  organization_name?: string | null;
  category?: string | null;
  tags?: string[];
  is_discoverable?: boolean;
  announcement_only?: boolean;
  template_key?: string | null;
  growth_goal?: number;
}

interface GroupResponse {
  id: string;
  name: string;
  description?: string | null;
  type: GroupType;
  organization_name?: string | null;
  category?: string | null;
  tags: string[];
  is_discoverable: boolean;
  is_verified: boolean;
  verification_status: string;
  announcement_only: boolean;
  template_key?: string | null;
  onboarding_steps: Array<{ title?: string; body?: string }>;
  welcome_message?: string | null;
  growth_goal: number;
  created_by: string;
  created_at: string;
}

interface GroupListResponse extends GroupResponse {
  is_member: boolean;
  membership_status?: string | null;
  member_count: number;
  message_count: number;
  event_count: number;
  discovery_score: number;
}

interface GroupMessageResponse {
  id: string;
  sender_id?: string | null;
  sender_alias?: string | null;
  group_id: string;
  content: string;
  timestamp: string;
}

interface GroupTemplateResponse {
  key: string;
  name: string;
  description: string;
  category: string;
  tags: string[];
  welcome_message: string;
  growth_goal: number;
}

interface GroupEventResponse {
  id: string;
  group_id: string;
  host_id: string;
  title: string;
  description?: string | null;
  starts_at: string;
  ends_at?: string | null;
  location?: string | null;
  is_online: boolean;
}

interface GroupAnalyticsResponse {
  member_count: number;
  invited_count: number;
  message_count: number;
  event_count: number;
  days_active: number;
  growth_goal: number;
  growth_percent: number;
  discovery_score: number;
  engagement_rate: number;
  onboarding_completion_estimate: number;
}

interface GroupMemberResponse {
  user_id: string;
  group_id: string;
  role: string;
  status: string;
  alias?: string | null;
  joined_at: string;
}

function Groups() {
  const { user } = useAuth();
  const [groups, setGroups] = useState<GroupListResponse[]>([]);
  const { loading: groupsLoading, error: groupsError, run: runGroups } = useLoadingError();
  const { loading: actionLoading, error: actionError, run: runAction, setError: setActionError } =
    useLoadingError();
  const [createName, setCreateName] = useState('');
  const [createDescription, setCreateDescription] = useState('');
  const [createType, setCreateType] = useState<GroupType>('public');
  const [createOrg, setCreateOrg] = useState('');
  const [createCategory, setCreateCategory] = useState('');
  const [createTags, setCreateTags] = useState('');
  const [createTemplate, setCreateTemplate] = useState('');
  const [createDiscoverable, setCreateDiscoverable] = useState(true);
  const [createAnnouncementOnly, setCreateAnnouncementOnly] = useState(false);
  const [createGrowthGoal, setCreateGrowthGoal] = useState(100);
  const [templates, setTemplates] = useState<GroupTemplateResponse[]>([]);
  const [directoryQuery, setDirectoryQuery] = useState('');
  const [groupMessages, setGroupMessages] = useState<GroupMessageResponse[]>([]);
  const [events, setEvents] = useState<GroupEventResponse[]>([]);
  const [analytics, setAnalytics] = useState<GroupAnalyticsResponse | null>(null);
  const [groupMembers, setGroupMembers] = useState<GroupMemberResponse[]>([]);
  const [currentUserProfile, setCurrentUserProfile] = useState<{ id: string } | null>(null);
  const [messagesLoading, setMessagesLoading] = useState(false);
  const [messageDraft, setMessageDraft] = useState('');
  const [inviteUserId, setInviteUserId] = useState('');
  const [eventTitle, setEventTitle] = useState('');
  const [eventStart, setEventStart] = useState('');
  const [eventLocation, setEventLocation] = useState('');
  const [eventOnline, setEventOnline] = useState(true);

  const selectedGroupId = useGroupStore((state) => state.activeGroupId);
  const setSelectedGroupId = useGroupStore((state) => state.setActiveGroup);
  const joinModal = useModal<string>(false);
  const canFetch = useMemo(() => Boolean(user), [user]);
  const selectedGroup = useMemo(
    () => groups.find((group) => group.id === selectedGroupId) ?? null,
    [groups, selectedGroupId],
  );
  const myGroups = useMemo(() => groups.filter((group) => group.is_member), [groups]);
  const discoverGroups = useMemo(() => groups.filter((group) => !group.is_member), [groups]);

  const currentUserMember = useMemo(() => {
    if (!currentUserProfile) return null;
    return groupMembers.find((m) => m.user_id === currentUserProfile.id) ?? null;
  }, [groupMembers, currentUserProfile]);

  const isCurrentGroupAdmin = useMemo(() => {
    return currentUserMember?.role === 'admin' || currentUserMember?.role === 'owner';
  }, [currentUserMember]);

  const filteredDiscoverGroups = useMemo(() => {
    const query = directoryQuery.trim().toLowerCase();
    if (!query) return discoverGroups;
    return discoverGroups.filter((group) =>
      [group.name, group.description, group.category, group.organization_name, ...(group.tags ?? [])]
        .filter(Boolean)
        .join(' ')
        .toLowerCase()
        .includes(query),
    );
  }, [directoryQuery, discoverGroups]);
  const trendingGroups = useMemo(
    () => [...groups].sort((a, b) => b.discovery_score - a.discovery_score).slice(0, 4),
    [groups],
  );
  const listContainerRef = useRef<HTMLDivElement | null>(null);
  const [groupListHeight, setGroupListHeight] = useState(420);
  const renderCount = useRenderCount('GroupThread');

  const [completedSteps, setCompletedSteps] = useState<Record<string, boolean>>(() => {
    try {
      return JSON.parse(localStorage.getItem('chattingapp.completedOnboardingSteps') || '{}');
    } catch {
      return {};
    }
  });

  const [activeGroupTab, setActiveGroupTab] = useState<'chat' | 'members' | 'events' | 'admin'>('chat');
  const groupVirtualListRef = useRef<any>(null);

  const getHashColor = (str: string) => {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      hash = str.charCodeAt(i) + ((hash << 5) - hash);
    }
    const h = Math.abs(hash % 360);
    return `hsl(${h}, 70%, 65%)`;
  };

  const activePinnedMessage = useMemo(() => {
    return groupMessages.find((m) => m.content.toLowerCase().includes('[pinned]')) || groupMessages[0] || null;
  }, [groupMessages]);

  useEffect(() => {
    localStorage.setItem('chattingapp.completedOnboardingSteps', JSON.stringify(completedSteps));
  }, [completedSteps]);

  useEffect(() => {
    setActiveGroupTab('chat');
  }, [selectedGroupId]);

  const toggleOnboardingStep = (stepId: string) => {
    setCompletedSteps((prev) => ({
      ...prev,
      [stepId]: !prev[stepId]
    }));
  };

  useLayoutEffect(() => {
    const element = listContainerRef.current;
    if (!element) return;
    const updateHeight = () => setGroupListHeight(element.clientHeight);
    updateHeight();
    const observer = new ResizeObserver(() => updateHeight());
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  const { isConnected, isConnecting, error: wsError, messages: wsMessages, sendMessage } =
    useGroupWebSocket(selectedGroupId);

  const loadGroups = async () =>
    runGroups(
      apiGet('/api/v1/groups').then((response) => {
        const nextGroups = response as GroupListResponse[];
        setGroups(nextGroups);
        return nextGroups;
      }),
    );

  const refreshGroupList = async () => {
    await loadGroups();
  };

  const loadTemplates = async () => {
    try {
      setTemplates((await apiGet('/api/v1/groups/templates')) as GroupTemplateResponse[]);
    } catch {
      setTemplates([]);
    }
  };

  const splitTags = (value: string) =>
    value
      .split(',')
      .map((tag) => tag.trim())
      .filter(Boolean)
      .slice(0, 8);

  const renderableGroupMessages = useMemo(() => {
    const items: { type: 'message'; data: GroupMessageResponse; isConsecutive: boolean }[] = [];
    let prevMsg: GroupMessageResponse | undefined = undefined;

    groupMessages.forEach((msg) => {
      const msgDate = new Date(msg.timestamp);
      const prevDate = prevMsg ? new Date(prevMsg.timestamp) : null;

      const consecutive = prevMsg && prevMsg.sender_id === msg.sender_id &&
        (msgDate.getTime() - prevDate!.getTime() < 5 * 60 * 1000);

      items.push({
        type: 'message',
        data: msg,
        isConsecutive: !!consecutive
      });

      prevMsg = msg;
    });

    return items;
  }, [groupMessages]);

  const estimateGroupMessageHeight = (item: any) => {
    const message = item.data;
    const contentLength = displayMessageContent(message.content).length;
    const lines = Math.ceil(contentLength / 45);
    let height = Math.max(96, 90 + lines * 18);
    if (item.isConsecutive) {
      height -= 36; // consecutive items have no headers, so they are shorter
    }
    return Math.max(52, height);
  };

  const handleCreateGroup = async (e: React.FormEvent) => {
    e.preventDefault();
    setActionError(null);
    if (!createName.trim() && !createTemplate) return;

    try {
      const payload: GroupCreatePayload = {
        name: createName.trim() || 'New community',
        description: createDescription.trim() ? createDescription.trim() : null,
        type: createType,
        organization_name: createOrg.trim() ? createOrg.trim() : null,
        category: createCategory.trim() ? createCategory.trim() : null,
        tags: splitTags(createTags),
        is_discoverable: createDiscoverable,
        announcement_only: createAnnouncementOnly,
        template_key: createTemplate || null,
        growth_goal: createGrowthGoal,
      };

      const created = await runAction(
        apiPost('/api/v1/groups', payload as unknown as Record<string, unknown>) as Promise<GroupResponse>,
      );

      setSelectedGroupId(created.id);
      setCreateName('');
      setCreateDescription('');
      setCreateOrg('');
      setCreateCategory('');
      setCreateTags('');
      setCreateTemplate('');
      setCreateDiscoverable(true);
      setCreateAnnouncementOnly(false);
      setCreateGrowthGoal(100);
      await refreshGroupList();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Could not create group');
    }
  };

  const handleTemplateSelection = (templateKey: string) => {
    setCreateTemplate(templateKey);
    const selected = templates.find((template) => template.key === templateKey);
    if (!selected) {
      setCreateName('');
      setCreateDescription('');
      setCreateCategory('');
      setCreateTags('');
      setCreateGrowthGoal(100);
      return;
    }
    setCreateName(selected.name);
    setCreateDescription(selected.description);
    setCreateCategory(selected.category);
    setCreateTags(selected.tags.join(', '));
    setCreateGrowthGoal(selected.growth_goal);
  };

  const loadGroupMessages = async (groupId: string) => {
    setMessagesLoading(true);
    setActionError(null);
    try {
      setGroupMessages((await apiGet(`/api/v1/groups/${groupId}/messages?limit=50`)) as GroupMessageResponse[]);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Could not load group messages');
      setGroupMessages([]);
    } finally {
      setMessagesLoading(false);
    }
  };

  const loadGroupEvents = async (groupId: string) => {
    try {
      setEvents((await apiGet(`/api/v1/groups/${groupId}/events`)) as GroupEventResponse[]);
    } catch {
      setEvents([]);
    }
  };

  const loadGroupAnalytics = async (groupId: string) => {
    try {
      setAnalytics((await apiGet(`/api/v1/groups/${groupId}/analytics`)) as GroupAnalyticsResponse);
    } catch {
      setAnalytics(null);
    }
  };

  const loadGroupMembers = async (groupId: string) => {
    try {
      setGroupMembers((await apiGet(`/api/v1/groups/${groupId}/members`)) as GroupMemberResponse[]);
    } catch {
      setGroupMembers([]);
    }
  };

  const handleUpdateMemberRole = async (targetUserId: string, newRole: string) => {
    if (!selectedGroupId) return;
    setActionError(null);
    try {
      await runAction(apiPatch(`/api/v1/groups/${selectedGroupId}/members/${targetUserId}/role`, { role: newRole }));
      void loadGroupMembers(selectedGroupId);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Could not change member role');
    }
  };

  useEffect(() => {
    if (!canFetch) return;
    void loadGroups();
    void loadTemplates();
    apiGet('/api/v1/users/me')
      .then((data) => setCurrentUserProfile(data as { id: string }))
      .catch(() => {});
  }, [canFetch]);

  useEffect(() => {
    if (!canFetch || !selectedGroupId || !selectedGroup?.is_member) {
      setGroupMessages([]);
      setEvents([]);
      setAnalytics(null);
      setGroupMembers([]);
      return;
    }
    void loadGroupMessages(selectedGroupId);
    void loadGroupEvents(selectedGroupId);
    void loadGroupAnalytics(selectedGroupId);
    void loadGroupMembers(selectedGroupId);
  }, [selectedGroupId, canFetch, selectedGroup?.is_member]);

  useEffect(() => {
    if (wsMessages.length === 0) return;
    const latest = wsMessages[wsMessages.length - 1];
    if (latest.type === 'message' && latest.data && typeof latest.data === 'object') {
      setGroupMessages((prev) => [...prev, latest.data as GroupMessageResponse]);
    }
  }, [wsMessages]);

  const handleJoinGroup = async (groupId: string) => {
    setActionError(null);
    try {
      await runAction(apiPost(`/api/v1/groups/${groupId}/join`, {}));
      await refreshGroupList();
      setSelectedGroupId(groupId);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Could not join group');
    }
  };

  const handleInviteUser = async (groupId: string) => {
    if (!inviteUserId.trim()) return;
    setActionError(null);
    try {
      await runAction(apiPost(`/api/v1/groups/${groupId}/invite`, { user_id: inviteUserId.trim() }));
      setInviteUserId('');
      await refreshGroupList();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Could not invite user');
    }
  };

  const handleToggleAnnouncementMode = async (group: GroupListResponse) => {
    try {
      await runAction(apiPatch(`/api/v1/groups/${group.id}/settings`, { announcement_only: !group.announcement_only }));
      await refreshGroupList();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Could not update announcement channel');
    }
  };

  const handleRequestVerification = async (groupId: string) => {
    try {
      await runAction(apiPost(`/api/v1/groups/${groupId}/verify`, {}));
      await refreshGroupList();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Could not request verification');
    }
  };

  const handleCreateEvent = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedGroupId || !eventTitle.trim() || !eventStart) return;
    try {
      await runAction(
        apiPost(`/api/v1/groups/${selectedGroupId}/events`, {
          title: eventTitle.trim(),
          starts_at: new Date(eventStart).toISOString(),
          location: eventLocation.trim() || null,
          is_online: eventOnline,
        }),
      );
      setEventTitle('');
      setEventStart('');
      setEventLocation('');
      await loadGroupEvents(selectedGroupId);
      await refreshGroupList();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Could not schedule event');
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedGroupId) return;
    const content = messageDraft.trim();
    if (!content) return;

    setActionError(null);
    try {
      if (isConnected) sendMessage(content);
      await runAction(apiPost(`/api/v1/groups/${selectedGroupId}/messages`, { content }));
      setMessageDraft('');
      await loadGroupMessages(selectedGroupId);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Could not send group message');
    }
  };

  const renderGroupCard = (group: GroupListResponse, context: 'my' | 'discover' | 'trending') => (
    <article key={`${context}-${group.id}`} className={`group-card ${group.id === selectedGroupId ? 'selected' : ''}`}>
      <div className="group-card-top">
        <div>
          <strong>{group.name}</strong>
          <p className="small-note">{group.description ?? 'No description'}</p>
        </div>
        <span className="pill soft">{group.type}</span>
      </div>
      <div className="group-tag-row">
        {group.is_verified ? <span className="pill success">Verified</span> : null}
        {group.category ? <span className="pill soft">{group.category}</span> : null}
        {group.announcement_only ? <span className="pill accent">Announcements</span> : null}
      </div>
      <div className="group-preview-row">
        <span>{group.is_member ? 'Member' : 'Discoverable'}</span>
        <span>{group.membership_status ?? 'Open preview'}</span>
        <span>{group.member_count} members</span>
        <span>{group.message_count} messages</span>
        <span>{group.event_count} events</span>
        <span>Score {group.discovery_score}</span>
      </div>
      <div className="group-card-actions">
        {group.is_member ? (
          <button className="secondary-button" type="button" onClick={() => setSelectedGroupId(group.id)}>
            Open
          </button>
        ) : (
          <button className="primary-button" type="button" onClick={() => joinModal.open(group.id)}>
            Join
          </button>
        )}
      </div>
    </article>
  );

  return (
    <div className="page-panel glass-panel">
      <div className="panel-header">
        <div>
          <span className="hero-label">Groups</span>
          <h2>Community pods</h2>
        </div>
        <div className="group-top-actions">
          <a className="primary-button" href="#create-group">+ Create group</a>
          <a className="secondary-button" href="#discover-groups">Join group</a>
          <button className="ghost-button" type="button" onClick={refreshGroupList} disabled={groupsLoading || !canFetch}>
            {groupsLoading ? 'Refreshing...' : 'Refresh groups'}
          </button>
        </div>
      </div>

      {actionError ? <div className="error-message">{actionError}</div> : null}
      {wsError ? <div className="error-message">WebSocket: {wsError}</div> : null}

      <div className="groups-grid groups-grid-layout">
        <section className="glass-panel groups-panel-padded" id="create-group">
          <div className="groups-panel-header">
            <div>
              <h3 className="hero-label">Create group</h3>
              <p className="small-note">Start a community from a template or tune it yourself.</p>
            </div>
          </div>
          <form className="group-create-form" onSubmit={handleCreateGroup}>
            <label>
              Template
              <select value={createTemplate} onChange={(e) => handleTemplateSelection(e.target.value)}>
                <option value="">Blank group</option>
                {templates.map((template) => (
                  <option key={template.key} value={template.key}>{template.name}</option>
                ))}
              </select>
            </label>
            <label>
              Group name
              <input value={createName} onChange={(e) => setCreateName(e.target.value)} placeholder="Enter a name" />
            </label>
            <label>
              Description
              <textarea value={createDescription} onChange={(e) => setCreateDescription(e.target.value)} placeholder="Write a short summary" />
            </label>
            <label>
              Type
              <select value={createType} onChange={(e) => setCreateType(e.target.value as GroupType)}>
                <option value="public">Public</option>
                <option value="private">Private</option>
                <option value="anonymous">Anonymous</option>
                <option value="organization">Organization</option>
              </select>
            </label>
            <label>
              Category
              <input value={createCategory} onChange={(e) => setCreateCategory(e.target.value)} placeholder="Education, Product, Events" />
            </label>
            <label>
              Tags
              <input value={createTags} onChange={(e) => setCreateTags(e.target.value)} placeholder="design, support, local" />
            </label>
            <label>
              Organization
              <input value={createOrg} onChange={(e) => setCreateOrg(e.target.value)} placeholder="Optional organization" />
            </label>
            <label>
              Growth goal
              <input type="number" min={1} value={createGrowthGoal} onChange={(e) => setCreateGrowthGoal(Number(e.target.value))} />
            </label>
            <label className="toggle-row">
              <input type="checkbox" checked={createDiscoverable} onChange={(e) => setCreateDiscoverable(e.target.checked)} />
              Discoverable
            </label>
            <label className="toggle-row">
              <input type="checkbox" checked={createAnnouncementOnly} onChange={(e) => setCreateAnnouncementOnly(e.target.checked)} />
              Announcement channel
            </label>
            <button className="primary-button" type="submit" disabled={actionLoading}>
              {actionLoading ? 'Creating...' : 'Create group'}
            </button>
          </form>
        </section>

        <section className="glass-panel groups-panel-padded" id="discover-groups">
          <div className="groups-panel-header">
            <div>
              <h3 className="hero-label">Groups directory</h3>
              <p className="small-note">Your rooms, public discoveries, and trending communities.</p>
            </div>
          </div>
          <div className="group-discovery-hint">
            <p className="small-note">Search by name, category, or tags to discover groups. Verified and active communities are surfaced first.</p>
          </div>
          <input
            className="group-directory-search"
            value={directoryQuery}
            onChange={(e) => setDirectoryQuery(e.target.value)}
            placeholder="Search communities, tags, or categories"
          />

          {groupsLoading ? (
            <p>Loading groups...</p>
          ) : groupsError ? (
            <div className="error-message">{groupsError}</div>
          ) : groups.length === 0 ? (
            <p>No groups available yet.</p>
          ) : (
            <div className="group-directory">
              <div className="group-list-section">
                <h4>My Groups</h4>
                <div className="group-list">{myGroups.length ? myGroups.map((group) => renderGroupCard(group, 'my')) : <p className="small-note">Join a group to see it here.</p>}</div>
              </div>
              <div className="group-list-section">
                <h4>Discover Groups</h4>
                <div className="group-list">{filteredDiscoverGroups.length ? filteredDiscoverGroups.map((group) => renderGroupCard(group, 'discover')) : <p className="small-note">No discoverable groups right now.</p>}</div>
              </div>
              <div className="group-list-section">
                <h4>Trending Groups</h4>
                <div className="group-list">{trendingGroups.map((group) => renderGroupCard(group, 'trending'))}</div>
              </div>
            </div>
          )}
        </section>

        <section className="glass-panel groups-panel-padded">
          {selectedGroup ? (
            <>
              <div className="group-details-header">
                <div>
                  <span className="hero-label">{selectedGroup.name}</span>
                  <p className="small-note">{selectedGroup.description ?? 'Group details'}</p>
                </div>
                <div className="group-status-row">
                  <span className="pill soft">{selectedGroup.type}</span>
                  {selectedGroup.is_verified ? <span className="pill success">Verified</span> : null}
                  {selectedGroup.is_member ? <span className="pill soft">Joined</span> : <span className="pill soft">Not joined</span>}
                </div>
              </div>

              {selectedGroup.is_member ? (
                <>
                  <div className="group-chat-status">
                    <small>WebSocket: {isConnecting ? 'Connecting...' : isConnected ? 'Live' : 'Offline'}</small>
                  </div>
                  <ReconnectBanner
                    isConnecting={isConnecting}
                    isConnected={isConnected}
                    error={wsError}
                    label="Group chat"
                  />

                  {/* Group sections tab navigation */}
                  <div className="group-tab-nav" role="tablist" aria-label="Group sections">
                    <button
                      type="button"
                      role="tab"
                      aria-selected={activeGroupTab === 'chat'}
                      className={`group-tab-btn ${activeGroupTab === 'chat' ? 'active' : ''}`}
                      onClick={() => setActiveGroupTab('chat')}
                    >
                      💬 Chat Pod
                    </button>
                    <button
                      type="button"
                      role="tab"
                      aria-selected={activeGroupTab === 'members'}
                      className={`group-tab-btn ${activeGroupTab === 'members' ? 'active' : ''}`}
                      onClick={() => setActiveGroupTab('members')}
                    >
                      👥 Members ({selectedGroup.member_count})
                    </button>
                    <button
                      type="button"
                      role="tab"
                      aria-selected={activeGroupTab === 'events'}
                      className={`group-tab-btn ${activeGroupTab === 'events' ? 'active' : ''}`}
                      onClick={() => setActiveGroupTab('events')}
                    >
                      📅 Events & Onboarding
                    </button>
                    {isCurrentGroupAdmin && (
                      <button
                        type="button"
                        role="tab"
                        aria-selected={activeGroupTab === 'admin'}
                        className={`group-tab-btn ${activeGroupTab === 'admin' ? 'active' : ''}`}
                        onClick={() => setActiveGroupTab('admin')}
                      >
                        🛡️ Admin Settings
                      </button>
                    )}
                  </div>

                  {/* TAB 1: Chat Thread */}
                  {activeGroupTab === 'chat' && (
                    <div className="group-tab-panel chat-pod-panel">
                      {selectedGroup.announcement_only && (
                        <div className="announcement-banner">
                          📢 <strong>Announcement Channel:</strong> Only admins can broadcast messages here.
                        </div>
                      )}

                      {activePinnedMessage && (
                        <div
                          className="group-pinned-banner"
                          onClick={() => {
                            const idx = renderableGroupMessages.findIndex((m) => m.data.id === activePinnedMessage.id);
                            if (idx !== -1 && groupVirtualListRef.current) {
                              groupVirtualListRef.current.scrollToItem(idx, 'center');
                            }
                          }}
                          role="button"
                          tabIndex={0}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' || e.key === ' ') {
                              const idx = renderableGroupMessages.findIndex((m) => m.data.id === activePinnedMessage.id);
                              if (idx !== -1 && groupVirtualListRef.current) {
                                groupVirtualListRef.current.scrollToItem(idx, 'center');
                              }
                            }
                          }}
                        >
                          📌 <strong>Pinned Announcement:</strong> {displayMessageContent(activePinnedMessage.content).slice(0, 60)}...
                        </div>
                      )}

                      <div className="thread-messages" role="log" aria-live="polite" aria-atomic="false">
                        <div className="chat-wallpaper" aria-hidden="true" />
                        {messagesLoading ? <p>Loading messages...</p> : null}
                        {import.meta.env.DEV ? <div className="dev-badge">Group render count: {renderCount}</div> : null}
                        {groupMessages.length === 0 && !messagesLoading ? (
                          <p className="empty-chat-placeholder">No messages yet. Send a message to start the conversation!</p>
                        ) : renderableGroupMessages.length > 20 ? (
                          <div ref={listContainerRef} className="virtualized-group-thread-list">
                            <VirtualizedList
                              items={renderableGroupMessages}
                              itemHeight={estimateGroupMessageHeight}
                              estimatedItemHeight={110}
                              height={groupListHeight}
                              overscan={6}
                              listRef={groupVirtualListRef}
                              className="virtualized-message-list"
                              renderItem={(item) => {
                                const message = item.data;
                                const isConsecutive = item.isConsecutive;
                                const isOutgoing = message.sender_id === currentUserProfile?.id;
                                return (
                                  <div key={message.id} className={`message-row ${isOutgoing ? 'outgoing' : 'incoming'} group-message-row ${isConsecutive ? 'consecutive' : ''}`}>
                                    <div className="group-message-body">
                                      {!isConsecutive && (
                                        <small className="group-message-sender-header">
                                          <strong style={{ color: getHashColor(message.sender_alias ?? message.sender_id ?? 'Unknown') }}>
                                            {message.sender_alias ?? message.sender_id ?? 'Unknown'}
                                          </strong> · {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                          {selectedGroup.created_by === message.sender_id && <span className="role-badgeowner">Owner</span>}
                                        </small>
                                      )}
                                      <p className={isEncryptedToken(message.content) ? 'encrypted-message-placeholder' : undefined}>
                                        {displayMessageContent(message.content)}
                                      </p>
                                    </div>
                                  </div>
                                );
                              }}
                            />
                          </div>
                        ) : (
                          renderableGroupMessages.map((item) => {
                            const message = item.data;
                            const isConsecutive = item.isConsecutive;
                            const isOutgoing = message.sender_id === currentUserProfile?.id;
                            return (
                              <div key={message.id} className={`message-row ${isOutgoing ? 'outgoing' : 'incoming'} group-message-row ${isConsecutive ? 'consecutive' : ''}`}>
                                <div className="group-message-body">
                                  {!isConsecutive && (
                                    <small className="group-message-sender-header">
                                      <strong style={{ color: getHashColor(message.sender_alias ?? message.sender_id ?? 'Unknown') }}>
                                        {message.sender_alias ?? message.sender_id ?? 'Unknown'}
                                      </strong> · {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                      {selectedGroup.created_by === message.sender_id && <span className="role-badgeowner">Owner</span>}
                                    </small>
                                  )}
                                  <p className={isEncryptedToken(message.content) ? 'encrypted-message-placeholder' : undefined}>
                                    {displayMessageContent(message.content)}
                                  </p>
                                </div>
                              </div>
                            );
                          })
                        )}
                      </div>

                      {(!selectedGroup.announcement_only || isCurrentGroupAdmin) && (
                        <form onSubmit={handleSendMessage} className="message-input group-chat-form floating-input-bar">
                          <input
                            placeholder={selectedGroup.announcement_only ? 'Post an announcement...' : 'Write a group message...'}
                            value={messageDraft}
                            onChange={(e) => setMessageDraft(e.target.value)}
                            aria-label="Group message text"
                          />
                          <button className="primary-button send-btn" type="submit" disabled={messagesLoading}>➤</button>
                        </form>
                      )}
                    </div>
                  )}

                  {/* TAB 2: Members List */}
                  {activeGroupTab === 'members' && (
                    <div className="group-tab-panel group-members-panel">
                      <div className="invite-panel glass-panel">
                        <h4>Invite user by ID</h4>
                        <div className="settings-row">
                          <input type="text" value={inviteUserId} onChange={(e) => setInviteUserId(e.target.value)} placeholder="Paste a user id" />
                          <button className="primary-button" type="button" disabled={!inviteUserId.trim()} onClick={() => handleInviteUser(selectedGroup.id)}>
                            Send Invite
                          </button>
                        </div>
                      </div>

                      <div className="members-panel glass-panel">
                        <div className="groups-panel-header"><h3 className="hero-label">Members & Roles</h3></div>
                        <div className="members-list">
                          {groupMembers.length ? groupMembers.map((member) => (
                            <div key={member.user_id} className="member-card">
                              <div className="member-info">
                                <strong>{member.alias ?? 'Group Member'}</strong>
                                <small className="member-id-label">@{member.user_id.slice(0, 8)}</small>
                                <span className={`role-badge ${member.role}`}>{member.role}</span>
                              </div>
                              {isCurrentGroupAdmin && currentUserProfile?.id !== member.user_id && member.role !== 'owner' ? (
                                <div className="member-actions">
                                  <select
                                    value={member.role}
                                    onChange={(e) => void handleUpdateMemberRole(member.user_id, e.target.value)}
                                    className="role-select"
                                  >
                                    <option value="member">Member</option>
                                    <option value="moderator">Moderator</option>
                                    <option value="admin">Admin</option>
                                  </select>
                                </div>
                              ) : null}
                            </div>
                          )) : <p className="small-note">No members loaded.</p>}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* TAB 3: Events & Onboarding */}
                  {activeGroupTab === 'events' && (
                    <div className="group-tab-panel group-events-panel">
                      <div className="advanced-group-dashboard glass-panel">
                        <h4>Group Dashboard & Checklist</h4>
                        <div className="metric-strip">
                          <span><strong>{selectedGroup.member_count}</strong> members</span>
                          <span><strong>{selectedGroup.message_count}</strong> messages</span>
                          <span><strong>{selectedGroup.event_count}</strong> events</span>
                          <span><strong>{analytics?.growth_percent ?? 0}%</strong> growth</span>
                        </div>
                        {selectedGroup.welcome_message ? <p className="privacy-explainer">{selectedGroup.welcome_message}</p> : null}

                        {selectedGroup.onboarding_steps?.length ? (
                          <div className="onboarding-step-list-wrapper">
                            {(() => {
                              const stepsCount = selectedGroup.onboarding_steps.length;
                              const doneCount = selectedGroup.onboarding_steps.filter(
                                (_, idx) => !!completedSteps[`${selectedGroup.id}-step-${idx}`]
                              ).length;
                              const pct = Math.round((doneCount / stepsCount) * 100);
                              return (
                                <div className="onboarding-progress-container">
                                  <div className="onboarding-progress-header">
                                    <span>Checklist completion</span>
                                    <strong>{pct}%</strong>
                                  </div>
                                  <div className="onboarding-progress-bar-track">
                                    <div className="onboarding-progress-bar-fill" style={{ width: `${pct}%` }} />
                                  </div>
                                </div>
                              );
                            })()}
                            <h5>Onboarding Checklist</h5>
                            <div className="onboarding-step-list">
                              {selectedGroup.onboarding_steps.map((step, index) => {
                                const stepId = `${selectedGroup.id}-step-${index}`;
                                const isDone = !!completedSteps[stepId];
                                return (
                                  <div key={stepId} className={`onboarding-step-card ${isDone ? 'done' : ''}`}>
                                    <label className="onboarding-step-checkbox-row">
                                      <input
                                        type="checkbox"
                                        checked={isDone}
                                        onChange={() => toggleOnboardingStep(stepId)}
                                      />
                                      <div>
                                        <strong>{step.title ?? `Step ${index + 1}`}</strong>
                                        <p>{step.body ?? 'Complete this onboarding step.'}</p>
                                      </div>
                                    </label>
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        ) : null}
                      </div>

                      <div className="event-panel glass-panel">
                        <div className="groups-panel-header"><h3 className="hero-label">Events</h3></div>
                        <form className="event-form" onSubmit={handleCreateEvent}>
                          <input value={eventTitle} onChange={(e) => setEventTitle(e.target.value)} placeholder="Event title" />
                          <input type="datetime-local" value={eventStart} onChange={(e) => setEventStart(e.target.value)} />
                          <input value={eventLocation} onChange={(e) => setEventLocation(e.target.value)} placeholder="Location or meeting link" />
                          <label className="toggle-row">
                            <input type="checkbox" checked={eventOnline} onChange={(e) => setEventOnline(e.target.checked)} />
                            Online
                          </label>
                          <button className="primary-button" type="submit">Schedule</button>
                        </form>
                        <div className="event-list">
                          {events.length ? events.map((event) => (
                            <div key={event.id} className="event-card">
                              <strong>{event.title}</strong>
                              <span>{new Date(event.starts_at).toLocaleString()}</span>
                              <span>{event.is_online ? 'Online' : event.location ?? 'In person'}</span>
                            </div>
                          )) : <p className="small-note">No events scheduled.</p>}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* TAB 4: Admin Moderation */}
                  {activeGroupTab === 'admin' && isCurrentGroupAdmin && (
                    <div className="group-tab-panel group-admin-panel glass-panel">
                      <h4>Group Settings</h4>
                      <div className="group-admin-actions">
                        <button className="secondary-button" type="button" onClick={() => handleToggleAnnouncementMode(selectedGroup)}>
                          {selectedGroup.announcement_only ? 'Open discussion' : 'Make announcements'}
                        </button>
                        <button
                          className="secondary-button"
                          type="button"
                          disabled={selectedGroup.verification_status === 'pending' || selectedGroup.is_verified}
                          onClick={() => handleRequestVerification(selectedGroup.id)}
                        >
                          {selectedGroup.is_verified ? 'Verified' : selectedGroup.verification_status === 'pending' ? 'Verification pending' : 'Request verification'}
                        </button>
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="empty-state-card">
                  <p>This group is not joined yet. Click Join to participate in the room.</p>
                </div>
              )}
            </>
          ) : (
            <div><p>Select a group from the list to view details and chat.</p></div>
          )}
        </section>
      </div>

      <ConfirmationDialog
        isOpen={joinModal.isOpen}
        title="Join group"
        message="Would you like to join this group?"
        confirmLabel="Join"
        cancelLabel="Cancel"
        loading={actionLoading}
        onConfirm={async () => {
          if (!joinModal.payload) return;
          await handleJoinGroup(joinModal.payload);
          joinModal.close();
        }}
        onCancel={joinModal.close}
      />
    </div>
  );
}

export default Groups;
