'use client'

import { useEffect, useRef } from 'react'

interface PlotlyChartProps {
  data: Record<string, unknown>[]
  layout: Record<string, unknown>
}

export function PlotlyChart({ data, layout }: PlotlyChartProps) {
  const divRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!divRef.current || !data) return

    let cancelled = false
    const el = divRef.current

    import('plotly.js-dist-min').then((Plotly) => {
      if (cancelled || !el) return
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      Plotly.newPlot(el, data as any, layout as any, { responsive: true })
    })

    const handleResize = () => {
      import('plotly.js-dist-min').then((Plotly) => {
        if (el) Plotly.Plots.resize(el)
      })
    }
    window.addEventListener('resize', handleResize)

    return () => {
      cancelled = true
      window.removeEventListener('resize', handleResize)
      import('plotly.js-dist-min').then((Plotly) => {
        if (el) Plotly.purge(el)
      })
    }
  }, [data, layout])

  return <div ref={divRef} style={{ width: '100%', minHeight: '300px' }} />
}
