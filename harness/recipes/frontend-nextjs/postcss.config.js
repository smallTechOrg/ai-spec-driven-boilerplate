// Tailwind 3 runs as a PostCSS plugin — this file wires the pipeline Next.js
// applies to globals.css. Without it, the @tailwind directives are not expanded.
module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
