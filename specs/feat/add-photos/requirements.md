# Photos: Requirements

> Scope: this document defines **what** the feature must do. Implementation (storage, schema, API shape, loading strategy) is deferred to `design.md`.

## Overview

Users can attach photos (and other supported files) to a journal entry. Attachments are private to the uploading user, linked to a single journal entry, and displayed in an attachments footer on that entry's journal box. A `Photo` model exists in the backend today but is only a placeholder, not wired to any controller or the frontend; the design may modify or remove it.

## Functional Requirements

### Upload and management
- **FR-1** When creating a new journal entry, the user can attach one or more files; the files are saved with the entry as part of the same submission.
- **FR-2** The user can select files via a file browser dialog (required).
- **FR-3** The user can drag and drop files onto the entry form to attach them (nice to have).
- **FR-4** An entry can have at most **5** attachments. The UI prevents selecting more, and the backend rejects submissions that would exceed the limit.
- **FR-5** Each file may be at most **15 MB**. The UI warns before upload and the backend rejects larger files with a clear error. The server's request size limit must accommodate a full submission (5 files).
- **FR-6** Supported file types include at least JPEG, HEIC, and PDF; other common image types (e.g. PNG, WebP, GIF) should also be accepted. Uploaded files may be converted for storage; the original format and bytes need not be preserved (but may be).
- **FR-7** Selected files are shown to the user before submission (e.g. a list or thumbnails) and can be removed prior to submitting.
- **FR-8** On an existing entry, the user can add new attachments and remove existing ones (subject to the 5-attachment limit).
- **FR-9** If an upload fails partway (the entry saves but one or more files do not), the user is told which files failed. Offering a retry for just the failed files is a **nice to have**; if it significantly expands the work, failing the whole submission is acceptable. This behavior is identical when adding attachments to an existing entry (FR-8).
- **FR-10** While files are uploading, the UI shows an in-progress state and prevents duplicate submission. Cancelling an in-flight upload is not required.

### Association and access control
- **FR-11** Each attachment belongs to exactly one journal entry.
- **FR-12** Attachments are accessible only to the user who uploaded them. Other users (and unauthenticated requests) must not be able to retrieve an attachment, even with a direct URL.
- **FR-13** Deleting a journal entry also deletes its attachments.

### Display
- **FR-14** Every attachment linked to an entry is displayed in a footer area for attachments within that entry's journal box.
- **FR-15** Attachments are shown as thumbnails of a **standard, uniform size** on initial display, regardless of the dimensions or orientation of the source image.
- **FR-16** The user can view or open an attachment at a larger size than its thumbnail (the sizes available are left to design).
- **FR-17** Attachments render in the footer as a placeholder first and are replaced by the actual thumbnail as each one loads (see NFR-1, NFR-2).
- **FR-18** Non-image attachments (e.g. PDF) that cannot be thumbnailed are shown in a recognizable form of the same standard size (icon and filename) and can be opened or downloaded.

## Non-Functional Requirements

- **NFR-1 Performance** Loading any day's view (entries for the selected month/day across years, including attachments) must complete its initial render in under 2 seconds.
- **NFR-2 Progressive loading** The page must not wait on all attachments before rendering. Placeholders appear immediately and attachments load independently and incrementally.
- **NFR-3 Privacy in logs** Attachment contents, original filenames, and embedded metadata (e.g. EXIF) must never appear in any log (access or application), consistent with the existing access-log policy of path/method/status only. Attachment endpoints identify files by opaque ID rather than filename so paths are safe to log. Logs may include attachment IDs, content type, size, and error category to aid debugging.
- **NFR-4 Consistency** Behavior follows existing conventions: session-based auth, per-user scoping, and the existing error-surfacing pattern in the frontend.
- **NFR-5 Configurable storage location** The location where attachments are stored must be settable via an environment variable (loaded the same way as existing settings, including `.env` and `example.env` documentation). When unset, it defaults to a location sibling to the default database (`one_line_day_py/src/data/`).
- **NFR-6 Persistence and mountability** Stored attachments must persist across restarts and be mountable as a volume or bind mount, the same way the SQLite database is under Docker, so they survive container rebuilds and live on the host.
- **NFR-7 Accessibility** The file picker, attachment removal, and opening an attachment are operable by keyboard. Each displayed attachment exposes its filename as its accessible text (alt text for images). Custom alt text is out of scope.
- **NFR-8 Testability** Backend and frontend changes ship with tests in line with the existing Pytest and Vitest suites.
- **NFR-9 Failure isolation** A failure involving an attachment or thumbnail (e.g. a missing, corrupt, or unprocessable file, a failed or slow image request, or an error in the attachment storage or its metadata) must never prevent journal entries from loading or the page from rendering and being used. The failure is contained to the affected attachment (or the attachments area of the affected entry) and shown there, and the rest of the page, including creating, editing, and deleting entries, keeps working. Likewise, a failed attachment upload never loses or blocks the entry itself (see FR-9).

## Out of Scope (initial)

- Captions, alt text editing, and user-defined ordering of attachments (upload order is sufficient).
- Sharing attachments with other users.
- Preserving or returning the original unmodified file.
- **Stripping private metadata (deferred from the initial version).** Removing embedded private information (e.g. EXIF metadata such as GPS location) from served copies, and optionally from downloads. For PDFs, stripping would have been best effort. Until this is done, served copies may carry the metadata of the original file.
- **Content validation (deferred from the initial version).** Validating uploads by content rather than by file extension or declared type, rejecting files that do not match a supported type, and guarding against oversized-dimension images (decompression bombs). Until this is done, file type checking is not required beyond what the design needs to produce thumbnails.

## Open Questions / Rabbit Holes

Items here are not yet requirements. Each needs a decision before it is promoted into the sections above or dropped.

_None currently open._

_Resolved and removed: log privacy (NFR-3), maximum file size (FR-5), edit-time failures (FR-9), accessibility (NFR-7), upload progress and cancellation (FR-10), existing `Photo` model (placeholder; the design may modify or remove it). Per-user storage quota was dropped as unnecessary for a personal-use app. Content validation and metadata stripping moved to Out of Scope._
