/** Firebase (Identity Platform) web configuration. Absent in local dev, where auth is disabled. */
export interface FirebaseWebConfig {
  apiKey: string;
  authDomain: string;
  projectId: string;
}

// Next inlines `process.env.NEXT_PUBLIC_X` only where it is written out in full, so the browser bundle must name each
// variable here. Reading them off a bare `process.env` object (as a default parameter did) yields nothing in the
// browser: auth then looks disabled, no token is sent, and every call is a 401 that falls back to replay.
const BUILD_TIME_ENV: Record<string, string | undefined> = {
  NEXT_PUBLIC_FIREBASE_API_KEY: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
  NEXT_PUBLIC_FIREBASE_PROJECT_ID: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
  NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
};

export function getFirebaseConfig(env: Record<string, string | undefined> = BUILD_TIME_ENV): FirebaseWebConfig | null {
  const apiKey = env.NEXT_PUBLIC_FIREBASE_API_KEY;
  const projectId = env.NEXT_PUBLIC_FIREBASE_PROJECT_ID;
  if (!apiKey || !projectId) return null;
  return {
    apiKey,
    projectId,
    authDomain: env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN || `${projectId}.firebaseapp.com`,
  };
}

export const isAuthEnabled = (): boolean => getFirebaseConfig() !== null;
