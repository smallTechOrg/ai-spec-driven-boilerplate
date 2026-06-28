'use client'

import { useEffect, useRef, useState } from 'react'

// Renders an interactive Vega-Lite chart from a chart_spec returned by the backend.
// vega-embed is imported dynamically so it never breaks the static-export build.
export default function VegaChart({ spec }: { spec: Record<string, unknown> }) {
  const ref = useRef<HTMLDivElement>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    let view: { finalize: () => void } | null = null
    let cancelled = false
    setErr(null)

    import('vega-embed')
      .then(({ default: embed }) => {
        if (cancelled || !ref.current) return
        return embed(ref.current, spec as never, {
          actions: false,
          renderer: 'svg',
          width: 'container' as never,
        })
      })
      .then(result => {
        if (result && 'view' in result) view = (result as { view: typeof view }).view
      })
      .catch((e: unknown) => {
        if (!cancelled) setErr(e instanceof Error ? e.message : 'Could not render chart')
      })

    return () => {
      cancelled = true
      view?.finalize()
    }
  }, [spec])

  if (err) {
    return (
      <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
        Chart could not be rendered: {err}
      </div>
    )
  }

  return <div ref={ref} data-testid="vega-chart" className="w-full overflow-x-auto" />
}
