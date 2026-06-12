# Dependency and Size Reduction Report

---

## 1. Backend Dependency Audit

### 1.1 Redundant JWT Packages
- **Finding:** The backend `requirements.txt` specifies both `python-jose[cryptography]==3.3.0` and `PyJWT>=2.8.0`.
- **Audit Analysis:** A search of the codebase shows that `python-jose` (`from jose import jwt`) is used exclusively for token encoding, decoding, and signature verification. `PyJWT` is not imported anywhere.
- **Recommendation:** Remove `PyJWT>=2.8.0` from `backend/requirements.txt` to eliminate package bloat.

### 1.2 Dual Task Queue Overhead
- **Finding:** Both `celery` and `rq` are installed in the requirements.
- **Audit Analysis:** `task_queue.py` dynamically selects between Celery and RQ depending on the `TASK_QUEUE_BACKEND` environment variable. While this provides flexibility, maintaining both engines increases setup complexity and dependency footprints.
- **Recommendation:** Standardize on Celery for production deployment (supporting multi-protocol routing and rate limiting) and deprecate RQ in future iterations.

---

## 2. Frontend Dependency Audit

### 2.1 Misplaced DevDependencies
- **Finding:** `@tanstack/react-query-devtools` is listed under `"dependencies"` in `frontend/package.json`.
- **Audit Analysis:** Developer tooling should not be bundled in production builds. Listing it in production dependencies increases the bundle size.
- **Recommendation:** Move `@tanstack/react-query-devtools` to `"devDependencies"`.

### 2.2 Circular Parent-Link Dependency
- **Finding:** `"chattingapp": "file:.."` is listed in the dependencies.
- **Audit Analysis:** This causes npm to link the parent directory (which includes backend `venv`, `node_modules`, etc.) recursively, leading to massive installations and build errors.
- **Recommendation:** Remove the self-referencing parent link from `frontend/package.json`.

---

## 3. Dead Code Cleanup

### 3.1 Unused simple `VirtualList.tsx`
- **Finding:** `frontend/src/ui/VirtualList.tsx` provides a basic fixed-height scrolling hook.
- **Audit Analysis:** Both `Chat.tsx` and `Groups.tsx` import and use `VirtualizedList.tsx` (which leverages `react-window` for Fixed and Variable height lists). `VirtualList.tsx` is not imported or referenced anywhere in the app.
- **Recommendation:** Delete `frontend/src/ui/VirtualList.tsx` immediately to keep the codebase clean.

---

## 4. Size Reduction Implementation Results

1. **Unused File Removal:** `frontend/src/ui/VirtualList.tsx` has been deleted.
2. **Redundant Package Removal:** `PyJWT` is slated for removal from `requirements.txt`.
3. **Circular Reference Removal:** Removed `"chattingapp": "file:.."` to ensure clean, sandboxed frontend installs.
