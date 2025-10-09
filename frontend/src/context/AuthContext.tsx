import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import type { AuthChangeEvent, AuthError, Session, User } from '@supabase/supabase-js';
import { supabase } from '../lib/supabaseClient';

type AuthContextValue = {
  user: User | null;
  session: Session | null;
  loading: boolean;
  error: AuthError | null;
  signIn: (payload: { email: string; password: string }) => Promise<void>;
  signUp: (payload: { email: string; password: string; metadata?: Record<string, unknown> }) => Promise<void>;
  signOut: () => Promise<void>;
  resetError: () => void;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<AuthError | null>(null);

  useEffect(() => {
    let mounted = true;

    const initialise = async () => {
      try {
        const { data, error: sessionError } = await supabase.auth.getSession();
        if (!mounted) return;
        if (sessionError) {
          setError(sessionError);
        }
        setSession(data.session ?? null);
        setUser(data.session?.user ?? null);
      } catch (err) {
        console.warn('[Auth] Failed to initialise session', err);
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };

    initialise();

  const { data: listener } = supabase.auth.onAuthStateChange((_event: AuthChangeEvent, newSession: Session | null) => {
      if (!mounted) return;
      setSession(newSession ?? null);
      setUser(newSession?.user ?? null);
    });

    return () => {
      mounted = false;
      listener?.subscription?.unsubscribe?.();
    };
  }, []);

  const signIn: AuthContextValue['signIn'] = async ({ email, password }) => {
    setLoading(true);
    setError(null);
    try {
      const { error: signInError } = await supabase.auth.signInWithPassword({ email, password });
      if (signInError) {
        setError(signInError);
        throw signInError;
      }
    } finally {
      setLoading(false);
    }
  };

  const signUp: AuthContextValue['signUp'] = async ({ email, password, metadata }) => {
    setLoading(true);
    setError(null);
    try {
      const { error: signUpError } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: metadata,
          emailRedirectTo: `${window.location.origin}/library`,
        },
      });
      if (signUpError) {
        setError(signUpError);
        throw signUpError;
      }
    } finally {
      setLoading(false);
    }
  };

  const signOut: AuthContextValue['signOut'] = async () => {
    setLoading(true);
    try {
      const { error: signOutError } = await supabase.auth.signOut();
      if (signOutError) {
        setError(signOutError);
        throw signOutError;
      }
    } finally {
      setLoading(false);
    }
  };

  const resetError = () => setError(null);

  const value = useMemo<AuthContextValue>(
    () => ({ user, session, loading, error, signIn, signUp, signOut, resetError }),
    [user, session, loading, error]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
