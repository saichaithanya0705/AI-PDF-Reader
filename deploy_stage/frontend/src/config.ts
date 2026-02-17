export const API_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8080').replace(/\/$/, '');

const deriveWsUrl = () => {
  if (import.meta.env.VITE_WS_URL) {
    return import.meta.env.VITE_WS_URL.replace(/\/$/, '');
  }

  if (API_URL.startsWith('https://')) {
    return API_URL.replace('https://', 'wss://');
  }

  if (API_URL.startsWith('http://')) {
    return API_URL.replace('http://', 'ws://');
  }

  return 'ws://localhost:8080';
};

export const WS_URL = deriveWsUrl();
