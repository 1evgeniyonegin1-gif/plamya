/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // COSMOS — Бездна
        'void': '#050508',
        'abyss': '#0a0a0f',
        'deep-space': '#0d0d14',
        'nebula-dark': '#12121c',

        // COSMOS — Свечения
        'glow': {
          DEFAULT: '#6366f1',
          soft: '#818cf8',
          muted: '#4f46e5',
        },
        'nebula': {
          purple: '#7c3aed',
          blue: '#3b82f6',
        },
        'star': {
          DEFAULT: '#e2e8f0',
          dim: '#94a3b8',
        },
        'dust': '#64748b',

        // Telegram theme mapping
        'tg-bg': 'var(--void)',
        'tg-text': 'var(--star-white)',
        'tg-hint': 'var(--dust)',
        'tg-link': 'var(--glow-soft)',
        'tg-button': 'var(--glow-primary)',
        'tg-button-text': '#ffffff',
        'tg-secondary-bg': 'var(--abyss)',

        // Status — космические
        'success': '#818cf8',
        'error': '#f87171',
        'warning': '#fbbf24',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      borderRadius: {
        '2xl': '1rem',
        '3xl': '1.5rem',
      },
      boxShadow: {
        'glow-sm': '0 0 10px rgba(99, 102, 241, 0.2)',
        'glow-md': '0 0 20px rgba(99, 102, 241, 0.3)',
        'glow-lg': '0 0 40px rgba(99, 102, 241, 0.4)',
        'cosmic': '0 4px 24px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.03)',
      },
      animation: {
        'float': 'float 6s ease-in-out infinite',
        'breathe': 'breathe 4s ease-in-out infinite',
        'glow': 'glow 3s ease-in-out infinite',
        'twinkle': 'twinkle 2s ease-in-out infinite',
        'drift': 'drift 20s ease-in-out infinite',
        'orbit': 'orbit 8s linear infinite',
        'pulse-ring': 'pulse-ring 2s ease-out infinite',
      },
      keyframes: {
        twinkle: {
          '0%, 100%': { opacity: '0.3', transform: 'scale(1)' },
          '50%': { opacity: '1', transform: 'scale(1.2)' },
        },
        drift: {
          '0%': { transform: 'translate(0, 0) rotate(0deg)' },
          '25%': { transform: 'translate(10px, -10px) rotate(90deg)' },
          '50%': { transform: 'translate(0, -20px) rotate(180deg)' },
          '75%': { transform: 'translate(-10px, -10px) rotate(270deg)' },
          '100%': { transform: 'translate(0, 0) rotate(360deg)' },
        },
        orbit: {
          from: { transform: 'rotate(0deg) translateX(30px) rotate(0deg)' },
          to: { transform: 'rotate(360deg) translateX(30px) rotate(-360deg)' },
        },
      },
    },
  },
  plugins: [],
}
