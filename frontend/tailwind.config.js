/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        'store-bg': '#1a1a1a',
        'anchor': '#3b82f6',
        'tag': '#10b981',
        'item': '#f59e0b',
      },
    },
  },
  plugins: [],
}
