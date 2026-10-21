# Photos: Design

> Status: **Implemented** on `feat/add-photos` (backend 0.4.0, frontend 0.3.0). Implements `requirements.md` (FR-x / NFR-x references below point there). Where the implementation refined a detail, the notes in `tasks.md` record it.

## Summary

Attachments are uploaded **one file per request** to a new endpoint on an existing entry, after the entry itself is created. The backend processes each file once at upload time (images become a fixed-size thumbnail and a display-size copy; PDFs are stored as-is), writes the results to a configurable directory on disk, and records metadata in SQLite. Reads are plain authenticated file serves, so the browser's native lazy `<img>` loading gives us the progressive loading NFR-2 asks for. Entry responses embed lightweight attachment metadata so a day's view needs no extra round trips.

Structurally, all attachment behavior lives behind a single `AttachmentService` (D11). The journal side reaches it only through a two-method interface it defines itself (`EntryAttachments`), and the database, not journal code, deletes attachment rows when an entry is deleted (D10).

## Key decisions

| # | Decision | Why |
|---|---|---|
| D1 | One file per upload request, entry created first | Makes partial failure, retry (FR-9), progress (FR-10) and per-file limits (FR-5) fall out naturally. Avoids a single 75 MB request. Keeps the existing query-param create endpoint unchanged. |
| D2 | Process at upload, not at read | Reads are static file serves, so NFR-1 doesn't depend on image decoding speed. |
| D3 | Images are re-encoded to WebP (thumbnail + display copy); originals are not kept. PDFs stored as-is | FR-6 allows conversion and says the original need not be kept. Solves HEIC display. PDF page rendering would need an extra native dependency, so PDFs get an icon instead (FR-18). |
| D4 | Files on disk, metadata in SQLite, no stored absolute paths | Mountable and relocatable (NFR-5, NFR-6). On-disk names are derived from IDs. |
| D5 | Attachment metadata is embedded in journal entry responses | One extra query per day load instead of N+1 requests (NFR-1). |
| D6 | Thumbnails fetched by `<img loading="lazy">` from authenticated URLs | Native progressive loading, no JS blob juggling, and cached per ID (NFR-2). |
| D7 | PDFs get a generic icon first; a rendered first page is a small follow-up (see D4) | The schema and API already allow it later (`has_thumbnail`). |
| D8 | Native `<dialog>` lightbox for viewing larger | Accessible for free, no library. |
| D9 | Attachments location is independent of `DB_PATH`; only the *defaults* are siblings | The two locations are separately configurable, with no assumed relationship. |
| D10 | Attachment rows are deleted by the database (`ON DELETE CASCADE`, SQLite foreign keys on); files by a call behind the `EntryAttachments` interface plus a startup orphan sweep | `JournalDb` stays only about journals; the relationship is enforced in the schema, not in code. |
| D11 | One `AttachmentService` owns all attachment behavior; the journal controller sees only a narrow `EntryAttachments` interface | Thin controllers, one place for rollback and rules, and the journal side depends on a two-method interface rather than on attachment classes. |

## Options considered

Each decision below lists the realistic alternatives, what each costs, and why the chosen one wins for this app (single-user-scale, SQLite, Docker on one host). If you disagree with a pick, the "switch if" line says what would change my mind.

### D1. How files get from the browser to the server (FR-1, FR-8, FR-9, FR-10)

| Option | Pros | Cons |
|---|---|---|
| **A. One request creates entry + all files** (multipart) | Single atomic action; no partial-failure state between entry and files | Changes the existing query-param create endpoint to multipart; up to 75 MB in one body; any file failure fails or half-fails everything; per-file progress and retry are hard; harder to reuse for the edit flow |
| **B. Create entry, then one request per file** (chosen) | Existing create endpoint untouched; per-file errors, retry and progress are natural; each body is ≤ 16 MB; the same code serves create and edit | Not atomic: an entry can exist with fewer attachments than intended (handled by the failure notice and Retry); more requests |
| **C. Create entry, then all files in one multipart request** | One upload call; keeps entry creation unchanged | Still a 75 MB body, and one bad file complicates the response shape (which succeeded?); retry is all-or-nothing or needs bookkeeping |

**Why B:** FR-9 asks for "which files failed" and a retry, which B gives almost for free. It also makes the edit flow (FR-8) the same code path. **Switch to A if** you later want true all-or-nothing posts and are willing to build rollback.

### D2. When images are processed (NFR-1)

| Option | Pros | Cons |
|---|---|---|
| **A. At upload** (chosen) | Reads are static file serves, so day load never waits on decoding; upload latency absorbs the cost, and the user is already waiting there with a progress state | Upload takes longer (decode + resize + encode, typically well under a second for phone photos); a new thumbnail size means reprocessing existing files |
| **B. Lazily on first read, then cached** | Fast uploads; can add sizes later without a backfill | First view of each day pays the cost, which puts NFR-1 at risk and needs cache-fill concurrency control |
| **C. On the fly every read** (resize per request) | Smallest storage; any size on demand | Every day load decodes full-size originals; worst fit for NFR-1 |

**Why A:** it protects the 2-second budget on the path that matters most. **Switch to B if** upload latency becomes noticeable and you're comfortable with a slower first view.

### D3. What gets stored (FR-6)

| Option | Pros | Cons |
|---|---|---|
| **A. Derived WebP thumbnail + display copy only; PDFs as-is** (chosen) | Small, uniform, solves HEIC display, and the re-encode happens to drop EXIF | Original image is gone; can't re-derive at higher quality or new sizes later |
| **B. Keep the original plus derived copies** | Nothing lost; can regenerate; original available to download | Roughly 3–5× the disk; the original carries full metadata (GPS) which becomes a privacy concern once serving it is possible; extra code for download path |
| **C. Keep only the original, convert at read** | Least storage logic | Same cost problem as D2-C, and HEIC is unreadable in most browsers without conversion |

