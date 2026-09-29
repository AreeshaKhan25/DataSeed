# Frontend

React 19-era stack: Vite + TypeScript + Tailwind + Framer Motion. No router and no
data-fetching library, a nine-screen single-page tool does not need either, and each
one is a dependency plus a build step.

```bash
npm install
npm run dev     # http://localhost:5173, proxies /api to port 8000
npm run build   # emits into ../web, which FastAPI serves at /
```

## Design

- **Source Serif 4** for headings, **Mona Sans** for interface text. The serif/geometric
  split is what stops this reading as a generic dashboard template.
- Google-grade light palette on `#f6f8fb`, white cards, hairline `#e4e8ef` borders,
  navy `#1f4e79` as the single primary, functional colours for status only.
- Numbers use tabular figures (`.tnum`) so columns do not jitter while values stream in.
- A floating macOS-style dock with true distance-based magnification, driven by one
  shared motion value rather than a React re-render per mouse move.

## Structure

```
src/
  lib/api.ts       typed client; every backend error carries a remedy
  lib/motion.ts one motion vocabulary, durations and springs live here
  lib/store.tsx    small context store; screen, project, schema, report, job
  components/      Dock, DataTable, Icons, ui primitives
  screens/         one file per dock destination
```

## Motion

Every animation is defined in `lib/motion.ts` so the whole app shares a rhythm.
`prefers-reduced-motion` is respected in `index.css`.

Note: browsers throttle `requestAnimationFrame` in background tabs, so entry animations
pause until the tab is visible and then complete. That is expected behaviour.
