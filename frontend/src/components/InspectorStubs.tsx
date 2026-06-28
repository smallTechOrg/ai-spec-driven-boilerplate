'use client'

import { ComingSoonBadge, StubChip } from './Stub'

// The observability surfaces that arrive in later phases. Rendered here as
// visible, clearly-labelled non-functional placeholders so the Inspector shows
// the full eventual shape without any of these reading as a bug.

export default function InspectorStubs() {
  return (
    <div className="space-y-4">
      {/* Data-quality flags — P3 */}
      <StubPanel title="Data-quality flags" phase="P3" hint="Nulls, duplicates and outliers spotted at profile time.">
        <div className="flex flex-wrap gap-1.5">
          <StubChip label="Nulls in column" />
          <StubChip label="Possible duplicates" />
          <StubChip label="Outliers" />
        </div>
      </StubPanel>

      {/* Step timeline — P3 (static placeholder in P1) */}
      <StubPanel title="Step timeline" phase="P3" hint="Watch the agent plan → run code → check the result.">
        <ol className="space-y-2">
          {['Planning', 'Running code', 'Checking result'].map((label, i) => (
            <li key={label} className="flex items-center gap-2">
              <span className="flex h-5 w-5 items-center justify-center rounded-full border border-dashed border-slate-300 text-[10px] text-slate-400">
                {i + 1}
              </span>
              <span className="text-xs text-slate-400">{label}</span>
            </li>
          ))}
        </ol>
      </StubPanel>

      {/* Daily cost total — P4 */}
      <StubPanel title="Daily cost total" phase="P4" hint="A running total of today's analysis spend.">
        <p className="font-mono text-lg text-slate-300">$ —.——</p>
      </StubPanel>

      {/* Run-history browser — P4 */}
      <StubPanel title="Run history" phase="P4" hint="Every past question with its code, result, tokens and cost.">
        <div className="space-y-1.5" aria-hidden="true">
          {[0, 1].map(i => (
            <div key={i} className="h-8 rounded border border-dashed border-slate-200 bg-slate-50" />
          ))}
        </div>
      </StubPanel>
    </div>
  )
}

function StubPanel({
  title,
  phase,
  hint,
  children,
}: {
  title: string
  phase: string
  hint: string
  children: React.ReactNode
}) {
  return (
    <section
      aria-disabled="true"
      className="select-none rounded-xl border border-dashed border-slate-300 bg-slate-50/60 p-3.5 opacity-80"
    >
      <header className="mb-1 flex items-center justify-between gap-2">
        <h3 className="text-xs font-semibold text-slate-500">{title}</h3>
        <ComingSoonBadge phase={phase} />
      </header>
      <p className="mb-2.5 text-[11px] leading-relaxed text-slate-400">{hint}</p>
      {children}
    </section>
  )
}
