'use client'

import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from 'react'
import type { DatasetSummary } from '@/lib/api'

/**
 * Schema / ER-diagram panel — REAL (Phase 4).
 *
 * Renders each dataset as a table card in an SVG canvas and draws inferred
 * foreign-key edges between them. `_erFkLinks(datasets)` is the SINGLE SOURCE OF
 * TRUTH for both the edges drawn here AND the PK/FK badges in the table
 * description panel (which imports it), so the diagram and the badges never
 * disagree.
 *
 * Interactions: Fit / + / − zoom controls (0.5×–3×), drag-pan, wheel-zoom, click
 * a card to select that dataset (lifted to DatabaseTab), and hover a card to
 * highlight its relationships while dimming the rest.
 */

// ---------------------------------------------------------------------------
// Dataset-with-columns helpers
// ---------------------------------------------------------------------------

/** A dataset carrying its column metadata for the diagram. */
export interface ErDataset extends DatasetSummary {
  /** Column names — `GET /datasets` may carry these directly. */
  columns?: string[]
  /** Or a {name,dtype} schema (GET /datasets/{id}). */
  columns_schema?: { name: string; dtype: string }[]
}

interface ColInfo {
  name: string
  dtype: string
}

/** Extract column {name,dtype} from whatever column shape a dataset carries. */
function datasetColumns(ds: ErDataset): ColInfo[] {
  if (Array.isArray(ds.columns_schema) && ds.columns_schema.length > 0) {
    return ds.columns_schema.map(c => ({ name: String(c.name), dtype: String(c.dtype) }))
  }
  if (Array.isArray(ds.columns)) {
    return ds.columns.map(name => ({ name: String(name), dtype: 'text' }))
  }
  // Some payloads carry `columns_json` (raw {name:dtype} or string[]).
  const raw = (ds as Record<string, unknown>).columns_json
  if (Array.isArray(raw)) {
    return raw.map(name => ({ name: String(name), dtype: 'text' }))
  }
  if (raw && typeof raw === 'object') {
    return Object.entries(raw as Record<string, unknown>).map(([name, dt]) => ({
      name,
      dtype: String(dt),
    }))
  }
  return []
}

// ---------------------------------------------------------------------------
// FK inference — _erFkLinks (the single source of truth)
// ---------------------------------------------------------------------------

/** Generic columns that are too common to be a meaningful join key. */
const GENERIC_DENYLIST = new Set([
  'id',
  'name',
  'date',
  'value',
  'count',
  'type',
  'status',
  'description',
  'title',
  'created_at',
  'updated_at',
  'timestamp',
  'index',
])

/** The `zip_code_prefix` family normalises to a single geolocation hub. */
const ZIP_FAMILY = new Set([
  'zip_code_prefix',
  'geolocation_zip_code_prefix',
  'customer_zip_code_prefix',
  'seller_zip_code_prefix',
])

export interface ErLink {
  /** The PK ("one") side dataset id. */
  fromId: string
  /** The FK ("many") side dataset id. */
  toId: string
  /** The join column (normalised name). */
  column: string
  /** Whether either endpoint is a derived dataset (drawn dashed green). */
  derived: boolean
}

/** A per-dataset key summary derived from `_erFkLinks`, for the badge panel. */
export interface ErKeys {
  /** Columns where this dataset is the canonical PK ("one") table. */
  pk: string[]
  /** Columns where this dataset references another (the "many"/FK side). */
  fk: { column: string; references: string }[]
}

function norm(col: string): string {
  return col.trim().toLowerCase()
}

/** Choose the canonical PK table for a shared column by filename heuristics. */
function pickPkTable(
  column: string,
  candidates: { id: string; filename: string }[],
): string {
  if (candidates.length === 0) return ''
  // A column like `customer_id` points at the table whose stem matches the
  // column's entity (`customer` / `customers`). Prefer the shortest matching
  // filename (the dimension table), else the shortest filename overall.
  const entity = column.replace(/_id$/, '')
  const singular = entity.replace(/s$/, '')
  const stem = (fn: string) =>
    fn.replace(/\.[^.]+$/, '').toLowerCase().replace(/[^a-z0-9]/g, '')

  const matches = candidates.filter(c => {
    const s = stem(c.filename)
    return s === entity || s === `${entity}s` || s === singular || s === `${singular}s`
  })
  const pool = matches.length > 0 ? matches : candidates
  return [...pool].sort((a, b) => a.filename.length - b.filename.length)[0].id
}

