'use client'

import { useEffect, useRef } from 'react'
import type { Data, Layout } from 'plotly.js'

/**
 * Inline Plotly chart renderer (C4).
 *
 * The agent captures any Plotly figure it builds during analysis and returns it
 * as a JSON STRING (one per figure) on the answer's `charts` array. Each string
 * parses to a Plotly figure `{ data, layout, ... }`.
 *
 * We render IMPERATIVELY via `Plotly.newPlot(div, data, layout, { responsive })`
 * inside a `useEffect`, rather than `react-plotly.js`, to avoid React-19 peer
 * friction with the static export. Plotly is imported dynamically (browser-only)
 * so the static-export build never tries to evaluate the bundle during SSG.
 *
 * Robustness:
 *  - Each entry is parsed independently; a malformed JSON entry is skipped
 *    (renders nothing for that slot) and never crashes the surrounding turn.
 *  - `purge` is called on unmount / before re-render to release the Plotly graph.
 */
export function ChartRender({ charts }: { charts?: string[] }) {
  const figures = parseFigures(charts)

  if (figures.length === 0) return null

  return (
    <div className="mt-3 space-y-3" aria-label="Charts">
      {figures.map((fig, i) => (
        <PlotlyFigure key={i} figure={fig} index={i} />
      ))}
    </div>
  )
}

interface Figure {
  data: Data[]
  layout: Partial<Layout>
}

/** Parse the chart JSON strings, dropping any that are malformed / not figures. */
function parseFigures(charts?: string[]): Figure[] {
  if (!Array.isArray(charts)) return []
  const out: Figure[] = []
  for (const raw of charts) {
    if (typeof raw !== 'string' || raw.trim() === '') continue
    try {
      const parsed = JSON.parse(raw) as unknown
      if (!parsed || typeof parsed !== 'object') continue
      const obj = parsed as { data?: unknown; layout?: unknown }
      // A valid Plotly figure has a `data` array; layout is optional.
      if (!Array.isArray(obj.data)) continue
      out.push({
        data: obj.data as Data[],
        layout: (obj.layout && typeof obj.layout === 'object'
          ? (obj.layout as Partial<Layout>)
          : {}) as Partial<Layout>,
      })
    } catch {
      // Malformed JSON for this entry — skip it, never break the turn.
    }
  }
  return out
}

/** A single figure drawn into a responsive div via Plotly's imperative API. */
function PlotlyFigure({ figure, index }: { figure: Figure; index: number }) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    let cancelled = false

    // Browser-only dynamic import keeps the heavy bundle out of SSG.
    import('plotly.js-dist-min')
      .then(mod => {
        if (cancelled || !ref.current) return
        const Plotly = (mod as { default?: typeof import('plotly.js-dist-min') }).default ??
          (mod as unknown as typeof import('plotly.js-dist-min'))
        const layout: Partial<Layout> = {
          autosize: true,
          margin: { l: 48, r: 16, t: 32, b: 40 },
          ...figure.layout,
        }
        void Plotly.newPlot(ref.current, figure.data, layout, {
          responsive: true,
          displaylogo: false,
        })
      })
      .catch(() => {
        // Plotly failed to load — leave an empty box rather than crash the turn.
      })

    return () => {
      cancelled = true
      // Best-effort purge; ignore if Plotly never attached.
      import('plotly.js-dist-min')
        .then(mod => {
          const Plotly = (mod as { default?: typeof import('plotly.js-dist-min') }).default ??
            (mod as unknown as typeof import('plotly.js-dist-min'))
          if (el) Plotly.purge(el)
        })
        .catch(() => {})
    }
  }, [figure])

  return (
    <div
      ref={ref}
      role="img"
      aria-label={`Chart ${index + 1}`}
      className="min-h-[18rem] w-full overflow-hidden rounded-md border border-gray-200 bg-white"
    />
  )
}
