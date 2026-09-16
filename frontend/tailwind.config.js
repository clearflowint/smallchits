/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // ClearFlow Automations brand palette (Blueprint section 10)
        clearflow: {
          slate: '#0F172A',
          blue: '#2563EB',
          'blue-light': '#3B82F6',
          surplus: '#16A34A',
          deficit: '#DC2626',
          pending: '#F59E0B'
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif']
      }
    }
  },
  plugins: []
}
