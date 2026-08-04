import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        axt: {
          dark: '#0a0a0f',
          card: '#111118',
          border: '#1e1e2e',
          accent: '#6366f1',
          success: '#22c55e',
          warning: '#f59e0b',
          danger: '#ef4444',
          muted: '#4b5563',
        },
      },
    },
  },
  plugins: [],
}

export default config
