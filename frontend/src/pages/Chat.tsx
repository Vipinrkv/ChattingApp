import { ChangeEvent, FormEvent, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { apiDelete, apiGet, apiPatch, apiPost, apiPostForm } from '../lib/api';
import { formatTimestamp } from '../lib/dateTime';
import { useWebSocket } from '../hooks/useWebSocket';
import { useAuth } from '../contexts/AuthContext';
import VirtualizedList from '../ui/VirtualizedList';
import { useRenderCount } from '../hooks/useRenderCount';
import { MessageBookmark } from '../components/MessageBookmark';
import { ScheduleMessage } from '../components/ScheduleMessage';
import { TranslateMessage } from '../components/TranslateMessage';
import { SmartReplies } from '../components/SmartReplies';
import { VoiceMessage } from '../components/VoiceMessage';
import { SharedMediaGallery } from '../components/SharedMediaGallery';
import { ChatBackupExport } from '../components/ChatBackupExport';
import ReconnectBanner from '../components/ReconnectBanner';
import { displayMessageContent, isEncryptedToken } from '../lib/messageContent';
import { Link } from 'react-router-dom';
import { Dropdown, type DropdownItem } from '../ui';

interface Peer {
  id: string;
  username: string;
  email?: string | null;
  bio?: string | null;
}

interface FriendResponse {
  id: string;
  username: string;
}

type LocalFriendStatus = 'idle' | 'pending' | 'accepted' | 'rejected' | 'blocked';

interface MessageData {
  id: string;
  sender_id: string;
  receiver_id: string;
  content: string;
  media_url?: string | null;
  media_type?: string | null;
  media_name?: string | null;
  media_size?: number | null;

  timestamp: string;
  is_seen: boolean;
  reply_to_message_id?: string | null;
  reply_preview?: string | null;
  reactions?: Record<string, string[]>;
  is_pinned?: boolean;
  edited_at?: string | null;
}

type ChatListItem =
  | { type: 'message'; data: MessageData; isConsecutive: boolean }
  | { type: 'date-separator'; dateString: string; id: string };

function Chat() {
  const { user } = useAuth();
  const [peers, setPeers] = useState<Peer[]>([]);
  const [friends, setFriends] = useState<FriendResponse[]>([]);
  const [nicknames, setNicknames] = useState<Record<string, string>>(() => {
    try {
      return JSON.parse(localStorage.getItem('chattingapp.friendNicknames') || '{}') as Record<string, string>;
    } catch {
      return {};
    }
  });
  const [requestStatusByPeerId, setRequestStatusByPeerId] = useState<Record<string, LocalFriendStatus>>(() => {
    try {
      return JSON.parse(localStorage.getItem('chattingapp.friendRequestDrafts') || '{}') as Record<string, LocalFriendStatus>;
    } catch {
      return {};
    }
  });
  const [isThreadOpen, setIsThreadOpen] = useState(false);
  const [selectedPeer, setSelectedPeer] = useState<Peer | null>(null);
  const [messageHistory, setMessageHistory] = useState<MessageData[]>([]);
  const [draft, setDraft] = useState('');
  const [loadingPeers, setLoadingPeers] = useState(true);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [peerStatus, setPeerStatus] = useState<'online' | 'offline'>('offline');
  const [isPeerTyping, setIsPeerTyping] = useState(false);
  const [messageSeenMap, setMessageSeenMap] = useState<Record<string, boolean>>({});
  const [searchTerm, setSearchTerm] = useState('');
  const [searchResults, setSearchResults] = useState<MessageData[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [deletedMessageIds, setDeletedMessageIds] = useState<Set<string>>(new Set());
  const [editedMessages, setEditedMessages] = useState<Record<string, MessageData>>({});
  const [editingMessageId, setEditingMessageId] = useState<string | null>(null);
  const [editingDraft, setEditingDraft] = useState('');
  const [replyTarget, setReplyTarget] = useState<MessageData | null>(null);
  const [activeTranslationMessageId, setActiveTranslationMessageId] = useState<string | null>(null);
  const [activeSmartReplyMessageId, setActiveSmartReplyMessageId] = useState<string | null>(null);
  const [hasMoreHistory, setHasMoreHistory] = useState(true);
  const [loadingOlder, setLoadingOlder] = useState(false);
  const seenMessageIdsRef = useRef<Set<string>>(new Set());
  const listContainerRef = useRef<HTMLDivElement | null>(null);
  const [listHeight, setListHeight] = useState(520);
  const renderCount = useRenderCount('ChatThread');

  // Modern chat lists state
  const [pinnedPeerIds, setPinnedPeerIds] = useState<string[]>(() => {
    try {
      return JSON.parse(localStorage.getItem('chattingapp.pinnedPeers') || '[]');
    } catch {
      return [];
    }
  });
  const [archivedPeerIds, setArchivedPeerIds] = useState<string[]>(() => {
    try {
      return JSON.parse(localStorage.getItem('chattingapp.archivedPeers') || '[]');
    } catch {
      return [];
    }
  });
  const [showArchived, setShowArchived] = useState(false);
  const [chatListSearch, setChatListSearch] = useState('');
  const [chatListFilter, setChatListFilter] = useState<'all' | 'friends'>('all');

  // Floating bottom navigation
  const [showScrollBottom, setShowScrollBottom] = useState(false);

  // Refs
  const threadMessagesRef = useRef<HTMLDivElement | null>(null);
  const virtualListRef = useRef<any>(null);

  // Redesign & UX States
  const [isDetailsOpen, setIsDetailsOpen] = useState(false);
  const [stagedFile, setStagedFile] = useState<File | null>(null);
  const [draftsByPeerId, setDraftsByPeerId] = useState<Record<string, string>>({});

  const draftRef = useRef(draft);
  useEffect(() => {
    draftRef.current = draft;
  }, [draft]);

  const selectPeer = (peer: Peer | null) => {
    if (selectedPeer) {
      setDraftsByPeerId((prev) => ({ ...prev, [selectedPeer.id]: draftRef.current }));
    }
    setSelectedPeer(peer);
    setDraft(peer ? (draftsByPeerId[peer.id] ?? '') : '');
    setStagedFile(null);
    setIsThreadOpen(!!peer);
  };

  useEffect(() => {
    localStorage.setItem('chattingapp.friendNicknames', JSON.stringify(nicknames));
  }, [nicknames]);

  useEffect(() => {
    localStorage.setItem('chattingapp.friendRequestDrafts', JSON.stringify(requestStatusByPeerId));
  }, [requestStatusByPeerId]);

  useEffect(() => {
    localStorage.setItem('chattingapp.pinnedPeers', JSON.stringify(pinnedPeerIds));
  }, [pinnedPeerIds]);

  useEffect(() => {
    localStorage.setItem('chattingapp.archivedPeers', JSON.stringify(archivedPeerIds));
  }, [archivedPeerIds]);

  const togglePinPeer = (peerId: string) => {
    setPinnedPeerIds((prev) =>
      prev.includes(peerId) ? prev.filter((id) => id !== peerId) : [...prev, peerId]
    );
  };

  const toggleArchivePeer = (peerId: string) => {
    setArchivedPeerIds((prev) =>
      prev.includes(peerId) ? prev.filter((id) => id !== peerId) : [...prev, peerId]
    );
  };

  useLayoutEffect(() => {
    const element = listContainerRef.current;
    if (!element) return;

    const updateHeight = () => setListHeight(element.clientHeight);
    updateHeight();

    const observer = new ResizeObserver(() => updateHeight());
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  const { isConnected, isConnecting, error, messages, sendMessage, sendTyping, sendReadReceipt } = useWebSocket(selectedPeer?.id ?? null);

  useEffect(() => {
    let isMounted = true;
    setLoadingPeers(true);
    setFetchError(null);

    apiGet('/api/v1/users')
      .then((payload) => {
        if (!isMounted) return;
        setPeers(payload as Peer[]);
        // Avoid auto-selecting the first peer to allow showing the welcome screen
        setSelectedPeer((prev) => prev ?? null);
      })
      .catch((err) => {
        if (!isMounted) return;
        setFetchError(err instanceof Error ? err.message : 'Could not load conversations');
      })
      .finally(() => {
        if (isMounted) {
          setLoadingPeers(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    let isMounted = true;
    apiGet('/api/v1/friends')
      .then((payload) => {
        if (!isMounted) return;
        setFriends(payload as FriendResponse[]);
      })
      .catch(() => {
        if (isMounted) setFriends([]);
      });
    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    if (!selectedPeer) {
      setMessageHistory([]);
      setPeerStatus('offline');
      setIsPeerTyping(false);
      return;
    }

    setLoadingHistory(true);
    setFetchError(null);
    setMessageHistory([]);
    setPeerStatus('offline');
    setIsPeerTyping(false);
    setSearchTerm('');
    setSearchResults([]);
    setDeletedMessageIds(new Set());
    setEditedMessages({});
    setEditingMessageId(null);
    setEditingDraft('');
    setReplyTarget(null);
    setHasMoreHistory(true);

    apiGet(`/api/v1/chat/${selectedPeer.id}/messages?limit=50`)
      .then((payload) => {
        const history = payload as MessageData[];
        setMessageHistory(history);
        setHasMoreHistory(history.length === 50);
      })
      .catch((err) => {
        setFetchError(err instanceof Error ? err.message : 'Could not load conversation history');
      })
      .finally(() => {
        setLoadingHistory(false);
      });
  }, [selectedPeer]);

  const friendIds = useMemo(() => new Set(friends.map((friend) => friend.id)), [friends]);

  const processedPeers = useMemo(() => {
    let result = peers.filter((peer) => {
      const label = nicknames[peer.id] || peer.username;
      return label.toLowerCase().includes(chatListSearch.toLowerCase());
    });

    if (chatListFilter === 'friends') {
      result = result.filter((peer) => friendIds.has(peer.id));
    }

    if (showArchived) {
      result = result.filter((peer) => archivedPeerIds.includes(peer.id));
    } else {
      result = result.filter((peer) => !archivedPeerIds.includes(peer.id));
    }

    return [...result].sort((a, b) => {
      const aPinned = pinnedPeerIds.includes(a.id);
      const bPinned = pinnedPeerIds.includes(b.id);
      if (aPinned && !bPinned) return -1;
      if (!aPinned && bPinned) return 1;
      return 0;
    });
  }, [peers, chatListSearch, chatListFilter, showArchived, archivedPeerIds, pinnedPeerIds, nicknames, friendIds]);

  const chatMessages = useMemo(
    () => messages.filter((message) => message.type === 'message'),
    [messages],
  );

  const combinedMessages = useMemo(() => {
    const allMessages = [...messageHistory, ...chatMessages.map((message) => message.data).filter(Boolean) as MessageData[]];
    const messageMap = new Map<string, MessageData>();

    allMessages
      .filter((message) => !deletedMessageIds.has(message.id))
      .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
      .forEach((message) => {
        const editedMessage = editedMessages[message.id];
        const messageContent = displayMessageContent(editedMessage?.content ?? message.content);
        const overrideSeen = messageSeenMap[message.id] ?? false;
        messageMap.set(message.id, {
          ...message,
          ...editedMessage,
          content: messageContent,
          is_seen: overrideSeen || message.is_seen,
        });
      });

    return Array.from(messageMap.values());
  }, [messageHistory, chatMessages, messageSeenMap, deletedMessageIds, editedMessages]);

  useEffect(() => {
    if (!selectedPeer || !searchTerm.trim()) {
      setSearchResults([]);
      setIsSearching(false);
      return;
    }

    const timeoutId = window.setTimeout(() => {
      setIsSearching(true);
      apiGet(`/api/v1/chat/${selectedPeer.id}/messages/search?q=${encodeURIComponent(searchTerm.trim())}`)
        .then((payload) => {
          setSearchResults(payload as MessageData[]);
        })
        .catch((err) => {
          setFetchError(err instanceof Error ? err.message : 'Could not search messages');
        })
        .finally(() => {
          setIsSearching(false);
        });
    }, 250);

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [searchTerm, selectedPeer]);

  const displayedMessages = searchTerm.trim()
    ? searchResults
      .filter((message) => !deletedMessageIds.has(message.id))
      .map((message) => editedMessages[message.id] ?? message)
    : combinedMessages;

  const formatDateLabel = (timestamp: string) => {
    const d = new Date(timestamp);
    const now = new Date();
    if (d.toDateString() === now.toDateString()) {
      return 'Today';
    }
    const yesterday = new Date();
    yesterday.setDate(now.getDate() - 1);
    if (d.toDateString() === yesterday.toDateString()) {
      return 'Yesterday';
    }
    return d.toLocaleDateString(undefined, { weekday: 'long', month: 'short', day: 'numeric', year: 'numeric' });
  };

  const renderableChatItems = useMemo(() => {
    const items: ChatListItem[] = [];
    let prevMsg: MessageData | undefined = undefined;

    displayedMessages.forEach((msg, idx) => {
      const msgDate = new Date(msg.timestamp);
      const prevDate = prevMsg ? new Date(prevMsg.timestamp) : null;

      if (!prevDate || msgDate.toDateString() !== prevDate.toDateString()) {
        const label = formatDateLabel(msg.timestamp);
        items.push({
          type: 'date-separator',
          dateString: label,
          id: `sep-${msg.timestamp}-${idx}`
        });
      }

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
  }, [displayedMessages]);

  const handleScrollToBottom = (behavior: 'auto' | 'smooth' = 'smooth') => {
    if (threadMessagesRef.current) {
      threadMessagesRef.current.scrollTo({
        top: threadMessagesRef.current.scrollHeight,
        behavior,
      });
    }
    if (virtualListRef.current) {
      virtualListRef.current.scrollToItem(renderableChatItems.length - 1, 'end');
    }
  };

  useEffect(() => {
    const timer = setTimeout(() => handleScrollToBottom('auto'), 50);
    return () => clearTimeout(timer);
  }, [renderableChatItems.length, selectedPeer]);

  const canChatWithSelectedPeer = Boolean(selectedPeer && friendIds.has(selectedPeer.id));
  const selectedPeerLabel = selectedPeer ? nicknames[selectedPeer.id] || selectedPeer.username : 'Select a chat';

  useEffect(() => {
    let typingResetTimer: number | null = null;
    setPeerStatus('offline');

    messages.forEach((message) => {
      if (message.type === 'presence' && message.data && typeof message.data === 'object') {
        const payload = message.data as { user_id?: string; status?: string };
        if (payload.user_id === selectedPeer?.id) {
          setPeerStatus(payload.status === 'online' ? 'online' : 'offline');
        }
      }

      if (message.type === 'typing' && message.data && typeof message.data === 'object') {
        const payload = message.data as { user_id?: string };
        if (payload.user_id === selectedPeer?.id) {
          setIsPeerTyping(true);
          if (typingResetTimer) {
            window.clearTimeout(typingResetTimer);
          }
          typingResetTimer = window.setTimeout(() => {
            setIsPeerTyping(false);
            typingResetTimer = null;
          }, 1500);
        }
      }

      if (message.type === 'read_receipt' && message.data && typeof message.data === 'object') {
        const payload = message.data as { message_id?: string };
        const messageId = payload.message_id;
        if (messageId) {
          setMessageSeenMap((prev) => ({
            ...prev,
            [messageId]: true,
          }));
        }
      }
    });

    return () => {
      if (typingResetTimer) {
        window.clearTimeout(typingResetTimer);
      }
    };
  }, [messages, selectedPeer]);

  const handleSend = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (stagedFile) {
      await handleSendMedia(stagedFile);
      setStagedFile(null);
      return;
    }

    const content = draft.trim();
    if (!content || !selectedPeer) {
      return;
    }
    if (!canChatWithSelectedPeer) {
      setFetchError('Send a friend request first. Chat unlocks after they accept.');
      return;
    }

    if (replyTarget) {
      try {
        const created = await apiPost(`/api/v1/chat/${selectedPeer.id}/messages`, {
          content,
          reply_to_message_id: replyTarget.id,
        }) as MessageData;
        setMessageHistory((prev) => [...prev, created]);
        setReplyTarget(null);
      } catch (err) {
        setFetchError(err instanceof Error ? err.message : 'Could not send reply');
        return;
      }
    } else {
      sendMessage(content);
    }
    setDraft('');
  };

  const [mediaCaption, setMediaCaption] = useState('');
  const [mediaSending, setMediaSending] = useState(false);

  const handleSendMedia = async (file: File) => {
    if (!selectedPeer || !canChatWithSelectedPeer) return;

    setMediaSending(true);
    setFetchError(null);

    try {
      const form = new FormData();
      form.append('file', file);
      const captionText = mediaCaption.trim() || draft.trim();
      form.append('caption', captionText);

      // backend expects: caption (Form) + file (UploadFile)
      const created = await apiPostForm(
        `/api/v1/chat/${selectedPeer.id}/messages/media`,
        form
      ) as MessageData;

      setMessageHistory((prev) => [...prev, created]);
      setMediaCaption('');
      setDraft('');
    } catch (err) {
      setFetchError(err instanceof Error ? err.message : 'Could not send media');
    } finally {
      setMediaSending(false);
    }
  };

  useEffect(() => {
    if (!selectedPeer) return;

    combinedMessages.forEach((message) => {
      const isIncoming = message.sender_id === selectedPeer.id;
      if (isIncoming && !message.is_seen && message.id && !seenMessageIdsRef.current.has(message.id)) {
        seenMessageIdsRef.current.add(message.id);
        apiPatch(`/api/v1/chat/${selectedPeer.id}/messages/${message.id}/seen`)
          .then((updated) => {
            if (updated && typeof updated === 'object' && 'id' in updated) {
              const updatedMessage = updated as MessageData;
              setMessageSeenMap((prev) => ({
                ...prev,
                [updatedMessage.id]: updatedMessage.is_seen,
              }));
              sendReadReceipt(updatedMessage.id);
            }
          })
          .catch((err) => console.error('Failed to mark message as seen:', err));
      }
    });
  }, [combinedMessages, selectedPeer, sendReadReceipt]);

  const handleDraftChange = (event: ChangeEvent<HTMLInputElement>) => {
    setDraft(event.target.value);
    if (event.target.value.trim()) {
      sendTyping();
    }
  };

  const toggleMessageTranslation = (messageId: string) => {
    setActiveTranslationMessageId((prev) => (prev === messageId ? null : messageId));
    if (activeSmartReplyMessageId === messageId) {
      setActiveSmartReplyMessageId(null);
    }
  };

  const toggleSmartReplies = (messageId: string) => {
    setActiveSmartReplyMessageId((prev) => (prev === messageId ? null : messageId));
    if (activeTranslationMessageId === messageId) {
      setActiveTranslationMessageId(null);
    }
  };

  const handleSendVoiceMessage = async (audioUrl: string) => {
    if (!selectedPeer) return;

    try {
      const created = await apiPost(`/api/v1/chat/${selectedPeer.id}/messages`, {
        content: 'Voice message',
        media_url: audioUrl,
        media_type: 'audio/webm',
      }) as MessageData;
      setMessageHistory((prev) => [...prev, created]);
    } catch (err) {
      setFetchError(err instanceof Error ? err.message : 'Could not send voice message');
    }
  };

  const handleDeleteMessage = async (message: MessageData) => {
    if (!selectedPeer) return;

    try {
      await apiDelete(`/api/v1/chat/${selectedPeer.id}/messages/${message.id}`);
      setDeletedMessageIds((prev) => new Set(prev).add(message.id));
      setMessageHistory((prev) => prev.filter((item) => item.id !== message.id));
      setSearchResults((prev) => prev.filter((item) => item.id !== message.id));
      setMessageSeenMap((prev) => {
        const next = { ...prev };
        delete next[message.id];
        return next;
      });
    } catch (err) {
      setFetchError(err instanceof Error ? err.message : 'Could not delete message');
    }
  };

  const startEditingMessage = (message: MessageData) => {
    setEditingMessageId(message.id);
    setEditingDraft(message.content);
  };

  const cancelEditingMessage = () => {
    setEditingMessageId(null);
    setEditingDraft('');
  };

  const handleEditMessage = async (event: FormEvent<HTMLFormElement>, message: MessageData) => {
    event.preventDefault();
    if (!selectedPeer) return;

    const content = editingDraft.trim();
    if (!content) return;

    try {
      const updated = await apiPatch(`/api/v1/chat/${selectedPeer.id}/messages/${message.id}`, { content }) as MessageData;
      setEditedMessages((prev) => ({ ...prev, [updated.id]: updated }));
      setMessageHistory((prev) => prev.map((item) => (item.id === updated.id ? updated : item)));
      setSearchResults((prev) => prev.map((item) => (item.id === updated.id ? updated : item)));
      cancelEditingMessage();
    } catch (err) {
      setFetchError(err instanceof Error ? err.message : 'Could not edit message');
    }
  };

  const applyUpdatedMessage = (updated: MessageData) => {
    setEditedMessages((prev) => ({ ...prev, [updated.id]: updated }));
    setMessageHistory((prev) => prev.map((item) => (item.id === updated.id ? updated : item)));
    setSearchResults((prev) => prev.map((item) => (item.id === updated.id ? updated : item)));
  };

  const handleToggleReaction = async (message: MessageData, emoji: string) => {
    if (!selectedPeer) return;

    try {
      const updated = await apiPatch(`/api/v1/chat/${selectedPeer.id}/messages/${message.id}/reactions`, { emoji }) as MessageData;
      applyUpdatedMessage(updated);
    } catch (err) {
      setFetchError(err instanceof Error ? err.message : 'Could not update reaction');
    }
  };

  const handleTogglePin = async (message: MessageData) => {
    if (!selectedPeer) return;

    try {
      const updated = await apiPatch(`/api/v1/chat/${selectedPeer.id}/messages/${message.id}/pin`) as MessageData;
      applyUpdatedMessage(updated);
    } catch (err) {
      setFetchError(err instanceof Error ? err.message : 'Could not update pin');
    }
  };

  const handleForwardMessage = async (message: MessageData) => {
    if (!selectedPeer) return;
    const receiver = peers.find((peer) => peer.id !== selectedPeer.id);
    if (!receiver) {
      setFetchError('No other peer is available to forward this message.');
      return;
    }

    try {
      await apiPost(`/api/v1/chat/${selectedPeer.id}/messages/${message.id}/forward`, {
        receiver_id: receiver.id,
      });
      setFetchError(`Forwarded to ${receiver.username}`);
    } catch (err) {
      setFetchError(err instanceof Error ? err.message : 'Could not forward message');
    }
  };

  const handleLoadOlder = async () => {
    if (!selectedPeer || messageHistory.length === 0) return;

    const firstMessage = messageHistory[0];
    setLoadingOlder(true);
    try {
      const older = await apiGet(
        `/api/v1/chat/${selectedPeer.id}/messages?limit=50&before=${encodeURIComponent(firstMessage.timestamp)}`,
      ) as MessageData[];
      setMessageHistory((prev) => [...older, ...prev]);
      setHasMoreHistory(older.length === 50);
    } catch (err) {
      setFetchError(err instanceof Error ? err.message : 'Could not load older messages');
    } finally {
      setLoadingOlder(false);
    }
  };

  const estimateChatMessageHeight = (item: any) => {
    if (item.type === 'date-separator') {
      return 52;
    }
    const message = item.data;
    let height = 110;
    const contentLength = message.content?.length ?? 0;

    if (contentLength > 0) {
      const lines = Math.ceil(contentLength / 40);
      height += lines * 18;
    }

    if (message.reply_to_message_id) height += 32;
    if (message.is_pinned) height += 24;
    if (message.reactions && Object.keys(message.reactions).length > 0) height += 32;

    if (message.media_url) {
      if (message.media_type?.startsWith('image/')) {
        height += 220;
      } else if (message.media_type?.startsWith('video/')) {
        height += 240;
      } else if (message.media_type?.startsWith('audio/')) {
        height += 80;
      } else {
        height += 60;
      }
    }

    return Math.min(Math.max(height, 120), 360);
  };

  const getReplyPreview = (message: MessageData) => {
    if (message.reply_preview) return displayMessageContent(message.reply_preview);
    if (!message.reply_to_message_id) return null;
    return displayMessageContent(combinedMessages.find((item) => item.id === message.reply_to_message_id)?.content) || 'Original message';
  };

  const renderPeer = (peer: Peer) => {
    const lastMessage = combinedMessages.length > 0 && peer.id === selectedPeer?.id
      ? displayMessageContent(combinedMessages[combinedMessages.length - 1]?.content) || 'Media message'
      : peer.bio ? peer.bio : friendIds.has(peer.id) ? 'Tap to chat' : 'Friend request required';
    const unreadCount = peer.id === selectedPeer?.id
      ? combinedMessages.filter((message) => message.sender_id === peer.id && !message.is_seen).length
      : 0;
    const isFriend = friendIds.has(peer.id);
    const isPinned = pinnedPeerIds.includes(peer.id);
    const isArchived = archivedPeerIds.includes(peer.id);

    return (
      <div
        key={peer.id}
        className={`conversation-card ${peer.id === selectedPeer?.id ? 'active' : ''} ${!isFriend ? 'locked' : ''} ${isPinned ? 'pinned' : ''}`}
        onClick={() => {
          selectPeer(peer);
        }}
        role="button"
        tabIndex={0}
        onKeyDown={(event) => {
          if (event.key === 'Enter' || event.key === ' ') {
            selectPeer(peer);
          }
        }}
      >
        <div className="conversation-avatar" aria-hidden="true">
          {(nicknames[peer.id] || peer.username).slice(0, 1).toUpperCase()}
          <span className={`presence-dot ${isFriend ? 'online' : ''}`} />
        </div>
        <div className="conversation-copy">
          <p className="conversation-title">
            {isPinned && <span className="pin-icon" aria-label="Pinned chat">📌 </span>}
            {nicknames[peer.id] || peer.username}
          </p>
          <p className="conversation-meta">{lastMessage}</p>
          {nicknames[peer.id] ? <small>Real profile: {peer.username}</small> : null}
        </div>
        <div className="conversation-side">
          {unreadCount > 0 ? <span className="unread-badge">{unreadCount}</span> : null}
          <div className="conversation-actions-row">
            <button
              type="button"
              className="peer-action-btn"
              title={isPinned ? 'Unpin chat' : 'Pin chat'}
              onClick={(e) => {
                e.stopPropagation();
                togglePinPeer(peer.id);
              }}
            >
              📌
            </button>
            <button
              type="button"
              className="peer-action-btn"
              title={isArchived ? 'Unarchive chat' : 'Archive chat'}
              onClick={(e) => {
                e.stopPropagation();
                toggleArchivePeer(peer.id);
              }}
            >
              📥
            </button>
          </div>
        </div>
      </div>
    );
  };

  const renderMessageContent = (content: string) => {
    const text = displayMessageContent(content);
    if (!searchTerm.trim() || isEncryptedToken(content)) {
      return text;
    }
    const query = searchTerm.trim();
    const idx = text.toLowerCase().indexOf(query.toLowerCase());
    if (idx === -1) {
      return text;
    }
    const parts = [];
    let remaining = text;
    let keyCounter = 0;
    while (remaining) {
      const matchIdx = remaining.toLowerCase().indexOf(query.toLowerCase());
      if (matchIdx === -1) {
        parts.push(remaining);
        break;
      }
      if (matchIdx > 0) {
        parts.push(remaining.substring(0, matchIdx));
      }
      parts.push(
        <mark key={`highlight-${keyCounter++}`} className="search-highlight">
          {remaining.substring(matchIdx, matchIdx + query.length)}
        </mark>
      );
      remaining = remaining.substring(matchIdx + query.length);
    }
    return <>{parts}</>;
  };

  const renderMessageRow = (item: any, index: number) => {
    if (item.type === 'date-separator') {
      return (
        <div key={item.id} className="chat-date-separator" role="separator" aria-label={item.dateString}>
          <span>{item.dateString}</span>
        </div>
      );
    }

    const message = item.data;
    const isConsecutive = item.isConsecutive;
    const isOutgoing = message.sender_id !== selectedPeer?.id;
    const replyPreview = getReplyPreview(message);
    const reactions = Object.entries(message.reactions ?? {}).filter(([, users]) => (users as any).length > 0) as [string, string[]][];

    const messageActionItems: DropdownItem[] = [
      {
        id: 'reply',
        label: 'Reply',
        onSelect: () => setReplyTarget(message)
      },
      {
        id: 'translate',
        label: 'Translate',
        onSelect: () => toggleMessageTranslation(message.id)
      },
      {
        id: 'smart-replies',
        label: 'Smart replies',
        onSelect: () => toggleSmartReplies(message.id)
      },
      {
        id: 'like',
        label: 'Like',
        onSelect: () => handleToggleReaction(message, '👍')
      },
      {
        id: 'pin',
        label: message.is_pinned ? 'Unpin' : 'Pin',
        onSelect: () => handleTogglePin(message)
      },
      {
        id: 'forward',
        label: 'Forward',
        onSelect: () => handleForwardMessage(message)
      }
    ];

    if (isOutgoing) {
      messageActionItems.push(
        {
          id: 'edit',
          label: 'Edit',
          onSelect: () => startEditingMessage(message)
        },
        {
          id: 'delete',
          label: 'Delete',
          onSelect: () => handleDeleteMessage(message)
        }
      );
    }

    return (
      <div
        key={message.id ?? `${message.timestamp}-${index}`}
        className={`message-row ${isOutgoing ? 'outgoing' : 'incoming'} ${isConsecutive ? 'consecutive' : ''}`}
        role="article"
        aria-label={`Message from ${isOutgoing ? 'you' : selectedPeer?.username ?? 'peer'}`}
      >
        <div className="message-quick-reactions">
          {['👍', '❤️', '😂', '😮', '😢', '🙏'].map((emoji) => (
            <button
              key={emoji}
              type="button"
              onClick={() => handleToggleReaction(message, emoji)}
              className="quick-reaction-btn"
              title={`React with ${emoji}`}
            >
              {emoji}
            </button>
          ))}
        </div>
        {message.is_pinned && <span className="pinned-label">Pinned</span>}
        {replyPreview && <div className="reply-preview">{replyPreview}</div>}

        {editingMessageId === message.id ? (
          <form className="message-edit-form" onSubmit={(event) => handleEditMessage(event, message)}>
            <input
              value={editingDraft}
              onChange={(event) => setEditingDraft(event.target.value)}
              placeholder="Edit message"
              aria-label="Edit message"
              autoFocus
            />
            <button type="submit" className="message-action">Save</button>
            <button type="button" className="message-action" onClick={cancelEditingMessage}>Cancel</button>
          </form>
        ) : (
          <>
            {message.media_url ? (
              <div className="media-preview">
                {message.media_type?.startsWith('image/') ? (
                  <img
                    src={message.media_url}
                    alt={message.media_name ?? 'image'}
                    className="media-image"
                    loading="lazy"
                  />
                ) : message.media_type?.startsWith('video/') ? (
                  <video controls className="media-video" src={message.media_url} />
                ) : message.media_type?.startsWith('audio/') ? (
                  <audio controls src={message.media_url} className="media-audio" />
                ) : (
                  <a
                    href={message.media_url}
                    target="_blank"
                    rel="noreferrer"
                    className="media-link"
                  >
                    {message.media_name ?? 'Open attachment'}
                  </a>
                )}
              </div>
            ) : null}

            {message.content ? (
              <p className={isEncryptedToken(message.content) ? 'encrypted-message-placeholder' : undefined}>
                {renderMessageContent(message.content)}
              </p>
            ) : null}
          </>
        )}

        {reactions.length > 0 ? (
          <div className="reaction-strip" aria-label="Message reactions">
            {reactions.map(([emoji, users]) => (
              <button
                key={emoji}
                type="button"
                className="reaction-chip"
                onClick={() => handleToggleReaction(message, emoji)}
              >
                {emoji} {users.length}
              </button>
            ))}
          </div>
        ) : null}

        <div className="message-meta">
          <small>{formatTimestamp(message.timestamp)}{message.edited_at ? ' · edited' : ''}</small>
          <div className="message-actions-container">
            <MessageBookmark messageId={message.id} />
            <Dropdown
              trigger={<span className="message-actions-trigger" role="button" aria-label="Message actions">⋮</span>}
              items={messageActionItems}
              align="end"
            />
          </div>
        </div>
        {activeTranslationMessageId === message.id ? (
          <div className="message-feature-panel">
            <TranslateMessage messageId={message.id} sourceText={displayMessageContent(message.content)} />
          </div>
        ) : null}
        {activeSmartReplyMessageId === message.id ? (
          <div className="message-feature-panel">
            <SmartReplies messageId={message.id} onReplySelected={(text) => setDraft(text)} />
          </div>
        ) : null}
      </div>
    );
  };

  return (
    <div className={`page-panel glass-panel chat-page chat-page-container ${isThreadOpen ? 'thread-open' : ''} ${isDetailsOpen ? 'details-open' : ''}`}>
      <div className="chat-grid">
        <aside className="chat-list" aria-label="Conversations">
          <div className="chat-list-header">
            <div>
              <span className="hero-label">Inbox</span>
              <h3>Recent chats</h3>
            </div>
            <Link className="primary-button add-friend-sidebar-btn" to="/friends" title="Add friend">Add friend</Link>
          </div>

          <div className="chat-list-search-bar">
            <input
              type="text"
              placeholder="Search chats..."
              value={chatListSearch}
              onChange={(e) => setChatListSearch(e.target.value)}
              className="chat-search-input"
              aria-label="Search conversations"
            />
            <div className="chat-list-filters">
              <button
                type="button"
                className={`filter-tab-btn ${chatListFilter === 'all' && !showArchived ? 'active' : ''}`}
                onClick={() => { setChatListFilter('all'); setShowArchived(false); }}
              >
                All
              </button>
              <button
                type="button"
                className={`filter-tab-btn ${chatListFilter === 'friends' && !showArchived ? 'active' : ''}`}
                onClick={() => { setChatListFilter('friends'); setShowArchived(false); }}
              >
                Friends
              </button>
              <button
                type="button"
                className={`filter-tab-btn ${showArchived ? 'active' : ''}`}
                onClick={() => setShowArchived(true)}
              >
                Archived
              </button>
            </div>
          </div>

          <div className="chat-list-content">
            {loadingPeers ? (
              <div className="conversation-card loading" aria-live="polite">Loading chats...</div>
            ) : processedPeers.length > 0 ? (
              processedPeers.map(renderPeer)
            ) : (
              <div className="conversation-card empty">
                {chatListSearch.trim() || chatListFilter !== 'all' || showArchived
                  ? 'No conversations found matching filters.'
                  : 'No available chat peers yet.'}
              </div>
            )}
          </div>

          {fetchError ? <div className="error-message" role="alert">{fetchError}</div> : null}
        </aside>

        {!selectedPeer ? (
          <section className="chat-thread-welcome glass-panel" aria-label="Welcome screen">
            <div className="welcome-content">
              <div className="welcome-illustration" aria-hidden="true">💬</div>
              <h2>Welcome to ChattingApp</h2>
              <p>Select a contact from the inbox list or add new friends to start messaging.</p>
              <div className="welcome-actions">
                <Link to="/friends" className="primary-button">Find friends</Link>
                <Link to="/groups" className="secondary-button">Explore communities</Link>
              </div>
              <div className="welcome-onboarding-steps">
                <h4>Getting Started Checklist</h4>
                <ul>
                  <li><span className="checkbox-icon">✅</span> Account created</li>
                  <li><span className="checkbox-icon">👤</span> Add friends by username</li>
                  <li><span className="checkbox-icon">💬</span> Send direct encrypted messages</li>
                  <li><span className="checkbox-icon">🌐</span> Join hyperlocal societies</li>
                </ul>
              </div>
            </div>
          </section>
        ) : (
          <section className="chat-thread glass-panel" aria-label="Chat thread">
            <div className="thread-header">
              <div className="header-contact-info">
                <button className="ghost-button chat-back-button" type="button" onClick={() => setIsThreadOpen(false)} aria-label="Back to chats">
                  ←
                </button>
                <div className="contact-avatar" onClick={() => setIsDetailsOpen(!isDetailsOpen)} role="button" tabIndex={0} onKeyDown={(e) => e.key === 'Enter' && setIsDetailsOpen(!isDetailsOpen)}>
                  {(nicknames[selectedPeer.id] || selectedPeer.username).slice(0, 1).toUpperCase()}
                </div>
                <div className="contact-details" onClick={() => setIsDetailsOpen(!isDetailsOpen)} role="button" tabIndex={0} onKeyDown={(e) => e.key === 'Enter' && setIsDetailsOpen(!isDetailsOpen)}>
                  <div className="contact-name-row">
                    <h3>{selectedPeerLabel}</h3>
                    <span className="verified-badge-tick" title="Verified User" aria-label="Verified user">☑️</span>
                  </div>
                  <p className="contact-status-subtitle">
                    {peerStatus === 'online' ? (
                      <span className="status-online">Online</span>
                    ) : (
                      <span className="status-offline">Offline</span>
                    )}
                    {isPeerTyping && <span className="typing-status"> · typing...</span>}
                  </p>
                </div>
              </div>
              <div className="header-actions">
                <button className={`icon-btn search-thread-btn ${isSearchOpen ? 'active' : ''}`} type="button" title="Search messages" onClick={() => { setIsSearchOpen(!isSearchOpen); if (isSearchOpen) setSearchTerm(''); }} aria-label="Search messages">🔍</button>
                <button className="icon-btn call-btn" type="button" title="Voice call" onClick={() => alert('Voice call feature is coming soon!')} aria-label="Voice call">📞</button>
                <button className="icon-btn video-call-btn" type="button" title="Video call" onClick={() => alert('Video call feature is coming soon!')} aria-label="Video call">🎥</button>
                <button className="icon-btn info-btn" type="button" title={isDetailsOpen ? 'Hide contact details' : 'Show contact details'} onClick={() => setIsDetailsOpen(!isDetailsOpen)} aria-label="Toggle contact details">ℹ️</button>
              </div>
            </div>

            <ReconnectBanner
              isConnecting={isConnecting}
              isConnected={isConnected}
              error={error}
              label="Direct chat"
            />

            {!canChatWithSelectedPeer ? (
              <div className="chat-lock-state" role="status">
                <strong>Friend request required</strong>
                <p>Non-friends cannot chat. Send a request and this conversation unlocks after acceptance.</p>
                <button
                  className="primary-button"
                  type="button"
                  disabled={requestStatusByPeerId[selectedPeer.id] === 'pending' || requestStatusByPeerId[selectedPeer.id] === 'blocked'}
                  onClick={async () => {
                    setRequestStatusByPeerId((prev) => ({ ...prev, [selectedPeer.id]: 'pending' }));
                    try {
                      await apiPost(`/api/v1/friends/requests/${selectedPeer.id}`, {});
                      setFetchError('Friend request sent. Chat will unlock when accepted.');
                    } catch (err) {
                      setRequestStatusByPeerId((prev) => ({ ...prev, [selectedPeer.id]: 'idle' }));
                      setFetchError(err instanceof Error ? err.message : 'Could not send friend request');
                    }
                  }}
                >
                  {requestStatusByPeerId[selectedPeer.id] === 'pending' ? 'Request pending' : 'Send friend request'}
                </button>
              </div>
            ) : null}

            <div className="chat-feature-toolbar">
              <ScheduleMessage receiverId={selectedPeer.id} onScheduled={() => setFetchError('Scheduled message created')} />
              <VoiceMessage receiverId={selectedPeer.id} onSendVoiceMessage={handleSendVoiceMessage} />
            </div>

            {isSearchOpen && (
              <div className="message-search">
                <input
                  type="search"
                  placeholder="Search messages..."
                  value={searchTerm}
                  onChange={(event) => setSearchTerm(event.target.value)}
                  autoFocus
                />
                {searchTerm.trim() ? (
                  <span className="pill soft">{isSearching ? 'Searching...' : `${searchResults.length} found`}</span>
                ) : null}
                <button className="ghost-button" type="button" onClick={() => { setIsSearchOpen(false); setSearchTerm(''); }} style={{ marginLeft: '8px', padding: '4px 8px' }}>Cancel</button>
              </div>
            )}

            <div
              ref={threadMessagesRef}
              onScroll={(e) => {
                const target = e.currentTarget;
                const isScrollUp = target.scrollHeight - target.scrollTop - target.clientHeight > 300;
                setShowScrollBottom(isScrollUp);
              }}
              className="thread-messages"
              role="log"
              aria-live="polite"
              aria-atomic="false"
            >
              <div className="chat-wallpaper" aria-hidden="true" />
              {hasMoreHistory && !searchTerm.trim() && messageHistory.length > 0 ? (
                <button
                  type="button"
                  className="ghost-button load-older-button"
                  onClick={handleLoadOlder}
                  disabled={loadingOlder}
                >
                  {loadingOlder ? 'Loading older messages...' : 'Load older messages'}
                </button>
              ) : null}

              {import.meta.env.DEV ? (
                <div className="dev-badge">Chat render count: {renderCount}</div>
              ) : null}

              {loadingHistory ? (
                <div className="message-row incoming">
                  <p>Loading conversation history...</p>
                </div>
              ) : renderableChatItems.length === 0 ? (
                <div className="message-row incoming">
                  <p>{searchTerm.trim() ? 'No messages match your search.' : 'Start a new conversation by sending the first message.'}</p>
                </div>
              ) : renderableChatItems.length > 80 ? (
                <div ref={listContainerRef} className="virtualized-thread-list">
                  <VirtualizedList
                    items={renderableChatItems}
                    itemHeight={estimateChatMessageHeight}
                    estimatedItemHeight={140}
                    height={listHeight}
                    overscan={6}
                    listRef={virtualListRef}
                    className="virtualized-message-list"
                    renderItem={(item, index) => renderMessageRow(item, index)}
                  />
                </div>
              ) : (
                renderableChatItems.map((item, index) => renderMessageRow(item, index))
              )}

              {error ? (
                <div className="message-row incoming error-message" role="alert">
                  <p>{error}</p>
                </div>
              ) : null}
            </div>

            {showScrollBottom && (
              <button
                type="button"
                className="scroll-bottom-btn"
                onClick={() => handleScrollToBottom()}
                aria-label="Scroll to bottom"
              >
                ↓
              </button>
            )}

            <form className="message-input floating-input-bar glass-panel" onSubmit={handleSend} aria-label="Send message form">
              {replyTarget ? (
                <div className="reply-composer" aria-live="polite">
                  <span className="reply-preview-text">Replying to: {displayMessageContent(replyTarget.content)}</span>
                  <button type="button" className="icon-btn close-reply" onClick={() => setReplyTarget(null)} aria-label="Cancel reply">
                    ✕
                  </button>
                </div>
              ) : null}

              {stagedFile && (
                <div className="composer-staging-area">
                  <div className="staging-preview-card">
                    <div className="staging-thumb">
                      {stagedFile.type.startsWith('image/') ? (
                        <img src={URL.createObjectURL(stagedFile)} alt="Staged upload" className="staging-image-preview" />
                      ) : (
                        <span className="file-icon">📄</span>
                      )}
                    </div>
                    <div className="staging-meta">
                      <span className="staging-name">{stagedFile.name}</span>
                      <span className="staging-size">{(stagedFile.size / 1024).toFixed(1)} KB</span>
                    </div>
                    <button
                      type="button"
                      className="staging-remove-btn"
                      onClick={() => setStagedFile(null)}
                      aria-label="Remove attachment"
                    >
                      ✕
                    </button>
                  </div>
                </div>
              )}

              <div className="input-row">
                <button type="button" className="icon-btn emoji-toggle" aria-label="Choose emoji" disabled={!selectedPeer}>
                  😊
                </button>

                <label className="icon-btn attachment-btn" aria-label="Attach file">
                  📎
                  <input
                    type="file"
                    className="sr-only"
                    aria-label="Attach file"
                    title="Attach file"
                    disabled={!selectedPeer || !isConnected || mediaSending}
                    accept="image/*,video/*,audio/*,application/pdf,text/plain"
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) setStagedFile(file);
                      e.currentTarget.value = '';
                    }}
                  />
                </label>

                <div className="input-stack">
                  <input
                    className="chat-textfield"
                    placeholder={selectedPeer ? 'Message...' : 'Select a chat to begin'}
                    value={draft}
                    onChange={handleDraftChange}
                    disabled={!isConnected || !selectedPeer || !canChatWithSelectedPeer}
                    aria-label="Message text"
                    autoComplete="off"
                  />
                  {stagedFile && (
                    <input
                      className="caption-textfield animate-fade-in"
                      type="text"
                      placeholder="Add a caption..."
                      value={mediaCaption}
                      onChange={(e) => setMediaCaption(e.target.value)}
                      disabled={!selectedPeer || !isConnected || mediaSending || !canChatWithSelectedPeer}
                      aria-label="Media caption"
                    />
                  )}
                </div>

                <button
                  className="primary-button send-btn"
                  type="submit"
                  disabled={!isConnected || (!draft.trim() && !stagedFile) || !selectedPeer || !canChatWithSelectedPeer}
                  aria-label="Send message"
                >
                  ➤
                </button>
              </div>

              {mediaSending && <div className="sending-indicator" aria-live="polite">Uploading media...</div>}
            </form>
          </section>
        )}

        {isDetailsOpen && selectedPeer && (
          <aside className="chat-details-panel glass-panel animate-slide-left" aria-label="Contact details">
            <div className="details-header">
              <h3>Contact Info</h3>
              <button className="icon-btn close-details-btn" onClick={() => setIsDetailsOpen(false)} aria-label="Close contact details">✕</button>
            </div>
            <div className="details-scrollable-content">
              <div className="details-profile-card">
                <div className="details-avatar">
                  {(nicknames[selectedPeer.id] || selectedPeer.username).slice(0, 1).toUpperCase()}
                </div>
                <h3>{nicknames[selectedPeer.id] || selectedPeer.username}</h3>
                <p className="details-subtext">@{selectedPeer.username}</p>
                {selectedPeer.email && <p className="details-email">{selectedPeer.email}</p>}
              </div>

              <div className="details-form-section">
                <label htmlFor="nickname-details-input">Edit Local Nickname</label>
                <input
                  id="nickname-details-input"
                  className="chat-textfield nickname-details-input"
                  value={nicknames[selectedPeer.id] ?? ''}
                  placeholder="Enter local nickname"
                  onChange={(event) => setNicknames((prev) => ({ ...prev, [selectedPeer.id]: event.target.value }))}
                />
              </div>

              {selectedPeer.bio && (
                <div className="details-bio-section">
                  <h4>Bio</h4>
                  <p>{selectedPeer.bio}</p>
                </div>
              )}

              <div className="details-gallery-section">
                <h4>Shared Media</h4>
                <SharedMediaGallery receiverId={selectedPeer.id} conversationId={`${selectedPeer.id}-${user?.uid ?? 'anonymous'}`} />
              </div>

              <div className="details-actions-section">
                <h4>Actions</h4>
                <ChatBackupExport />
                <button type="button" className="danger-button clear-history-btn" onClick={() => alert('Clear history is coming soon!')}>Clear Chat History</button>
              </div>
            </div>
          </aside>
        )}
      </div>
    </div>
  );
}

export default Chat;
