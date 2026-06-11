# Performance Report

This report documents the performance audits, caching strategies, and load-time optimizations for the ChattingApp platform.

---

## 1. Frontend Performance Optimizations

- **Component Lazy Loading**: Routes are loaded asynchronously using `React.lazy` and wrapped in `React.Suspense` fallback boundaries, reducing initial bundle sizes.
- **Preloading Strategy**: A dynamic preloader in `App.tsx` imports major pages (Feed, Chat, Groups, Profile) 1.2 seconds after mount, ensuring sub-second route transitions once the user is authenticated.
- **Virtualized Lists**: Long chats and post lists use virtualized rendering (`react-window`), maintaining stable memory footprints by only mounting nodes in the active viewport.

---

## 2. Caching Strategy & Redis Performance

- **EPHEMERAL CACHING**: Relations (friendships, blocks, and follows) are cached in Redis via `FeedService._load_relationships` to minimize expensive database joins on feed rendering.
- **Cache invalidation**: Caches are invalidated instantly when users perform muting, following, or blocking actions.
- **Connection timeouts**: The Redis client is configured with socket connection timeouts (`socket_connect_timeout=5`) to prevent backend worker blockage if Redis encounters downtime.

---

## 3. Database Performance Tuning

- **Eager Loading**: Eager relationship fetching via `selectinload` on `Post.quoted_post` prevents `N+1` roundtrips during feed extraction.
- **Cursor Pagination Efficiency**: Realtime feeds utilize tuple cursor-based pagination `(created_at, id)` instead of SQL offsets. Cursor queries execute in constant time $O(1)$ relative to index size, avoiding database performance degradation as table volume grows.
- **Batch commits**: Transaction operations are batched using async connection contexts to minimize connection handshakes.
