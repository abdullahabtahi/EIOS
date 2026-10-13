/** Firebase (Identity Platform) web configuration. Absent in local dev, where auth is disabled. */
export interface FirebaseWebConfig {
  apiKey: string;
  authDomain: string;
  projectId: string;
}

export function getFirebaseConfig(env: Record<string, string | undefined> = process.env): FirebaseWebConfig | null {
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
