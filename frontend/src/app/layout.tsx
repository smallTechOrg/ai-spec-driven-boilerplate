import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'DataChat — private spreadsheet analysis',
  description:
    'Ask your CSV/Excel files in plain language. The agent writes pandas that runs locally — your raw rows never leave the machine.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-50 text-slate-900 antialiased">{children}</body>
    </html>
  )
}
