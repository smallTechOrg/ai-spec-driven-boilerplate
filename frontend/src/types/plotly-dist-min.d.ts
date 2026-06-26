/**
 * Type shim for `plotly.js-dist-min`.
 *
 * The `plotly.js-dist-min` package ships only the minified bundle (no `.d.ts`),
 * while the community `@types/plotly.js` declares the full API under the
 * `plotly.js` module name. This re-exports those types for the dist-min entry
 * point so we get full typing on `Plotly.newPlot` / `Plotly.purge` etc. without
 * pulling in the (heavier, source-build) `plotly.js` package.
 */
declare module 'plotly.js-dist-min' {
  import * as Plotly from 'plotly.js'
  export = Plotly
}
