import { initializeApp } from 'firebase/app';
import {
  Auth,
  getAuth,
  GoogleAuthProvider,
  RecaptchaVerifier,
  signInWithPhoneNumber,
  type ConfirmationResult,
} from 'firebase/auth';

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID
};

const firebaseConfigError =
  !firebaseConfig.apiKey || !firebaseConfig.authDomain || !firebaseConfig.projectId
    ? 'Missing Firebase configuration. Add VITE_FIREBASE_* values to your frontend/.env file.'
    : null;

const app = firebaseConfigError ? null : initializeApp(firebaseConfig);
const auth: Auth | null = app ? getAuth(app) : null;
const googleProvider = firebaseConfigError ? null : new GoogleAuthProvider();

async function getPhoneConfirmationResult(
  phoneNumber: string,
  recaptchaContainerId: string,
): Promise<ConfirmationResult> {
  if (!auth) {
    throw new Error(firebaseConfigError ?? 'Firebase authentication is not configured.');
  }

  const container = document.getElementById(recaptchaContainerId);
  if (!container) {
    throw new Error(`Missing reCAPTCHA container: #${recaptchaContainerId}`);
  }

  const verifier = new RecaptchaVerifier(auth, container, {});
  return signInWithPhoneNumber(auth, phoneNumber, verifier);
}

export { auth, firebaseConfigError, googleProvider, getPhoneConfirmationResult };
