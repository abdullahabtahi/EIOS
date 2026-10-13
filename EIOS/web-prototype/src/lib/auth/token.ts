import { getFirebaseAuth } from './firebase';

/** The current user's ID token (refreshed by the SDK when near expiry), or null when signed out or auth is off. */
export async function getIdToken(): Promise<string | null> {
  const auth = getFirebaseAuth();
  const user = auth?.currentUser;
  return user ? user.getIdToken() : null;
}

/** fetch() that attaches the operator's ID token. Without a session the request goes out unauthenticated and the API decides. */
export async function authFetch(input: RequestInfo | URL, init: RequestInit = {}): Promise<Response> {
  const token = await getIdToken();
  const headers = new Headers(init.headers);
  if (token) headers.set('Authorization', `Bearer ${token}`);
  return fetch(input, { ...init, headers });
}
