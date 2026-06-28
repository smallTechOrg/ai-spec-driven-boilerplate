import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Local Data Analyst',
  description: 'Ask questions of your spreadsheets in plain English — your data stays local.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-50 text-slate-900 antialiased">{children}</body>
    </html>
  )
}