/**
 * Infer foreign-key links across datasets. The SINGLE SOURCE OF TRUTH for both
 * the diagram edges and the description panel's PK/FK badges.
 *
 * Rules (spec/ui.md):
 *  - columns ending `_id` shared by ≥2 tables → an FK link (PK table chosen by
 *    filename; the other tables reference it);
 *  - the `zip_code_prefix` family normalises to a geolocation hub;
 *  - other exact-name shared specific columns link (denylist of generic columns
 *    excluded);
 *  - generic columns (`id`, `name`, `date`, `value`, `count`, `type`, `status`,…)
 *    never link.
 */
export function _erFkLinks(datasets: ErDataset[]): ErLink[] {
  const tables = datasets.map(ds => ({
    id: ds.id,
    filename: ds.filename,
    derived: ds.origin === 'derived',
    cols: new Set(datasetColumns(ds).map(c => norm(c.name))),
  }))

  // Map a (normalised) join column → the tables that contain it.
  const colToTables = new Map<string, { id: string; filename: string; derived: boolean }[]>()

  for (const t of tables) {
    for (const raw of t.cols) {
      // Normalise the zip family to one logical column.
      const col = ZIP_FAMILY.has(raw) ? 'zip_code_prefix' : raw
      const isId = col.endsWith('_id')
      const isZip = col === 'zip_code_prefix'
      const isSpecific = !GENERIC_DENYLIST.has(col)
      // Only `_id` columns, the zip hub, or specific (non-generic) shared names
      // are eligible to be join keys.
      if (!isId && !isZip && !isSpecific) continue
      if (GENERIC_DENYLIST.has(col)) continue
      const arr = colToTables.get(col) ?? []
      arr.push({ id: t.id, filename: t.filename, derived: t.derived })
      colToTables.set(col, arr)
    }
  }

  const links: ErLink[] = []
  const seen = new Set<string>()

  for (const [col, members] of colToTables) {
    if (members.length < 2) continue // shared by ≥2 tables only

    const pkId =
      col === 'zip_code_prefix'
        ? // The geolocation hub: prefer a table whose name mentions geolocation.
          (members.find(m => /geo/i.test(m.filename)) ?? members[0]).id
        : pickPkTable(col, members)

    for (const m of members) {
      if (m.id === pkId) continue
      const key = `${pkId}->${m.id}:${col}`
      if (seen.has(key)) continue
      seen.add(key)
      const pkMember = members.find(x => x.id === pkId)
      links.push({
        fromId: pkId,
        toId: m.id,
        column: col,
        derived: m.derived || (pkMember?.derived ?? false),
      })
    }
  }

  return links
}

/** Per-dataset PK/FK key summary for the description panel, from `_erFkLinks`. */
export function _erKeysFor(datasetId: string, datasets: ErDataset[]): ErKeys {
  const links = _erFkLinks(datasets)
  const byId = new Map(datasets.map(d => [d.id, d.filename] as const))
  const pk = new Set<string>()
  const fk: { column: string; references: string }[] = []
  for (const l of links) {
    if (l.fromId === datasetId) pk.add(l.column)
    if (l.toId === datasetId) {
      fk.push({ column: l.column, references: byId.get(l.fromId) ?? l.fromId })
    }
  }
  return { pk: [...pk], fk }
}

// ---------------------------------------------------------------------------
// Layout
// ---------------------------------------------------------------------------

const CARD_W = 220
const HEADER_H = 34
const ROW_H = 20
const MAX_ROWS = 8
const GAP_X = 90
const GAP_Y = 56

