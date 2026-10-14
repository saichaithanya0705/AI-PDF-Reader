const NETWORK_ERROR_PATTERNS = [
  'failed to fetch',
  'load failed',
  'networkerror',
  'supabase client not configured',
];

export const AUTH_SERVICE_UNAVAILABLE_MESSAGE =
  'Authentication service is unreachable. Check the configured Supabase project URL and redeploy the app.';

export const toAuthErrorMessage = (error: unknown): string => {
  if (error instanceof Error) {
    const message = error.message.trim();
    const normalized = message.toLowerCase();
    if (NETWORK_ERROR_PATTERNS.some((pattern) => normalized.includes(pattern))) {
      return AUTH_SERVICE_UNAVAILABLE_MESSAGE;
    }
    if (normalized.includes('rate limit') || normalized.includes('only request this after')) {
      return 'Too many emails were requested. Wait a few minutes before asking for another reset link.';
    }
    if (normalized.includes('should be different from the old password')) {
      return 'Choose a password that is different from your current one.';
    }
    if (normalized.includes('auth session missing') || normalized.includes('expired')) {
      return 'This reset link is invalid or has expired. Request a new one.';
    }
    return message || 'Unable to sign in. Try again shortly.';
  }

  if (typeof error === 'string' && error.trim()) {
    return error.trim();
  }

  return 'Unable to sign in. Try again shortly.';
};
