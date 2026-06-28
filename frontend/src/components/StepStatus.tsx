'use client'

import { STEP_ORDER, type StepName, type StepStatus } from '@/lib/api'
import { Spinner } from './UploadZone'

export type StepMap = Record<StepName, StepStatus>

export const INITIAL_STEPS: StepMap = {
  plan: 'pending',
  generate_code: 'pending',
  execute_local: 'pending',
  visualize: 'pending',
}

export function StepStatusBar({ steps }: { steps: StepMap }) {
  return (
    <ol className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs">
      {STEP_ORDER.map(({ key, label }, i) => {
        const status = steps[key]
        return (
          <li key={key} className="flex items-center gap-2">
            <span
              className={[
                'flex items-center gap-1.5 rounded-full px-2.5 py-1 font-medium',
                status === 'done'
                  ? 'bg-emerald-50 text-emerald-700'
                  : status === 'running'
                    ? 'bg-indigo-50 text-indigo-700'
                    : status === 'error'
                      ? 'bg-red-50 text-red-700'
                      : 'bg-slate-100 text-slate-400',
              ].join(' ')}
            >
              {status === 'running' ? (
                <Spinner className="h-3 w-3 text-indigo-500" />
              ) : status === 'done' ? (
                <Check />
              ) : status === 'error' ? (
                <Cross />
              ) : (
                <span className="h-1.5 w-1.5 rounded-full bg-slate-300" />
              )}
              {label}
            </span>
            {i < STEP_ORDER.length - 1 && <span className="text-slate-300">→</span>}
          </li>
        )
      })}
    </ol>
  )
}

function Check() {
  return (
    <svg className="h-3 w-3" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
      <path fillRule="evenodd" d="M16.7 5.3a1 1 0 0 1 0 1.4l-7.5 7.5a1 1 0 0 1-1.4 0L3.3 9.7a1 1 0 1 1 1.4-1.4l3.1 3.1 6.8-6.8a1 1 0 0 1 1.4 0Z" clipRule="evenodd" />
    </svg>
  )
}

function Cross() {
  return (
    <svg className="h-3 w-3" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
      <path fillRule="evenodd" d="M10 8.6 5.7 4.3a1 1 0 0 0-1.4 1.4L8.6 10l-4.3 4.3a1 1 0 1 0 1.4 1.4L10 11.4l4.3 4.3a1 1 0 0 0 1.4-1.4L11.4 10l4.3-4.3a1 1 0 0 0-1.4-1.4L10 8.6Z" clipRule="evenodd" />
    </svg>
  )
}