**Why A:** the requirements explicitly don't need the original, and A is the cheapest to store and serve. **Switch to B if** you decide you want your own photo archive in the app. It is an additive change (store one more file) and fits the layout, but it reopens the deferred metadata-stripping item.

### D4. PDF thumbnails (FR-18)

| Option | Pros | Cons |
|---|---|---|
| **A. Generic icon + filename** (chosen) | No new dependency; matches FR-18 as written | Less recognizable when several PDFs are attached |
| **B. Render page 1 server-side** (e.g. PyMuPDF) | Real preview | Adds a native dependency and a PDF parser to everything uploaded; PDFs are an untrusted-input surface, and content validation is out of scope |
| **C. Render client-side** (pdf.js) | No backend dependency | Large JS dependency; must fetch the whole PDF just to show a thumbnail, which fights NFR-1/NFR-2 |

**Why A:** matches the requirement and avoids parsing PDFs with a library while validation is deferred. **Switch to B** if PDF previews turn out to matter in practice.

**How hard is rendering page 1?** Small. The code is roughly 10–15 lines using a library such as `pypdfium2` (open from bytes, `page.render(scale=...)`, convert to a Pillow image) feeding the same thumbnail step the images use. Real costs are mostly around it:
- **Dependency choice:** `pypdfium2` bundles Google's PDFium in a permissively licensed wheel (a few MB). PyMuPDF is faster and richer but is AGPL-licensed, which matters if the app is ever distributed or hosted for others.
- **Untrusted input:** it parses uploaded PDFs, which is the one thing content validation (deferred) was meant to keep minimal. PDFium is a hardened engine, but it's still new attack surface.
- **Resource limits:** needs a cap on rendered size and a timeout so a huge page can't stall the worker.
- **Fallback:** encrypted, corrupt or oversized PDFs must fall back to the icon. That is already the NFR-9 behavior, so the fallback comes nearly free.
- **Tests:** a small PDF fixture (checked in or generated) plus tests for success and fallback.

Estimate: a few hours including tests. The design leaves the seam: `has_thumbnail` is `False` for PDFs now and would become `True` when rendering succeeds, so the thumbnail route and `AttachmentThumb` already handle both cases with no API or schema change. Recommendation: ship with the icon, add rendering as a follow-up if you find yourself wanting it.

### D5. Where file bytes live (NFR-5, NFR-6)

| Option | Pros | Cons |
|---|---|---|
| **A. Filesystem directory + metadata rows in SQLite** (chosen) | Simple; static serving; easy to mount, inspect and back up with normal tools; matches the "location via env var" requirement directly | Files and DB can drift (orphans after a crash); two things to back up together |
| **B. BLOBs in SQLite** | One file to back up; transactional with metadata | DB grows large and every backup/copy moves all images; the requirement for a separately configurable, mountable photo location doesn't map onto this; large reads hurt the shared connection model |
| **C. Object storage (S3/MinIO) behind a storage interface** | Scales, cheap durability | Heavy for a personal-use Docker app; doesn't fit "mount a directory" |

**Why A:** it is the only option that satisfies NFR-5/NFR-6 as written without extra machinery. The `AttachmentStorage` wrapper keeps C possible later without touching controllers.

### D6. How the frontend learns what attachments an entry has (NFR-1)

| Option | Pros | Cons |
|---|---|---|
| **A. Embed in the entries response** (chosen) | No extra round trips; thumbnails can start loading as soon as entries arrive | Changes the entry response shape (new `JournalEntryPublic`) and the `Journal` TS type |
| **B. Separate request per entry** (`GET .../attachments`) | Entry endpoints untouched | N+1 requests per day view, with ~10 years of entries that is ~10 extra requests before any thumbnail can load |
| **C. One batch request per day** | Entry endpoints untouched; one extra request | Still an extra serial round trip; a second endpoint to keep consistent with the first |

**Why A (currently):** metadata is tiny, and it removes a round trip from the critical path. The list endpoint (`GET .../attachments`) still exists for refreshes after edits. **This pick is under review** because of coupling and failure isolation; see the notes below and the open comments on D4/D5.

