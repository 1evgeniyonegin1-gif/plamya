/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // PHOENIX 鳳凰 — Fire & Rebirth
        void: '#09090B',
        ember: '#18181B',
        ash: '#27272A',
        smoke: '#3F3F46',
        flame: '#EF4444',
        blaze: '#F97316',
        gold: '#EAB308',
        silk: '#FAFAF9',
        pearl: '#A1A1AA',
        mist: '#71717A',
        jade: '#22C55E',
        water: '#3B82F6',
        amber: '#F59E0B',
      },
      backgroundImage: {
        'fire-gradient': 'linear-gradient(135deg, #EF4444, #F97316, #EAB308)',
        'fire-glow': 'radial-gradient(circle at 50% 0%, rgba(239,68,68,0.08) 0%, transparent 50%)',
      },
      animation: {
        'shimmer': 'shimmer 2s infinite',
        'glow': 'glow 3s ease-in-out infinite',
        'fade-in': 'fadeIn 0.3s ease-out',
      },
      keyframes: {
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        glow: {
          '0%, 100%': { opacity: '0.4' },
          '50%': { opacity: '0.8' },
        },
        fadeIn: {
          from: { opacity: '0', transform: 'translateY(8px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
}
