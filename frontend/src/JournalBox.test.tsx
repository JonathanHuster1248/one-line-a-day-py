import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { JournalBox } from "./JournalBox";
import { AttachmentThumb } from "./AttachmentThumb";
import type { Attachment, Journal } from "./models";

vi.mock("./AttachmentThumb", async (importOriginal) => {
    const actual = await importOriginal<typeof import("./AttachmentThumb")>();
    return { AttachmentThumb: vi.fn(actual.AttachmentThumb) };
});

const mockedThumb = vi.mocked(AttachmentThumb);

function makeAttachment(overrides: Partial<Attachment> = {}): Attachment {
    return {
        id: "att-1",
        entry_id: "1",
        filename: "beach.jpg",
        kind: "image",
        content_type: "image/webp",
        has_thumbnail: true,
        width: 640,
        height: 480,
        ...overrides,
    };
}

function makeJournal(overrides: Partial<Journal> = {}): Journal {
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

function jsonResponse(body: unknown, status = 201): Response {
    return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

function makeFile(name: string): File {
    return new File(["data"], name, { type: "image/jpeg" });
}

const fetchMock = vi.fn<typeof fetch>();

describe("JournalBox", () => {
    const onUpdate = vi.fn<(journal: Journal, date: string, message: string) => Promise<void>>();
    const onDelete = vi.fn<(journal: Journal) => Promise<void>>();
    const onAttachmentsChange = vi.fn<(journalId: string, attachments: Attachment[]) => void>();

    function renderBox(journal: Journal) {
        const user = userEvent.setup();
        render(
            <JournalBox
                journal={journal}
                onUpdate={onUpdate}
                onDelete={onDelete}
                onAttachmentsChange={onAttachmentsChange}
            />,
        );
        return user;
    }

    beforeEach(() => {
        onUpdate.mockReset().mockResolvedValue(undefined);
        onDelete.mockReset().mockResolvedValue(undefined);
        onAttachmentsChange.mockReset();
        vi.stubGlobal("fetch", fetchMock);
        URL.createObjectURL = vi.fn(() => "blob:preview");
        URL.revokeObjectURL = vi.fn();
    });

    afterEach(() => {
        fetchMock.mockReset();
        mockedThumb.mockClear();
        vi.unstubAllGlobals();
        vi.restoreAllMocks();
    });

    it("shows the entry's attachments in view mode", () => {
        renderBox(makeJournal({ attachments: [makeAttachment()] }));
        expect(screen.getByRole("button", { name: "beach.jpg" })).toBeInTheDocument();
    });

    it("uploads added files after saving the text", async () => {
        const existing = makeAttachment();
        const added = makeAttachment({ id: "att-2", filename: "dog.jpg" });
        fetchMock.mockResolvedValue(jsonResponse(added));
        const user = renderBox(makeJournal({ attachments: [existing] }));

        await user.click(screen.getByRole("button", { name: "Edit" }));
        await user.upload(screen.getByLabelText("Attach files"), makeFile("dog.jpg"));
        await user.click(screen.getByRole("button", { name: "Save" }));

        await waitFor(() => expect(onAttachmentsChange).toHaveBeenCalledWith("1", [existing, added]));
        expect(onUpdate).toHaveBeenCalledWith(expect.objectContaining({ id: "1" }), "2025-07-25", "Had a great day");
        expect(fetchMock).toHaveBeenCalledTimes(1);
        expect(fetchMock.mock.calls[0][1]?.method).toBe("POST");
        // Back in view mode.
        expect(screen.getByRole("button", { name: "Edit" })).toBeInTheDocument();
    });

    it("deletes removed attachments on save", async () => {
        const keep = makeAttachment({ id: "keep", filename: "keep.jpg" });
        const drop = makeAttachment({ id: "drop", filename: "drop.jpg" });
        fetchMock.mockResolvedValue(new Response(null, { status: 204 }));
        const user = renderBox(makeJournal({ attachments: [keep, drop] }));

        await user.click(screen.getByRole("button", { name: "Edit" }));
        await user.click(screen.getByRole("button", { name: "Remove drop.jpg" }));
        expect(screen.queryByText("drop.jpg")).not.toBeInTheDocument();
        await user.click(screen.getByRole("button", { name: "Save" }));

        await waitFor(() => expect(onAttachmentsChange).toHaveBeenCalledWith("1", [keep]));
        expect(String(fetchMock.mock.calls[0][0])).toMatch(/\/journals\/1\/attachments\/drop$/);
        expect(fetchMock.mock.calls[0][1]?.method).toBe("DELETE");
    });

    it("doesn't touch attachments when Cancel is pressed", async () => {
        const user = renderBox(makeJournal({ attachments: [makeAttachment()] }));

        await user.click(screen.getByRole("button", { name: "Edit" }));
        await user.click(screen.getByRole("button", { name: "Remove beach.jpg" }));
        await user.click(screen.getByRole("button", { name: "Cancel" }));
        await user.click(screen.getByRole("button", { name: "Edit" }));

        expect(screen.getByRole("button", { name: "Remove beach.jpg" })).toBeInTheDocument();
        expect(fetchMock).not.toHaveBeenCalled();
    });

    it("counts existing attachments toward the cap", async () => {
        const attachments = [1, 2, 3, 4].map((n) => makeAttachment({ id: `a${n}`, filename: `${n}.jpg` }));
        const user = renderBox(makeJournal({ attachments }));

        await user.click(screen.getByRole("button", { name: "Edit" }));
        await user.upload(screen.getByLabelText("Attach files"), [makeFile("5.jpg"), makeFile("6.jpg")]);

        expect(screen.getByRole("alert")).toHaveTextContent("An entry can have at most 5 attachments.");
        expect(screen.getByText("5.jpg")).toBeInTheDocument();
        expect(screen.queryByText("6.jpg")).not.toBeInTheDocument();
        expect(screen.getByLabelText("Attach files")).toBeDisabled();

        // Removing an existing attachment frees a slot.
        await user.click(screen.getByRole("button", { name: "Remove 1.jpg" }));
        expect(screen.getByLabelText("Attach files")).not.toBeDisabled();
    });

    it("saves the text even when an upload fails, and reports the failure", async () => {
        fetchMock.mockResolvedValue(new Response(null, { status: 415 }));
        const user = renderBox(makeJournal());

        await user.click(screen.getByRole("button", { name: "Edit" }));
        await user.upload(screen.getByLabelText("Attach files"), makeFile("notes.jpg"));
        await user.click(screen.getByRole("button", { name: "Save" }));

        const notice = await screen.findByRole("alert");
        expect(notice).toHaveTextContent("notes.jpg");
        expect(notice).toHaveTextContent("This file type isn't supported.");
        expect(onUpdate).toHaveBeenCalled();
        expect(onAttachmentsChange).not.toHaveBeenCalled();
        expect(screen.getByRole("button", { name: "Edit" })).toBeInTheDocument();
    });

    it("retries failed uploads from the notice", async () => {
        const added = makeAttachment({ id: "att-2", filename: "dog.jpg" });
        fetchMock.mockResolvedValueOnce(new Response(null, { status: 503 })).mockResolvedValueOnce(jsonResponse(added));
        const user = renderBox(makeJournal());

        await user.click(screen.getByRole("button", { name: "Edit" }));
        await user.upload(screen.getByLabelText("Attach files"), makeFile("dog.jpg"));
        await user.click(screen.getByRole("button", { name: "Save" }));
        await user.click(await screen.findByRole("button", { name: "Retry" }));

        await waitFor(() => expect(onAttachmentsChange).toHaveBeenCalledWith("1", [added]));
        expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    });

    it("saves the text even when removing an attachment fails, and says which", async () => {
        const attachment = makeAttachment();
        fetchMock.mockResolvedValue(new Response(null, { status: 500 }));
        vi.spyOn(console, "error").mockImplementation(() => {});
        const user = renderBox(makeJournal({ attachments: [attachment] }));

        await user.click(screen.getByRole("button", { name: "Edit" }));
        await user.click(screen.getByRole("button", { name: "Remove beach.jpg" }));
        await user.click(screen.getByRole("button", { name: "Save" }));

        expect(await screen.findByText("Couldn't remove beach.jpg. Please try again.")).toBeInTheDocument();
        expect(onUpdate).toHaveBeenCalled();
        expect(onAttachmentsChange).toHaveBeenCalledWith("1", [attachment]);
        expect(screen.getByRole("button", { name: "Edit" })).toBeInTheDocument();
    });

    it("doesn't touch attachments when the text save fails", async () => {
        onUpdate.mockRejectedValue(new Error("down"));
        vi.spyOn(console, "error").mockImplementation(() => {});
        const user = renderBox(makeJournal({ attachments: [makeAttachment()] }));

        await user.click(screen.getByRole("button", { name: "Edit" }));
        await user.click(screen.getByRole("button", { name: "Remove beach.jpg" }));
        await user.upload(screen.getByLabelText("Attach files"), makeFile("dog.jpg"));
        await user.click(screen.getByRole("button", { name: "Save" }));

        expect(await screen.findByText("Failed to save changes. Please try again.")).toBeInTheDocument();
        expect(fetchMock).not.toHaveBeenCalled();
        // Still editing, with the pending changes intact.
        expect(screen.getByRole("button", { name: "Remove dog.jpg" })).toBeInTheDocument();
    });

    it("keeps Edit and Delete working when the attachments area throws", async () => {
        vi.spyOn(console, "error").mockImplementation(() => {});
        vi.spyOn(window, "confirm").mockReturnValue(true);
        mockedThumb.mockImplementation(() => {
            throw new Error("boom");
        });
        const user = renderBox(makeJournal({ attachments: [makeAttachment()] }));

        expect(screen.getByText("Attachments unavailable")).toBeInTheDocument();
        expect(screen.getByText("Had a great day")).toBeInTheDocument();

        await user.click(screen.getByRole("button", { name: "Delete" }));
        expect(onDelete).toHaveBeenCalled();

        await user.click(screen.getByRole("button", { name: "Edit" }));
        expect(screen.getByDisplayValue("Had a great day")).toBeInTheDocument();
    });
});
