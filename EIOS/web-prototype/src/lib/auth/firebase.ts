import { getApps, initializeApp, type FirebaseApp } from 'firebase/app';
import { getAuth, type Auth } from 'firebase/auth';
import { getFirebaseConfig } from './config';

let cached: Auth | null = null;

/** The Firebase Auth instance, or null when auth is not configured (local development). */
export function getFirebaseAuth(): Auth | null {
  const config = getFirebaseConfig();
  if (!config) return null;
  if (!cached) {
    const app: FirebaseApp = getApps()[0] ?? initializeApp(config);
    cached = getAuth(app);
  }
  return cached;
}
