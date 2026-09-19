/** @type {import('tailwindcss').Config} */
const withAlpha = (v) => `rgb(var(${v}) / <alpha-value>)`

export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Surfaces
        canvas: withAlpha('--canvas'),
        surface: withAlpha('--surface'),
        'surface-2': withAlpha('--surface-2'),
        'surface-3': withAlpha('--surface-3'),
        line: withAlpha('--line'),
        'line-strong': withAlpha('--line-strong'),

        // Ink
        ink: withAlpha('--ink'),
        muted: withAlpha('--muted'),
        faint: withAlpha('--faint'),

        // Brand — the single "do this" colour
        brand: {
          DEFAULT: withAlpha('--brand'),
          hover: withAlpha('--brand-hover'),
          fg: withAlpha('--brand-fg'),
          soft: withAlpha('--brand-soft'),
          ink: withAlpha('--brand-ink'),
        },

        // Neutral emphasis (near-black in light, near-white in dark)
        accent: withAlpha('--accent'),
        'accent-fg': withAlpha('--accent-fg'),

        // Semantic
        success: {
          DEFAULT: withAlpha('--success'),
          soft: withAlpha('--success-soft'),
        },
        warning: {
          DEFAULT: withAlpha('--warning'),
          soft: withAlpha('--warning-soft'),
        },
        danger: {
          DEFAULT: withAlpha('--danger'),
          soft: withAlpha('--danger-soft'),
        },
        info: {
          DEFAULT: withAlpha('--info'),
          soft: withAlpha('--info-soft'),
        },

        focus: withAlpha('--focus'),
      },

      fontFamily: {
        sans: [
          'Inter Variable', 'Inter', 'ui-sans-serif', 'system-ui', '-apple-system',
          'Segoe UI', 'Roboto', 'Helvetica', 'Arial', 'sans-serif',
        ],
        serif: ['Georgia', 'Cambria', 'Times New Roman', 'serif'],
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'Consolas', 'monospace'],
      },

      /* A closed type scale. Nothing in the product should need a size that is
         not on this list — 11px is the floor, and it is for badges only. */
      fontSize: {
        '2xs': ['0.6875rem', { lineHeight: '1rem', letterSpacing: '0.01em' }],   // 11
        xs: ['0.75rem', { lineHeight: '1.125rem' }],                              // 12
        sm: ['0.8125rem', { lineHeight: '1.25rem' }],                             // 13
        base: ['0.875rem', { lineHeight: '1.5rem' }],                             // 14
        md: ['0.9375rem', { lineHeight: '1.5rem' }],                              // 15
        lg: ['1rem', { lineHeight: '1.625rem' }],                                 // 16
        xl: ['1.125rem', { lineHeight: '1.75rem', letterSpacing: '-0.01em' }],    // 18
        '2xl': ['1.375rem', { lineHeight: '1.875rem', letterSpacing: '-0.015em' }],
        '3xl': ['1.75rem', { lineHeight: '2.125rem', letterSpacing: '-0.02em' }],
        '4xl': ['2.25rem', { lineHeight: '2.5rem', letterSpacing: '-0.025em' }],
        '5xl': ['3rem', { lineHeight: '1.08', letterSpacing: '-0.03em' }],
        '6xl': ['3.75rem', { lineHeight: '1.05', letterSpacing: '-0.032em' }],
      },

      /* 4px grid. The defaults already are one; these fill the gaps we use. */
      spacing: {
        4.5: '1.125rem',
        13: '3.25rem',
        18: '4.5rem',
        22: '5.5rem',
      },

      /* Radius has meaning: sm = chips, md = controls, lg = cards,
         xl = panels and sheets. */
      borderRadius: {
        sm: '0.375rem',
        DEFAULT: '0.5rem',
        md: '0.5rem',
        lg: '0.75rem',
        xl: '1rem',
        '2xl': '1.25rem',
      },

      boxShadow: {
        xs: 'var(--shadow-xs)',
        sm: 'var(--shadow-sm)',
        DEFAULT: 'var(--shadow-sm)',
        md: 'var(--shadow-md)',
        lg: 'var(--shadow-lg)',
        xl: 'var(--shadow-xl)',
        none: 'none',
      },

      maxWidth: {
        prose: '46rem',
        content: '90rem', // 1440 — the app shell at 1536px and above
      },

      /* One motion vocabulary: 150–250ms, ease-out, no bounce. */
      transitionTimingFunction: {
        out: 'cubic-bezier(0.16, 1, 0.3, 1)',
      },
      transitionDuration: {
        fast: '150ms',
        DEFAULT: '200ms',
        slow: '250ms',
      },

      keyframes: {
        'fade-in': {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
        'fade-up': {
          from: { opacity: '0', transform: 'translateY(6px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        'scale-in': {
          from: { opacity: '0', transform: 'scale(0.97)' },
          to: { opacity: '1', transform: 'scale(1)' },
        },
        'slide-up': {
          from: { opacity: '0', transform: 'translateY(100%)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        shimmer: {
          '100%': { transform: 'translateX(100%)' },
        },
        'indeterminate': {
          '0%': { transform: 'translateX(-100%) scaleX(0.4)' },
          '100%': { transform: 'translateX(320%) scaleX(0.4)' },
        },
      },
      animation: {
        'fade-in': 'fade-in 150ms cubic-bezier(0.16, 1, 0.3, 1)',
        'fade-up': 'fade-up 200ms cubic-bezier(0.16, 1, 0.3, 1)',
        'scale-in': 'scale-in 150ms cubic-bezier(0.16, 1, 0.3, 1)',
        'slide-up': 'slide-up 250ms cubic-bezier(0.16, 1, 0.3, 1)',
        shimmer: 'shimmer 1.6s infinite',
        indeterminate: 'indeterminate 1.4s cubic-bezier(0.65, 0, 0.35, 1) infinite',
      },
    },
  },
  plugins: [],
}
