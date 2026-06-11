/* eslint-disable react/no-unescaped-entities */
//src/pages/Feed.tsx
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { apiGet, apiPost } from '../lib/api';
import MediaUploader from '../components/MediaUploader';
import { useAuth } from '../contexts/AuthContext';
import { useFeedStore } from '../stores/feedStore';
import Modal from '../ui/Modal';

interface PostResponse {
  id: string;
  user_id: string;
  content: string;
  visibility: string;
  created_at: string;
}

interface LikeState {
  post_id: string;
  likes: number;
  liked: boolean;
}

interface RepostState {
  post_id: string;
  reposts: number;
  reposted: boolean;
}

interface CommentState {
  id: string;
  post_id: string;
  user_id: string;
  content: string;
  created_at: string;
}

const DEFAULT_LIMIT = 12;
const IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.gif', '.webp'];
const VIDEO_EXTENSIONS = ['.mp4', '.webm', '.ogg'];

function findMediaUrl(text: string) {
  const urls = Array.from(text.matchAll(/https?:\/\/[\w\-./?=&%]+/gi)).map((match) => match[0]);
  if (!urls.length) return null;
  return urls.find((url) => {
    const lower = url.toLowerCase();
    return IMAGE_EXTENSIONS.some((ext) => lower.endsWith(ext)) || VIDEO_EXTENSIONS.some((ext) => lower.endsWith(ext));
  });
}

function getMediaType(url: string) {
  const lower = url.toLowerCase();
  if (IMAGE_EXTENSIONS.some((ext) => lower.endsWith(ext))) return 'image';
  if (VIDEO_EXTENSIONS.some((ext) => lower.endsWith(ext))) return 'video';
  return null;
}

function stripMediaAndLocation(text: string, mediaUrl: string | null) {
  return text
    .replace(mediaUrl ?? '', '')
    .replace('[Nearby]', '')
    .trim();
}

