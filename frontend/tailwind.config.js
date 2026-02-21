/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: {
          DEFAULT: '#1c1917',
          secondary: '#57534e',
          muted: '#a8a29e',
          light: '#d6d3d1',
        },
        cream: {
          DEFAULT: '#faf8f4',
          warm: '#f5f0e8',
        },
        accent: {
          DEFAULT: '#b91c1c',
          light: '#fef2f2',
        },
        rule: {
          DEFAULT: '#d4cfc6',
          heavy: '#1c1917',
        },
        team: {
          england: '#e4002b',
          france: '#002654',
          ireland: '#009a44',
          italy: '#009246',
          scotland: '#003399',
          wales: '#d4003c',
        },
        tier: {
          green: '#15803d',
          'green-bg': '#f0fdf4',
          blue: '#1d4ed8',
          'blue-bg': '#eff6ff',
        },
        // Keep primary alias for accent (used in some Tailwind classes)
        primary: {
          50: '#fef2f2',
          100: '#fee2e2',
          500: '#b91c1c',
          600: '#991b1b',
          700: '#7f1d1d',
        },
      },
      fontFamily: {
        display: ['Fraunces', 'Georgia', 'serif'],
        sans: ['Source Sans 3', 'system-ui', 'sans-serif'],
        mono: ['IBM Plex Mono', 'Menlo', 'monospace'],
      },
      boxShadow: {
        'card': '0 1px 3px 0 rgb(0 0 0 / 0.04), 0 1px 2px -1px rgb(0 0 0 / 0.04)',
        'card-hover': '0 4px 6px -1px rgb(0 0 0 / 0.06), 0 2px 4px -2px rgb(0 0 0 / 0.06)',
      },
    },
  },
  plugins: [],
}
