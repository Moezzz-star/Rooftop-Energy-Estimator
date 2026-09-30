/**
 * Ambient module declarations for non-TS assets imported by the app.
 *
 * - `*.geojson?raw` — Vite `?raw` import of the bundled sample area (parsed +
 *   Zod-validated at load time, so the untyped string is contained).
 * - `*.css` — side-effect stylesheet imports (e.g. the MapLibre GL stylesheet);
 *   Vite handles bundling, Vitest ignores them (`css: false`).
 */
declare module '*.geojson?raw' {
  const content: string;
  export default content;
}

declare module '*.css';
