/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // NEXUS — Neural Command Grid
        abyss: '#050A0E',
        hull: '#0A1628',
        steel: '#162032',
        graphite: '#2A3A52',
        signal: '#00FF88',
        pulse: '#00D4AA',
        electric: '#00AAFF',
        alert: '#FF4444',
        caution: '#FFB800',
        chrome: '#E2E8F0',
        alloy: '#94A3B8',
        oxide: '#64748B',
      },
      animation: {
        'radar': 'radar 8s linear infinite',
        'pulse-dot': 'pulseDot 2s ease-in-out infinite',
        'fade-in': 'fadeIn 0.3s ease-out',
        'shimmer': 'shimmer 2s infinite',
      },
      keyframes: {
        radar: {
          '0%': { transform: 'rotate(0deg)' },
          '100%': { transform: 'rotate(360deg)' },
        },
        pulseDot: {
          '0%, 100%': { opacity: '1', transform: 'scale(1)' },
          '50%': { opacity: '0.5', transform: 'scale(1.5)' },
        },
        fadeIn: {
          from: { opacity: '0', transform: 'translateY(8px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
      },
    },
  },
  plugins: [],
}
