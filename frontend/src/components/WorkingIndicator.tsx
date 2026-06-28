'use client'

import { useEffect, useState } from 'react'

const STEPS = ['Planning', 'Generating code', 'Executing', 'Verifying']

// Live working indicator with a frontend-side elapsed timer. The cycling step label is
// indicative of the agent loop; the timer reflects real wall-clock time.
export default function WorkingIndicator() {
  const [elapsed, setElapsed] = useState(0)
  const [step, setStep] = useState(0)

  useEffect(() => {
    const t = setInterval(() => setElapsed(e => e + 0.1), 100)
    const s = setInterval(() => setStep(i => (i + 1) % STEPS.length), 1500)
    return () => {
      clearInterval(t)
      clearInterval(s)
    }
  }, [])

  return (
    <div
      data-testid="working-indicator"
      className="flex items-center gap-3 rounded-xl border border-indigo-200 bg-indigo-50 p-4 text-sm text-indigo-800 shadow-sm"
    >
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-indigo-300 border-t-indigo-600" />
      <span className="font-medium">{STEPS[step]}…</span>
      <span className="ml-auto font-mono text-xs tabular-nums text-indigo-500">
        {elapsed.toFixed(1)}s
      </span>
    </div>
  )
}
