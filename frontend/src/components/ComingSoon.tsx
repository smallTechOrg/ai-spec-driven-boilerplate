// Shared "Coming soon" badge used to mark non-functional, deferred-phase stubs
// so the user sees the product vision without mistaking a stub for a bug.
export function ComingSoonBadge({ className = '' }: { className?: string }) {
  return (
    <span
      className={`inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-amber-700 ${className}`}
    >
      Coming soon
    </span>
  )
}
