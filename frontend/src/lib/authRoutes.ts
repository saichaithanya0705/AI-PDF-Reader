// Where Supabase sends the user from the reset email. This URL must be on the
// project's Auth > URL Configuration redirect allow-list.
export const PASSWORD_RESET_PATH = '/reset-password';
export const FORGOT_PASSWORD_PATH = '/forgot-password';

// Supabase Auth's minimum password length (Auth > Providers > Email).
export const MIN_PASSWORD_LENGTH = 6;
