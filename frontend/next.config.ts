import type { NextConfig } from 'next'

const config: NextConfig = {
  output: 'export',
  basePath: '/app',
  trailingSlash: true,
  webpack: config => {
    // vega pulls in an optional Node-only `canvas` dep; we render with the SVG renderer in
    // the browser, so alias it to false to avoid the (benign) "Can't resolve 'canvas'" warning.
    config.resolve.alias = { ...config.resolve.alias, canvas: false }
    return config
  },
}

export default config
