# ChattingApp Frontend

> Note: This README documents the frontend application and how it connects to the backend API and authentication layer.
>
> Use it when setting up or debugging the React/Vite client side of ChattingApp.

This frontend is a React + Vite UI built to work with the ChattingApp backend.

## Features

- Light/dark theme with blue modern styling
- Clean, easy-to-use interface
- Dashboard, Feed, Chat, Groups, Profile, Login, Register
- Responsive layout for desktop and smaller screens
- Firebase authentication support via environment variables
- Backend API connection via environment variable
- Variable-height virtualization for chat and group message threads
- Developer render-count instrumentation available in dev mode

## Setup

1. Open a terminal in `frontend/`
2. Install dependencies:

   ```bash
   npm install
   ```

3. Copy the environment template:

   ```bash
   copy .env.example .env
   ```

4. Set backend API base URL and Firebase keys in `.env`:

   ```env
   VITE_API_BASE=http://localhost:8000
   VITE_FIREBASE_API_KEY=your_firebase_api_key
   VITE_FIREBASE_AUTH_DOMAIN=your_project.firebaseapp.com
   VITE_FIREBASE_PROJECT_ID=your_project_id
   VITE_FIREBASE_STORAGE_BUCKET=your_project.appspot.com
   VITE_FIREBASE_MESSAGING_SENDER_ID=your_sender_id
   VITE_FIREBASE_APP_ID=your_app_id
   ```

5. Run the app:

   ```bash
   npm run dev
   ```

6. Open the browser address shown by Vite.

## UI Guide

### Login

- Enter your Firebase token and username.
- This stores a demo token in local storage.

### Notes

- Global auth hardening is enabled: the frontend will attempt token refreshes automatically on 401/403 responses and will trigger a logout if refresh fails.
- Zustand is used for centralized frontend state; basic stores live under `src/stores`.

### Register

- Create a session with a token and username.
- This is a simple placeholder signup.

### Dashboard

- View app health and quick insights.
- Includes backend connection status.

### Feed

- Read content cards in a clean scroll view.

### Chat

- View conversations on the left.
- Active thread on the right with a message input.

### Groups

- Shows group cards with member counts and status.

### Profile

- View and edit profile information.

## Styling

- Uses a soft neon-inspired blue palette.
- Panels are glass-style cards for visual clarity.
- The layout is designed to be easy to read and navigate.

## Backend Connection

The frontend calls the backend via `VITE_API_BASE`.

Default value:

```env
VITE_API_BASE=http://localhost:8000
```

## Build

```bash
npm run build
```

## Preview

```bash
npm run preview
```