**How costly is N+1 (option B)?**
- Each metadata request is a small JSON response from local SQLite: a few ms of server time plus one network round trip. On a LAN or localhost that is single-digit to tens of ms each, so ~10 entries is not a lot in absolute terms (perhaps 50–150 ms in total).
- What hurts is not the metadata itself but **contention and ordering**. A browser keeps only about 6 connections per host over HTTP/1.1 (the nginx setup here doesn't enable HTTP/2). Thumbnails can't be requested until their entry's metadata has arrived, and those metadata requests queue alongside thumbnail requests that are already in flight. On a slow or mobile connection (100+ ms per round trip) that adds visible waves of delay, and the cost grows with the number of years of entries. It stays inside the 2-second budget for typical use but spends budget the other options keep.
- Option C (one batch request per day, issued **in parallel** with the entries request) costs essentially nothing extra: both requests start together, so no serial round trip is added.

**Backwards compatibility.** A adds a field to existing entry responses and swaps the return type to `JournalEntryPublic`. Adding a JSON field is non-breaking for tolerant clients (the only client here is our frontend, deployed together with the backend), but it does change a response contract that everything else in the API shares. B and C leave existing endpoints untouched, so there is nothing to be compatible with.

**When to pick B over A.** B is the better choice when attachments should be loaded lazily or independently of the entry: for example the attachments area is collapsed by default or far below the fold, most views don't need attachments, the entries endpoint is consumed by other clients that shouldn't pay for attachment data, or attachments might eventually be large or slow enough to deserve their own failure handling and caching. Each `JournalBox` can then load its own attachments and fail independently (NFR-9). A is the better choice only when attachments are always shown and the extra request would dominate.

### D7. How the browser fetches authenticated thumbnails (FR-12, NFR-2)

| Option | Pros | Cons |
|---|---|---|
| **A. Plain `<img src>` with the session cookie** (chosen) | Native lazy loading and caching, no JS code; works with the existing cookie | Depends on the cookie being sent to the API origin. Same origin through nginx (Docker) is fine; in local dev, `localhost:5173` → `localhost:8000` is same-site, so the default `SameSite=Lax` cookie is sent. Mixing `localhost` and `127.0.0.1` would break images (and already breaks login) |
| **B. `fetch` each image with credentials, show via blob URL** | Works regardless of cookie rules; could show real progress | Reimplements caching/lazy loading in JS, holds blobs in memory, and needs revoking; loses the browser's HTTP cache |
| **C. Short-lived signed URLs** | Works without cookies; can be handed to non-browser consumers | New signing scheme and expiry handling for a single-user app; URLs that leak work until they expire |

**Why A:** least code and best caching, and the only caveat is a dev-environment one. **Switch to B** if you ever serve the API from a different site than the frontend.

### D8. Viewing larger (FR-16)

| Option | Pros | Cons |
|---|---|---|
| **A. Native `<dialog>` lightbox** (chosen) | Esc and focus handling built in, no dependency, keeps the user on the page | Little custom UI to write and style |
| **B. Open the image in a new tab** | Trivially simple | Leaves the app; slower to browse several |
| **C. Lightbox library** | Swipe, zoom, galleries | New dependency for a small feature |

**Why A:** accessible and dependency-free. PDFs still open in a new tab since a browser's PDF viewer is the better experience there.

### D9. Default storage location (NFR-5)

| Option | Pros | Cons |
|---|---|---|
| **A. Independent setting; default is a sibling of the *default* DB path** (chosen) | Matches the requirement literally: `ATTACHMENTS_PATH` and `DB_PATH` can each point anywhere; no hidden coupling | Overriding only `DB_PATH` leaves attachments at the default location, so moving the database means also setting `ATTACHMENTS_PATH` if you want them to move |
| **B. Default derived from the configured `DB_PATH`'s directory** | Overriding `DB_PATH` moves everything together, as `.sessions` does | Creates an implicit relationship between the two settings, which the requirements rule out |

**Why A:** per your direction, the only relationship between the two is that their defaults happen to be siblings. A computed default that is a constant, not a function of `DB_PATH`, keeps behaviour predictable. This does differ from how `.sessions` is placed (it follows `DB_PATH`), and that's intentional.

### D10. How attachments follow their entry when it is deleted (FR-13)

| Option | Pros | Cons |
|---|---|---|
| **A. `JournalDb.delete_entry` also deletes attachment rows** | Obvious; no pragma change | Journal data code now knows about the attachments table; every future table that hangs off entries needs another edit there |
| **B. Database cascade: `ON DELETE CASCADE` on `attachments.entry_id` + `PRAGMA foreign_keys=ON`** (chosen) | The relationship lives in the schema; `JournalDb` is unchanged; atomic with the entry delete; an upload racing a delete fails cleanly instead of leaving an orphan | Turns on foreign-key enforcement for the whole app (see below); files still need separate handling |
| **C. B plus an `entry_deleted` event so journal code names nothing attachment-related** | The journal controller only announces a fact | Event delivery is in-process and best-effort, so the sweep is still needed; one more mechanism to understand |

**Why B:** it removes the coupling at its root at no code cost. Files on disk can't be cascaded by the database, so the journal controller calls `remove_entry_files(entry_id)` on the `EntryAttachments` interface (D11) after the delete commits, and a startup sweep removes any directory whose entry no longer exists as a backstop. **Switch to C if** you want `JournalController` to import nothing attachment-related at all, not even the interface.

### D11. How controllers reach attachment behavior (NFR-4, NFR-9)

| Option | Pros | Cons |
|---|---|---|
| **A. Controllers use `AttachmentDb`, `AttachmentStorage`, and `images` directly** | Matches how the existing controllers use `JournalDb`; no new layer | Upload orchestration (limits, processing, file writes, insert, rollback on failure) sits in a controller and is only testable through HTTP; the journal controller must know three attachment classes |
| **B. One `AttachmentService`; the journal controller sees a narrow `EntryAttachments` interface** (chosen) | Thin controllers; rules and rollback in one unit-testable place; the journal side depends on two methods it defines itself, and the "attachments unavailable" fallback lives in the adapter, not in journal code | A service layer the codebase doesn't have yet; one more concept |

**Why B:** attachments are the first feature that coordinates a database, a filesystem, and image processing in one operation, which is where a thin-controller pattern pays off. **Switch to A if** you'd rather keep strictly to the current two-layer style and accept a heavier controller.

## Backend

### Data model (`src/model.py`)

Replace the placeholder `Photo` model (requirements say the design may modify or remove it) with `Attachment`:

```python
class AttachmentKind(StrEnum):
    IMAGE = "image"
    PDF = "pdf"


class Attachment(SQLModel, table=True):
    __tablename__ = "attachments"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    entry_id: UUID = Field(
        foreign_key="journal_entries.id", ondelete="CASCADE", index=True
    )
    author_id: UUID = Field(foreign_key="users.id", index=True)  # denormalized owner
    filename: str  # original name, used only as display text (NFR-7)
    kind: AttachmentKind
    content_type: str  # of the stored full-size content, e.g. image/webp
    size_bytes: int  # of the stored full-size content
    has_thumbnail: bool  # False for PDFs today; lets the UI skip a doomed request
    width: int | None  # of the display copy; None for PDFs
    height: int | None
    original_content_type: str | None  # e.g. image/heic, before conversion
    content_hash: str | None  # sha256 of the uploaded bytes
    taken_at: datetime | None  # capture time from EXIF, if present
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )  # upload order (out of scope: user ordering)
```

**Why these extra columns now:** there is no migration tool, and because originals are not kept (D3) some information exists only at upload time and is lost forever if we don't record it then. Adding a nullable column later is cheap in SQLite, but backfilling the data is impossible.

| Field | Future use it enables | Why now |
|---|---|---|
| `taken_at` | Show or sort by when a photo was taken (e.g. "On this day" using the photo's own date) | EXIF is discarded when we re-encode, so this is unrecoverable later. Stored in the DB only; not logged (NFR-3) and not in `AttachmentPublic` until a feature needs it. |
| `original_content_type` | Show "HEIC" badge, decide download behaviour, debug conversion issues | The original format is lost after conversion. |
| `content_hash` | Duplicate detection, integrity checks, "this photo is already attached" | Can't be computed from the converted copy. |
| `width` / `height` | Reserve space in the lightbox and avoid layout shift; aspect-aware layouts | Cheap to record while the image is already decoded. |
| `has_thumbnail` | Lets PDFs gain a rendered first-page thumbnail later (see D4) without an API or schema change, and avoids the UI requesting thumbnails that can't exist | Part of the API shape the frontend codes against. |
| `author_id` | Ownership check on every attachment route with no lookup of the entry (see Endpoints); per-user storage totals or quotas; user-deletion cleanup (see TODO); keeps access control working even if an entry is ever moved | Denormalized, so it needs to be set correctly from day one. It always equals the owning entry's `author_id` (verified against the entry at upload). |

Considered and **not** added: `position` (user ordering is out of scope and `created_at` is enough to add it later without data loss), `caption` / `alt_text` (out of scope, and a nullable column can be added any time), and a `status` / processing-state column (only needed if processing becomes asynchronous; today it is synchronous, so a row exists only when its files do).

`AttachmentPublic` (id, entry_id, filename, kind, content_type, has_thumbnail, width, height) is the API shape. A `JournalEntryPublic` response model (the existing entry fields plus `attachments: list[AttachmentPublic]` and `attachments_available: bool = True`) replaces `JournalEntry` as the return type of the journal endpoints, with a pure mapper `to_public_entry(entry, attachments, available)` alongside `to_public_user` in `schemas.py`. Create returns `attachments=[]`. `attachments_available` is `False` only when the attachments lookup failed (see Failure isolation), so the UI can say so instead of silently showing none.

There is no migration tool: `SQLModel.metadata.create_all` creates the new `attachments` table on next start (the `ON DELETE CASCADE` is part of the new table's DDL, so it applies to existing databases too). The old, unused `photos` table, if present, is left behind and is harmless.

### Foreign key enforcement (`src/data/db.py`, `init_db`)

SQLite ignores foreign keys unless `PRAGMA foreign_keys=ON` is set on each connection. `init_db` is shared by every database class, so add a SQLAlchemy `connect` event listener there that runs the pragma. This is what makes `ON DELETE CASCADE` work (D10), and it is the only change to existing database code.

I tried this against the existing suite in a scratch copy of the repo: **all 39 backend tests pass** with foreign keys enforced. Two behavior notes:
- The existing foreign keys (e.g. `journal_entries.author_id → users.id`) start being enforced. That is what the existing TODO in `add_entry` wants (a bad `author_id` becomes an integrity error), but until that TODO is done it would surface as a 500.
- Deleting a user who still has entries now fails with an integrity error instead of silently leaving orphaned entries. Existing tests don't cover that case. It overlaps with the user-deletion TODO and is not made worse by attachments.

### Settings (`src/settings.py`, `example.env`)

- New field `attachments_path: Path` read from `ATTACHMENTS_PATH`, with a module-level default constant `DEFAULT_ATTACHMENTS_PATH = Path(__file__).parent.resolve() / "data" / "attachments"` next to `DEFAULT_DB_PATH`. The two settings are fully independent: nothing derives one from the other, and the only relationship is that their defaults are siblings (`one_line_day_py/src/data/`). The directory is created on startup. (NFR-5)
- This directory is already covered by the existing `.gitignore` rule for `data/*`.
- Document `ATTACHMENTS_PATH` in `example.env`.

### On-disk layout (`src/data/attachment_storage.py`, new)

```
{attachments_path}/{entry_id}/{attachment_id}.thumb.webp     # images
{attachments_path}/{entry_id}/{attachment_id}.display.webp    # images
{attachments_path}/{entry_id}/{attachment_id}.pdf             # pdfs
```

Keying by entry ID means changing an entry's date doesn't move anything, and deleting an entry is one directory removal. `AttachmentStorage` wraps save, open/path-for, delete-one, and delete-entry so controllers never build paths. Nothing user-supplied (filename, content type) is ever part of a path, so there is no path traversal surface.

### Database layer (`src/data/db.py`)

#### How `State`, `Provide`, and `AttachmentStorage` fit together

These are how the existing code wires databases to controllers, and the attachments follow the same pattern.

- **`State`** is Litestar's application-wide store of objects that live as long as the app does. In `make_app()` it is built once at startup: `state=State({"users_db": create_users_db(), "journals_db": create_journals_db()})`. Creating a `JournalDb` opens the SQLite engine, so we want exactly one per process rather than one per request. The state holds those long-lived instances.
- **`Provide`** is Litestar's dependency injection. `dependencies={"journals_db": Provide(provide_journals_db, ...)}` registers a function (`provide_journals_db(state) -> state.journals_db`) under the name `journals_db`. Any handler with a parameter called `journals_db` gets the result of that function automatically. `JournalsDb = NamedDependency[JournalDb]` in `journal.py` is just the type annotation for that parameter. The payoff is that controllers never construct or import database objects, and tests can swap them out.
- **`AttachmentStorage`** is a new plain class (not a database) that owns the attachments directory. It holds the root `Path` from `settings.attachments_path` and exposes a handful of methods, so no controller ever builds a filesystem path:
  - `save(entry_id, attachment_id, variant, data)` writes to a temp file then renames it, so a half-written file is never served.
  - `path_for(entry_id, attachment_id, variant)` returns the file path to serve, or `None` if it's missing.
  - `delete_attachment(...)` and `delete_entry(entry_id)` remove files.
  
  Because it is a class with one root path, tests give it a `tmp_path`, and a future S3-style backend could replace it behind the same methods.

Wiring for attachments, mirroring the above. `AttachmentDb` and `AttachmentStorage` are built once and wrapped by the service; only the service (and its adapter) are exposed to controllers:

```python
# dependencies.py
def create_attachment_service(journals_db: JournalDb) -> AttachmentService:
    return AttachmentService(
        attachments_db=AttachmentDb(settings.db_path),
        storage=AttachmentStorage(settings.attachments_path),
        journals_db=journals_db,
    )
def provide_attachment_service(state: State) -> AttachmentService: return state.attachment_service
def provide_entry_attachments(state: State) -> EntryAttachments: return state.entry_attachments

# main.py
journals_db = create_journals_db()
service = create_attachment_service(journals_db)
state=State({..., "attachment_service": service,
                  "entry_attachments": GuardedEntryAttachments(service)})
dependencies={..., "attachment_service": Provide(provide_attachment_service, sync_to_thread=False),
                   "entry_attachments": Provide(provide_entry_attachments, sync_to_thread=False)}
on_startup=[service.sweep_orphans, ...]
```

#### Database layer

`AttachmentDb` follows the `JournalDb` pattern and is used **only by `AttachmentService`**, never by a controller:

- `add_attachment` (the count check and insert happen in one session), `delete`, `count_for_entry`.
- `get_scoped(attachment_id, entry_id, author_id)`: the single authorization-and-lookup query, `WHERE id = :attachment_id AND entry_id = :entry_id AND author_id = :author_id`. It returns nothing for a wrong entry, a wrong owner, or a missing attachment, so there is exactly one place where "may this user touch this attachment?" is decided.
- `list_for_entry(entry_id, author_id)` and `list_for_entries(entry_ids, author_id)` (single `IN` query), ordered by `created_at`.
- `all_entry_ids()` helpers for the orphan sweep.

`JournalDb` is **unchanged**: it gets no attachment code at all.

#### Cleanup on entry deletion (FR-13, D10)

1. **Rows:** the database deletes them. `JournalDb.delete_entry` is untouched; `ON DELETE CASCADE` removes the entry's attachment rows in the same statement.
2. **Files:** after `delete_entry` commits, `JournalController` calls `entry_attachments.remove_entry_files(entry_id)`. The adapter logs and swallows any error (IDs only), so a file-removal problem can never fail the delete response.
3. **Backstop:** `AttachmentService.sweep_orphans()` runs at startup and removes any attachment directory whose entry no longer exists. It covers a crash between the commit and the file removal, and any failed removal. It catches and logs its own errors and never blocks startup (NFR-9). Between the delete and a sweep, orphan files are unreachable: their rows are gone, so no route can serve them.

### Service layer (`src/services/attachments.py`, new) (D11)

`AttachmentService` is the one place that knows how attachments work. It holds `AttachmentDb`, `AttachmentStorage`, the image functions, and a read-only `JournalDb` reference used for a single purpose: confirming at upload that the target entry exists and belongs to the caller.

| Method | Behavior |
|---|---|
| `add(user_id, entry_id, upload)` | Verify the entry is the caller's (via `journals_db.get_entry`) → check size (15 MB) and type → process the image off-thread → write files → insert row together with the count check (≤ 5). If the insert fails, the written files are removed, so a failed upload leaves nothing behind. |
| `list_for_entry(user_id, entry_id)` / `list_for_entries(user_id, entry_ids)` | Metadata for display. |
| `delete(user_id, entry_id, attachment_id)` | `get_scoped`, delete the row, then the files. |
| `open(user_id, entry_id, attachment_id, variant)` | `get_scoped`, then return the file path, its content type, and the filename to serve. |
| `remove_entry_files(entry_id)` | Remove an entry's directory (best effort). |
| `sweep_orphans()` | Startup backstop described above. |

**Domain exceptions** (defined in `src/exceptions.py` next to the existing `NoResultFound` mapping, and registered in `exception_handlers`), so the service never imports Litestar HTTP types and statuses stay consistent:

| Exception | HTTP |
|---|---|
| `AttachmentLimitExceeded` | `400` |
| `AttachmentTooLarge` | `413` |
| `UnsupportedAttachmentType` | `415` |
| `AttachmentProcessingError` | `422` |
| `StorageUnavailable` | `503` |
| missing or not-yours attachment/entry | `404` (existing `NoResultFound` handler, or `NotFoundException`) |

#### The `EntryAttachments` interface (journal side)

`JournalController` needs exactly two things from attachments, so it defines a small `Protocol` in `journal.py` and depends only on that:

```python
class EntryAttachments(Protocol):
    async def for_entries(
        self, user_id: UUID, entry_ids: list[UUID]
    ) -> AttachmentLookup: ...
    async def remove_entry_files(self, entry_id: UUID) -> None: ...
```

`AttachmentLookup` is `(by_entry: dict[UUID, list[AttachmentPublic]], available: bool)`. `GuardedEntryAttachments` (in `dependencies.py`) is the adapter built over `AttachmentService`. It implements that protocol and holds the failure policy: if the lookup raises, it logs the exception class and returns `by_entry={}, available=False`; `remove_entry_files` swallows and logs. The journal controller therefore contains no try/except and no attachment knowledge. It maps results into `JournalEntryPublic` with `to_public_entry`. The import boundary is testable: `journal.py` and `JournalDb` import no attachment modules.

### Image processing (`src/images.py`, new)

`process_image(data: bytes) -> ProcessedImage(thumb: bytes, display: bytes)`:

1. Open with Pillow; HEIC/HEIF support via `pillow-heif` (`register_heif_opener()` at import).
2. Apply EXIF orientation (`ImageOps.exif_transpose`) so photos aren't rotated after re-encoding. Animated inputs (GIF) use the first frame.
3. **Thumbnail:** cover-crop to a fixed **320×320** and save as WebP (~quality 80). Always the same dimensions regardless of source shape. (FR-15)
4. **Display copy:** fit within **2048 px** on the long edge, WebP (~quality 85). (FR-16)

Pillow re-encoding does not copy EXIF unless asked, so the derived files carry no metadata as a side effect. That's a convenience, not a requirement (stripping is out of scope), and the design relies on not passing `exif=` to `save`.

Decoding and encoding are CPU work, so `AttachmentService.add` runs `process_image` via `asyncio.to_thread` to keep the event loop free. A file Pillow can't decode raises `AttachmentProcessingError` (`422`). `images.py` stays a pure module of functions with no knowledge of HTTP, the database, or storage.

Type dispatch (content validation is out of scope): the declared content type or extension picks the image path or the PDF path; unsupported types raise `UnsupportedAttachmentType` (`415`). For images, "Pillow can decode it" is the only check we need to make thumbnails. PDFs are not inspected.

### Endpoints (`src/controllers/attachment.py`, new `AttachmentController`)

Path: `/journals/{entry_id:uuid}/attachments`. The controller is a thin HTTP adapter: it parses the request, calls `AttachmentService` with `request.user.id`, and shapes the response. It holds no rules and builds no paths. It does **not** use `_get_owned_entry` and does not depend on the journal controller.

**Authorization (FR-12).** Every route that takes an `attachment_id` goes through `AttachmentDb.get_scoped(attachment_id, entry_id, author_id)`, which matches the attachment ID **and** the entry ID in the URL **and** the caller as owner in one query, returning `404` otherwise. This closes a subtle hole: if a handler first checked that the URL's entry belongs to the caller and then loaded the attachment by ID alone, a user could read someone else's attachment through their own `entry_id`. It also takes the thumbnail route, the hot path with up to dozens of requests per day view, down to a single query with no entry lookup. Only `POST` needs to look at the entry (it must exist and be the caller's), which `AttachmentService.add` does through `JournalDb`.

| Method & path | Purpose | Notes |
|---|---|---|
| `POST /` | Upload one file (multipart, field `file`) | `201` with `AttachmentPublic`. Errors come from the service's domain exceptions: `404` entry not yours, `400` already 5 (FR-4), `413` over 15 MB (FR-5), `415` unsupported type, `422` undecodable, `503` storage unavailable. Per-handler `request_max_body_size` of ~16 MB (the app default of 10 MB is too low for FR-5, and a per-request limit means 5 files never need to fit in one body). |
| `GET /` | List an entry's attachments | Mostly for refresh after edits; day load uses the embedded list (D5). |
| `GET /{attachment_id}/thumbnail` | Thumbnail | Images only (`has_thumbnail`). 404 otherwise. |
| `GET /{attachment_id}/content` | Display copy (images) or the PDF | `Content-Disposition: inline`; `?download=true` switches to `attachment` with the original filename (properly escaped). |
| `DELETE /{attachment_id}` | Remove one | `204`. Deletes the row, then the files. (FR-8) |

The upload sequence (verify entry → limits → process off-thread → write files → insert with count check → remove files if the insert fails) lives in `AttachmentService.add`, described above.

Serving uses Litestar's `File` response with `Cache-Control: private, max-age=31536000, immutable`. Content under an attachment ID never changes, and `private` keeps shared proxies from caching authenticated content. Responses are sent with `X-Content-Type-Options: nosniff`.

The 5-file limit is checked in the same transaction as the insert. A concurrent pair of uploads could in theory both pass the check; the frontend uploads sequentially (D1), so this is accepted for a personal-use app.

### Logging (NFR-3)

- URLs use UUIDs only, so the existing path/method/status access log is safe.
- Application logs on failure include attachment ID (when it exists), kind, content type, size, and exception **class**. They never include the filename, file bytes, or Pillow's exception message text.
- `debug=True` returns tracebacks in responses rather than logs. That's a dev setting, unchanged.

### Request size limits

- Litestar: the per-handler limit above.
- **nginx (`frontend/nginx.conf`):** the default `client_max_body_size` is 1 MB, which would reject nearly every photo in the Docker setup. Add `client_max_body_size 16m;` to `location /api/`.

### Docker (`docker-compose.yml`) (NFR-6)

Add a bind mount next to the database one:

```yaml
- ./one_line_day_py/src/data/attachments:/app/one_line_day_py/src/data/attachments
```

The host directory should exist before first run, otherwise Docker creates it owned by root. The README setup steps get a `mkdir -p` line. `ATTACHMENTS_PATH` can be left unset in the container since the default location matches the mount. If you set it to a different path (for example a separate volume), change the mount target to match; the DB mount is unaffected.

### Dependencies

Add `pillow` and `pillow-heif` to `pyproject.toml`. Both ship prebuilt Linux wheels, so `backend.Dockerfile` needs no apt packages. Litestar handles multipart itself (to confirm during implementation).

## Frontend

### Types and API client

- `models.ts`: add `Attachment` (`id`, `entry_id`, `filename`, `kind`, `content_type`); `Journal` gains `attachments: Attachment[]` and `attachments_available: boolean`. Hand-kept in sync with the backend as usual.
- `attachments.ts` (new), same style as `journals.ts` (`credentials: "include"`, throw on `!response.ok`):
  - `uploadAttachment(entryId, file)` posts `FormData` (no manual `Content-Type`, so the browser sets the multipart boundary).
  - `deleteAttachment(entryId, attachmentId)`.
  - `thumbnailUrl(...)` and `contentUrl(...)` build `${API_BASE_URL}/journals/{entryId}/attachments/{id}/...` for `<img src>` / links.
  - `uploadAttachments(entryId, files)` uploads **sequentially** and returns `{ uploaded: Attachment[], failed: { file: File; error: string }[] }`. This is shared by create and edit flows so FR-9's behaviour is identical in both.
- Unlike `createJournalEntry`/`updateJournalEntry`, which send scalars as query params, files go in a multipart body. That is the one place this client departs from that pattern, intentionally.

### Components

- **`AttachmentPicker`** (new): used in the new-entry form and in `JournalBox` edit mode.
  - A visually-hidden-but-focusable `<input type="file" multiple>` behind a labelled button, which gives keyboard access and the file browser (FR-2, NFR-7). `accept` lists the supported types as a hint only.
  - A drop zone around the picker for drag and drop (FR-3). It is a progressive enhancement over the same input.
  - Client-side checks: total attachments ≤ 5 and each file ≤ 15 MB, with inline messages (FR-4, FR-5).
  - Shows the selected files with a remove button each (FR-7). Image previews use `URL.createObjectURL` (revoked on removal/unmount). Browsers can't render HEIC, so any preview that errors falls back to a file icon with the name.
  - Controlled component: parent owns the `File[]`, which keeps `JournalApp` and `JournalBox` tests simple.
- **`AttachmentThumb`** (new): a fixed-size box (same size for every attachment, FR-15) that shows a CSS skeleton placeholder until the `<img loading="lazy">` fires `onLoad`, then swaps in the image; `onError` shows an error state. PDFs render a static icon plus filename at the same size (FR-18). Image thumbnails are a button that opens the viewer; the accessible name is the filename (NFR-7). (FR-17)
- **`AttachmentFooter`** (new): the footer area of a `JournalBox`, a wrapping row of `AttachmentThumb`s. Rendered only when the entry has attachments, or shows a small "Attachments unavailable" note when the entry has `attachments_available: false`. (FR-14)
- **Viewer:** clicking an image thumbnail opens a native `<dialog>` with the display-size image (Esc closes, focus is managed by the platform) plus a Download link. PDFs open in a new tab from the thumb. (FR-16)

### Flows

**Create (`JournalApp.handleSubmit`)**
1. `createJournalEntry(date, message)` exactly as today.
2. If files are selected, `uploadAttachments(entry.id, files)`. The Send button stays disabled with "Sending..." throughout and the picker is disabled, which covers duplicate submission (FR-10). Per-file status (queued / uploading / done / failed) shows in the picker list.
3. The new entry is added to state with whichever attachments succeeded.
4. If some failed (FR-9), the entry stays, and an inline notice lists the failed filenames with **Retry** and **Dismiss**. Retry calls `uploadAttachments` again with only the failed files against the same entry. Because the entry already exists and each file is its own request, this retry adds very little code, so we implement the nice-to-have rather than falling back to whole-submission failure.

**Edit (`JournalBox`)**
- Edit mode shows existing attachments (each with a remove control) plus the picker for additions, with the 5-attachment cap counting both.
- On Save: update the entry (as today), delete removed attachments, upload added ones; failures use the same notice and retry component as create. The box's existing `error` pattern is reused for failures (NFR-4).

**Day load**
- `getJournals` already returns entries, now including `attachments`. Boxes render immediately with placeholders; each thumbnail loads on its own (NFR-2).

## Failure isolation (NFR-9)

The rule: **entries are the critical path; attachments are an enhancement that may fail without taking anything else down.**

**Frontend**
- `JournalApp`'s `isLoading` gate and `getJournals` call never wait on or depend on attachment data or images. Entries render as soon as they arrive.
- Each `AttachmentThumb` handles its own `onError` and shows an in-place error state (broken-image icon, filename, and a **Retry** button that re-requests the thumbnail). A slow image just stays a placeholder; nothing else waits on it.
- `AttachmentFooter` is wrapped in a small React error boundary. If anything in the attachments area throws while rendering, only that footer is replaced by "Attachments unavailable", and the entry text, Edit and Delete still work. This is the one place an error boundary is warranted; the rest of the app is unchanged.
- The viewer `<dialog>` shows an error message inside the dialog if the large image fails, and can always be closed.
- Upload failures follow FR-9: the entry is already saved before any file is sent, and failures only produce the retry notice. Attachment errors use the box's own `error` area or the notice, never the page-level `page-error` that applies to entries, so one failing attachment can't mask or block entry actions.
- Delete failures for a single attachment during edit are reported inline and don't abort saving the entry text.

**Backend**
- Entry endpoints reach attachments only through the `EntryAttachments` interface, whose adapter (`GuardedEntryAttachments`) never raises. They never read attachment files, so a missing, deleted, or corrupt file cannot break an entry request. File problems surface only on the thumbnail/content routes, as a `404` for that one request.
- Upload processing errors (undecodable file, encode failure, disk error) fail only that upload request, with nothing written (see Upload sequence). The entry is unaffected.
- If the attachments directory can't be created or written at startup, the app logs the error (path only) and still starts, so entries keep working. Uploads then return `503`, and reads of missing files `404`.
- Failure of the `pillow-heif` import (for example an unsupported platform) disables HEIC uploads with a `415`, not the whole app.
- Embedded attachment metadata is the one place an attachment problem could reach an entries request, so it is guarded: if the attachments query fails, `GuardedEntryAttachments` logs the exception class and returns no attachments with `available=False`. The entries still return `200`, with `attachments_available: false` on each. The frontend shows "Attachments unavailable" in the footer area instead of nothing. The guard lives in the adapter, so journal code has no try/except. File removal on entry delete is guarded the same way.

## Performance (NFR-1, NFR-2)

- Day load makes the same entry request as today, plus one `IN (...)` attachment query server-side. No additional frontend round trips before first render.
- Thumbnails are small (320×320 WebP, typically tens of KB) and cached `immutable`, so revisiting a day costs nothing after the first view.
- Thumbnail requests are issued by the browser as images enter the viewport, so a day with many years of entries doesn't block rendering.
- Heavy work (decode, resize, encode) happens only on upload, never on read.

Verification plan: measure a day with a worst case of 5 attachments on each of ~10 years of entries over the nginx path, and confirm the entries render and placeholders appear well inside 2 seconds.

## Testing (NFR-8)

**Backend (pytest, fresh tmp attachments directory per test via the existing fixture approach)**
- Upload an image and a PDF; thumbnail is exactly 320×320 for landscape, portrait and square inputs; PDF thumbnail request returns 404.
- Sixth upload returns 400; file over 15 MB returns 413; unsupported type 415; undecodable image 422; failed upload leaves no files or rows.
- Ownership: another user (the `bob` fixture) gets 404 on every attachment route; unauthenticated gets 401.
- **Cross-entry access:** requesting alice's attachment ID through bob's own `entry_id` returns 404 on thumbnail, content, and delete (guards the `get_scoped` query).
- Deleting an attachment removes its row and files. Deleting an entry cascades its rows at the database level (with `JournalDb` unchanged) and removes its directory; a failing file removal still returns `204`.
- The startup sweep removes directories whose entry is gone and leaves valid ones, and does not block startup if it errors.
- Foreign keys are enforced on new connections (the pragma is on), and an upload racing an entry delete fails cleanly with no files left behind.
- **Boundaries:** `journal.py` and `JournalDb` import no attachment modules (only the `EntryAttachments` protocol defined in `journal.py`); `AttachmentService` is unit-testable with a temp directory and no HTTP; each domain exception maps to its status code.
- With the attachments lookup forced to fail, entry endpoints return `200` with `attachments_available: false`.
- List/get/update/create entry responses include `attachments`.
- Failure isolation (NFR-9): deleting an attachment's files from disk (or pointing storage at a missing directory) leaves entry endpoints returning `200`; the thumbnail route returns `404` for that attachment only; the app starts when the attachments directory is unwritable and uploads return `503`.
- Settings: `ATTACHMENTS_PATH` override; the default is the sibling-of-default-DB location; overriding `DB_PATH` alone does not change the attachments location (and vice versa).
- HEIC upload test, if `pillow-heif` can encode a fixture in the test environment; otherwise a small checked-in sample file.

**Frontend (Vitest + RTL)**
- `AttachmentPicker`: file browse adds files, drag and drop adds files, over-limit and oversize are rejected with a message, remove works, keyboard operable.
- `AttachmentThumb`: placeholder until load, error state, PDF rendering, accessible name.
- `JournalApp` submit with mocked `fetch`: all succeed; some fail then Retry succeeds; Send is disabled while uploading.
- `JournalBox` edit: add and remove attachments, cap counts existing plus new.
- `attachments.ts`: sequential upload ordering and result shape.
- Failure isolation (NFR-9): entries still render when every thumbnail request fails; a throwing `AttachmentFooter` is contained by its error boundary and the entry's Edit/Delete still work; a thumbnail Retry works; the viewer shows an error and closes.

## Requirement traceability

| Requirement | Where addressed |
|---|---|
| FR-1, FR-8 | Create and edit flows; per-entry upload endpoint |
| FR-2, FR-3, FR-7 | `AttachmentPicker` |
| FR-4, FR-5 | Client checks in the picker; server count/size checks; 16 MB per-request limits (Litestar and nginx) |
| FR-6 | `process_image` conversion; PDFs stored as-is |
| FR-9, FR-10 | Sequential per-file uploads, failure notice with Retry, disabled form while sending |
| FR-11, FR-12 | `entry_id` foreign key; `author_id` + `entry_id` + `id` scoped query (`get_scoped`) on every attachment route |
| FR-13 | `ON DELETE CASCADE` for rows; `remove_entry_files` after the delete plus the startup orphan sweep for files |
| FR-14, FR-15, FR-16, FR-17, FR-18 | `AttachmentFooter`, `AttachmentThumb`, fixed 320×320 thumbnail, `<dialog>` viewer, display copy, PDF icon |
| NFR-1, NFR-2 | Embedded metadata, process-at-upload, lazy `<img>`, immutable caching |
| NFR-3 | UUID-only URLs; log field policy above |
| NFR-4 | Reuses session auth, the `State`/`Provide` wiring, the central exception-handler pattern, and the `box-error` / `page-error` patterns |
| NFR-5, NFR-6 | Independent `ATTACHMENTS_PATH` setting, sibling-of-default-DB default, compose bind mount |
| NFR-7 | Keyboard-operable picker, filename as accessible name |
| NFR-8 | Testing section |
| NFR-9 | Failure isolation section: entry endpoints never touch files; per-thumb error states; error boundary around the footer; startup tolerates an unusable attachments directory |

## Risks and things to watch

- **Foreign key enforcement is new behavior for the whole app.** The existing suite passes with it on (checked in a scratch copy), but existing foreign keys start being enforced, so previously tolerated bad data now raises integrity errors, and deleting a user who still has entries now fails. See "Foreign key enforcement".
- **Extra layer:** `AttachmentService` is the first service in a two-layer codebase. Keep it from becoming a template for everything; it earns its place by coordinating a database, a filesystem, and image processing.
- **Reverse proxy limits:** a forgotten body limit (nginx's 1 MB default is the likely one) shows up as unexplained upload failures only in Docker. Called out in the nginx and compose changes above.
- **First-run directory ownership** for the bind mount (see Docker).
- **No migration tooling:** fine for adding a table, but any later change to `attachments` columns will need a plan.
- **User deletion (TODO, tracked in the root `TODO.md`):** `UserController` deletes don't currently remove a user's entries, so they won't remove attachments either. Unchanged by this feature, but when user deletion is completed it must also delete the user's attachment rows and files. The denormalized `author_id` on `Attachment` makes that cleanup a single query.
- **Orphans:** a crash between file write and DB insert, or a failed directory removal, can leave unreferenced files. They are harmless (no row, so no route can serve them), and the startup sweep removes entry-level orphans. A crash between a file write and its insert inside a still-existing entry leaves an unreferenced file in that entry's directory until the entry is deleted; a finer-grained sweep could be added if it ever matters.
