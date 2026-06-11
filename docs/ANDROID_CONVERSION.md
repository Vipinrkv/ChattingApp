# Android Conversion Walkthrough (Capacitor)

This guide documents the steps to build, package, and compile the **ChattingApp** frontend into an Android application package (.apk or .aab) using Ionic Capacitor.

---

## 1. Prerequisites

Ensure you have the following installed on your development machine:
1. **Node.js & npm**: Installed (LTS version recommended).
2. **Java Development Kit (JDK)**: JDK 17 is required for modern Android builds.
3. **Android Studio**: Installed.
4. **Android SDK & Build Tools**: Installed via Android Studio SDK Manager (targeting Android API Level 33 or 34).

---

## 2. Step-by-Step Conversion Flow

Run the following commands inside the `frontend/` directory.

### Step 1: Install Dependencies
If you haven't already, install the required packages:
```bash
npm install @capacitor/core
npm install -D @capacitor/cli @capacitor/android
```

### Step 2: Build the Frontend Assets
Compile the React/TypeScript source code into static web assets:
```bash
npm run build
```
This outputs the web assets to the `frontend/dist/` directory.

### Step 3: Add the Android Platform
Initialize the Android project directory inside the Capacitor setup:
```bash
npx cap add android
```
This creates an `android/` directory inside `frontend/` which contains a native Gradle project.

### Step 4: Sync Web Assets to Android Project
Whenever you modify your frontend code, run the build command followed by the sync command to copy the compiled assets into the native Android application:
```bash
npm run build
npx cap sync
```

### Step 5: Open in Android Studio
Launch Android Studio with the newly created native project:
```bash
npx cap open android
```
Android Studio will import the project, index the files, and download any required Gradle dependencies.

---

## 3. Building and Running the App

### Option A: Running on a Device/Emulator via Android Studio
1. In Android Studio, wait for the Gradle sync to finish.
2. Select your device or virtual emulator from the device dropdown.
3. Click the green **Run** button (or press `Shift + F10`) to build and launch the app.

### Option B: Building a Release APK via CLI
You can compile a release build directly from the command line:
```bash
npx cap build android
```
This triggers the native gradle wrapper to compile the application and outputs the APK to:
`frontend/android/app/build/outputs/apk/release/app-release-unsigned.apk`

---

## 4. Key Configurations & Tips

### CORS and API Connectivity
Capacitor runs the web application from a local web server (origin `https://localhost` or `http://localhost`). Ensure your backend `CORS_ORIGINS` settings allow connections from:
* `http://localhost`
* `https://localhost`

### Permissions (Camera, Photos, Audio)
To allow users to upload media or use voice messages in the Android app, add the following to `frontend/android/app/src/main/AndroidManifest.xml` within the `<manifest>` tag:
```xml
<!-- Audio Recording -->
<uses-permission android:name="android.permission.RECORD_AUDIO" />
<!-- Camera Access -->
<uses-permission android:name="android.permission.CAMERA" />
<!-- Photo Gallery -->
<uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" />
<uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" />
```
Additionally, prompt the user for runtime permissions using Capacitor's plugins (e.g. `@capacitor/camera`, `@capacitor/voice-recorder`).
