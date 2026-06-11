# Native App Wrapper Integration Plan (Capacitor & Android)

This document provides the roadmap and configuration plan for bundling the Vite + React frontend into a native Android application using [Capacitor](https://capacitorjs.com/).

## Overview

Capacitor wraps the web application in a native container, rendering the frontend inside the platform's high-performance native web view (Android System WebView). It exposes native device features (camera, push notifications, local storage) via uniform JavaScript APIs.

```
+-------------------------------------------------+
|               Vite + React App                  |
|  (State, IndexedDB, UI Components, WebRTC, etc.)|
+-------------------------------------------------+
                        |  Bridge API
+-------------------------------------------------+
|            Capacitor Native Plugins             |
|   (Push Notifications, Camera, Filesystem, SQLite)|
+-------------------------------------------------+
                        |  Runtime
+-------------------------------------------------+
|              Android Native SDK                 |
+-------------------------------------------------+
```

## Setup & Initialization

The project root already contains a `capacitor.config.ts` configuration. To initialize the Android build pipeline:

1. **Install Capacitor CLI & Android package**:
   ```bash
   cd frontend
   npm install @capacitor/core @capacitor/cli
   npm install @capacitor/android
   npx cap init ChattingApp com.vipinrkv.chattingapp --web-dir=dist
   ```
2. **Build Web App**:
   ```bash
   npm run build
   ```
3. **Add Android Platform**:
   ```bash
   npx cap add android
   ```
4. **Sync Web assets to Native**:
   ```bash
   npx cap sync
   ```

## Native Capabilities Integration

### 1. Push Notifications
* **Plugin**: `@capacitor/push-notifications`
* **Backend**: Firebase Cloud Messaging (FCM) is used to register tokens and trigger pushes.
* **Flow**:
  ```typescript
  import { PushNotifications } from '@capacitor/push-notifications';

  const registerPush = async () => {
    let perm = await PushNotifications.checkPermissions();
    if (perm.receive !== 'granted') {
      perm = await PushNotifications.requestPermissions();
    }
    if (perm.receive === 'granted') {
      await PushNotifications.register();
    }
  };
  ```

### 2. SQLite / IndexedDB Local Sync
* Capacitor web view supports standard IndexedDB out of the box, allowing the existing database layer to function seamlessly without rewriting queries to native SQLite.
* For heavy storage limits, the `@capacitor-community/sqlite` plugin is recommended as a durable storage engine.

### 3. Media & Camera Permissions
* Permissions are declared in `android/app/src/main/AndroidManifest.xml`:
  ```xml
  <uses-permission android:name="android.permission.CAMERA" />
  <uses-permission android:name="android.permission.RECORD_AUDIO" />
  <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" />
  ```

## Build & Release Pipeline

1. **Open in Android Studio**:
   ```bash
   npx cap open android
   ```
2. **Generate Release Bundle**:
   * Build -> Generate Signed Bundle / APK.
   * Target Android App Bundle (.aab) for Google Play Store optimization.
