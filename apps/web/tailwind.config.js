/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    fontFamily: {
      sans: [
        'Pretendard Variable',
        'Pretendard',
        'Noto Sans KR',
        'sans-serif',
      ],
      mono: [
        'Consolas',
        'Courier New',
        'monospace',
      ],
    },
    fontSize: {
      '2xs': ['12px', { lineHeight: '16px' }],
      xs: ['13px', { lineHeight: '18px' }],
      sm: ['14.5px', { lineHeight: '22px' }],
      base: ['16px', { lineHeight: '24px' }],
      lg: ['18px', { lineHeight: '26px' }],
      xl: ['22px', { lineHeight: '30px' }],
      '2xl': ['26px', { lineHeight: '34px' }],
      '3xl': ['32px', { lineHeight: '40px' }],
      '4xl': ['38px', { lineHeight: '46px' }],
    },
    extend: {
      fontSize: {
        '2xs': ['12px', { lineHeight: '16px' }],
        xs: ['13px', { lineHeight: '18px' }],
        sm: ['14.5px', { lineHeight: '22px' }],
        base: ['16px', { lineHeight: '24px' }],
        lg: ['18px', { lineHeight: '26px' }],
        xl: ['22px', { lineHeight: '30px' }],
        '2xl': ['26px', { lineHeight: '34px' }],
        '3xl': ['32px', { lineHeight: '40px' }],
      },
      fontFamily: {
        sans: [
          'Pretendard Variable',
          'Pretendard',
          'Noto Sans KR',
          'sans-serif',
        ],
        mono: [
          'Consolas',
          'Courier New',
          'monospace',
        ],
      },
      colors: {
        canvas: 'var(--color-bg-canvas)',
        surface: {
          DEFAULT: 'var(--color-bg-surface)',
          muted: 'var(--color-bg-surface-muted)',
          hover: 'var(--color-bg-surface-hover)',
        },
        border: {
          subtle: 'var(--color-border-subtle)',
          DEFAULT: 'var(--color-border-default)',
          strong: 'var(--color-border-strong)',
        },
        fg: {
          DEFAULT: 'var(--color-fg-default)',
          muted: 'var(--color-fg-muted)',
          subtle: 'var(--color-fg-subtle)',
        },
        accent: {
          DEFAULT: 'var(--color-accent)',
          hover: 'var(--color-accent-hover)',
          subtle: 'var(--color-accent-subtle)',
          fg: 'var(--color-accent-fg)',
        },
        success: {
          DEFAULT: 'var(--color-success)',
          subtle: 'var(--color-success-subtle)',
        },
        warning: {
          DEFAULT: 'var(--color-warning)',
          subtle: 'var(--color-warning-subtle)',
        },
        danger: {
          DEFAULT: 'var(--color-danger)',
          subtle: 'var(--color-danger-subtle)',
        },
        primary: {
          50: '#f0f7ff',
          100: '#e0effe',
          500: '#0284c7',
          600: '#0369a1',
          700: '#075985',
        },
        slate: {
          850: '#151e2e',
          900: '#0f172a',
          950: '#020617'
        }
      }
    },
  },
  plugins: [],
}
