# Photos: Implementation Tasks

> Derived from `requirements.md` and `design.md`. Work happens on `feat/add-photos`. Each task is small enough to finish, test, and commit on its own. Tasks within a phase are ordered by dependency; later phases depend on earlier ones unless noted.

**Conventions**
- Tests go next to the code they cover, following the existing layout (`one_line_day_py/tests/test_src/...` for backend, `*.test.ts(x)` beside modules for frontend). Write the tests in the same task as the code.
- Backend checks: `.venv/bin/pytest`, `ruff check --fix`, `ruff format`. Frontend checks (from `frontend/`): `npm run test`, `npm run typecheck`.
- "Done when" is the exit criterion for each task. Requirement references are in brackets.

---

## Phase 0: Spikes and setup

Short checks to confirm assumptions the design flagged as "to confirm", before building on them.

- [x] **T0.1 Spike: framework behavior.** *(Confirmed on Litestar 2.24 / SQLModel 0.0.31; a–d all hold. Extra findings: the app default body limit is 10 MB and returns `413`; a per-handler limit works in both directions; `File` filenames are emitted RFC 5987 percent-encoded, so quotes and CRLF can't inject headers; a dataclass body with `file: UploadFile` enforces the multipart field name `file` (and returns `400` otherwise), while a bare `UploadFile` accepts any field name.)* In a scratch file (not committed), confirm in the installed versions: (a) Litestar parses a multipart `UploadFile` without extra dependencies; (b) a per-handler `request_max_body_size` overrides the 10 MB default and returns `413` when exceeded; (c) `File` responses accept custom `Cache-Control` and `Content-Disposition`; (d) SQLModel's `Field(foreign_key=..., ondelete="CASCADE")` emits `ON DELETE CASCADE` in the DDL. *Done when:* each of a–d is confirmed, or the design is amended with the actual API.
- [x] **T0.2 Dependencies.** *(Added pillow 13.0.0 and pillow-heif 1.8.1. HEIC encode and decode both work in this environment, so T2.2 can generate its HEIC fixture in code; no checked-in sample needed.)* Add `pillow` and `pillow-heif` to `pyproject.toml`; refresh `uv.lock`. Confirm `backend.Dockerfile`'s install step still works. *Done when:* `.venv/bin/python -c "import PIL, pillow_heif"` works and the existing suite still passes.
- [x] **T0.3 Settings.** *(Also repointed `attachments_path` at `tmp_path` in the `app` fixture in `conftest.py` so tests never write into the real data directory.)* Add `attachments_path: Path` (env `ATTACHMENTS_PATH`) with `DEFAULT_ATTACHMENTS_PATH` as a sibling of the default DB, independent of `db_path`. Document in `example.env`. [NFR-5] *Done when:* tests show the default value, an env override, and that overriding `DB_PATH` alone does not move it.

## Phase 1: Data foundation

- [x] **T1.1 Foreign key enforcement.** *(Full suite passes with FKs on; tests in `tests/test_src/test_db.py`.)* Add the SQLAlchemy `connect` listener running `PRAGMA foreign_keys=ON` in `init_db`. Add a test asserting the pragma is on for new connections. [FR-13] *Done when:* the full existing suite passes (it did in the scratch experiment) and the new test passes.
- [x] **T1.2 `Attachment` model.** *(`Photo` was only referenced in `model.py`; removed. Cascade test is in `test_db.py`.)* Replace `Photo` in `model.py` with `AttachmentKind` and `Attachment` as designed (including `ondelete="CASCADE"`, `author_id`, `has_thumbnail`, `width`/`height`, `original_content_type`, `content_hash`, `taken_at`, default `created_at`). Add `AttachmentPublic`. Make sure the unused `Photo` is removed everywhere. [FR-11] *Done when:* the table is created on startup, and a test confirms deleting a `JournalEntry` row cascades to its attachment rows.

## Phase 2: Backend building blocks (no HTTP yet)

These three are independent of each other and can be done in any order.

- [x] **T2.1 `AttachmentStorage`** (`src/data/attachment_storage.py`). `save` (temp file then rename), `path_for`, `delete_attachment`, `delete_entry`, `entry_dirs`. Path layout `{root}/{entry_id}/{attachment_id}.{variant}`. Create the root lazily and tolerate failure, raising `StorageUnavailable` only on write. [NFR-5, NFR-6, NFR-9] *Done when:* tests (using `tmp_path`) cover round-trip, missing file returns `None`, delete one/delete entry, no user-supplied value ever appears in a path, and an unwritable root raises on write only.
- [x] **T2.2 Image processing** (`src/images.py`). `process_image(data)` returning thumbnail, display copy, width, height, `taken_at`; HEIC via `pillow-heif`; EXIF orientation; first frame of GIFs. Thumbnail is exactly 320×320 cover-crop WebP; display copy fits 2048 px WebP. [FR-6, FR-15, FR-16] *Done when:* tests cover landscape, portrait and square inputs (all thumbnails 320×320), a rotated-EXIF image, a GIF, PNG with alpha, HEIC (generated fixture or small checked-in sample), `taken_at` extraction, and an undecodable input raising a clear error.
- [x] **T2.3 Domain exceptions and handlers** (`src/exceptions.py`). Add `AttachmentLimitExceeded`, `AttachmentTooLarge`, `UnsupportedAttachmentType`, `AttachmentProcessingError`, `StorageUnavailable`, and register their handlers in `exception_handlers` (400/413/415/422/503). *Done when:* a test per exception verifies the mapped status code.

## Phase 3: Attachment data access and service

- [x] **T3.1 `AttachmentDb`** *(Also added `existing_entry_ids` for the sweep; `MAX_ATTACHMENTS_PER_ENTRY` lives in `db.py`. Tests in `test_attachment_db.py`.)* (`src/data/db.py`). `add_attachment` (count check and insert in one session), `get_scoped(attachment_id, entry_id, author_id)`, `list_for_entry`, `list_for_entries`, `delete`, `count_for_entry`, `all_entry_ids`-style helpers for the sweep. [FR-4, FR-11, FR-12] *Done when:* tests cover scoped lookup returning nothing for a wrong entry, a wrong owner and a missing ID; ordering by `created_at`; the sixth insert being rejected; and `list_for_entries` returning an empty map for no ids.
- [x] **T3.2 `AttachmentService`** *(`add` takes `filename, content_type, data: bytes` so the service stays free of Litestar types; the type rule uses the declared content type, plus a `%PDF-` magic check. `open` takes `thumbnail=` and raises `NoResultFound` (404) for anything missing. Rollback cleanup is best-effort so it can't mask the original error. Tests in `test_attachment_service.py`.)* (`src/services/attachments.py`). `add`, `list_for_entry`, `list_for_entries`, `delete`, `open`, `remove_entry_files`, `sweep_orphans`, per the design's method table. `add` verifies the entry through `JournalDb`, enforces 15 MB and the type rule, processes images via `asyncio.to_thread`, writes files, inserts, and removes the files if the insert fails. PDFs are stored as-is with `has_thumbnail=False`. [FR-1, FR-4 to FR-6, FR-8, FR-11 to FR-13, NFR-3] *Done when:* unit tests (no HTTP) cover success for image and PDF, each domain exception, rollback leaving no files when the insert fails, delete removing row then files, `open` for each variant, the sweep removing only orphan directories, and that nothing sensitive (filename, bytes, exception messages) reaches the logs.
- [x] **T3.3 Wiring and the journal-side interface.** *(Tests in `test_attachment_wiring.py`.)* In `dependencies.py` add `create_attachment_service`, `provide_attachment_service`, `provide_entry_attachments`; define the `EntryAttachments` protocol and `AttachmentLookup` in `journal.py`; implement `GuardedEntryAttachments` (logs the exception class and returns `available=False` on failure; swallows and logs `remove_entry_files` errors); register state, providers and the `on_startup` sweep in `make_app`. The app must still start if the attachments directory is unwritable. [NFR-4, NFR-9] *Done when:* the app boots in tests with the new state, the adapter's failure behavior is tested, and startup with an unwritable directory logs and continues.

## Phase 4: HTTP layer

- [x] **T4.1 `AttachmentController`** *(Upload body is a dataclass with `file: UploadFile`, so the multipart field must be named `file` (else `400`). Body limit is 16 MB, so files just over 15 MB still reach the service and get its `413`. Tests in `test_controllers/test_attachment.py`; they also cover a file missing on disk returning `404` while the entry still returns `200`.)* (`src/controllers/attachment.py`, exported from `controllers/__init__.py`, registered in `make_app`). Routes under `/journals/{entry_id}/attachments`: `POST`, `GET`, thumbnail, content (with `?download=true`), `DELETE`. Per-handler ~16 MB body limit. `File` responses with `Cache-Control: private, max-age=31536000, immutable`, `X-Content-Type-Options: nosniff`, and escaped `Content-Disposition`. Controller calls only `AttachmentService`. [FR-1 to FR-5, FR-8, FR-12, FR-14 to FR-18, NFR-1] *Done when* tests (using `alice`/`bob`) cover: upload image and PDF; thumbnail is 320×320; PDF thumbnail is `404`; sixth upload `400`; over 15 MB `413`; unsupported `415`; undecodable `422`; failed upload leaves no files or rows; other users get `404` on every route; unauthenticated gets `401`; **cross-entry access** (alice's attachment through bob's `entry_id`) is `404`; download disposition; caching headers present.

## Phase 5: Journal integration

- [x] **T5.1 `JournalEntryPublic` and mapper.** *(Both live in `schemas.py`; tests in `test_schemas.py`.)* Add `JournalEntryPublic` (existing fields + `attachments` + `attachments_available`) and the pure `to_public_entry` mapper in `schemas.py`. *Done when:* mapper unit tests pass.
- [x] **T5.2 Journal controller changes.** *(`EntryAttachments` is now `@runtime_checkable`, because Litestar's signature model validates injected dependencies by `isinstance` and a plain `Protocol` fails with a 500. Tests in `test_controllers/test_journal_attachments.py`; `test_journal.py` is unchanged.)* `create_entry` returns an empty attachments list; `list_entries`, `get_entry` and `update_entry` fetch attachments in one call through `EntryAttachments.for_entries`; `delete_entry` calls `remove_entry_files` after the delete commits. `JournalDb` and `journal.py` import no attachment modules (only the protocol defined in `journal.py`). [FR-14, FR-13, NFR-9] *Done when:* all existing journal tests still pass untouched; new tests cover attachments appearing in list/get/update/create responses, deleting an entry cascading rows and removing the directory (and still returning `204` if file removal fails), the sweep covering a missed removal, entry endpoints returning `200` with `attachments_available: false` when the lookup is forced to fail, and an import-boundary test.

## Phase 6: Deployment and configuration

- [ ] **T6.1 nginx body limit.** Add `client_max_body_size 16m;` to `location /api/` in `frontend/nginx.conf`. [FR-5] *Done when:* a 15 MB upload succeeds through the Docker setup (verified in T10.2).
- [ ] **T6.2 Docker and docs.** Add the attachments bind mount to `docker-compose.yml`; add a `mkdir -p` step to the README setup; document `ATTACHMENTS_PATH` in `example.env` and the README; note the bind-mount host directory must exist first. [NFR-5, NFR-6] *Done when:* `docker compose up --build` starts and uploaded files appear in the host directory.

## Phase 7: Frontend foundation

- [ ] **T7.1 Types, limits and API client.** Add `Attachment` to `models.ts`; add `attachments` and `attachments_available` to `Journal`; add the 5-file and 15 MB limits to `config.ts` with a comment pointing to the backend constants; create `attachments.ts` (`uploadAttachment`, `uploadAttachments` that uploads sequentially and returns `{ uploaded, failed }`, `deleteAttachment`, `thumbnailUrl`, `contentUrl`). [FR-4, FR-5, FR-9] *Done when:* tests (mocked `fetch`) cover URL building, `FormData` upload without a manual `Content-Type`, sequential ordering, and the `uploaded`/`failed` result shape; existing frontend tests still compile and pass.

## Phase 8: Frontend components

`AttachmentThumb`, `AttachmentPicker`, and `UploadFailureNotice` are independent of each other; the footer needs the thumb.

- [ ] **T8.1 `AttachmentThumb`.** Fixed-size box; CSS skeleton until the lazy `<img>` loads; error state with Retry; `has_thumbnail: false` renders an icon plus filename at the same size; image thumbs are buttons with the filename as accessible name. [FR-15, FR-17, FR-18, NFR-7, NFR-9] *Done when:* tests cover placeholder, loaded, error and retry, PDF rendering, and accessible name.
- [ ] **T8.2 `AttachmentFooter` and viewer.** Footer row of thumbs with an error boundary ("Attachments unavailable"), also shown when `attachments_available` is `false`; native `<dialog>` viewer with the display image and a Download link; PDFs open in a new tab; viewer shows an error inside itself if the image fails. [FR-14, FR-16, NFR-9] *Done when:* tests cover rendering, opening and closing the viewer (including Esc), the failure state, a thrown render error being contained, and the unavailable note.
- [ ] **T8.3 `AttachmentPicker`.** Hidden-but-focusable file input behind a labelled button; drop zone; enforces the file-count and size limits with inline messages; lists selected files with per-file remove and status; image previews via `URL.createObjectURL` (revoked on removal/unmount) with a file-icon fallback; controlled by the parent. [FR-2, FR-3, FR-4, FR-5, FR-7, FR-10, NFR-7] *Done when:* tests cover browse, drag and drop, over-limit and oversize rejection, remove, preview fallback, and keyboard operation.
- [ ] **T8.4 `UploadFailureNotice`.** Lists failed filenames with **Retry** and **Dismiss**; shared by create and edit. [FR-9] *Done when:* tests cover rendering, Retry callback, and Dismiss.

## Phase 9: Frontend integration

- [ ] **T9.0 Styles.** Add the CSS for the thumb box, skeleton, footer, picker, drop zone, notice and viewer in `frontend/style.css`. (Do alongside T8.x; listed separately so it isn't forgotten.)
- [ ] **T9.1 New-entry flow** in `JournalApp`. Picker in the form; on submit create the entry, then `uploadAttachments`; Send disabled and picker disabled while uploading; the new entry is added with the attachments that succeeded; failed files go to `UploadFailureNotice` with Retry against the same entry. [FR-1, FR-9, FR-10] *Done when:* `JournalApp` tests (mocked `fetch`) cover all-succeed, partial failure then Retry, entry kept when every upload fails, and the form being disabled during upload.
- [ ] **T9.2 Edit flow** in `JournalBox`. Edit mode shows existing attachments with remove controls plus the picker; the 5-attachment cap counts both; Save updates the entry, deletes removed attachments, uploads added ones, with failures reported via the notice and the box's `error` area; view mode renders `AttachmentFooter`. [FR-7, FR-8, FR-9, NFR-4] *Done when:* tests cover add, remove, cap counting, attachment failure not aborting the text save, and an attachment error not affecting Edit/Delete.
- [ ] **T9.3 Frontend failure isolation.** Verify entries render when every thumbnail fails and when `attachments_available` is `false`. [NFR-9] *Done when:* integration tests cover those two cases.

## Phase 10: Verification and wrap-up

- [ ] **T10.1 Full checks.** Backend: `.venv/bin/pytest`, `ruff check`, `ruff format --check`. Frontend: `npm run test`, `npm run typecheck`, `npm run build`. *Done when:* all green.
- [ ] **T10.2 Manual end-to-end** via `docker compose up --build`, with a real phone photo (JPEG and HEIC), a PNG, a PDF, a 15 MB file and a 16 MB file; add/remove on an existing entry; delete an entry and confirm its directory disappears; log in as a second user and confirm no access (including by pasting a direct URL); confirm logs contain no filenames or EXIF. [FR-1 to FR-18, NFR-3, NFR-6]
- [ ] **T10.3 Performance check.** With throttled network, load a day with 5 attachments on each of ~10 years of entries through nginx; confirm entries and placeholders appear well within 2 seconds and thumbnails load progressively. [NFR-1, NFR-2]
- [ ] **T10.4 Docs.** Update `CLAUDE.md` (structure: new controller, service, storage, images, endpoints, settings, frontend components, `Photo` model removal), the backend and frontend READMEs and CHANGELOGs, and `TODO.md` (remove the finished photo items; keep the user-deletion item). Mark `design.md` status as implemented.

---

## Suggested commit and PR plan

1. Phases 0–1: setup, settings, FK pragma, model.
2. Phase 2–3: storage, images, exceptions, DB access, service, wiring.
3. Phases 4–5: attachment controller and journal integration (backend complete).
4. Phase 6: nginx, Docker, docs for deployment.
5. Phases 7–9: frontend.
6. Phase 10: verification and docs.

Each step leaves the suite green. Steps 1–3 can be reviewed and merged as a backend-only change before any frontend work, since the new `attachments` fields are additive for the current frontend.

## Risks to watch while implementing

- **T1.1** enables foreign keys app-wide; stop and look at any test that newly fails rather than loosening it.
- **T0.1** assumptions (multipart, per-handler body limit, `ondelete` on `Field`) shape T1.2 and T4.1; amend the design if reality differs.
- **HEIC in tests (T2.2):** if `pillow-heif` can't encode a fixture in CI, use a small checked-in sample file.
- **nginx and Docker (T6.x)** only matter in the container setup; local dev (`npm run dev` plus the backend) will not reveal missing limits, so don't skip T10.2.
