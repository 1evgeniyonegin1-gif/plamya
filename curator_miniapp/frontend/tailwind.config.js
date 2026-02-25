/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // VELVET — Фоны
        'obsidian': '#0C0A09',
        'charcoal': '#1C1917',
        'smoke': '#292524',

        // VELVET — Акценты
        'amber': {
          DEFAULT: '#F59E0B',
          soft: '#FCD34D',
          deep: '#D97706',
        },

        // VELVET — Текст
        'cream': '#FAF7F2',
        'sand': '#A8A29E',
        'stone': '#78716C',

        // Статусы
        'sage': '#10B981',
        'error': '#F87171',
        'warning': '#FBBF24',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      borderRadius: {
        '2xl': '1rem',
        '3xl': '1.5rem',
      },
      boxShadow: {
        'warm-sm': '0 0 10px rgba(245, 158, 11, 0.1)',
        'warm-md': '0 0 20px rgba(245, 158, 11, 0.15)',
        'warm-lg': '0 0 40px rgba(245, 158, 11, 0.2)',
        'card': '0 4px 24px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.02)',
      },
      animation: {
        'drift-1': 'drift-1 20s ease-in-out infinite',
        'drift-2': 'drift-2 25s ease-in-out infinite',
        'drift-3': 'drift-3 18s ease-in-out infinite',
        'glow-pulse': 'glow-pulse 3s ease-in-out infinite',
        'breathe': 'breathe 4s ease-in-out infinite',
      },
      keyframes: {
        'drift-1': {
          '0%, 100%': { transform: 'translate(0, 0)' },
          '25%': { transform: 'translate(30px, -20px)' },
          '50%': { transform: 'translate(-10px, 30px)' },
          '75%': { transform: 'translate(20px, 10px)' },
        },
        'drift-2': {
          '0%, 100%': { transform: 'translate(0, 0)' },
          '25%': { transform: 'translate(-20px, 30px)' },
          '50%': { transform: 'translate(30px, -10px)' },
          '75%': { transform: 'translate(-10px, -30px)' },
        },
        'drift-3': {
          '0%, 100%': { transform: 'translate(0, 0)' },
          '33%': { transform: 'translate(20px, 20px)' },
          '66%': { transform: 'translate(-30px, 10px)' },
        },
        'glow-pulse': {
          '0%, 100%': { boxShadow: '0 0 20px rgba(245, 158, 11, 0.1)' },
          '50%': { boxShadow: '0 0 40px rgba(245, 158, 11, 0.2)' },
        },
        breathe: {
          '0%, 100%': { opacity: '0.6', transform: 'scale(1)' },
          '50%': { opacity: '1', transform: 'scale(1.02)' },
        },
      },
    },
  },
  plugins: [],
}
