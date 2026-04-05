import type { Config } from 'tailwindcss'

export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        background: '#FFF9F5',
        surface: '#FFFFFF',
        surfaceAlt: '#FFF4EE',
        textPrimary: '#4A3F3A',
        textSecondary: '#7A6C65',
        border: '#F1DDD4',
        navButton: '#8B6F63',
        navButtonHover: '#775C51',
        navButtonActive: '#6A5046',
        navButtonText: '#FFF9F5',
        accentPrimary: '#F58C7C',
        accentSecondary: '#F6B7A9',
        accentHighlight: '#FFE0B8',
        accentLeaf: '#B7C9A8',
        success: '#7FA37A',
        warning: '#F0B56A',
        error: '#D9776A',
        info: '#A7C7E7',
      },
      fontFamily: {
        display: ['"Fraunces"', 'Georgia', 'serif'],
        ui: ['"Plus Jakarta Sans"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        glass: '0 24px 60px rgba(139, 111, 99, 0.12)',
        panel: '0 18px 45px rgba(122, 108, 101, 0.12)',
      },
      backgroundImage: {
        'pomelo-wash':
          'radial-gradient(circle at top left, rgba(245, 140, 124, 0.16), transparent 30%), radial-gradient(circle at top right, rgba(255, 224, 184, 0.38), transparent 28%), linear-gradient(180deg, #fff9f5 0%, #fff4ee 100%)',
      },
    },
  },
  plugins: [],
} satisfies Config
