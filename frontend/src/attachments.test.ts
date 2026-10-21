import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
    contentUrl,
    deleteAttachment,
    thumbnailUrl,
    uploadAttachment,
    uploadAttachments,
} from "./attachments";
import { API_BASE_URL } from "./config";
import type { Attachment } from "./models";

const BASE = `${API_BASE_URL}/journals/entry-1/attachments`;

function makeAttachment(overrides: Partial<Attachment> = {}): Attachment {
    return {
        id: "att-1",
        entry_id: "entry-1",
        filename: "photo.jpg",
        kind: "image",
        content_type: "image/webp",
        has_thumbnail: true,
        width: 640,
        height: 480,
        ...overrides,
    };
}

function jsonResponse(body: unknown, status = 201): Response {
    return new Response(JSON.stringify(body), {
        status,
        headers: { "Content-Type": "application/json" },
    });
}

function makeFile(name: string): File {
    return new File(["data"], name, { type: "image/jpeg" });
}

const fetchMock = vi.fn<typeof fetch>();

beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
    fetchMock.mockReset();
    vi.unstubAllGlobals();
});

describe("URL builders", () => {
    it("builds the thumbnail URL", () => {
        expect(thumbnailUrl("entry-1", "att-1")).toBe(`${BASE}/att-1/thumbnail`);
    });

    it("builds the inline content URL", () => {
        expect(contentUrl("entry-1", "att-1")).toBe(`${BASE}/att-1/content`);
    });

    it("builds the download content URL", () => {
        expect(contentUrl("entry-1", "att-1", true)).toBe(`${BASE}/att-1/content?download=true`);
    });
});

describe("uploadAttachment", () => {
    it("posts the file as FormData without a manual Content-Type", async () => {
        const attachment = makeAttachment();
        fetchMock.mockResolvedValue(jsonResponse(attachment));
        const file = makeFile("photo.jpg");

        await expect(uploadAttachment("entry-1", file)).resolves.toEqual(attachment);

        const [url, init] = fetchMock.mock.calls[0];
        expect(url).toBe(`${BASE}/`);
        expect(init?.method).toBe("POST");
        expect(init?.credentials).toBe("include");
        expect(init?.headers).toBeUndefined();
        expect(init?.body).toBeInstanceOf(FormData);
        expect((init?.body as FormData).get("file")).toBe(file);
    });

    it.each([
        [400, "maximum number of attachments"],
        [404, "no longer exists"],
        [413, "too large"],
        [415, "isn't supported"],
        [422, "couldn't be processed"],
        [503, "storage is unavailable"],
        [500, "Upload failed: 500"],
    ])("throws a readable error for status %i", async (status, message) => {
        fetchMock.mockResolvedValue(new Response(null, { status }));

        await expect(uploadAttachment("entry-1", makeFile("a.jpg"))).rejects.toThrow(message);
    });
});

describe("uploadAttachments", () => {
    it("uploads sequentially, in order", async () => {
        const order: string[] = [];
        let inFlight = 0;
        fetchMock.mockImplementation(async (_url, init) => {
            inFlight += 1;
            expect(inFlight).toBe(1);
            const file = (init?.body as FormData).get("file") as File;
            order.push(file.name);
            await new Promise((resolve) => setTimeout(resolve, 0));
            inFlight -= 1;
            return jsonResponse(makeAttachment({ id: file.name, filename: file.name }));
        });

        const result = await uploadAttachments("entry-1", [makeFile("a"), makeFile("b"), makeFile("c")]);

        expect(order).toEqual(["a", "b", "c"]);
        expect(result.uploaded.map((a) => a.id)).toEqual(["a", "b", "c"]);
        expect(result.failed).toEqual([]);
    });

    it("keeps going after a failure and reports which files failed", async () => {
        const a = makeFile("a");
        const b = makeFile("b");
        const c = makeFile("c");
        fetchMock
            .mockResolvedValueOnce(jsonResponse(makeAttachment({ id: "a" })))
            .mockResolvedValueOnce(new Response(null, { status: 413 }))
            .mockRejectedValueOnce(new TypeError("network down"));

        const result = await uploadAttachments("entry-1", [a, b, c]);

        expect(result.uploaded.map((x) => x.id)).toEqual(["a"]);
        expect(result.failed).toEqual([
            { file: b, error: "The file is too large." },
            { file: c, error: "network down" },
        ]);
    });

    it("reports each file's status as it goes", async () => {
        const a = makeFile("a");
        const b = makeFile("b");
        fetchMock
            .mockResolvedValueOnce(jsonResponse(makeAttachment({ id: "a" })))
            .mockResolvedValueOnce(new Response(null, { status: 415 }));
        const onStatus = vi.fn();

        await uploadAttachments("entry-1", [a, b], onStatus);

        expect(onStatus.mock.calls).toEqual([
            [a, "uploading"],
            [a, "done"],
            [b, "uploading"],
            [b, "failed"],
        ]);
    });

    it("returns empty results for no files without calling fetch", async () => {
        await expect(uploadAttachments("entry-1", [])).resolves.toEqual({ uploaded: [], failed: [] });
        expect(fetchMock).not.toHaveBeenCalled();
    });
});

describe("deleteAttachment", () => {
    it("sends a DELETE for the attachment", async () => {
        fetchMock.mockResolvedValue(new Response(null, { status: 204 }));

        await deleteAttachment("entry-1", "att-1");

        expect(fetchMock).toHaveBeenCalledWith(`${BASE}/att-1`, {
            method: "DELETE",
            credentials: "include",
        });
    });

    it("throws when the delete fails", async () => {
        fetchMock.mockResolvedValue(new Response(null, { status: 404 }));

        await expect(deleteAttachment("entry-1", "att-1")).rejects.toThrow("404");
    });
});
