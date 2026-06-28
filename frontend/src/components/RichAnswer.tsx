import type { AskResult, Dataset } from '../lib/api'
import { Card } from './ui'
import { KeyStats } from './KeyStats'
import { ChartView } from './ChartView'
import { SummaryTable } from './SummaryTable'
import { CostBadge } from './CostBadge'
import { CodePanel } from './CodePanel'
import { FollowUps } from './FollowUps'

interface RichAnswerProps {
  result: AskResult
  dataset: Dataset
}

/**
 * Renders the full rich-answer envelope from `/api/ask`:
 * plain-language answer, key-stat callouts, auto-picked chart, summary table,
 * written insight, per-query cost, follow-up chips (display-only), and the
 * expandable code/steps/profile panel.
 *
 * A failed run (status === "failed") is rendered TRANSPARENTLY: the user sees
 * the error message and exactly what SQL was attempted, never a crash.
 */
export function RichAnswer({ result, dataset }: RichAnswerProps) {
  const failed = result.status === 'failed'

  if (failed) {
    return <FailedRun result={result} dataset={dataset} />
  }

  return (
    <div className="space-y-5">
      <Card>
        <div className="space-y-5">
          {result.answer && (
            <p className="text-lg font-medium leading-relaxed text-slate-900">{result.answer}</p>
          )}

          <KeyStats stats={result.key_stats} />

          {result.chart_spec && (
            <div>
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                Chart
              </h3>
              <ChartView spec={result.chart_spec} />
            </div>
          )}

          {result.summary_table && (
            <div>
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                Summary
              </h3>
              <SummaryTable table={result.summary_table} />
            </div>
          )}

          {result.insight && (
            <div className="rounded-lg border border-indigo-100 bg-indigo-50/70 p-4">
              <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-indigo-600">
                Insight
              </h3>
              <p className="text-sm leading-relaxed text-slate-800">{result.insight}</p>
            </div>
          )}

          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-4">
            <CostBadge cost={result.cost} />
          </div>
        </div>
      </Card>

      <FollowUps followUps={result.follow_ups} />

      <CodePanel
        generatedSql={result.generated_sql}
        planSteps={result.plan_steps}
        dataset={dataset}
      />
    </div>
  )
}

function FailedRun({ result, dataset }: RichAnswerProps) {
  return (
    <div className="space-y-5">
      <Card className="border-rose-200">
        <div role="alert" className="space-y-3">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center rounded-full bg-rose-100 px-2 py-0.5 text-xs font-medium text-rose-700">
              Run failed
            </span>
            <h2 className="text-base font-semibold text-slate-900">Here&rsquo;s what I tried</h2>
          </div>

          <p className="text-sm leading-relaxed text-slate-700">
            {result.error ?? 'The query could not be completed. The attempted SQL is shown below.'}
          </p>

          {result.generated_sql && (
            <div>
              <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
                Attempted DuckDB SQL
              </h3>
              <pre className="overflow-x-auto rounded-lg bg-slate-900 p-3 text-xs leading-relaxed text-slate-100">
                <code>{result.generated_sql}</code>
              </pre>
            </div>
          )}

          {result.plan_steps.length > 0 && (
            <div>
              <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
                Plan it followed
              </h3>
              <ol className="list-decimal space-y-1 pl-5 text-sm text-slate-700">
                {result.plan_steps.map((step, i) => (
                  <li key={i}>{step}</li>
                ))}
              </ol>
            </div>
          )}

          <p className="text-xs text-slate-500">
            Try rephrasing your question. Available columns:{' '}
            {dataset.profile.columns.map((c) => c.name).join(', ')}.
          </p>
        </div>
      </Card>
    </div>
  )
}
