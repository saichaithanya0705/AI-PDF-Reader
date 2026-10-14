import { createContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import type { AuthChangeEvent, AuthError, Session, User } from '@supabase/supabase-js';
import { supabase } from '../lib/supabaseClient';
import { getDevelopmentUser, isDevAuthBypassEnabled } from '../lib/devAuth';
import { PASSWORD_RESET_PATH } from '../lib/authRoutes';

type AuthContextValue = {
  user: User | null;
  session: Session | null;
  loading: boolean;
  error: AuthError | null;
  signIn: (payload: { email: string; password: string }) => Promise<void>;
  signUp: (payload: { email: string; password: string; metadata?: Record<string, unknown> }) => Promise<void>;
  signOut: () => Promise<void>;
  resetError: () => void;
  /** True after the user opens a password-recovery link from their email. */
  isPasswordRecovery: boolean;
  requestPasswordReset: (email: string) => Promise<void>;
  updatePassword: (newPassword: string) => Promise<void>;
};

export const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<AuthError | null>(null);
  const [isPasswordRecovery, setIsPasswordRecovery] = useState(false);

  useEffect(() => {
    let mounted = true;
    if (isDevAuthBypassEnabled()) {
      setUser(getDevelopmentUser());
      setSession(null);
      setLoading(false);
      return () => {
        mounted = false;
      };
    }

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

    const { data: listener } = supabase.auth.onAuthStateChange((event: AuthChangeEvent, newSession: Session | null) => {
      if (!mounted) return;
      if (event === 'PASSWORD_RECOVERY') {
        setIsPasswordRecovery(true);
      } else if (event === 'SIGNED_OUT') {
        setIsPasswordRecovery(false);
      }
      setSession(newSession ?? null);
      setUser(newSession?.user ?? null);
    });

    return () => {
      mounted = false;
      listener?.subscription?.unsubscribe?.();
    };
  }, []);

  const signIn: AuthContextValue['signIn'] = async ({ email, password }) => {
    if (isDevAuthBypassEnabled()) {
      setUser(getDevelopmentUser());
      setSession(null);
      setLoading(false);
      return;
    }

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
    if (isDevAuthBypassEnabled()) {
      setUser(getDevelopmentUser());
      setSession(null);
      setLoading(false);
      return;
    }

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
    if (isDevAuthBypassEnabled()) {
      setUser(getDevelopmentUser());
      setSession(null);
      setLoading(false);
      return;
    }

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

  const requestPasswordReset: AuthContextValue['requestPasswordReset'] = async (email) => {
    setError(null);
    const { error: resetRequestError } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}${PASSWORD_RESET_PATH}`,
    });
    if (resetRequestError) {
      setError(resetRequestError);
      throw resetRequestError;
    }
  };

  const updatePassword: AuthContextValue['updatePassword'] = async (newPassword) => {
    setError(null);
    const { error: updateError } = await supabase.auth.updateUser({ password: newPassword });
    if (updateError) {
      setError(updateError);
      throw updateError;
    }
    setIsPasswordRecovery(false);
  };

  const resetError = () => setError(null);

  const value = useMemo<AuthContextValue>(
    () => ({
      user, session, loading, error, signIn, signUp, signOut, resetError,
      isPasswordRecovery, requestPasswordReset, updatePassword,
    }),
    [user, session, loading, error, isPasswordRecovery]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
