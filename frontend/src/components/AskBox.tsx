'use client'

// The question input. Disabled until a dataset is loaded or while a run is in flight.
// The value is controlled by the parent so follow-up chips can pre-fill it.
export function AskBox({
  value,
  onChange,
  onSubmit,
  disabled,
  loading,
}: {
  value: string
  onChange: (v: string) => void
  onSubmit: () => void
  disabled: boolean
  loading: boolean
}) {
  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (disabled || loading || !value.trim()) return
    onSubmit()
  }

  return (
    <form onSubmit={handleSubmit} className="flex items-end gap-2">
      <div className="flex-1">
        <label htmlFor="ask-input" className="sr-only">
          Ask a question about your data
        </label>
        <textarea
          id="ask-input"
          rows={2}
          value={value}
          onChange={e => onChange(e.target.value)}
          onKeyDown={e => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              handleSubmit(e)
            }
          }}
          disabled={disabled || loading}
          placeholder={
            disabled
              ? 'Upload a CSV to start asking questions…'
              : 'Ask a question about your data — e.g. “what is the total revenue by region?”'
          }
          className="w-full resize-none rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
        />
      </div>
      <button
        type="submit"
        disabled={disabled || loading || !value.trim()}
        className="mb-px h-10 shrink-0 rounded-lg bg-indigo-600 px-5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-indigo-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {loading ? 'Working…' : 'Ask'}
      </button>
    </form>
  )
}
