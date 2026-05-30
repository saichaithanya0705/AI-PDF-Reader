import type { User } from '@supabase/supabase-js';

const DEV_AUTH_EMAIL_DEFAULT = 'ysaichaithu2005@gmail.com';
const TRUTHY = new Set(['1', 'true', 'yes', 'on']);
const DEVELOPMENT_ENVS = new Set(['development', 'dev', 'local', 'test']);

export const isDevAuthBypassEnabled = (): boolean => {
  const appEnv = String(import.meta.env.VITE_APP_ENV ?? import.meta.env.MODE ?? 'production').toLowerCase();
  const bypassFlag = String(import.meta.env.VITE_AUTH_BYPASS_ENABLED ?? '').toLowerCase();
  return import.meta.env.DEV && DEVELOPMENT_ENVS.has(appEnv) && TRUTHY.has(bypassFlag);
};

export const getDevelopmentUser = (): User => {
  const email = String(import.meta.env.VITE_DEV_AUTH_EMAIL ?? DEV_AUTH_EMAIL_DEFAULT);
  const id = String(import.meta.env.VITE_DEV_AUTH_USER_ID ?? email);
  const now = new Date(0).toISOString();

  return {
    id,
    email,
    aud: 'authenticated',
    role: 'authenticated',
    app_metadata: {
      provider: 'dev-auth-bypass',
      providers: ['dev-auth-bypass'],
    },
    user_metadata: {
      email,
      auth_bypassed: true,
    },
    created_at: now,
    updated_at: now,
  } as User;
};
