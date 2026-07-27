/** @type {import('tailwindcss').Config} */
const withAlpha = (v) => `rgb(var(${v}) / <alpha-value>)`

export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        canvas: withAlpha('--canvas'),
        surface: withAlpha('--surface'),
        'surface-2': withAlpha('--surface-2'),
        line: withAlpha('--line'),
        'line-strong': withAlpha('--line-strong'),
        ink: withAlpha('--ink'),
        muted: withAlpha('--muted'),
        faint: withAlpha('--faint'),
        accent: withAlpha('--accent'),
        'accent-fg': withAlpha('--accent-fg'),
        focus: withAlpha('--focus'),
        danger: withAlpha('--danger'),
      },
      fontFamily: {
        sans: [
          'Inter', 'ui-sans-serif', 'system-ui', '-apple-system', 'Segoe UI',
          'Roboto', 'Helvetica', 'Arial', 'sans-serif',
        ],
        serif: ['Georgia', 'Cambria', 'Times New Roman', 'serif'],
      },
      borderRadius: {
        DEFAULT: '0.5rem',
      },
      maxWidth: {
        prose: '46rem',
      },
    },
  },
  plugins: [],
}
