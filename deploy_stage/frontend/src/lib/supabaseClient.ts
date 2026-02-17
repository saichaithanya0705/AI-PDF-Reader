import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL as string | undefined;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined;

if (!supabaseUrl || !supabaseAnonKey) {
  console.warn(
    '[Supabase] Missing VITE_SUPABASE_URL or VITE_SUPABASE_ANON_KEY. Authentication routes will not function until these env vars are provided.'
  );
}

export const supabase = supabaseUrl && supabaseAnonKey
  ? createClient(supabaseUrl, supabaseAnonKey, {
      auth: {
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: true,
      },
    })
  : ({
      auth: {
        async getSession() {
          throw new Error('Supabase client not configured');
        },
        onAuthStateChange() {
          throw new Error('Supabase client not configured');
        },
        async signInWithPassword() {
          throw new Error('Supabase client not configured');
        },
        async signUp() {
          throw new Error('Supabase client not configured');
        },
        async signInWithOAuth() {
          throw new Error('Supabase client not configured');
        },
        async signOut() {
          throw new Error('Supabase client not configured');
        },
      },
      from() {
        throw new Error('Supabase client not configured');
      },
    } as unknown as ReturnType<typeof createClient>);
