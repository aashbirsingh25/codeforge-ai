/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          bg: '#090d16',
          panel: '#111726',
          card: '#1b233a',
          code: '#05080e',
        },
        accent: {
          primary: '#00f2fe',
          secondary: '#4facfe',
          green: '#10b981',
          red: '#ef4444',
          purple: '#a855f7',
        }
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        mono: ['Fira Code', 'monospace'],
      }
    },
  },
  plugins: [],
}
