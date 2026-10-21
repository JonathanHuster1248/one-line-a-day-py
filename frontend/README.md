# Frontend

React 19 + TypeScript single-page app, built with Vite and tested with Vitest + React Testing Library.

## Run

The supported way to run the full app is Docker from the repo root (see the [main README](../README.md)):

```
docker compose up --build
```

For frontend development (needs the backend running on port 8000):

```
npm install
npm run dev
```

The dev server runs at <http://localhost:5173> and calls the backend cross-origin, so the backend's CORS settings must allow it (the default `example.env` does).

## Scripts

| Command | What it does |
| --- | --- |
| `npm run dev` | Vite dev server |
| `npm run build` | Type-check (`tsc --noEmit`) then `vite build` |
| `npm run typecheck` | Type-check only |
| `npm run test` | Run Vitest once (`npm run test:watch` to watch) |

## Attachments

Entries can have up to 5 photos or PDFs (15 MB each). The limits in `src/config.ts` mirror the backend's and only let the UI reject early; the backend enforces them.

- `AttachmentPicker` (browse or drag and drop) is used in the new-entry form and in edit mode. The entry is always saved before files upload, one at a time; any failures are listed in `UploadFailureNotice` with Retry.
- `AttachmentFooter` shows an entry's attachments as `AttachmentThumb` tiles that load lazily. Images open in `AttachmentViewer` (a native `<dialog>`), and PDFs open in a new tab.
- Attachment failures stay contained: a broken thumbnail shows its own Retry, and an error in the attachments area shows "Attachments unavailable" without affecting the entry.

## Configuration

`VITE_API_BASE_URL` sets the API base URL (defaults to `http://localhost:8000`). The Docker build sets it to `/api`, and nginx (`nginx.conf`) proxies that path to the backend so everything is same-origin.

Note: `createJournalEntry` / `updateJournalEntry` send `date` and `message` as query parameters on purpose, to match the backend.
