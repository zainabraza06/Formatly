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

      /* A closed type scale, benchmarked against the systems this product sits
         beside: 14px body, 13px for secondary text, and display sizes that
         carry real negative tracking so a heading reads as engineered rather
         than as large body text. Hierarchy comes from size and weight, which
         is why there are big jumps between the last four. */
      fontSize: {
        '2xs': ['0.6875rem', { lineHeight: '1rem', letterSpacing: '0.005em' }],       // 11 — badges only
        xs: ['0.75rem', { lineHeight: '1.125rem' }],                                   // 12 — captions
        sm: ['0.8125rem', { lineHeight: '1.25rem', letterSpacing: '-0.005em' }],       // 13 — secondary
        base: ['0.875rem', { lineHeight: '1.375rem', letterSpacing: '-0.006em' }],     // 14 — body
        md: ['0.9375rem', { lineHeight: '1.5rem', letterSpacing: '-0.008em' }],        // 15
        lg: ['1rem', { lineHeight: '1.5rem', letterSpacing: '-0.011em' }],             // 16 — lead
        xl: ['1.25rem', { lineHeight: '1.75rem', letterSpacing: '-0.014em' }],         // 20 — h3
        '2xl': ['1.5rem', { lineHeight: '1.875rem', letterSpacing: '-0.018em' }],      // 24 — h2
        '3xl': ['2rem', { lineHeight: '2.25rem', letterSpacing: '-0.022em' }],         // 32 — h1
        '4xl': ['2.5rem', { lineHeight: '2.75rem', letterSpacing: '-0.024em' }],       // 40
        '5xl': ['3rem', { lineHeight: '1.08', letterSpacing: '-0.026em' }],            // 48 — display
        '6xl': ['3.75rem', { lineHeight: '1.04', letterSpacing: '-0.028em' }],         // 60
      },

      /* 4px grid. The defaults already are one; these fill the gaps we use. */
      spacing: {
        4.5: '1.125rem',
        13: '3.25rem',
        18: '4.5rem',
        22: '5.5rem',
      },

      /* Row heights, so every list in the product shares one rhythm rather
         than each screen inventing its own padding. */
      height: {
        row: '2.25rem',      // 36 — list and nav rows
        'row-lg': '2.75rem', // 44 — table rows with two lines
      },

      /* Radius has meaning, and the steps are small: 4 for things inside
         things, 6 for controls, 10 for cards, 14 for sheets. Anything rounder
         reads as a consumer app rather than a tool. */
      borderRadius: {
        sm: '0.25rem',
        DEFAULT: '0.375rem',
        md: '0.375rem',
        lg: '0.625rem',
        xl: '0.875rem',
        '2xl': '1.125rem',
      },

      /* Elevation is for things that float. A card that is simply on the page
         gets a hairline and nothing else — stacking a border and a shadow on
         every surface is what makes an interface look like a pile of boxes. */
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
