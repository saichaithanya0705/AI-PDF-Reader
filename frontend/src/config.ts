/**
 * Dynamic API and WebSocket URL configuration
 * 
 * This automatically detects the correct URLs based on:
 * 1. Environment variables (VITE_API_URL, VITE_WS_URL)
 * 2. Localhost fallback for development only
 */

const getApiUrl = (): string => {
  // Check for explicit environment variable first
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL.replace(/\/$/, '');
  }

  // Vercel and Render use different origins, so production must provide the
  // Render service URL explicitly instead of guessing a port on this host.
  return 'http://localhost:8000';
};

const getWsUrl = (): string => {
  // Check for explicit environment variable first
  if (import.meta.env.VITE_WS_URL) {
    return import.meta.env.VITE_WS_URL.replace(/\/$/, '');
  }

  const apiUrl = getApiUrl();

  // Convert HTTP/HTTPS to WS/WSS
  if (apiUrl.startsWith('https://')) {
    return apiUrl.replace('https://', 'wss://');
  }

  if (apiUrl.startsWith('http://')) {
    return apiUrl.replace('http://', 'ws://');
  }

  // Fallback
  return 'ws://localhost:8000';
};

export const API_URL = getApiUrl();
export const WS_URL = getWsUrl();

console.log('🚀 [Config] Detected API URL:', API_URL);
console.log('🚀 [Config] Detected WS URL:', WS_URL);

