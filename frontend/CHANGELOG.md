# Changelog

All notable changes to the frontend are documented here.

## [0.3.1] - 2026-10-21

Clearer errors, two bug fixes, and a feature-based source layout.

### Fixed
- A failed load left "Failed to load entries for this day." on screen after later loads succeeded.
- An entry edited onto a different month/day stayed listed on the current page.
- `getJournal` returned the error body as an entry instead of throwing on a non-OK response.

### Changed
- Creating or moving an entry onto a date that already has one shows "You already have an entry for that date." (`DuplicateDateError`, from the backend's `409`), and keeps the draft.
- Signing up with an email that's already registered shows "That email is already registered." (`EmailTakenError`).
- Source is grouped by feature: `src/auth/`, `src/journal/`, `src/attachments/` and `src/shared/`, with `main.tsx`/`App.tsx` at the root. Tests stay next to the modules they cover.

### Tests
- New suites for `journals.ts`, `auth.ts`, `AttachmentViewer`, and the `App`/`AuthProvider` auth gate.
- `JournalApp`: date navigation, duplicate-date message, blank entries, editing (including moving to another day), logout. `JournalBox`: plain edits, Cancel, blank messages, declined and failed deletes. `AuthForms`: signup errors.
- Shared test data in `src/test/factories.ts` (`makeUser`, `makeJournal`, `makeAttachment`, `makeFile`, `jsonResponse`), replacing per-file copies that had drifted apart.

## [0.3.0] - 2026-10-19

Photo and PDF attachments on journal entries.

### Added
- Attachments when creating an entry: `AttachmentPicker` with browse, drag and drop, previews, client-side checks against the 5-file and 15 MB limits, and per-file upload status. The entry is saved first, then files upload one at a time, and failures are listed in `UploadFailureNotice` with Retry and Dismiss.
- Attachments when editing an entry: remove existing ones and add new ones (the cap counts both). Text changes save even if an attachment change fails.
- `AttachmentFooter` with lazy `AttachmentThumb` tiles (skeleton, in-place error with Retry, PDF icon) and an `AttachmentViewer` dialog with Download. An error boundary falls back to "Attachments unavailable".
- `src/attachments.ts` API client, `Attachment` type, and the attachment limits in `src/config.ts`.

### Changed
- `Journal` gains `attachments` and `attachments_available`.
- The new-entry text input and Send button sit in `.new-entry-row`, so their styles no longer apply to the picker.
- `nginx.conf` allows 16 MB request bodies on `/api/` (the default is 1 MB).

## [0.2.2] - 2026-10-18

Tooling and docs.

### Added
- `frontend/.nvmrc` pinning the Node version for consistent local and CI builds.
- Frontend README with setup and usage instructions.

## [0.2.1] - 2026-10-17

Serve the API through nginx so the frontend can be shared on the local network.

### Added
- `frontend/nginx.conf`: serves the SPA (with `index.html` fallback) and proxies `/api/` to the backend over the compose network; `/api/schema` is blocked.

### Changed
- Docker build uses `VITE_API_BASE_URL=/api` (relative) so the app works from whatever address it is opened at.
- `docker-compose.yml` publishes the frontend on all interfaces (`3000`); the backend stays on `127.0.0.1`.

## [0.2.0] - 2026-10-17

Split `App.tsx` responsibilities, add frontend test suite

### Added
- Test suite via Vitest + React Testing Library (`npm run test`/`test:watch`), with `src/test/setup.ts` wiring up `@testing-library/jest-dom` and RTL cleanup; new tests cover `JournalApp`, `AuthForms`, and `date.ts` helpers.
- `src/date.ts` extracted as pure date helpers (`todayISODate`, `toISODate`, `formatMonthDay`, `formatYear`, `shiftDate`, `shiftYear`), previously inlined in `App.tsx`.
- `src/JournalBox.tsx` extracted as its own per-entry card component (view mode plus inline edit/delete, with its own error surfacing).
- `npm run typecheck` script; `npm run build` now type-checks via `tsc --noEmit` before `vite build`.

### Changed
- `App.tsx` reduced to just the auth gate; journal page logic moved into the new `JournalApp.tsx`.
- `greeting.ts` renamed to `journals.ts` as the API client for journal endpoints.
- `models.ts` now holds the single `Journal` type shared across modules instead of duplicating it in `greeting.ts`.

## [0.1.0] - 2026-09-16

Journal page redesign

### Added
- Changelog added with history

## [0.0.1] - 2026-09-16

Journal page redesign

### Added
- Journal-style page layout: entries and the new-entry form now sit inside a single paper-like card (`.journal-page`) centered on a soft backdrop, with a green "bound page" edge accent.
- Date navigation controls on the title row: previous/next day and previous/next year buttons (`shiftDate`, `shiftYear` helpers in `App.tsx`), alongside a large uppercase "MONTH DAY" heading (`formatMonthDay`).
- Scrollable entries list (`.entries`, max-height with `overflow-y: auto`) so a long history of past entries no longer pushes the entry form off-screen.

### Changed
- Entry boxes (`.box`) restyled with a green-bordered, rounded card look, a ruled-notebook-line background behind the entry text, and a header rule under the date.
- Each entry now shows just the year (`formatYear`) as its heading instead of the full ISO date, since day/month is already shown in the page title.
- Date selector and new-entry form/input/button restyled as green pill-shaped controls consistent with the new theme.
- Log Out button repositioned to the top-right corner of the journal card and restyled as a pill button.
- Overall page background, typography (serif), and spacing reworked to read as a physical journal page rather than a plain form.