interface CardLayout {
  ds: ErDataset
  cols: ColInfo[]
  x: number
  y: number
  w: number
  h: number
}

/** Grid layout with column-count derived from the dataset count + aspect. */
function layoutCards(datasets: ErDataset[]): { cards: CardLayout[]; width: number; height: number } {
  const n = datasets.length
  if (n === 0) return { cards: [], width: 0, height: 0 }
  const perRow = Math.max(1, Math.ceil(Math.sqrt(n)))
  const cards: CardLayout[] = datasets.map((ds, i) => {
    const cols = datasetColumns(ds)
    const shown = Math.min(cols.length, MAX_ROWS)
    const extra = cols.length > MAX_ROWS ? 1 : 0
    const h = HEADER_H + (shown + extra) * ROW_H + 8
    const c = i % perRow
    return {
      ds,
      cols,
      x: c * (CARD_W + GAP_X) + 24,
      y: 24, // reassigned in the per-row max-height pass below
      w: CARD_W,
      h,
    }
  })
  // Resolve per-row y using each row's tallest card so rows don't overlap.
  let rowY = 24
  const rows = Math.ceil(n / perRow)
  for (let r = 0; r < rows; r++) {
    const rowCards = cards.slice(r * perRow, r * perRow + perRow)
    const rowH = Math.max(...rowCards.map(c => c.h), HEADER_H)
    for (const c of rowCards) c.y = rowY
    rowY += rowH + GAP_Y
  }
  const width = perRow * (CARD_W + GAP_X) + 24
  const height = rowY + 24
  return { cards, width, height }
}

// ---------------------------------------------------------------------------
// dtype color dot
// ---------------------------------------------------------------------------

