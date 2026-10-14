import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');

  if (mode === 'production' && !env.VITE_API_URL?.trim()) {
    throw new Error('VITE_API_URL is required for production builds (set it to the Render backend URL).');
  }

  return {
    plugins: [react()],
    optimizeDeps: {
      exclude: ['lucide-react'],
    },
    build: {
      rollupOptions: {
        external: [],
      },
    },
    worker: {
      format: 'es',
    },
  };
});
