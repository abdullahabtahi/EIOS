'use client';

import * as React from 'react';
import { clearGeoChat } from '@/components/cockpit/geo/geo-chat-store';
import { getIdTokenResult, onAuthStateChanged, signInWithEmailAndPassword, signOut } from 'firebase/auth';
import { getFirebaseAuth } from './firebase';

export type AuthStatus = 'disabled' | 'loading' | 'signedOut' | 'signedIn';

export interface OperatorSession {
  uid: string;
  email: string | null;
  role: string | null;
}

interface AuthContextValue {
  status: AuthStatus;
  operator: OperatorSession | null;
  signIn: (email: string, password: string) => Promise<void>;
  signOutOperator: () => Promise<void>;
}

const AuthContext = React.createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const auth = React.useMemo(() => getFirebaseAuth(), []);
  const [status, setStatus] = React.useState<AuthStatus>(auth ? 'loading' : 'disabled');
  const [operator, setOperator] = React.useState<OperatorSession | null>(null);

  React.useEffect(() => {
    if (!auth) return;
    return onAuthStateChanged(auth, async (user) => {
      if (!user) {
        clearGeoChat();
        setOperator(null);
        setStatus('signedOut');
        return;
      }
      const result = await getIdTokenResult(user);
      const role = typeof result.claims.role === 'string' ? result.claims.role : null;
      setOperator({ uid: user.uid, email: user.email, role });
      setStatus('signedIn');
    });
  }, [auth]);

  const signIn = React.useCallback(
    async (email: string, password: string) => {
      if (!auth) throw new Error('Authentication is not configured');
      await signInWithEmailAndPassword(auth, email, password);
    },
    [auth],
  );

  const signOutOperator = React.useCallback(async () => {
    clearGeoChat();
    if (auth) await signOut(auth);
  }, [auth]);

  const value = React.useMemo(
    () => ({ status, operator, signIn, signOutOperator }),
    [status, operator, signIn, signOutOperator],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

const AUTH_DISABLED: AuthContextValue = {
  status: 'disabled',
  operator: null,
  signIn: async () => {
    throw new Error('Authentication is not configured');
  },
  signOutOperator: async () => {},
};

/** Outside an <AuthProvider> (unit tests, local tools) auth reads as disabled rather than throwing. */
export function useAuth(): AuthContextValue {
  return React.useContext(AuthContext) ?? AUTH_DISABLED;
}