function dtypeColor(dtype: string): string {
  const d = dtype.toLowerCase()
  if (/(int|float|number|numeric|double)/.test(d)) return '#3b82f6' // blue — number
  if (/(date|time)/.test(d)) return '#f59e0b' // amber — date
  if (/bool/.test(d)) return '#22c55e' // green — boolean
  if (/(text|object|string|str|category)/.test(d)) return '#a855f7' // purple — text
  return '#9ca3af' // grey — other
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ERDiagramPanel({
  datasets,
  selectedId,
  onSelect,
}: {
  datasets: ErDataset[]
  selectedId: string | null
  onSelect: (id: string) => void
}) {
  const { cards, width, height } = useMemo(() => layoutCards(datasets), [datasets])
  const links = useMemo(() => _erFkLinks(datasets), [datasets])

  const containerRef = useRef<HTMLDivElement>(null)
  const [zoom, setZoom] = useState(1)
  const [pan, setPan] = useState({ x: 0, y: 0 })
  const [hoverId, setHoverId] = useState<string | null>(null)
  const dragRef = useRef<{ startX: number; startY: number; panX: number; panY: number } | null>(
    null,
  )
  const [viewSize, setViewSize] = useState({ w: 600, h: 360 })

  // Track the container size so Fit can centre the diagram.
  useLayoutEffect(() => {
    const el = containerRef.current
    if (!el) return
    const update = () => setViewSize({ w: el.clientWidth, h: el.clientHeight })
    update()
    const ro = new ResizeObserver(update)
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  const clampZoom = (z: number) => Math.min(3, Math.max(0.5, z))

  const fit = useCallback(() => {
    if (width === 0 || height === 0) {
      setZoom(1)
      setPan({ x: 0, y: 0 })
      return
    }
    const z = clampZoom(Math.min(viewSize.w / width, viewSize.h / height, 1))
    setZoom(z)
    setPan({
      x: (viewSize.w - width * z) / 2,
      y: (viewSize.h - height * z) / 2,
    })
  }, [width, height, viewSize.w, viewSize.h])

  // Auto-fit when the dataset set changes.
  useEffect(() => {
    fit()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [datasets.length, viewSize.w, viewSize.h])

  const zoomBy = useCallback((factor: number) => {
    setZoom(z => clampZoom(z * factor))
  }, [])

  const onWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault()
    const factor = e.deltaY < 0 ? 1.1 : 1 / 1.1
    setZoom(z => clampZoom(z * factor))
  }, [])

  const onPointerDown = useCallback(
    (e: React.PointerEvent) => {
      // Only start a pan from empty canvas (cards stop propagation for clicks).
      dragRef.current = { startX: e.clientX, startY: e.clientY, panX: pan.x, panY: pan.y }
      ;(e.target as Element).setPointerCapture?.(e.pointerId)
    },
    [pan.x, pan.y],
  )

  const onPointerMove = useCallback((e: React.PointerEvent) => {
    const d = dragRef.current
    if (!d) return
    setPan({ x: d.panX + (e.clientX - d.startX), y: d.panY + (e.clientY - d.startY) })
  }, [])

  const onPointerUp = useCallback((e: React.PointerEvent) => {
    dragRef.current = null
    ;(e.target as Element).releasePointerCapture?.(e.pointerId)
  }, [])

  const cardById = useMemo(() => new Map(cards.map(c => [c.ds.id, c])), [cards])

  // The set of dataset ids related to the hovered card (for dim/highlight).
  const relatedIds = useMemo(() => {
    if (!hoverId) return null
    const ids = new Set<string>([hoverId])
    for (const l of links) {
      if (l.fromId === hoverId) ids.add(l.toId)
      if (l.toId === hoverId) ids.add(l.fromId)
    }
    return ids
  }, [hoverId, links])

  const isEmpty = datasets.length === 0

  return (
    <section
      aria-labelledby="schema-heading"
      className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm"
    >
      <div className="mb-3 flex items-center justify-between gap-2">
        <h2 id="schema-heading" className="text-sm font-semibold text-gray-800">
          Schema
        </h2>
        <div className="flex gap-1.5">
          <button
            type="button"
            onClick={fit}
            disabled={isEmpty}
            aria-label="Fit diagram to view"
            className="rounded-md border border-gray-200 bg-white px-3 py-1 text-xs font-medium text-gray-600 hover:bg-gray-50 disabled:cursor-not-allowed disabled:text-gray-300"
          >
            Fit
          </button>
          <button
            type="button"
            onClick={() => zoomBy(1.2)}
            disabled={isEmpty}
            aria-label="Zoom in"
            className="rounded-md border border-gray-200 bg-white px-3 py-1 text-xs font-medium text-gray-600 hover:bg-gray-50 disabled:cursor-not-allowed disabled:text-gray-300"
          >
            +
          </button>
          <button
            type="button"
            onClick={() => zoomBy(1 / 1.2)}
            disabled={isEmpty}
            aria-label="Zoom out"
            className="rounded-md border border-gray-200 bg-white px-3 py-1 text-xs font-medium text-gray-600 hover:bg-gray-50 disabled:cursor-not-allowed disabled:text-gray-300"
          >
            −
          </button>
        </div>
      </div>

      {isEmpty ? (
        <div className="flex min-h-[18rem] flex-col items-center justify-center rounded-md border-2 border-dashed border-gray-200 bg-gray-50 px-4 py-12 text-center">
          <span aria-hidden="true" className="mb-2 text-3xl text-gray-300">
            ⬚
          </span>
          <p className="text-sm font-medium text-gray-500">No datasets yet</p>
          <p className="mt-1 text-xs text-gray-400">
            Upload a CSV on the Analyse tab to see the schema diagram.
          </p>
        </div>
      ) : (
        <div
          ref={containerRef}
          onWheel={onWheel}
          className="relative h-[26rem] w-full cursor-grab touch-none overflow-hidden rounded-md border border-gray-100 bg-gray-50 active:cursor-grabbing"
        >
          <svg
            width="100%"
            height="100%"
            role="img"
            aria-label="Entity-relationship diagram"
            onPointerDown={onPointerDown}
            onPointerMove={onPointerMove}
            onPointerUp={onPointerUp}
            onPointerLeave={onPointerUp}
          >
            <defs>
              {/* Crow's-foot (many) marker at the FK end. */}
              <marker
                id="er-crow"
                viewBox="0 0 12 12"
                refX="11"
                refY="6"
                markerWidth="12"
                markerHeight="12"
                orient="auto"
              >
                <path d="M11,6 L1,1 M11,6 L1,6 M11,6 L1,11" stroke="#64748b" fill="none" />
              </marker>
              <marker
                id="er-crow-d"
                viewBox="0 0 12 12"
                refX="11"
                refY="6"
                markerWidth="12"
                markerHeight="12"
                orient="auto"
              >
                <path d="M11,6 L1,1 M11,6 L1,6 M11,6 L1,11" stroke="#16a34a" fill="none" />
              </marker>
              {/* Tick (one) marker at the PK end. */}
              <marker
                id="er-tick"
                viewBox="0 0 12 12"
                refX="1"
                refY="6"
                markerWidth="12"
                markerHeight="12"
                orient="auto"
              >
                <path d="M4,1 L4,11" stroke="#64748b" fill="none" />
              </marker>
              <marker
                id="er-tick-d"
                viewBox="0 0 12 12"
                refX="1"
                refY="6"
                markerWidth="12"
                markerHeight="12"
                orient="auto"
              >
                <path d="M4,1 L4,11" stroke="#16a34a" fill="none" />
              </marker>
            </defs>

            <g transform={`translate(${pan.x},${pan.y}) scale(${zoom})`}>
              {/* Edges first (under the cards). */}
              {links.map((l, i) => {
                const a = cardById.get(l.fromId)
                const b = cardById.get(l.toId)
                if (!a || !b) return null
                const dimmed =
                  relatedIds !== null && !(relatedIds.has(l.fromId) && relatedIds.has(l.toId))
                return (
                  <Edge key={`${l.fromId}-${l.toId}-${l.column}-${i}`} a={a} b={b} link={l} dimmed={dimmed} />
                )
              })}

              {/* Cards on top. */}
              {cards.map(card => {
                const dimmed = relatedIds !== null && !relatedIds.has(card.ds.id)
                return (
                  <TableCard
                    key={card.ds.id}
                    card={card}
                    selected={selectedId === card.ds.id}
                    dimmed={dimmed}
                    onSelect={() => onSelect(card.ds.id)}
                    onHover={() => setHoverId(card.ds.id)}
                    onLeave={() => setHoverId(null)}
                  />
                )
              })}
            </g>
          </svg>

          {/* Legend */}
          <div className="pointer-events-none absolute bottom-2 left-2 flex flex-wrap items-center gap-2 rounded bg-white/85 px-2 py-1 text-[10px] text-gray-500 shadow-sm">
            <span className="inline-flex items-center gap-1">
              <span className="inline-block h-2.5 w-2.5 rounded-sm bg-blue-500" /> uploaded
            </span>
            <span className="inline-flex items-center gap-1">
              <span className="inline-block h-2.5 w-2.5 rounded-sm bg-green-600" /> derived
            </span>
            <span className="inline-flex items-center gap-1">
              <span className="inline-block h-0.5 w-4 bg-slate-400" /> FK edge
            </span>
          </div>
        </div>
      )}
    </section>
  )
}

// ---------------------------------------------------------------------------
// SVG sub-components
// ---------------------------------------------------------------------------

/** A column-anchored elbow edge: crow's-foot at the FK end, tick at the PK end. */
function Edge({
  a,
  b,
  link,
  dimmed,
}: {
  a: CardLayout
  b: CardLayout
  link: ErLink
  dimmed: boolean
}) {
  // PK side = a (from), FK side = b (to). Anchor at the nearer horizontal edge.
  const aCenter = a.x + a.w / 2
  const bCenter = b.x + b.w / 2
  const aRight = bCenter >= aCenter
  const ax = aRight ? a.x + a.w : a.x
  const ay = a.y + HEADER_H / 2
  const bLeft = bCenter > aCenter
  const bx = bLeft ? b.x : b.x + b.w
  const by = b.y + HEADER_H / 2

  // Orthogonal elbow routed via the horizontal midpoint.
  const midX = (ax + bx) / 2
  const path = `M ${ax} ${ay} H ${midX} V ${by} H ${bx}`

  const stroke = link.derived ? '#16a34a' : '#64748b'
  const tickMarker = link.derived ? 'url(#er-tick-d)' : 'url(#er-tick)'
  const crowMarker = link.derived ? 'url(#er-crow-d)' : 'url(#er-crow)'

  return (
    <g opacity={dimmed ? 0.15 : 1}>
      <path
        d={path}
        fill="none"
        stroke={stroke}
        strokeWidth={1.5}
        strokeDasharray={link.derived ? '5 4' : undefined}
        markerStart={tickMarker}
        markerEnd={crowMarker}
      />
      {/* Hover-only join-key pill (title shows on hover). */}
      <title>{`${link.column} (FK)`}</title>
    </g>
  )
}

/** A single table card with a colored header and a zebra-striped column list. */
function TableCard({
  card,
  selected,
  dimmed,
  onSelect,
  onHover,
  onLeave,
}: {
  card: CardLayout
  selected: boolean
  dimmed: boolean
  onSelect: () => void
  onHover: () => void
  onLeave: () => void
}) {
  const derived = card.ds.origin === 'derived'
  const headerFill = derived ? '#16a34a' : '#2563eb'
  const shown = card.cols.slice(0, MAX_ROWS)
  const extra = card.cols.length - shown.length

  return (
    <g
      transform={`translate(${card.x},${card.y})`}
      opacity={dimmed ? 0.3 : 1}
      style={{ cursor: 'pointer' }}
      onPointerDown={e => e.stopPropagation()}
      onClick={onSelect}
      onMouseEnter={onHover}
      onMouseLeave={onLeave}
    >
      {/* Card body */}
      <rect
        x={0}
        y={0}
        width={card.w}
        height={card.h}
        rx={6}
        fill="#ffffff"
        stroke={selected ? '#f59e0b' : '#cbd5e1'}
        strokeWidth={selected ? 2.5 : 1}
      />
      {/* Header */}
      <rect x={0} y={0} width={card.w} height={HEADER_H} rx={6} fill={headerFill} />
      <rect x={0} y={HEADER_H - 6} width={card.w} height={6} fill={headerFill} />
      <text
        x={10}
        y={HEADER_H / 2 + 4}
        fontSize={12}
        fontWeight={600}
        fill="#ffffff"
        style={{ pointerEvents: 'none' }}
      >
        {truncate(card.ds.filename, 22)}
      </text>
      {derived && (
        <>
          <rect
            x={card.w - 56}
            y={8}
            width={48}
            height={16}
            rx={8}
            fill="rgba(255,255,255,0.25)"
          />
          <text
            x={card.w - 32}
            y={20}
            fontSize={9}
            fontWeight={600}
            fill="#ffffff"
            textAnchor="middle"
            style={{ pointerEvents: 'none' }}
          >
            derived
          </text>
        </>
      )}

      {/* Columns */}
      {shown.map((c, i) => {
        const y = HEADER_H + i * ROW_H
        return (
          <g key={c.name} style={{ pointerEvents: 'none' }}>
            {i % 2 === 1 && (
              <rect x={1} y={y} width={card.w - 2} height={ROW_H} fill="#f8fafc" />
            )}
            <circle cx={12} cy={y + ROW_H / 2} r={3.5} fill={dtypeColor(c.dtype)} />
            <text x={24} y={y + ROW_H / 2 + 4} fontSize={11} fill="#334155">
              {truncate(c.name, 22)}
            </text>
          </g>
        )
      })}
      {extra > 0 && (
        <text
          x={24}
          y={HEADER_H + shown.length * ROW_H + ROW_H / 2 + 4}
          fontSize={10}
          fontStyle="italic"
          fill="#94a3b8"
          style={{ pointerEvents: 'none' }}
        >
          +{extra} more
        </text>
      )}
    </g>
  )
}

function truncate(s: string, n: number): string {
  return s.length > n ? `${s.slice(0, n - 1)}…` : s
}
