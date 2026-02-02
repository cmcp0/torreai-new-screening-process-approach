/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Mulish', 'system-ui', 'sans-serif'],
      },
      colors: {
        background: {
          0: 'var(--background-0)',
          /* 5 corresponds to design token background-05 (near-black surface) */
          5: 'var(--background-05)',
          1: 'var(--background-1)',
          2: 'var(--background-2)',
          3: 'var(--background-3)',
        },
        'text-primary': 'var(--text-primary)',
        'text-accent': 'var(--text-accent)',
        'text-disabled': 'var(--text-disabled)',
        'text-primary-on-accent': 'var(--text-primary-on-accent)',
        warning: 'var(--warning)',
        error: 'var(--error)',
        'error-elevated': 'var(--error-elevated)',
        brand: 'var(--brand)',
        disabled: 'var(--disabled)',
        badge: 'var(--badge)',
        scrollbar: 'var(--scrollbar)',
        'scrollbar-background': 'var(--scrollbar-background)',
        tooltip: 'var(--tooltip)',
        divider: 'var(--divider)',
      },
      fontSize: {
        display: ['64px', { lineHeight: '72px', fontWeight: '700' }],
        h1: ['48px', { lineHeight: '56px', fontWeight: '700' }],
        h2: ['36px', { lineHeight: '44px', fontWeight: '600' }],
        h3: ['24px', { lineHeight: '32px', fontWeight: '600' }],
        'body-large': ['18px', { lineHeight: '28px', fontWeight: '400' }],
        body: ['16px', { lineHeight: '24px', fontWeight: '400' }],
        'body-small': ['14px', { lineHeight: '20px', fontWeight: '400' }],
        button: ['16px', { lineHeight: '24px', fontWeight: '600' }],
        caption: ['12px', { lineHeight: '16px', fontWeight: '400' }],
      },
    },
  },
  plugins: [],
}
