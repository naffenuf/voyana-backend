/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'voyana-brown': '#8B6F47',
        'voyana-brown-dark': '#6F5838',
        'voyana-brown-darker': '#944F2E',
        'voyana-brown-hover': '#7d4227',
        'voyana-cream': '#F6EDD9',
      },
    },
  },
  plugins: [],
}
