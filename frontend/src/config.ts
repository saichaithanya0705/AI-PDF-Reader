/**
 * Dynamic API and WebSocket URL configuration
 * 
 * This automatically detects the correct URLs based on:
 * 1. Environment variables (VITE_API_URL, VITE_WS_URL)
 * 2. Current page location (auto-detect in production)
 * 3. Fallback to localhost for development
 */

const getApiUrl = (): string => {
  // Check for explicit environment variable first
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL.replace(/\/$/, '');
  }

  // In production (non-localhost), derive from current page URL
  if (typeof window !== 'undefined' && !window.location.hostname.includes('localhost')) {
    const protocol = window.location.protocol; // http: or https:
    const hostname = window.location.hostname;
    // Assume backend is on same domain, port 8000 or 8080
    // You can customize this logic based on your deployment
    return `${protocol}//${hostname}:8000`.replace(/\/$/, '');
  }

  // Development fallback
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

