'use client'

import { useEffect, useRef } from 'react'
import type { ChartSpec } from '../lib/api'

interface Props {
  spec: ChartSpec
}

// Chart.js colors palette
const COLORS = [
  'rgba(59, 130, 246, 0.8)',
  'rgba(16, 185, 129, 0.8)',
  'rgba(245, 158, 11, 0.8)',
  'rgba(239, 68, 68, 0.8)',
  'rgba(139, 92, 246, 0.8)',
  'rgba(236, 72, 153, 0.8)',
  'rgba(20, 184, 166, 0.8)',
  'rgba(251, 146, 60, 0.8)',
]

export default function AnalystChart({ spec }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  // Store chart instance as an opaque ref to avoid importing Chart type at module level
  const chartRef = useRef<{ destroy: () => void } | null>(null)

  useEffect(() => {
    // Dynamically import Chart.js on the client only — avoids SSR issues in static export
    import('chart.js/auto').then(({ Chart }) => {
      if (!canvasRef.current) return

      // Destroy previous chart instance before creating a new one
      if (chartRef.current) {
        chartRef.current.destroy()
        chartRef.current = null
      }

      // Assign colors to datasets
      const datasetsWithColors = spec.datasets.map((ds, i) => ({
        ...ds,
        backgroundColor:
          spec.type === 'pie' ? COLORS.slice(0, ds.data.length) : COLORS[i % COLORS.length],
        borderColor: spec.type === 'line' ? COLORS[i % COLORS.length] : undefined,
        borderWidth: spec.type === 'line' ? 2 : undefined,
        fill: spec.type === 'line' ? false : undefined,
        tension: spec.type === 'line' ? 0.3 : undefined,
      }))

      chartRef.current = new Chart(canvasRef.current, {
        type: spec.type,
        data: {
          labels: spec.labels,
          datasets: datasetsWithColors,
        },
        options: {
          responsive: true,
          maintainAspectRatio: true,
          plugins: {
            legend: {
              display: spec.type === 'pie' || spec.datasets.length > 1,
              position: 'bottom',
            },
          },
        },
      }) as { destroy: () => void }
    })

    return () => {
      if (chartRef.current) {
        chartRef.current.destroy()
        chartRef.current = null
      }
    }
  }, [spec])

  return (
    <div className="mt-3 rounded-lg border border-gray-200 bg-white p-4" style={{ minHeight: '320px' }}>
      <canvas ref={canvasRef} />
    </div>
  )
}
