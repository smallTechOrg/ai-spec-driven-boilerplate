'use client'

import { ChartSpec } from '@/lib/api'
import { PlotlyChart } from './PlotlyChart'

interface AnswerCardProps {
  question: string
  answer: string | null
  chartSpec: ChartSpec | null
  isLoading?: boolean
  error?: string
}

export function AnswerCard({ question, answer, chartSpec, isLoading, error }: AnswerCardProps) {
  if (isLoading) {
    return (
      <div
        data-testid="answer-card"
        className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm"
      >
        <p className="text-sm text-gray-500 mb-3">{question}</p>
        <div className="animate-pulse space-y-2">
          <div className="h-4 bg-gray-200 rounded w-3/4" />
          <div className="h-4 bg-gray-200 rounded w-1/2" />
          <div className="h-4 bg-gray-200 rounded w-5/6" />
        </div>
        <p className="text-xs text-gray-400 mt-2">Analyzing data...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div
        data-testid="answer-card"
        className="bg-white border border-red-300 rounded-lg p-4 shadow-sm"
      >
        <p className="text-sm text-gray-500 mb-2">{question}</p>
        <div className="rounded bg-red-50 border border-red-200 p-3">
          <p className="text-sm text-red-700">{error}</p>
        </div>
      </div>
    )
  }

  return (
    <div
      data-testid="answer-card"
      className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm"
    >
      <p className="text-sm text-gray-400 mb-2">{question}</p>
      {answer && (
        <p className="text-sm text-gray-900 whitespace-pre-wrap leading-relaxed">{answer}</p>
      )}
      {chartSpec && (
        <div className="mt-3 w-full">
          <PlotlyChart data={chartSpec.data} layout={chartSpec.layout} />
        </div>
      )}
    </div>
  )
}