function Feed() {
  const { user } = useAuth();
  const { items: cachedItems, cursor: cachedCursor, hasMore: cachedHasMore, setFeedCache, clearFeedCache } = useFeedStore();

  const [posts, setPosts] = useState<PostResponse[]>(cachedItems);
  const [feedCursor, setFeedCursor] = useState<string | null>(cachedCursor);
  const [hasMore, setHasMore] = useState<boolean>(cachedHasMore);
  const [likesByPostId, setLikesByPostId] = useState<Record<string, LikeState>>({});
  const [repostsByPostId, setRepostsByPostId] = useState<Record<string, RepostState>>({});
  const [commentsByPostId, setCommentsByPostId] = useState<Record<string, CommentState[]>>({});
  const [commentDraftByPostId, setCommentDraftByPostId] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'nearby' | 'friends' | 'following' | 'trending' | 'global'>('friends');
  const [refreshIndex, setRefreshIndex] = useState(0);
  const [newPostContent, setNewPostContent] = useState('');
  const [attachedMediaUrl, setAttachedMediaUrl] = useState<string | null>(null);
  const [postVisibility, setPostVisibility] = useState<'public' | 'friends' | 'followers'>('public');
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [locationAllowed, setLocationAllowed] = useState(false);
  const [locationNote, setLocationNote] = useState('Location is off. Nearby stays private until you opt in.');

  const loaderRef = useRef<HTMLDivElement | null>(null);
  const observerRef = useRef<IntersectionObserver | null>(null);

  const canFetch = useMemo(() => Boolean(user), [user]);

  const getFeedPath = useCallback(
    (meId: string, cursor: string | null) => {
      let base = `/api/v1/posts/feed/${meId}`;
      if (viewMode === 'trending') {
        base = `/api/v1/posts/trending/${meId}`;
      } else if (viewMode === 'global') {
        base = `/api/v1/posts/explore/${meId}`;
      } else if (viewMode === 'following') {
        base = `/api/v1/posts/recommendations/${meId}`;
      }
      return cursor ? `${base}?cursor=${encodeURIComponent(cursor)}&limit=${DEFAULT_LIMIT}` : `${base}?limit=${DEFAULT_LIMIT}`;
    },
    [viewMode],
  );

  async function primeLikesAndComments(nextPosts: PostResponse[]) {
    const likeStates = await Promise.allSettled(
      nextPosts.map(async (p) => apiGet(`/api/v1/posts/${p.id}/likes`) as Promise<LikeState>),
    );
    const repostStates = await Promise.allSettled(
      nextPosts.map(async (p) => apiGet(`/api/v1/posts/${p.id}/reposts`) as Promise<RepostState>),
    );
    const commentStates = await Promise.allSettled(
      nextPosts.map(async (p) => apiGet(`/api/v1/posts/${p.id}/comments?limit=5`) as Promise<CommentState[]>),
    );

    const nextLikes: Record<string, LikeState> = {};
    likeStates.forEach((result) => {
      if (result.status === 'fulfilled') nextLikes[result.value.post_id] = result.value;
    });

    const nextReposts: Record<string, RepostState> = {};
    repostStates.forEach((result) => {
      if (result.status === 'fulfilled') nextReposts[result.value.post_id] = result.value;
    });

    const nextComments: Record<string, CommentState[]> = {};
    commentStates.forEach((result, index) => {
      nextComments[nextPosts[index].id] = result.status === 'fulfilled' ? result.value ?? [] : [];
    });

    setLikesByPostId((prev) => ({ ...prev, ...nextLikes }));
    setRepostsByPostId((prev) => ({ ...prev, ...nextReposts }));
    setCommentsByPostId((prev) => ({ ...prev, ...nextComments }));
  }

  const updateFeedCache = useCallback(
    (items: PostResponse[], cursor: string | null, hasMoreFlag: boolean) => {
      setFeedCache(items, cursor, hasMoreFlag);
    },
    [setFeedCache],
  );

  const fetchPage = useCallback(
    async (cursor: string | null, isRefresh: boolean, currentPosts: PostResponse[]) => {
      const me = (await apiGet('/api/v1/users/me')) as { id: string };
      const path = getFeedPath(me.id, cursor);

      const payload = (await apiGet(path)) as { feed: PostResponse[] };
      const nextPosts = payload.feed ?? [];
      const updatedPosts = isRefresh ? nextPosts : [...currentPosts, ...nextPosts];

      setPosts(updatedPosts);
      void primeLikesAndComments(nextPosts);

      const nextCursor = nextPosts.length > 0 ? nextPosts[nextPosts.length - 1].created_at : cursor;
      const nextHasMore = nextPosts.length === DEFAULT_LIMIT;
      setFeedCursor(nextCursor);
      setHasMore(nextHasMore);
      updateFeedCache(updatedPosts, nextCursor, nextHasMore);
    },
    [getFeedPath, updateFeedCache],
  );

  useEffect(() => {
    if (!canFetch) return;

    let isMounted = true;
    const cachedAvailable = viewMode === 'friends' && cachedItems.length > 0;

    (async () => {
      try {
        setLoading(true);
        setFetchError(null);

        if (!isMounted) return;

        setLikesByPostId({});
        setRepostsByPostId({});
        setCommentsByPostId({});
        setCommentDraftByPostId({});

        if (cachedAvailable) {
          setPosts(cachedItems);
          setFeedCursor(cachedCursor);
          setHasMore(cachedHasMore);
        } else {
          setPosts([]);
          setFeedCursor(null);
          setHasMore(true);
        }

        void fetchPage(null, true, [])
          .catch((err) => {
            if (!isMounted) return;
            setFetchError(err instanceof Error ? err.message : 'Could not load feed');
          })
          .finally(() => {
            if (isMounted) setLoading(false);
          });
      } catch (err) {
        if (!isMounted) return;
        setFetchError(err instanceof Error ? err.message : 'Could not load feed');
        setLoading(false);
      }
    })();

    return () => {
      isMounted = false;
    };
  }, [canFetch, fetchPage, refreshIndex, viewMode, cachedItems, cachedCursor, cachedHasMore]);

  useEffect(() => {
    clearFeedCache();
  }, [viewMode, clearFeedCache]);

  const requestNearby = () => {
    if (!navigator.geolocation) {
      setLocationNote('Location is not available in this browser.');
      return;
    }

    navigator.geolocation.getCurrentPosition(
      () => {
        setLocationAllowed(true);
        setLocationNote('Nearby is enabled for this session. Exact location is not stored by the UI.');
        setViewMode('nearby');
      },
      () => {
        setLocationAllowed(false);
        setLocationNote('Location permission was not granted. You can still use all other filters.');
      },
      { enableHighAccuracy: false, maximumAge: 300000, timeout: 7000 },
    );
  };

  const loadMore = useCallback(async () => {
    if (!hasMore || loadingMore || loading) return;
    setLoadingMore(true);
    setFetchError(null);

    try {
      await fetchPage(feedCursor, false, posts);
    } catch (err) {
      setFetchError(err instanceof Error ? err.message : 'Could not load more');
    } finally {
      setLoadingMore(false);
    }
  }, [fetchPage, feedCursor, hasMore, loading, loadingMore, posts]);

  useEffect(() => {
    if (!loaderRef.current || loading || loadingMore || !hasMore) return;

    observerRef.current?.disconnect();
    observerRef.current = new IntersectionObserver((entries) => {
      if (entries[0]?.isIntersecting) {
        void loadMore();
      }
    });

    observerRef.current.observe(loaderRef.current);
    return () => observerRef.current?.disconnect();
  }, [hasMore, loadMore, loading, loadingMore]);

  const submitComment = async (postId: string) => {
    const content = (commentDraftByPostId[postId] ?? '').trim();
    if (!content) return;

    const tempComment: CommentState = {
      id: `temp-${Date.now()}`,
      post_id: postId,
      user_id: user?.uid ?? 'me',
      content,
      created_at: new Date().toISOString(),
    };

    setCommentsByPostId((prev) => {
      const current = prev[postId] ?? [];
      return { ...prev, [postId]: [tempComment, ...current] };
    });
    setCommentDraftByPostId((prev) => ({ ...prev, [postId]: '' }));

    try {
      const res = (await apiPost(`/api/v1/posts/${postId}/comments`, { content })) as CommentState;
      setCommentsByPostId((prev) => {
        const current = prev[postId] ?? [];
        return {
          ...prev,
          [postId]: [res, ...current.filter((item) => item.id !== tempComment.id)],
        };
      });
    } catch {
      setCommentsByPostId((prev) => {
        const current = prev[postId] ?? [];
        return {
          ...prev,
          [postId]: current.filter((item) => item.id !== tempComment.id),
        };
      });
    }
  };

  const renderSkeletonCards = () => {
    return Array.from({ length: 3 }).map((_, index) => (
      <article key={index} className="feed-card skeleton-card">
        <div className="skeleton-title" />
        <div className="skeleton-body" />
        <div className="skeleton-actions" />
      </article>
    ));
  };

  const createPost = async () => {
    if (!newPostContent.trim() && !attachedMediaUrl) return;
    const contentParts = [newPostContent.trim()];
    if (attachedMediaUrl) contentParts.push(attachedMediaUrl);
    if (locationAllowed && viewMode === 'nearby') contentParts.push('[Nearby]');
    const content = contentParts.filter(Boolean).join('\n');

    const optimisticPost: PostResponse = {
      id: `temp-${Date.now()}`,
      user_id: user?.uid ?? 'me',
      content,
      visibility: postVisibility,
      created_at: new Date().toISOString(),
    };

    setPosts((prev) => [optimisticPost, ...prev]);
    setNewPostContent('');
    setAttachedMediaUrl(null);
    setIsCreateOpen(false);

    try {
      const created = await apiPost('/api/v1/posts/create', { content, visibility: postVisibility }) as PostResponse;
      setPosts((prev) => prev.map((post) => (post.id === optimisticPost.id ? created : post)));
    } catch (err) {
      setPosts((prev) => prev.filter((post) => post.id !== optimisticPost.id));
      setFetchError(err instanceof Error ? err.message : 'Could not create post');
    }
  };

  const hasVisiblePosts = posts.length > 0;

  return (
    <div className="page-panel glass-panel">
      <div className="panel-header">
        <div>
          <span className="hero-label">Feed</span>
          <h2>Pulse stream</h2>
        </div>
        <div className="feed-header-actions">
          {(['nearby', 'friends', 'following', 'trending', 'global'] as const).map((mode) => (
            <button
              key={mode}
              className={viewMode === mode ? 'secondary-button' : 'ghost-button'}
              type="button"
              onClick={() => {
                if (mode === 'nearby' && !locationAllowed) requestNearby();
                else setViewMode(mode);
              }}
              disabled={loading}
            >
              {mode[0].toUpperCase() + mode.slice(1)}
            </button>
          ))}
          <button
            className="ghost-button"
            type="button"
            onClick={() => setRefreshIndex((v) => v + 1)}
            disabled={loading}
          >
            {loading ? 'Refreshing...' : 'Refresh'}
          </button>
          <button className="primary-button create-post-button" type="button" onClick={() => setIsCreateOpen(true)}>
            Create post
          </button>
        </div>
      </div>
      <p className="small-note">
        {viewMode === 'trending'
          ? 'Showing ranked trending posts for your network.'
          : viewMode === 'global'
          ? 'Exploring public posts, hashtags, and broader community activity.'
          : viewMode === 'following'
          ? 'Showing recommendations and followed activity.'
          : viewMode === 'nearby'
          ? locationNote
          : 'Showing friend-first activity and posts you are allowed to see.'}
      </p>

      {fetchError ? <div className="error-message">{fetchError}</div> : null}

      <div className="feed-list">
        {loading && !hasVisiblePosts ? (
          renderSkeletonCards()
        ) : posts.length === 0 ? (
          <article className="feed-card">
            <p>No posts available.</p>
          </article>
        ) : (
          <>
            {posts.map((post) => {
              const likeState = likesByPostId[post.id];
              const likes = likeState?.likes ?? 0;
              const liked = likeState?.liked ?? false;
              const repostState = repostsByPostId[post.id];
              const reposts = repostState?.reposts ?? 0;
              const reposted = repostState?.reposted ?? false;
              const comments = commentsByPostId[post.id] ?? [];
              const mediaUrl = findMediaUrl(post.content);
              const mediaType = mediaUrl ? getMediaType(mediaUrl) : null;
              const displayContent = stripMediaAndLocation(post.content, mediaUrl ?? null);
              const isNearbyPost = post.content.includes('[Nearby]');

              return (
                <article key={post.id} className="feed-card">
                  <header className="feed-card-header">
                    <div className="conversation-avatar" aria-hidden="true">
                      {post.user_id.slice(0, 1).toUpperCase()}
                    </div>
                    <div>
                      <h3>{post.user_id === user?.uid ? 'You' : `User ${post.user_id.slice(0, 8)}`}</h3>
                      <div className="feed-card-meta">
                        <span>{new Date(post.created_at).toLocaleString()}</span>
                        <span>{isNearbyPost ? 'Nearby' : 'Global'}</span>
                        <span>#{post.visibility}</span>
                      </div>
                    </div>
                  </header>
                  {displayContent ? <p>{displayContent}</p> : null}
                  {mediaUrl && mediaType === 'image' ? (
                    <img className="feed-media" src={mediaUrl} alt="Post media" loading="lazy" />
                  ) : null}
                  {mediaUrl && mediaType === 'video' ? (
                    <video className="feed-media" controls src={mediaUrl} />
                  ) : null}

                  <div className="feed-actions">
                    <button
                      type="button"
                      className={`feed-action-btn like-btn ${liked ? 'active' : ''}`}
                      aria-label={liked ? 'Unlike post' : 'Like post'}
                      onClick={async () => {
                        const currentLike = likeState ?? { likes: 0, liked: false, post_id: post.id };
                        const optimisticLike = {
                          ...currentLike,
                          liked: !currentLike.liked,
                          likes: currentLike.liked ? Math.max(0, currentLike.likes - 1) : currentLike.likes + 1,
                        };
                        setLikesByPostId((prev) => ({ ...prev, [post.id]: optimisticLike }));

                        try {
                          const res = (await apiPost(`/api/v1/posts/${post.id}/like`, {})) as LikeState;
                          setLikesByPostId((prev) => ({ ...prev, [post.id]: res }));
                        } catch {
                          setLikesByPostId((prev) => ({ ...prev, [post.id]: currentLike }));
                        }
                      }}
                    >
                      <span className="action-icon">❤️</span>
                      <span className="action-count">{likes}</span>
                    </button>

                    <button
                      type="button"
                      className={`feed-action-btn repost-btn ${reposted ? 'active' : ''}`}
                      aria-label={reposted ? 'Unrepost' : 'Repost'}
                      onClick={async () => {
                        const currentRepost = repostState ?? { reposts: 0, reposted: false, post_id: post.id };
                        const optimisticRepost = {
                          ...currentRepost,
                          reposted: !currentRepost.reposted,
                          reposts: currentRepost.reposted ? Math.max(0, currentRepost.reposts - 1) : currentRepost.reposts + 1,
                        };
                        setRepostsByPostId((prev) => ({ ...prev, [post.id]: optimisticRepost }));

                        try {
                          const res = (await apiPost(`/api/v1/posts/${post.id}/repost`, {})) as RepostState;
                          setRepostsByPostId((prev) => ({ ...prev, [post.id]: res }));
                        } catch {
                          setRepostsByPostId((prev) => ({ ...prev, [post.id]: currentRepost }));
                        }
                      }}
                    >
                      <span className="action-icon">🔁</span>
                      <span className="action-count">{reposts}</span>
                    </button>

                    <button
                      type="button"
                      className="feed-action-btn comment-btn"
                      aria-label="View or write comments"
                    >
                      <span className="action-icon">💬</span>
                      <span className="action-count">{comments.length}</span>
                    </button>
                  </div>

                  <div className="feed-comments">
                    <div className="comment-list">
                      {comments.length === 0 ? (
                        <p className="comment-empty">No comments yet.</p>
                      ) : (
                        comments.slice(0, 5).map((c) => (
                          <div key={c.id} className="comment-row">
                            <p className="comment-content">{c.content}</p>
                            <small className="comment-time">{new Date(c.created_at).toLocaleString()}</small>
                          </div>
                        ))
                      )}
                    </div>

                    <form
                      className="comment-composer"
                      onSubmit={(e) => {
                        e.preventDefault();
                        void submitComment(post.id);
                      }}
                    >
                      <input
                        type="text"
                        placeholder="Write a comment..."
                        value={commentDraftByPostId[post.id] ?? ''}
                        onChange={(e) =>
                          setCommentDraftByPostId((prev) => ({ ...prev, [post.id]: e.target.value }))
                        }
                      />
                      <button className="secondary-button" type="submit">
                        Comment
                      </button>
                    </form>
                  </div>
                </article>
              );
            })}

            {hasMore ? (
              <div ref={loaderRef} className="load-more-anchor">
                <button
                  type="button"
                  className="ghost-button load-older-button"
                  onClick={() => void loadMore()}
                  disabled={loadingMore}
                >
                  {loadingMore ? 'Loading more...' : 'Load more'}
                </button>
              </div>
            ) : (
              <div className="soft-muted feed-end-message">
                You’ve reached the end.
              </div>
            )}
            {loading || loadingMore ? renderSkeletonCards().slice(0, 1) : null}
          </>
        )}
      </div>

      <button className="floating-action-button" type="button" onClick={() => setIsCreateOpen(true)} aria-label="Create post">
        +
      </button>

      <Modal title="Create post" isOpen={isCreateOpen} onClose={() => setIsCreateOpen(false)}>
        <div className="create-post-sheet">
          <textarea
            value={newPostContent}
            onChange={(event) => setNewPostContent(event.target.value)}
            placeholder="What's happening?"
            rows={5}
          />
          <div className="create-post-controls">
            <label>
              Visibility
              <select value={postVisibility} onChange={(event) => setPostVisibility(event.target.value as typeof postVisibility)}>
                <option value="public">Public</option>
                <option value="friends">Friends</option>
                <option value="followers">Following</option>
              </select>
            </label>
            <button className="ghost-button" type="button" onClick={requestNearby}>
              {locationAllowed ? 'Location enabled' : 'Add location'}
            </button>
          </div>
          <MediaUploader onComplete={(url) => setAttachedMediaUrl(url ?? null)} />
          {attachedMediaUrl ? <p className="small-note">Media attached: {attachedMediaUrl}</p> : null}
          <p className="small-note">{locationNote}</p>
          <button className="primary-button" type="button" onClick={() => void createPost()}>
            Post
          </button>
        </div>
      </Modal>
    </div>
  );
}

export default Feed;
