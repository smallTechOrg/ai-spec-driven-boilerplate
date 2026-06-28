// Type shim — plotly.js-dist-min exposes the same API as plotly.js
declare module 'plotly.js-dist-min' {
  export * from 'plotly.js'
  import * as Plotly from 'plotly.js'
  export default Plotly
}
