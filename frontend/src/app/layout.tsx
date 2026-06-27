import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Data Analysis Agent',
  description: 'Upload a CSV, ask a question, see the answer and the exact code it ran.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50 text-gray-900 antialiased">{children}</body>
    </html>
  )
}
