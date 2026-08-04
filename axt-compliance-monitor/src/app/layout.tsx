import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'AXT Compliance Monitor | ZOE by AXT Labs',
  description: 'Real-time AI audit log compliance monitoring for AXT — AVL-3 tier. Powered by ZOE.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="bg-[#0a0a0f] text-slate-100 antialiased">
        {children}
      </body>
    </html>
  )
}
