const c = (v) => `rgb(var(--${v}) / <alpha-value>)`

/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  darkMode: ['class', '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        bg: c('bg'), surface: c('surface'), surface2: c('surface2'), line: c('line'),
        ink: c('ink'), mute: c('mute'), accent: c('accent'), 'accent-ink': c('accent-ink'),
        sky: c('sky'), amber: c('amber'), rose: c('rose'), violet: c('violet'),
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        display: ['"Space Grotesk"', 'Inter', 'system-ui', 'sans-serif'],
      },
      boxShadow: { glow: '0 0 0 1px rgb(var(--accent) / .35), 0 8px 40px -12px rgb(var(--accent) / .45)' },
      keyframes: {
        rise: { '0%': { opacity: 0, transform: 'translateY(10px)' }, '100%': { opacity: 1, transform: 'none' } },
        drift: { '0%,100%': { transform: 'translate3d(0,0,0)' }, '50%': { transform: 'translate3d(0,-14px,0)' } },
        dash: { to: { strokeDashoffset: 0 } },
        pulseDot: { '0%,100%': { opacity: 1 }, '50%': { opacity: .35 } },
      },
      animation: {
        rise: 'rise .45s cubic-bezier(.2,.7,.2,1) both',
        drift: 'drift 9s ease-in-out infinite',
        pulseDot: 'pulseDot 1.6s ease-in-out infinite',
      },
    },
  },
  plugins: [],
}
