/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        display: ['"Space Grotesk"', 'sans-serif'],
        sans: ['"Inter"', 'sans-serif'],
      },
      colors: {
        brand: {
          50: '#f6f4ff',
          100: '#ebe6ff',
          200: '#d3c8ff',
          300: '#b3a0ff',
          400: '#9275ff',
          500: '#7a4bff',
          600: '#632bff',
          700: '#501ae6',
          800: '#3d11b3',
          900: '#2b0d80',
          950: '#18074d',
        },
        midnight: '#0f172a',
        cyber: '#22d3ee',
        aurora: '#f472b6',
      },
      boxShadow: {
        'glow-sm': '0 10px 40px -15px rgba(124, 58, 237, 0.45)',
        'glow': '0 20px 60px -25px rgba(34, 211, 238, 0.55)',
        'glow-strong': '0 25px 80px -20px rgba(244, 114, 182, 0.6)',
      },
      backdropBlur: {
        xs: '2px',
      },
    },
  },
  plugins: [],
};
