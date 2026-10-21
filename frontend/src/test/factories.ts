// Shared test data. Defaults describe one consistent world: Alice's journal entry
// "1" with one image attachment "att-1" on it. Override fields per test.
import type { User } from "../auth/auth";
import type { Attachment, Journal } from "../shared/models";

export function makeUser(overrides: Partial<User> = {}): User {
    return { id: "author-1", name: "Alice", email: "alice@example.com", ...overrides };
}

export function makeJournal(overrides: Partial<Journal> = {}): Journal {
    return {
        id: "1",
        author_id: "author-1",
        date: "2025-07-25",
        message: "Had a great day",
        attachments: [],
        attachments_available: true,
        ...overrides,
    };
}

export function makeAttachment(overrides: Partial<Attachment> = {}): Attachment {
    return {
        id: "att-1",
        entry_id: "1",
        filename: "beach.jpg",
        kind: "image",
        content_type: "image/webp",
        has_thumbnail: true,
        width: 2048,
        height: 1536,
        ...overrides,
    };
}

/** A File; `size` overrides the reported size without allocating that many bytes. */
export function makeFile(name: string, type = "image/jpeg", size?: number): File {
    const file = new File(["data"], name, { type });
    if (size !== undefined) Object.defineProperty(file, "size", { value: size });
    return file;
}

export function jsonResponse(body: unknown, status = 200): Response {
    return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}
