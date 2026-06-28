// Small shared UI primitives used across the workspace.

interface SpinnerProps {
  label?: string
}

/** An accessible spinner with optional context label. */
export function Spinner({ label }: SpinnerProps) {
  return (
    <div role="status" aria-live="polite" className="flex items-center gap-3 text-sm text-slate-600">
      <span
        aria-hidden="true"
        className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-indigo-600 motion-reduce:animate-none"
      />
      {label && <span>{label}</span>}
    </div>
  )
}

interface ErrorBannerProps {
  message: string
  title?: string
}

/** A human, non-stack-trace error banner. */
export function ErrorBanner({ message, title = 'Something went wrong' }: ErrorBannerProps) {
  return (
    <div
      role="alert"
      className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800"
    >
      <p className="font-semibold">{title}</p>
      <p className="mt-1 leading-relaxed">{message}</p>
    </div>
  )
}

interface CardProps {
  children: React.ReactNode
  className?: string
}

/** A standard white workspace card. */
export function Card({ children, className = '' }: CardProps) {
  return (
    <section className={`rounded-xl border border-slate-200 bg-white p-5 shadow-sm ${className}`}>
      {children}
    </section>
  )
}
