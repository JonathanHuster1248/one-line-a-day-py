# Changelog

All notable changes to the frontend are documented here.

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
