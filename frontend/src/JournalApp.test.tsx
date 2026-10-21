import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { JournalApp } from "./JournalApp";
import { useAuth } from "./AuthContext";
import { getJournals, createJournalEntry, deleteJournalEntry, updateJournalEntry, DuplicateDateError } from "./journals";
import type { Attachment, Journal } from "./models";

vi.mock("./AuthContext", () => ({
    useAuth: vi.fn(),
}));

vi.mock("./journals", async (importOriginal) => ({
    DuplicateDateError: (await importOriginal<typeof import("./journals")>()).DuplicateDateError,
    getJournals: vi.fn(),
    createJournalEntry: vi.fn(),
    updateJournalEntry: vi.fn(),
    deleteJournalEntry: vi.fn(),
}));

const mockedUseAuth = vi.mocked(useAuth);
const mockedGetJournals = vi.mocked(getJournals);
const mockedCreateJournalEntry = vi.mocked(createJournalEntry);
const mockedDeleteJournalEntry = vi.mocked(deleteJournalEntry);
const mockedUpdateJournalEntry = vi.mocked(updateJournalEntry);

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

function jsonResponse(body: unknown, status = 201): Response {
    return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

function makeFile(name: string): File {
    return new File(["data"], name, { type: "image/jpeg" });
}

// Attachment uploads go through the real attachments client against this fetch.
const fetchMock = vi.fn<typeof fetch>();

function uploadedName(init: RequestInit | undefined): string {
    return ((init?.body as FormData).get("file") as File).name;
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

describe("JournalApp", () => {
    beforeEach(() => {
        mockedUseAuth.mockReturnValue({
            user: { id: "author-1", name: "Alice", email: "alice@example.com" },
            loading: false,
            login: vi.fn(),
            signup: vi.fn(),
            logout: vi.fn(),
        });
        mockedGetJournals.mockReset();
        mockedCreateJournalEntry.mockReset();
        mockedDeleteJournalEntry.mockReset();
        mockedUpdateJournalEntry.mockReset();
        vi.stubGlobal("fetch", fetchMock);
        URL.createObjectURL = vi.fn(() => "blob:preview");
        URL.revokeObjectURL = vi.fn();
    });

    afterEach(() => {
        fetchMock.mockReset();
        vi.unstubAllGlobals();
        vi.restoreAllMocks();
    });

    it("renders entries returned for the selected day", async () => {
        mockedGetJournals.mockResolvedValue([makeJournal({ message: "Had a great day" })]);
        render(<JournalApp />);

        expect(await screen.findByText("Had a great day")).toBeInTheDocument();
    });

    it("shows an error when loading entries fails", async () => {
        mockedGetJournals.mockRejectedValue(new Error("network down"));
        render(<JournalApp />);

        expect(await screen.findByText("Failed to load entries for this day.")).toBeInTheDocument();
    });

    it("adds a new entry to the list on successful submit", async () => {
        mockedGetJournals.mockResolvedValue([]);
        mockedCreateJournalEntry.mockResolvedValue(makeJournal({ id: "2", message: "New entry" }));
        const user = userEvent.setup();
        render(<JournalApp />);

        await waitFor(() => expect(mockedGetJournals).toHaveBeenCalled());

        await user.type(screen.getByPlaceholderText("Write a new entry for this day..."), "New entry");
        await user.click(screen.getByRole("button", { name: "Send" }));

        expect(await screen.findByText("New entry")).toBeInTheDocument();
        expect(mockedCreateJournalEntry).toHaveBeenCalledWith(expect.any(String), "New entry");
    });

    it("removes an entry from the list after a successful delete", async () => {
        mockedGetJournals.mockResolvedValue([makeJournal({ message: "Delete me" })]);
        mockedDeleteJournalEntry.mockResolvedValue(undefined);
        vi.spyOn(window, "confirm").mockReturnValue(true);
        const user = userEvent.setup();
        render(<JournalApp />);

        await screen.findByText("Delete me");
        await user.click(screen.getByRole("button", { name: "Delete" }));

        await waitFor(() => expect(screen.queryByText("Delete me")).not.toBeInTheDocument());
    });

    async function submitWithFiles(files: File[]) {
        const user = userEvent.setup();
        render(<JournalApp />);
        await waitFor(() => expect(mockedGetJournals).toHaveBeenCalled());

        await user.type(screen.getByPlaceholderText("Write a new entry for this day..."), "With photos");
        await user.upload(screen.getByLabelText("Attach files"), files);
        await user.click(screen.getByRole("button", { name: "Send" }));
        return user;
    }

    it("creates the entry, then uploads its files and shows them", async () => {
        mockedGetJournals.mockResolvedValue([]);
        mockedCreateJournalEntry.mockResolvedValue(makeJournal({ id: "2", message: "With photos" }));
        fetchMock.mockImplementation(async (_url, init) => {
            const name = uploadedName(init);
            return jsonResponse(makeAttachment({ id: name, entry_id: "2", filename: name }));
        });

        await submitWithFiles([makeFile("a.jpg"), makeFile("b.jpg")]);

        expect(await screen.findByRole("button", { name: "a.jpg" })).toBeInTheDocument();
        expect(screen.getByRole("button", { name: "b.jpg" })).toBeInTheDocument();
        expect(String(fetchMock.mock.calls[0][0])).toMatch(/\/journals\/2\/attachments\/$/);
        expect(fetchMock).toHaveBeenCalledTimes(2);
        expect(screen.queryByRole("alert")).not.toBeInTheDocument();
        // The picker is cleared for the next entry.
        expect(screen.queryByRole("button", { name: "Remove a.jpg" })).not.toBeInTheDocument();
    });

    it("reports a partial failure and Retry uploads only the failed file to the same entry", async () => {
        mockedGetJournals.mockResolvedValue([]);
        mockedCreateJournalEntry.mockResolvedValue(makeJournal({ id: "2", message: "With photos" }));
        let failB = true;
        fetchMock.mockImplementation(async (_url, init) => {
            const name = uploadedName(init);
            if (name === "b.jpg" && failB) {
                failB = false;
                return new Response(null, { status: 413 });
            }
            return jsonResponse(makeAttachment({ id: name, entry_id: "2", filename: name }));
        });

        const user = await submitWithFiles([makeFile("a.jpg"), makeFile("b.jpg")]);

        const notice = await screen.findByRole("alert");
        expect(notice).toHaveTextContent("b.jpg");
        expect(notice).toHaveTextContent("The file is too large.");
        expect(notice).not.toHaveTextContent("a.jpg");
        expect(screen.getByRole("button", { name: "a.jpg" })).toBeInTheDocument();

        await user.click(screen.getByRole("button", { name: "Retry" }));

        expect(await screen.findByRole("button", { name: "b.jpg" })).toBeInTheDocument();
        expect(screen.queryByRole("alert")).not.toBeInTheDocument();
        expect(fetchMock).toHaveBeenCalledTimes(3);
        expect(String(fetchMock.mock.calls[2][0])).toMatch(/\/journals\/2\/attachments\/$/);
        expect(uploadedName(fetchMock.mock.calls[2][1])).toBe("b.jpg");
    });

    it("keeps the entry when every upload fails", async () => {
        mockedGetJournals.mockResolvedValue([]);
        mockedCreateJournalEntry.mockResolvedValue(makeJournal({ id: "2", message: "With photos" }));
        fetchMock.mockResolvedValue(new Response(null, { status: 503 }));

        const user = await submitWithFiles([makeFile("a.jpg"), makeFile("b.jpg")]);

        const notice = await screen.findByRole("alert");
        expect(notice).toHaveTextContent("2 files couldn't be uploaded");
        expect(screen.getByText("With photos")).toBeInTheDocument();
        expect(screen.queryByText("Failed to save entry. Please try again.")).not.toBeInTheDocument();

        await user.click(screen.getByRole("button", { name: "Dismiss" }));
        expect(screen.queryByRole("alert")).not.toBeInTheDocument();
        expect(screen.getByText("With photos")).toBeInTheDocument();
    });

    it("disables the form while files upload", async () => {
        mockedGetJournals.mockResolvedValue([]);
        mockedCreateJournalEntry.mockResolvedValue(makeJournal({ id: "2", message: "With photos" }));
        let finishUpload: (response: Response) => void = () => {};
        fetchMock.mockImplementation(() => new Promise<Response>((resolve) => (finishUpload = resolve)));

        await submitWithFiles([makeFile("a.jpg")]);

        expect(await screen.findByRole("button", { name: "Sending..." })).toBeDisabled();
        expect(screen.getByLabelText("Attach files")).toBeDisabled();
        expect(screen.getByPlaceholderText("Write a new entry for this day...")).toBeDisabled();
        expect(screen.getByText("Uploading...")).toBeInTheDocument();

        finishUpload(jsonResponse(makeAttachment({ entry_id: "2", filename: "a.jpg" })));

        expect(await screen.findByRole("button", { name: "Send" })).toBeInTheDocument();
        expect(screen.getByLabelText("Attach files")).not.toBeDisabled();
    });

    it("doesn't upload anything when creating the entry fails", async () => {
        mockedGetJournals.mockResolvedValue([]);
        mockedCreateJournalEntry.mockRejectedValue(new Error("down"));

        await submitWithFiles([makeFile("a.jpg")]);

        expect(await screen.findByText("Failed to save entry. Please try again.")).toBeInTheDocument();
        expect(fetchMock).not.toHaveBeenCalled();
        // The selection is kept so the user can try again.
        expect(screen.getByRole("button", { name: "Remove a.jpg" })).toBeInTheDocument();
    });

    describe("date navigation", () => {
        async function renderOn(date: string) {
            mockedGetJournals.mockResolvedValue([]);
            const user = userEvent.setup();
            render(<JournalApp />);
            await screen.findByLabelText("Select Date:");
            fireEvent.change(screen.getByLabelText("Select Date:"), { target: { value: date } });
            await waitFor(() => expect(screen.getByLabelText("Select Date:")).toHaveValue(date));
            return user;
        }

        it("loads today's month and day on mount", async () => {
            mockedGetJournals.mockResolvedValue([]);
            render(<JournalApp />);

            const today = new Date();
            await waitFor(() =>
                expect(mockedGetJournals).toHaveBeenCalledWith(today.getMonth() + 1, today.getDate()),
            );
        });

        it("reloads for a date typed into the picker", async () => {
            await renderOn("2025-03-01");

            expect(mockedGetJournals).toHaveBeenLastCalledWith(3, 1);
            expect(screen.getByRole("heading", { name: "MARCH 1" })).toBeInTheDocument();
        });

        it.each([
            ["Previous day", "2025-02-28", "FEBRUARY 28", [2, 28]],
            ["Next day", "2025-03-02", "MARCH 2", [3, 2]],
            ["Previous year", "2024-03-01", "MARCH 1", [3, 1]],
            ["Next year", "2026-03-01", "MARCH 1", [3, 1]],
        ])("%s moves to %s", async (button, date, heading, args) => {
            const user = await renderOn("2025-03-01");

            await user.click(screen.getByRole("button", { name: button }));

            await waitFor(() => expect(screen.getByLabelText("Select Date:")).toHaveValue(date));
            expect(screen.getByRole("heading", { name: heading })).toBeInTheDocument();
            expect(mockedGetJournals).toHaveBeenLastCalledWith(...args);
        });

        it("clears a load error once a later load succeeds", async () => {
            mockedGetJournals
                .mockRejectedValueOnce(new Error("network down"))
                .mockResolvedValue([makeJournal({ message: "Back online" })]);
            const user = userEvent.setup();
            render(<JournalApp />);

            expect(await screen.findByText("Failed to load entries for this day.")).toBeInTheDocument();
            await user.click(screen.getByRole("button", { name: "Next day" }));

            expect(await screen.findByText("Back online")).toBeInTheDocument();
            expect(screen.queryByText("Failed to load entries for this day.")).not.toBeInTheDocument();
        });
    });

    it("explains when an entry already exists for the date", async () => {
        mockedGetJournals.mockResolvedValue([]);
        mockedCreateJournalEntry.mockRejectedValue(new DuplicateDateError());
        vi.spyOn(console, "error").mockImplementation(() => {});
        const user = userEvent.setup();
        render(<JournalApp />);
        await waitFor(() => expect(mockedGetJournals).toHaveBeenCalled());

        await user.type(screen.getByPlaceholderText("Write a new entry for this day..."), "Again");
        await user.click(screen.getByRole("button", { name: "Send" }));

        expect(await screen.findByText("You already have an entry for that date.")).toBeInTheDocument();
        // The draft is kept so it isn't lost.
        expect(screen.getByPlaceholderText("Write a new entry for this day...")).toHaveValue("Again");
    });

    it("ignores a blank entry", async () => {
        mockedGetJournals.mockResolvedValue([]);
        const user = userEvent.setup();
        render(<JournalApp />);
        await waitFor(() => expect(mockedGetJournals).toHaveBeenCalled());

        await user.type(screen.getByPlaceholderText("Write a new entry for this day..."), "   ");

        expect(screen.getByRole("button", { name: "Send" })).toBeDisabled();
        await user.keyboard("{Enter}");
        expect(mockedCreateJournalEntry).not.toHaveBeenCalled();
    });

    describe("editing an entry", () => {
        async function editEntry(changes: { date?: string; message?: string }) {
            const entry = makeJournal({ date: "2025-07-25", message: "Original" });
            mockedGetJournals.mockResolvedValue([entry]);
            mockedUpdateJournalEntry.mockResolvedValue({
                ...entry,
                date: changes.date ?? entry.date,
                message: changes.message ?? entry.message,
            });
            const user = userEvent.setup();
            const { container } = render(<JournalApp />);
            fireEvent.change(await screen.findByLabelText("Select Date:"), { target: { value: "2024-07-25" } });

            await user.click(await screen.findByRole("button", { name: "Edit" }));
            const form = container.querySelector("form.box") as HTMLFormElement;
            if (changes.date) {
                fireEvent.change(form.querySelector('input[type="date"]')!, { target: { value: changes.date } });
            }
            if (changes.message) {
                const text = screen.getByDisplayValue("Original");
                await user.clear(text);
                await user.type(text, changes.message);
            }
            await user.click(screen.getByRole("button", { name: "Save" }));
        }

        it("shows the saved text in place", async () => {
            await editEntry({ message: "Edited" });

            expect(await screen.findByText("Edited")).toBeInTheDocument();
            expect(mockedUpdateJournalEntry).toHaveBeenCalledWith("1", "2025-07-25", "Edited");
        });

        it("keeps an entry moved to another year of the same day", async () => {
            await editEntry({ date: "2023-07-25" });

            expect(await screen.findByRole("heading", { name: "2023" })).toBeInTheDocument();
        });

        it("drops an entry moved to a different day from this page", async () => {
            await editEntry({ date: "2025-07-26" });

            await waitFor(() => expect(screen.queryByText("Original")).not.toBeInTheDocument());
            expect(mockedUpdateJournalEntry).toHaveBeenCalledWith("1", "2025-07-26", "Original");
        });
    });

    it("logs out from the header button", async () => {
        const logout = vi.fn().mockResolvedValue(undefined);
        mockedUseAuth.mockReturnValue({ ...mockedUseAuth(), logout });
        mockedGetJournals.mockResolvedValue([]);
        const user = userEvent.setup();
        render(<JournalApp />);

        await user.click(await screen.findByRole("button", { name: "Log Out" }));

        expect(logout).toHaveBeenCalled();
    });

    describe("failure isolation", () => {
        it("renders entries and keeps Edit/Delete working when every thumbnail fails", async () => {
            mockedGetJournals.mockResolvedValue([
                makeJournal({
                    id: "1",
                    message: "First year",
                    attachments: [makeAttachment({ id: "a", filename: "a.jpg" })],
                }),
                makeJournal({
                    id: "2",
                    date: "2024-07-25",
                    message: "Second year",
                    attachments: [
                        makeAttachment({ id: "b", entry_id: "2", filename: "b.jpg" }),
                        makeAttachment({ id: "c", entry_id: "2", filename: "c.jpg" }),
                    ],
                }),
            ]);
            mockedDeleteJournalEntry.mockResolvedValue(undefined);
            vi.spyOn(window, "confirm").mockReturnValue(true);
            const user = userEvent.setup();
            render(<JournalApp />);

            await screen.findByText("First year");
            for (const img of screen.getAllByRole("img")) fireEvent.error(img);

            expect(screen.getAllByRole("button", { name: /^Retry loading/ })).toHaveLength(3);
            expect(screen.getByText("Second year")).toBeInTheDocument();

            await user.click(screen.getAllByRole("button", { name: "Delete" })[0]);
            await waitFor(() => expect(screen.queryByText("First year")).not.toBeInTheDocument());

            await user.click(screen.getByRole("button", { name: "Edit" }));
            expect(screen.getByDisplayValue("Second year")).toBeInTheDocument();
        });

        it("renders entries with a note when attachments are unavailable", async () => {
            mockedGetJournals.mockResolvedValue([
                makeJournal({ message: "Still here", attachments: [], attachments_available: false }),
            ]);
            const user = userEvent.setup();
            render(<JournalApp />);

            expect(await screen.findByText("Still here")).toBeInTheDocument();
            expect(screen.getByText("Attachments unavailable")).toBeInTheDocument();

            await user.click(screen.getByRole("button", { name: "Edit" }));
            expect(screen.getByDisplayValue("Still here")).toBeInTheDocument();
        });
    });
});
