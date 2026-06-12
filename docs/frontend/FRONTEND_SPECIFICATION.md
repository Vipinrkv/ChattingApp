# Frontend Specification Document — ChattingApp

This Frontend Specification Document details the visual theme, typography, design system tokens, component rules, and API connection maps for the **ChattingApp** user interface.

---

## 1. Brand Theme & Color Palette
ChattingApp implements a premium, modern design system based on **Glassmorphism** and a dark/light mode engine that aligns with system preferences.

### Color Values

| Token Name | Light Theme | Dark Theme | Purpose |
| --- | --- | --- | --- |
| `--background` | `hsl(210, 30%, 98%)` | `hsl(222, 47%, 6%)` | Core app background. |
| `--foreground` | `hsl(222, 47%, 11%)` | `hsl(210, 40%, 98%)` | Text content color. |
| `--card-bg` | `rgba(255, 255, 255, 0.7)` | `rgba(15, 23, 42, 0.45)` | Semi-transparent card background. |
| `--card-border` | `rgba(226, 232, 240, 0.8)` | `rgba(255, 255, 255, 0.08)`| Soft border enabling glassmorphism. |
| `--primary` | `hsl(221, 83%, 53%)` | `hsl(217, 91%, 60%)` | Interactive actions, active tabs. |
| `--success` | `hsl(142, 71%, 45%)` | `hsl(142, 69%, 58%)` | Success alerts, active status indicators. |
| `--error` | `hsl(0, 84%, 60%)` | `hsl(0, 84%, 60%)` | Error states, validation failures. |

---

## 2. Typography
Typography relies on modern, clean sans-serif typefaces (e.g. Google Fonts Outfit or system fallback fonts) supporting hierarchy and readability:

- **Heading 1 (`h1`)**: Font size `1.875rem` (`30px`), Font weight `700`, Line-height `1.2` (used for page titles).
- **Heading 2 (`h2`)**: Font size `1.25rem` (`20px`), Font weight `600`, Line-height `1.3` (used for section headers).
- **Body Text**: Font size `0.875rem` (`14px`), Font weight `400`, Line-height `1.5` (used for chats and feed content).
- **Button/Label Text**: Font size `0.875rem` (`14px`), Font weight `500`, Letter-spacing `0.025em`.

---

## 3. Component Styles

### 1. Glassmorphism Container
Every main UI component utilizes a glassmorphism container to create depth:
- **Style**: Background set to `--card-bg`, backdrop filter set to `blur(12px)`, and bordered with `--card-border`.
- **Shadow**: Subtle shadow (`box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1)`).

### 2. Buttons
- **Primary Button**: Filled background using `--primary`, border-radius `8px`, transition `background-color 0.2s ease`. Hover states increase brightness.
- **Secondary Button**: Outline border of `--card-border` with hover background of `--card-bg`.

### 3. Modals & Settings Dialogs
- **Animation**: Smooth fade-in overlay with scale-up dialog (`transform: scale(0.95) -> scale(1)` over `0.2s`).
- **Layout**: Clear close button in upper-right corner, primary actions aligned bottom-right.

---

## 4. Spacing & Layout Rules
- **Responsive Layout**:
  - **Desktop**: A centered three-column layout (Left navigation panel, Center main feed/chat area, Right sidebar trends/stats).
  - **Mobile**: Collapsed left navigation into a responsive bottom bar (`BottomNav`) and drawer overlay for user list search.
- **Spacing Scale**:
  - Padding between elements: `1rem` (`16px`).
  - Margins between main sections: `1.5rem` (`24px`).
  - Grid columns gutter: `1rem` (`16px`).

---

## 5. API & Integration Specification

All REST endpoints map to `/api/v1/`. Real-time messaging uses WebSocket handlers.

### Key REST APIs

#### 1. Posts Feed Controls
- **Endpoint**: `GET` and `PUT` `/api/v1/posts/controls`
- **Request (PUT)**:
  ```json
  {
    "muted_words": ["spam", "spoiler"],
    "ranking_mode": "chronological",
    "sensitive_content_hidden": true
  }
  ```
- **Response**: Returns the updated `UserFeedControl` object configuration.

#### 2. Chat Backup & Restore
- **Endpoint**: `POST` `/api/v1/chat/backup/create` and `POST` `/api/v1/chat/backup/restore`
- **Request (Backup Create)**: Accepts an encryption passphrase to process database entries using Web Crypto AES-GCM.
- **Response**: Return file metadata and binary download stream.

### WebSockets Endpoint
- **Direct Message**: `/ws/chat?token=<FIREBASE_TOKEN>`
- **Group Message**: `/ws/groups/{group_id}?token=<FIREBASE_TOKEN>`
- **Events**: Receives and broadcasts events (`typing_indicator`, `message_sent`, `message_read`).

---

## 6. Embedded Frontend Specification Prompt
To generate or iterate on this Frontend Specification document, use the following prompt:
> "Act as a senior UI/UX designer and frontend architect. Create a Frontend Specification Document for my app. It should define a complete design system including color palette with hex codes (focusing on premium dark/light glassmorphism), typography choices, component styles for buttons, inputs, cards and modals, spacing and layout rules. It should also include a full API and integration spec for every third party service my app will use — including Firebase auth, REST feeds, backup export/restores, and WebSockets endpoints."
